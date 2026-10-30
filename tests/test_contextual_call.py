import asyncio,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deployment import governed_call as calls
from deployment.live_infrastructure import LiveInfrastructure

def observation(**overrides):
    return {'site':'bellini','site_label':'Bellini','category':'network','signals':[{'label':'AP 4','state':'not_reachable'},{'label':'HOST 2','state':'reachable'}],'collected_at':'2026-10-30T15:00:00+00:00','source_observed_at':'2026-10-30T14:59:00+00:00','freshness':'RECENT_SOURCE_SAMPLE',**overrides}

def test_spoken_context_is_observation_not_invented_failure():
    text=calls.spoken_report(observation())
    assert 'Bellini' in text and 'AP 4' in text and '09:59' in text
    assert 'no confirma una avería física' in text and 'no autoriza acciones' in text
    assert 'HOST 2' not in text and len(text)<=600
    healthy=calls.spoken_report(observation(signals=[{'label':'AP 4','state':'reachable'}]))
    assert 'no aparecen inaccesibles' in healthy and 'no alcanza' not in healthy

def test_server_aggregate_never_claims_host_power():
    text=calls.spoken_report(observation(site='casa',site_label='Casa Rafael',category='servers',signals=[{'label':'Server 1','state':'checks_need_attention'}]))
    assert 'no significa que estén apagados' in text

def test_prepare_binds_exact_report_and_only_dispatches_after_approval(monkeypatch,tmp_path):
    store=LiveInfrastructure(tmp_path/'calls.sqlite3');body=observation()
    with store.db() as db:db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?)',('obs','bellini','network','snapshot-digest',json.dumps(body),time.time()))
    request_id,snapshot=store.reserve_call('obs','session')
    operations=[]
    async def helper(operation,payload):
        operations.append((operation,payload))
        if operation=='prepare':return {'ok':True,'channel':'home_assistant_companion','task_id':'approval'}
        if operation=='execute':return {'contract_version':'voiceops.fieldops.telephony.v1','result':{'status':'dispatched','call_id':'real-call'}}
        return {'ok':True}
    monkeypatch.setattr(calls,'run_helper',helper)
    async def authority(*args):return {'status':'awaiting_owner_approval'}
    monkeypatch.setattr(calls,'mongo_read',authority)
    asyncio.run(calls.prepare_call(store,request_id,snapshot))
    def row():
        with store.db() as db:return dict(db.execute('SELECT * FROM live_calls WHERE id=?',(request_id,)).fetchone())
    pending=row();asyncio.run(calls.dispatch_one(store,pending))
    assert [x[0] for x in operations]==['prepare']
    async def approved(*args):return {'status':'approved'}
    monkeypatch.setattr(calls,'mongo_read',approved)
    asyncio.run(calls.dispatch_one(store,pending));asyncio.run(calls.dispatch_one(store,pending))
    assert [x[0] for x in operations]==['prepare','execute','finish']
    assert row()['status']=='COMPLETED'
    assert operations[1][1]['reason']==operations[0][1]['reason']
    assert operations[1][1]['snapshot_digest']=='snapshot-digest'

def test_expired_or_interrupted_dispatch_never_redials(monkeypatch,tmp_path):
    store=LiveInfrastructure(tmp_path/'calls.sqlite3');payload={'approval_task_id':'a','action_digest':'d'}
    with store.db() as db:db.execute('INSERT INTO live_calls VALUES (?,?,?,?,?,?,?,?,?)',('call','obs','digest','s','AWAITING_CONTEXT_APPROVAL',time.time(),time.time()-1,'action',json.dumps(payload)))
    async def approved(*args):return {'status':'approved'}
    async def forbidden(*args):raise AssertionError('must never dispatch expired approval')
    monkeypatch.setattr(calls,'mongo_read',approved);monkeypatch.setattr(calls,'run_helper',forbidden)
    with store.db() as db:row=dict(db.execute('SELECT * FROM live_calls').fetchone())
    asyncio.run(calls.dispatch_one(store,row))
