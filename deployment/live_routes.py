"""Curated real observations and existing Companion-governed owner callbacks."""
import asyncio,json,os,secrets,time
from pathlib import Path
from functools import lru_cache
from contextlib import asynccontextmanager
from fastapi import APIRouter,Request
from fastapi.responses import JSONResponse,Response
import httpx
from deployment.live_infrastructure import LiveInfrastructure,CATALOG,now,digest
from deployment.governed_call import prepare_call,worker
@asynccontextmanager
async def context_call_lifespan(app):
    task=asyncio.create_task(worker(store()))
    try:yield
    finally:
        task.cancel()
        try:await task
        except asyncio.CancelledError:pass
router=APIRouter(prefix='/api/guardian/live',lifespan=context_call_lifespan)
STATE=Path.home()/'.local/state/inneros-nebius-demo'
def state_path(name):return Path(os.environ.get('GUARDIAN_LIVE_STATE_DIR',str(STATE)))/name
@lru_cache(maxsize=4)
def _store(path):return LiveInfrastructure(path)
def store():return _store(str(state_path('live.sqlite3')))
def sid(request):
    value=request.cookies.get('guardian_session','')
    return value if len(value)==48 and all(c in '0123456789abcdef' for c in value) else ''
def owner_token():
    for line in (Path.home()/'.config/ambient-guardian/skill-bridge.env').read_text().splitlines():
        key,sep,value=line.partition('=')
        if sep and key.strip()=='AMBIENT_GUARDIAN_SKILL_BRIDGE_TOKEN':return value.strip().strip(chr(34)).strip(chr(39))
    raise RuntimeError('existing_call_credential_unavailable')
def budget():
    grant=state_path('real-infrastructure-one-shot-grant.json');consumed=state_path('real-infrastructure-one-shot.consumed')
    try:
        data=json.loads(grant.read_text())
        authorized=data.get('authorized') is True and data.get('max_output_tokens')==2048 and data.get('expires_at_epoch',0)>time.time()
    except (OSError,ValueError):authorized=False
    return authorized and not consumed.exists()
@router.get('/catalog')
def catalog():return {'ok':True,'sites':CATALOG,'mode':'REAL_READ_ONLY','new_model_request_available':budget(),'call_policy':'EXISTING_HOME_ASSISTANT_OWNER_APPROVAL','physical_device_execution_enabled':False}
@router.get('/readings/{site}/{category}')
async def readings(site:str,category:str,request:Request):
    try:result=await store().observe(site,category)
    except ValueError as e:return JSONResponse({'detail':str(e)},status_code=422)
    except Exception:return JSONResponse({'detail':'existing_source_unavailable_no_simulated_replacement','site':site,'category':category},status_code=503)
    response=JSONResponse(result)
    if not sid(request):response.set_cookie('guardian_session',secrets.token_hex(24),httponly=True,secure=request.url.scheme=='https',samesite='strict',max_age=1800)
    return response
@router.post('/call-request')
async def call_request(request:Request):
    body=await request.json()
    if body.get('confirm_owner_call_request') is not True or not sid(request):return JSONResponse({'detail':'explicit_call_request_and_session_required'},status_code=403)
    if set(body)-{'snapshot_id','confirm_owner_call_request'}:return JSONResponse({'detail':'destinations_and_extra_parameters_not_allowed'},status_code=422)
    try:request_id,snapshot=store().reserve_call(str(body.get('snapshot_id','')),sid(request))
    except ValueError as e:return JSONResponse({'detail':str(e)},status_code=429 if 'cooldown' in str(e) else 409)
    try:
        reason=await prepare_call(store(),request_id,snapshot)
        with store().db() as db:expiry=db.execute('SELECT expires FROM live_calls WHERE id=?',(request_id,)).fetchone()[0]
        return {'ok':True,'request_id':request_id,'status':'AWAITING_OWNER_APPROVAL','expires_at_epoch':expiry,'spoken_report':reason,'snapshot_id':snapshot['id'],'snapshot_digest':snapshot['digest'],'approval_url':'https://ha.pcdoctor.ai/inneros-approvals/pendientes','physical_device_action_authorized':False}
    except Exception:
        store().save_call(request_id,'PREPARATION_UNVERIFIED',{})
        return JSONResponse({'detail':'call_preparation_unverified_check_existing_owner_inbox_do_not_retry','request_id':request_id},status_code=502)
@router.get('/calls/{request_id}')
async def call_status(request_id:str,request:Request):
    try:return await store().call_status(request_id,sid(request))
    except ValueError as e:return JSONResponse({'detail':str(e)},status_code=404)
