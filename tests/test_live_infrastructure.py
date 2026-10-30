import json,sys,time
from pathlib import Path
import pytest
pytest.importorskip('httpx')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deployment.live_infrastructure import sanitize_home,sanitize_bellini,LiveInfrastructure

def test_live_sources_never_publish_identifiers_or_mixed_sites():
    raw={'entities':[{'entity_id':'sensor.private_192_168_1_4','label':'Private owner network','state':'online','unit':'','last_updated':'2026-10-30T14:00:00Z'},{'entity_id':'sensor.bellini_private','label':'Bellini external','state':'offline'},{'entity_id':'sensor.secret_ssid','state':'Private WiFi password 123'}]}
    result=sanitize_home('network',raw);encoded=json.dumps(result)
    assert len(result)==2 and result[0]['state']=='online'
    assert result[1]['state']=='not_published'
    for secret in ('192_168','Private owner','bellini_private','password 123','secret_ssid'):assert secret not in encoded
    assert result[0]['source_updated_at'].endswith('+00:00')

def test_bellini_keeps_actual_reachability_without_addresses():
    data={'timestamp':'2026-10-30T14:00:00Z','targets':[{'ip':'192.168.3.1','asset_id':'private-gateway','name':'Private customer','device_type':'gateway','online':False,'icmp':{'rtt_avg_ms':12}}]}
    items,updated=sanitize_bellini(data)
    assert items[0]['state']=='not_reachable' and updated
    assert '192.168' not in json.dumps(items) and 'Private customer' not in json.dumps(items)

def test_live_call_snapshot_binding_cooldown_and_session(tmp_path):
    store=LiveInfrastructure(tmp_path/'live.sqlite3')
    with store.db() as db:db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?)',('obs-a','casa','network','bound-digest','{}',time.time()))
    id,row=store.reserve_call('obs-a','owner-session')
    assert row['digest']=='bound-digest'
    with pytest.raises(ValueError,match='cooldown'):store.reserve_call('obs-a','attacker')
    store.save_call(id,'AWAITING_OWNER_APPROVAL',{'action_id':'opaque-action','expires_at':'2026-10-30T15:00:00Z'})
    with store.db() as db:row=db.execute('SELECT * FROM live_calls WHERE id=?',(id,)).fetchone()
    assert row['session']=='owner-session' and row['snapshot_id']=='obs-a'
    with pytest.raises(ValueError):store.reserve_call('does-not-exist','owner-session')

def test_server_metrics_only_publish_structural_status():
    items=sanitize_home('servers',{'nodes':[{'id':'private','name':'192.168.1.4','ok':True,'summary':{'password':'never-publish'}}]})
    assert items[0]['state']=='reachable'
    assert '192.168' not in json.dumps(items) and 'password' not in json.dumps(items)

def test_no_budget_is_implicit_and_expired_grant_is_denied(monkeypatch,tmp_path):
    from deployment import live_routes
    monkeypatch.setenv('GUARDIAN_LIVE_STATE_DIR',str(tmp_path))
    assert not live_routes.budget()
    grant=tmp_path/'real-infrastructure-one-shot-grant.json'
    grant.write_text(json.dumps({'authorized':True,'max_output_tokens':2048,'expires_at_epoch':time.time()-1}))
    assert not live_routes.budget()
    grant.write_text(json.dumps({'authorized':True,'max_output_tokens':2048,'expires_at_epoch':time.time()+300}))
    assert live_routes.budget()
    (tmp_path/'real-infrastructure-one-shot.consumed').touch()
    assert not live_routes.budget()
