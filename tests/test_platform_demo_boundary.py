"""Safety contract for hosting the real Guardian router in a public lab."""
import importlib.util,os,sys
from pathlib import Path
import pytest
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

@pytest.fixture
def client(monkeypatch,tmp_path):
    root=Path(__file__).resolve().parents[1]
    if not os.environ.get("INNEROS_PLATFORM_ROOT"):pytest.skip("Private platform not installed in standalone CI")
    monkeypatch.setenv("GUARDIAN_EVIDENCE_FILE",str(tmp_path/"evidence.json"))
    spec=importlib.util.spec_from_file_location("guardian_demo_test",root/"deployment/platform_demo.py")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return TestClient(mod.app)

def test_all_five_routes_are_real_and_safe(client):
    assert client.get("/api/guardian/overview").json()["contract_version"]=="guardian.v1"
    diag=client.post("/api/guardian/diagnose",json={"telemetry":{"device_ref":"ap_validation_01","offline":True}})
    assert diag.status_code==200
    assert diag.json()["result"]["inference_mode"]=="LOCAL_HEURISTIC"
    plan=client.post("/api/guardian/actions/plan",json={"capability_id":"network.device.reboot.v1","parameters":{"device_ref":"ap_validation_01","provider":"unifi"}})
    assert plan.status_code==200
    assert plan.json()["result"]["result"]["mutation_applied"] is False
    verify=client.post("/api/guardian/recovery/verify",json={"device_ref":"ap_validation_01","simulation":True,"provider":"unifi"})
    assert verify.status_code==200
    assert verify.json()["result"]["result"]["verification_mode"]=="SIMULATED"
    assert client.get("/api/guardian/evidence/"+diag.json()["evidence_id"]).status_code==200
    assert client.get("/healthz").json()["paid_inference_enabled"] is False

@pytest.mark.parametrize("path,body,status",[
    ("diagnose",{"inference_mode":"REAL","telemetry":{"device_ref":"ap_validation_01"}},409),
    ("diagnose",{"telemetry":{"device_ref":"Bellini"}},422),
    ("actions/plan",{"parameters":{"device_ref":"ap_validation_01","dry_run":False}},409),
    ("actions/plan",{"parameters":{"device_ref":"ap_validation_01","owner_approved":True}},409),
    ("recovery/verify",{"device_ref":"ap_validation_01","simulation":False},409),
])
def test_public_cannot_request_paid_inference_or_physical_authority(client,path,body,status):
    assert client.post("/api/guardian/"+path,json=body).status_code==status