def pdf_response(content,name):
    return Response(content,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="'+name+'"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
@router.get('/reports/snapshots/{snapshot_id}.pdf')
async def export_snapshot(snapshot_id:str):
    from deployment.pdf_report import snapshot_pdf
    try:row=store().get(snapshot_id)
    except ValueError:return JSONResponse({'detail':'snapshot_not_found'},status_code=404)
    data=json.loads(row['body'])
    return pdf_response(await asyncio.to_thread(snapshot_pdf,data),'guardian-'+data['site']+'-'+data['category']+'.pdf')
@router.get('/reports/analysis.pdf')
async def export_analysis():
    from deployment.pdf_report import analysis_pdf
    path=state_path('real-infrastructure-nemotron.json')
    if not path.exists():return JSONResponse({'detail':'no_recorded_model_analysis'},status_code=404)
    return pdf_response(await asyncio.to_thread(analysis_pdf,json.loads(path.read_text())),'guardian-nemotron-evidence.pdf')
@router.get('/reports/calls/{request_id}.pdf')
async def export_call(request_id:str,request:Request):
    from deployment.pdf_report import call_pdf
    try:data=await store().call_status(request_id,sid(request))
    except ValueError:return JSONResponse({'detail':'call_request_not_found'},status_code=404)
    return pdf_response(await asyncio.to_thread(call_pdf,data),'guardian-owner-call-audit.pdf')
@router.get('/reports/overview.pdf')
async def export_overview():
    from deployment.pdf_report import overview_pdf
    return pdf_response(await asyncio.to_thread(overview_pdf),'guardian-evaluation-guide.pdf')
@router.get('/analysis')
def analysis():
    path=state_path('real-infrastructure-nemotron.json')
    if not path.exists():return {'ok':True,'status':'NOT_REQUESTED','one_shot_available':budget()}
    return {'ok':True,'status':'RECORDED_REAL_INFRASTRUCTURE_ANALYSIS','one_shot_available':False,'analysis':json.loads(path.read_text())}
@router.post('/analyze')
async def analyze(request:Request):
    body=await request.json()
    if body!={'confirm_single_authorized_request':True}:return JSONResponse({'detail':'explicit_one_shot_confirmation_required'},status_code=403)
    if not budget():return JSONResponse({'detail':'no_remaining_owner_credit_authorization_read_recorded_analysis'},status_code=409)
    # Fetch only already-integrated sources; no arbitrary client telemetry or destinations.
    try:observations=await asyncio.gather(store().observe('casa','network'),store().observe('bellini','network'))
    except Exception:return JSONResponse({'detail':'real_sources_unavailable_no_credit_used'},status_code=503)
    safe=[{k:x[k] for k in ('snapshot_id','snapshot_digest','site_label','source','collected_at','source_observed_at','freshness','summary','signals')} for x in observations]
    fd=None
    try:fd=os.open(state_path('real-infrastructure-one-shot.consumed'),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:return JSONResponse({'detail':'one_shot_already_consumed_no_retry'},status_code=409)
    with os.fdopen(fd,'w') as f:json.dump({'authorization':'Owner explicit reply in Codex 30 October 2026','started_at':now(),'max_output_tokens':2048,'snapshots':[x['snapshot_digest'] for x in observations]},f)
    started=time.time()
    def run():
        from inneros_core_runtime.nebius_nvidia_reasoning import NebiusNvidiaReasoning,load_nebius_api_key_from_vault
        key,_=load_nebius_api_key_from_vault()
        if not key:raise RuntimeError('existing_vault_credential_unavailable')
        reasoner=NebiusNvidiaReasoning(api_key=key,model='nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B',timeout_seconds=75,max_output_tokens=2048)
        return reasoner.diagnose({'scope':'REAL_READ_ONLY_OBSERVATIONS','observations':safe,'instruction':'Use only supplied observations. Unreachable from a monitor is not proof of hardware failure. If data is stale or ambiguous say so. Do not invent faults or recommend reboot without evidence. No action will execute.'})
    try:result=await asyncio.to_thread(run)
    except Exception as e:return JSONResponse({'detail':'provider_request_failed_no_retry','error_type':type(e).__name__},status_code=502)
    report={'result':result,'observations':safe,'requested_at':datetime.fromtimestamp(started,timezone.utc).isoformat(),'elapsed_seconds':round(time.time()-started,3),'paid_requests_attempted':1,'max_output_tokens':2048,'physical_mutation_applied':False,'scope':'REAL infrastructure observations; model recommendation is not execution authority'}
    path=state_path('real-infrastructure-nemotron.json');path.write_text(json.dumps(report,indent=2)+'\n');path.chmod(0o600)
    return {'ok':True,'status':'COMPLETED' if result.get('inference_mode')=='REAL' else 'PROVIDER_FAILED_LOCAL_FALLBACK','analysis':report,'one_shot_available':False}

from datetime import datetime,timezone
