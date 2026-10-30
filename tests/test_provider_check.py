import asyncio,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deployment import provider_check
from deployment.governed_call import spoken_report

def test_catalog_check_is_read_only_bounded_and_cached(monkeypatch,tmp_path):
    attempts=[]
    def query():
        attempts.append(1)
        return {'provider_http_status':200,'model_count':4,'requested_model_available':True}
    monkeypatch.setattr(provider_check,'query_catalog',query)
    async def run():return await provider_check.connection_check(tmp_path),await provider_check.connection_check(tmp_path)
    fresh,cached=asyncio.run(run())
    assert len(attempts)==1 and fresh['new_external_request'] is True and cached['new_external_request'] is False
    assert fresh['endpoint'].endswith('/v1/models') and fresh['method']=='GET'
    assert fresh['generation_requests_sent']==0 and fresh['generated_tokens']==0 and fresh['inference_performed'] is False
    assert cached['delivery']=='RECORDED_CONNECTION_CHECK'

def test_connection_errors_never_fabricate_inference_or_automatically_retry(monkeypatch,tmp_path):
    attempts=[]
    def query():attempts.append(1);raise RuntimeError('private detail must not leave process')
    monkeypatch.setattr(provider_check,'query_catalog',query)
    async def run():return await provider_check.connection_check(tmp_path),await provider_check.connection_check(tmp_path)
    first,second=asyncio.run(run())
    assert len(attempts)==1 and first['ok'] is False and first['error_type']=='RuntimeError'
    assert 'private detail' not in json.dumps(first) and second['inference_performed'] is False

def test_current_phone_report_uses_actual_access_point_states_and_load():
    base={'site':'casa','site_label':'Casa Rafael','category':'network','collected_at':'2026-10-30T16:00:00+00:00','source_observed_at':None,'freshness':'SOURCE_UPDATE_TIMES_PER_SIGNAL'}
    report=spoken_report({**base,'signals':[{'label':'Living AP connectivity','state':'connected'},{'label':'Estudio AP connectivity','state':'connected'}]})
    assert 'Living conectado' in report and 'Estudio conectado' in report and len(report)<=600
    energy=spoken_report({**base,'category':'energy','signals':[{'ref':'battery_mode','state':'on'},{'ref':'battery_capacity_percent','state':75},{'ref':'output_power_w','state':541}]})
    assert '75 por ciento' in energy and '541 vatios' in energy

def test_brief_report_discloses_a_partial_list_of_unreachable_signals():
    report=spoken_report({'site':'bellini','category':'network','collected_at':'2026-10-30T16:00:00+00:00','source_observed_at':'2026-10-30T16:00:00+00:00','freshness':'RECENT_SOURCE_SAMPLE','signals':[{'label':'AP '+str(i),'state':'not_reachable'} for i in range(5)]})
    assert 'no alcanza 5; entre ellas' in report and 'AP 0, AP 1, AP 2' in report and len(report)<=600
