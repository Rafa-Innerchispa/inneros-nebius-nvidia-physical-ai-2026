import io,json,sys,time,os,importlib.util
from pathlib import Path
import pytest
from pypdf import PdfReader
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deployment.pdf_report import snapshot_pdf,analysis_pdf,call_pdf,overview_pdf

def snapshot():
    return {'site':'bellini','site_label':'Bellini','category':'network','source':'Existing monitor → MongoDB','collected_at':'2026-10-30T15:00:00+00:00','source_observed_at':'2026-10-30T14:59:00+00:00','freshness':'RECENT_SOURCE_SAMPLE','snapshot_id':'obs-test','snapshot_digest':'a'*64,'summary':{'signal_count':2,'signals_needing_review':1,'unavailable_or_unreachable_signals':1},'signals':[{'label':'AP 4 <safe>','state':'not_reachable','source_updated_at':'2026-10-30T14:59:00+00:00'},{'label':'GATEWAY 1','state':'reachable','source_updated_at':None}]}
def text(data):
    assert data.startswith(b'%PDF-')
    reader=PdfReader(io.BytesIO(data));assert all(float(p.mediabox.width)>500 for p in reader.pages)
    return ' '.join(('\n'.join(p.extract_text() for p in reader.pages)).split())
def test_pdf_preserves_actual_observations_and_uncertainty():
    t=text(snapshot_pdf(snapshot()))
    for word in ('Bellini','AP 4 <safe>','Not reachable','obs-test','a'*64,'not establish hardware failure','No new Nemotron inference'):assert word in t
    assert 'InnerOS' in t and 'Infrastructure Guardian' in t
def test_pdf_model_receipt_and_call_scope_do_not_claim_recovery():
    model={'result':{'inference_mode':'REAL','provider':'test-provider','model':'test-model','diagnosis':{'root_cause':'Sample observation','recommended_action':'review'},'provider_receipt':{'response_id':'fixture-receipt','usage':{'prompt_tokens':10,'completion_tokens':20},'receipt_sha256':'b'*64}},'observations':[snapshot()],'max_output_tokens':2048,'paid_requests_attempted':1,'elapsed_seconds':2}
    t=text(analysis_pdf(model));assert 'fixture-receipt' in t and '10 / 20' in t and 'not run a new inference' in t
    c=text(call_pdf({'request_id':'call-test','status':'EXPIRED','snapshot_id':'obs-test','snapshot_digest':'a'*64,'executed':False,'verified':False}))
    assert 'EXPIRED' in c and 'No response means expiry without dialing' in c and 'does not prove' in c
    assert 'request a call' in text(overview_pdf())

def test_pdf_routes_use_only_persisted_evidence_and_keep_call_session_gate(monkeypatch,tmp_path):
    if not os.getenv('INNEROS_PLATFORM_ROOT'):pytest.skip('Private router integration requires pinned platform')
    from fastapi.testclient import TestClient
    from deployment import live_routes
    monkeypatch.setenv('GUARDIAN_LIVE_STATE_DIR',str(tmp_path));monkeypatch.setenv('GUARDIAN_WORKFLOW_FILE',str(tmp_path/'lab.sqlite'))
    monkeypatch.setenv('GUARDIAN_EVIDENCE_FILE',str(tmp_path/'evidence.json'))
    spec=importlib.util.spec_from_file_location('pdf_test_app',Path(__file__).resolve().parents[1]/'deployment/platform_demo.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    client=TestClient(mod.app)
    store=live_routes.store();data=snapshot()
    with store.db() as db:
        db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?)',('obs-test','bellini','network','a'*64,json.dumps(data),time.time()))
        db.execute('INSERT INTO live_calls VALUES (?,?,?,?,?,?,?,?,?)',('call-test','obs-test','a'*64,'a'*48,'EXPIRED',time.time(),time.time()-1,'','{}'))
    r=client.get('/api/guardian/live/reports/snapshots/obs-test.pdf');assert r.status_code==200 and r.headers['content-type']=='application/pdf'
    assert 'attachment;' in r.headers['content-disposition'] and r.headers['cache-control']=='no-store'
    assert 'AP 4' in text(r.content)
    assert client.get('/api/guardian/live/reports/snapshots/missing.pdf').status_code==404
    assert client.get('/api/guardian/live/reports/analysis.pdf').status_code==404
    assert client.get('/api/guardian/live/reports/calls/call-test.pdf').status_code==404
    client.cookies.set('guardian_session','a'*48)
    assert client.get('/api/guardian/live/reports/calls/call-test.pdf').status_code==200
