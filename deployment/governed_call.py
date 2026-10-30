"""Contextual callbacks through the existing owner approval and VoiceOps contracts.

No SIP credentials, caller-supplied destination or device mutation is supported.
The only executor is the existing VoiceOps service, which consumes HA owner proof.
"""
import asyncio,json,os,secrets,shlex,sys,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
from deployment.live_infrastructure import digest,mongo_read

UNREACHABLE={'offline','unavailable','not_reachable','disconnected'}

def spoken_report(snapshot):
    site={'casa':'Casa Rafael','bellini':'Bellini'}[snapshot['site']]
    category={'network':'la red','cameras':'las cámaras','servers':'los servidores','energy':'la energía'}[snapshot['category']]
    signals=snapshot['signals'];bad=[x for x in signals if x.get('state') in UNREACHABLE]
    attention=[x for x in signals if x.get('state')=='checks_need_attention']
    at=snapshot.get('source_observed_at') or snapshot['collected_at']
    clock=datetime.fromisoformat(at).astimezone(timezone(timedelta(hours=-5))).strftime('%H:%M')
    text=f'Te llamo por la revisión de {category} en {site}. Lectura de las {clock}, hora de Ecuador. '
    if bad:
        text+=f'El monitor no alcanza {len(bad)} señales: '+', '.join(x['label'] for x in bad[:3])+'. Esto no confirma una avería física. '
    elif attention:text+=f'{len(attention)} servidores tienen comprobaciones de servicios que requieren revisión; no significa que estén apagados. '
    elif snapshot['category']=='energy':
        values={x['ref']:x['state'] for x in signals}
        if values.get('outage_active') in (True,'on','true') or values.get('battery_mode') in (True,'on','true'):text+='La fuente reporta operación con batería o corte de red. '
        elif values.get('outage_active') in (False,'off','false') and values.get('battery_mode') in (False,'off','false'):text+='La fuente no reporta un corte activo en esta lectura. '
        else:text+='La fuente no confirma el estado de corte o batería en esta lectura. '
        if type(values.get('battery_capacity_percent')) in (int,float):text+=f'Batería al {values["battery_capacity_percent"]} por ciento. '
    else:text+=f'Revisé {len(signals)} señales disponibles; no aparecen inaccesibles en esta lectura. '
    if snapshot.get('freshness')=='STALE':text+='Atención: la muestra está desactualizada. '
    elif not snapshot.get('source_observed_at'):text+='La hora indica la consulta; algunos estados pueden ser anteriores. '
    return (text+'Esta llamada solo informa; no autoriza acciones sobre equipos.')[:600]

def helper_main():
    """Run in canonical private Python; read only named existing config keys."""
    allowed={'AMBIENT_GUARDIAN_MOBILE_OWNER_ID','VOICEOPS_RUNTIME_URL','VOICEOPS_RUNTIME_TOKEN'}
    config=Path.home()/'.config/systemd/user/inneros-ambient-guardian-demo.service.d'
    for name in ('real-home.conf','50-mobile-approval.conf'):
        for line in (config/name).read_text().splitlines():
            if line.startswith('Environment='):
                for assignment in shlex.split(line.partition('=')[2]):
                    key,sep,value=assignment.partition('=')
                    if sep and key in allowed:os.environ[key]=value
    from ambient_guardian import mobile_approval
    from ambient_guardian.voiceops import LocalVoiceOpsRuntimeClient
    operation=sys.argv[1];payload=json.loads(sys.stdin.read() or '{}')
    if operation=='probe':
        client=LocalVoiceOpsRuntimeClient(os.getenv('VOICEOPS_RUNTIME_URL','http://127.0.0.1:8796'),bearer_token=os.getenv('VOICEOPS_RUNTIME_TOKEN',''))
        status=client.status()
        result={'owner_configured':bool(os.getenv('AMBIENT_GUARDIAN_MOBILE_OWNER_ID')),'contract_version':status.get('contract_version'),'state':status.get('state'),'owner_mobile_callback_ready':bool((status.get('owner_mobile') or {}).get('callback_ready')),'writes':False}
    elif operation=='prepare':result=mobile_approval.request(payload)
    elif operation=='finish':result=mobile_approval.finish(payload)
    elif operation=='execute':
        # VoiceOps independently checks target alias, owner identity, expiry and
        # single-use HA proof before placing the call. Never consume proof here.
        client=LocalVoiceOpsRuntimeClient(os.getenv('VOICEOPS_RUNTIME_URL','http://127.0.0.1:8796'),bearer_token=os.getenv('VOICEOPS_RUNTIME_TOKEN',''))
        result=dict(client.request_owner_callback(correlation_id=payload['action_id'],reason=payload['reason'],requested_by='guardian-real-infrastructure',target_alias='voiceops.owner.mobile',approval_id=payload['approval_task_id'],approval_channel='home_assistant_companion'))
    else:raise ValueError('unsupported operation')
    print(json.dumps(result,default=str))

