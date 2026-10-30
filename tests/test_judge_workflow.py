import importlib.util,json,os,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from deployment.lab_workflow import LabWorkflow,digest

def test_identity_nonce_digest_expiry_replay_and_rejection(tmp_path):
    store=LabWorkflow(tmp_path/'decisions.sqlite')
    row=store.create('judge-a',{'dry_run':True},now=100)
    assert store.create('judge-a',{'dry_run':True},now=101)['id']==row['id']
    for session,nonce,hash in [('attacker',row['nonce'],row['digest']),('judge-a','forged',row['digest']),('judge-a',row['nonce'],'changed')]:
        with pytest.raises(ValueError):store.decide(row['id'],session,nonce,'approve',hash,now=110)
    assert store.decide(row['id'],'judge-a',row['nonce'],'approve',row['digest'],now=110)['status']=='APPROVED'
    assert store.consume(row['id'],'judge-a',row['digest'],now=111)['status']=='CONSUMED'
    with pytest.raises(ValueError):store.consume(row['id'],'judge-a',row['digest'],now=112)
    rejected=store.create('judge-b',{'dry_run':True},now=100)
    store.decide(rejected['id'],'judge-b',rejected['nonce'],'reject',rejected['digest'],now=101)
    with pytest.raises(ValueError):store.consume(rejected['id'],'judge-b',rejected['digest'],now=102)
    expired=store.create('judge-c',{},now=100)
    with pytest.raises(ValueError):store.decide(expired['id'],'judge-c',expired['nonce'],'approve',expired['digest'],now=401)
    assert LabWorkflow(tmp_path/'decisions.sqlite').get(row['id'],'judge-a',now=113)['status']=='CONSUMED'
    assert store.reserve_call(row['id']) is True
    assert store.reserve_call(row['id']) is False

@pytest.fixture
def client(monkeypatch,tmp_path):
    if not os.getenv('INNEROS_PLATFORM_ROOT'):pytest.skip('Private platform required for integration')
    from fastapi.testclient import TestClient
    monkeypatch.setenv('GUARDIAN_EVIDENCE_FILE',str(tmp_path/'evidence.json'))
    monkeypatch.setenv('GUARDIAN_WORKFLOW_FILE',str(tmp_path/'workflow.sqlite3'))
    monkeypatch.setenv('GUARDIAN_NEMOTRON_FILE',str(tmp_path/'missing.json'))
    spec=importlib.util.spec_from_file_location('guardian_judge_tests',ROOT/'deployment/platform_demo.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return TestClient(mod.app)

def plan(client):
    return client.post('/api/guardian/actions/plan',json={'capability_id':'network.device.reboot.v1','parameters':{'device_ref':'ap_validation_01','provider':'unifi'}}).json()['evidence_id']

def test_complete_api_judge_flow_and_single_use(client):
    p=client.post('/api/guardian/permits/request',json={'plan_evidence_id':plan(client)}).json()['permit']
    assert p['owner_authenticated'] is False and p['physical_execution_authorized'] is False
    assert client.post('/api/guardian/permits/verify',json={'id':p['id'],'digest':p['digest']}).status_code==409
    body={**p,'decision':'approve'}
    assert client.post('/api/guardian/permits/decision',json=body).status_code==200
    response=client.post('/api/guardian/permits/verify',json=body)
    assert response.status_code==200
    data=response.json();assert data['physical_mutation_applied'] is False
    assert data['result']['result']['verification_mode']=='SIMULATED'
    assert client.get('/api/guardian/evidence/'+data['evidence_id']).status_code==200
    assert client.post('/api/guardian/permits/verify',json=body).status_code==409
    client.cookies.clear()
    assert client.get('/api/guardian/permits/'+p['id']).status_code==404

def test_public_never_dials_and_csrf_denied(client):
    assert client.post('/api/guardian/permits/owner-call',json={}).status_code==403
    assert client.post('/api/guardian/permits/request',json={},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.post('/api/guardian/permits/request',json={'plan_evidence_id':'made-up'}).status_code==422
    assert client.get('/api/guardian/inference').json()['new_paid_requests_enabled'] is False
    assert client.post('/api/guardian/diagnose',json={'inference_mode':'REAL_CACHED','telemetry':{'device_ref':'ap_validation_01'}}).status_code==409

def test_real_cached_result_must_match_exact_input(client,monkeypatch,tmp_path):
    telemetry={'device_ref':'ap_validation_01','offline':True}
    path=tmp_path/'receipt.json'
    path.write_text(json.dumps({'mode':'REAL','telemetry_sha256':digest(telemetry),'result':{'provider_receipt':{'response_id':'test-response'},'inference_mode':'REAL'}}))
    monkeypatch.setenv('GUARDIAN_NEMOTRON_FILE',str(path))
    ok=client.post('/api/guardian/diagnose',json={'inference_mode':'REAL_CACHED','telemetry':telemetry})
    assert ok.status_code==200 and ok.json()['result']['new_paid_request'] is False
    changed=client.post('/api/guardian/diagnose',json={'inference_mode':'REAL_CACHED','telemetry':{**telemetry,'offline':False}})
    assert changed.status_code==409

def test_phone_proof_is_read_only_redacted_and_never_action_authority(client,monkeypatch,tmp_path):
    path=tmp_path/'phone-proof.json';monkeypatch.setenv('GUARDIAN_PHONE_PROOF_FILE',str(path))
    assert client.get('/api/guardian/phone/proof').json()['status']=='NOT_VERIFIED'
    path.write_text(json.dumps({'phone':'never-public','owner_id':'never-public','proposal_digest':'bound-proposal','existing_authority_readback':{'status':'completed','execution':{'executed':True,'verified':True}},'readback':{'approval_channel':'home_assistant_companion'},'owner_confirmation':{'conversation_succeeded':True}}))
    response=client.get('/api/guardian/phone/proof');proof=response.json()
    assert proof['status']=='REAL_CALL_VERIFIED'
    assert proof['physical_action_authorized'] is False
    assert proof['public_dialing_enabled'] is False
    assert 'never-public' not in response.text
