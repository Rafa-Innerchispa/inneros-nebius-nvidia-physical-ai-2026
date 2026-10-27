"""Public lab shell importing the actual private InnerOS Guardian router.

Never mounts the core app or enables paid inference/physical execution.
"""
from pathlib import Path
import json,os,sys
from fastapi import FastAPI,Request
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT=Path(__file__).resolve().parents[1]
platform=Path(os.environ["INNEROS_PLATFORM_ROOT"]).resolve()
sys.path.insert(0,str(platform))
os.environ["NEBIUS_LIVE_SMOKE_AUTHORIZED"]="0"
from inneros_core_runtime import guardian_api_routes as guardian

app=FastAPI(title="InnerOS Guardian isolated lab",docs_url=None,redoc_url=None,openapi_url=None)
ALLOWED_DEVICES={"ap_validation_01"}
store=Path(os.environ.get("GUARDIAN_EVIDENCE_FILE",str(Path.home()/".local/state/inneros-nebius-demo/evidence.json")))
if store.exists():
    rows=json.loads(store.read_text())
    guardian._EVIDENCE.update({k:v for k,v in list(rows.items())[-500:] if k.startswith("evidence_")})

@app.middleware("http")
async def boundary(request:Request,call_next):
    path=request.url.path
    if request.method=="POST" and path.startswith("/api/guardian/"):
        if path not in {"/api/guardian/diagnose","/api/guardian/actions/plan","/api/guardian/recovery/verify"}:
            return JSONResponse({"detail":"public_execution_not_exposed"},status_code=405)
        raw=await request.body()
        if len(raw)>16384:return JSONResponse({"detail":"payload_too_large"},status_code=413)
        try: body=json.loads(raw)
        except ValueError:return JSONResponse({"detail":"invalid_json"},status_code=422)
        if not isinstance(body,dict):return JSONResponse({"detail":"object_required"},status_code=422)
        if path.endswith("/diagnose"):
            data=body.get("telemetry")
            if body.get("inference_mode")=="REAL":
                return JSONResponse({"detail":"new_paid_inference_disabled"},status_code=409)
        elif path.endswith("/plan"):
            data=body.get("parameters")
            if isinstance(data,dict) and (data.get("dry_run") is False or any(k in data for k in ("approval_token","owner_approved","owner_approval_ref"))):
                return JSONResponse({"detail":"physical_authority_not_exposed"},status_code=409)
        else:
            data=body
            if body.get("simulation") is not True:
                return JSONResponse({"detail":"public_verification_is_simulation_only"},status_code=409)
        if not isinstance(data,dict) or data.get("device_ref") not in ALLOWED_DEVICES:
            return JSONResponse({"detail":"synthetic_lab_target_required"},status_code=422)
        if data.get("provider","unifi")!="unifi":
            return JSONResponse({"detail":"synthetic_lab_provider_required"},status_code=422)
    result=await call_next(request)
    if path.startswith("/api/guardian/") and request.method=="POST":
        store.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        tmp=store.with_suffix(".tmp")
        tmp.write_text(json.dumps(guardian._EVIDENCE))
        tmp.chmod(0o600)
        tmp.replace(store)
    result.headers["Cache-Control"]="no-store"
    result.headers["X-Content-Type-Options"]="nosniff"
    result.headers["Referrer-Policy"]="no-referrer"
    result.headers["Content-Security-Policy"]="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    return result

app.include_router(guardian.router)
app.mount("/examples",StaticFiles(directory=ROOT/"examples"),name="recorded-evidence")

@app.get("/")
def index():return FileResponse(ROOT/"web/index.html")

@app.get("/healthz")
def health():return {"ok":True,"scope":"isolated_synthetic_lab","paid_inference_enabled":False,"physical_execution_enabled":False}