async def run_helper(operation,payload):
    if operation not in ('probe','prepare','finish','execute'):raise ValueError('unsupported operation')
    core=Path.home()/'inneros/inneros_core'
    env={**os.environ,'PYTHONPATH':os.pathsep.join((str(Path(__file__).resolve().parents[1]),str(core/'workspaces/inneros-ambient-guardian-amazon-2026/src'),str(core/'platform'))),'PYTHONDONTWRITEBYTECODE':'1'}
    process=await asyncio.create_subprocess_exec(str(core/'platform/venv/bin/python'),'-m','deployment.governed_call',operation,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,env=env,cwd=str(core/'platform'))
    try:out,_=await asyncio.wait_for(process.communicate(json.dumps(payload).encode()),300 if operation=='execute' else 15)
    except asyncio.TimeoutError:
        process.kill();await process.wait();raise RuntimeError('call_operation_unverified_no_retry')
    if process.returncode:raise RuntimeError('existing_call_contract_unavailable')
    return json.loads(out.decode().splitlines()[-1])

async def prepare_call(store,request_id,snapshot):
    observation=json.loads(snapshot['body']);reason=spoken_report(observation)
    action_id='guardian-'+secrets.token_hex(12)
    expires=datetime.now(timezone.utc)+timedelta(minutes=10)
    binding={'action_id':action_id,'snapshot_id':snapshot['id'],'snapshot_digest':snapshot['digest'],'reason':reason,'target_alias':'voiceops.owner.mobile','expires_at':expires.isoformat()}
    action_digest=digest(binding)
    payload={**binding,'action_digest':action_digest,'action_type':'voiceops_owner_mobile_callback','target_label':('Informe '+observation['site_label']+': '+reason.partition('. ')[2])[:120]}
    # Persist the exact immutable narrative before sending any notification.
    store.save_call(request_id,'PREPARING_CONTEXT',{**binding,'action_digest':action_digest})
    result=await run_helper('prepare',payload)
    if not result.get('ok') or result.get('channel')!='home_assistant_companion':raise RuntimeError('existing_owner_gate_not_verified')
    stored={**binding,'action_digest':action_digest,'approval_task_id':result['task_id'],'approval_channel':'home_assistant_companion'}
    store.save_call(request_id,'AWAITING_CONTEXT_APPROVAL',stored)
    return reason

async def dispatch_one(store,row):
    payload=json.loads(row['result'])
    if time.time()>=row['expires']:
        store.save_call(row['id'],'EXPIRED',payload);return
    authority=await mongo_read('ambient_guardian_mobile_approvals',{'task_id':payload['approval_task_id'],'action_id':row['action_id'],'action_digest':payload['action_digest']},{'_id':0,'status':1})
    status=authority.get('status')
    if status in ('cancelled','expired','failed','completed'):
        store.save_call(row['id'],status.upper(),payload);return
    if status!='approved':return
    if time.time()>=row['expires']:return
    # Durable local claim precedes network dispatch. Interrupted/ambiguous
    # dispatches are never retried, including after this API restarts.
    with store.db() as db:
        if db.execute("UPDATE live_calls SET status='DISPATCHING_CONTEXT' WHERE id=? AND status='AWAITING_CONTEXT_APPROVAL'",(row['id'],)).rowcount!=1:return
    try:
        receipt=await run_helper('execute',payload)
        result=receipt.get('result') or {}
        verified=receipt.get('contract_version')=='voiceops.fieldops.telephony.v1' and result.get('status')=='dispatched' and bool(result.get('call_id'))
        evidence={'executed':verified,'verified':verified,'verification_scope':'existing_voiceops_dispatch_receipt','physical_device_action_authorized':False}
        terminal='completed' if verified else 'failed'
        await run_helper('finish',{'task_id':payload['approval_task_id'],'status':terminal,'evidence':evidence})
        store.save_call(row['id'],terminal.upper(),{**payload,'dispatch_evidence':evidence})
    except Exception:
        store.save_call(row['id'],'DISPATCH_UNVERIFIED_NO_RETRY',payload)

async def worker(store):
    while True:
        try:
            with store.db() as db:rows=[dict(row) for row in db.execute("SELECT * FROM live_calls WHERE status='AWAITING_CONTEXT_APPROVAL'")]
            for row in rows:await dispatch_one(store,row)
        except Exception:pass
        await asyncio.sleep(3)

if __name__=='__main__':helper_main()
