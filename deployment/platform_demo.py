"""Public lab shell importing the actual private InnerOS Guardian router.

Never mounts the core app or enables paid inference/physical execution.
"""
from pathlib import Path
import json,os,sys
from fastapi import FastAPI,Request
import secrets,time
from deployment.lab_workflow import LabWorkflow,public_permit,digest
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT=Path(__file__).resolve().parents[1]
platform=Path(os.environ["INNEROS_PLATFORM_ROOT"]).resolve()
sys.path.insert(0,str(platform))
os.environ["NEBIUS_LIVE_SMOKE_AUTHORIZED"]="0"
from inneros_core_runtime import guardian_api_routes as guardian

app=FastAPI(title="InnerOS Guardian isolated lab",docs_url=None,redoc_url=None,openapi_url=None)
ALLOWED_DEVICES={"ap_validation_01"}
workflow=LabWorkflow(os.environ.get('GUARDIAN_WORKFLOW_FILE',str(Path.home()/'.local/state/inneros-nebius-demo/workflow.sqlite3')))
store=Path(os.environ.get("GUARDIAN_EVIDENCE_FILE",str(Path.home()/".local/state/inneros-nebius-demo/evidence.json")))
if store.exists():
    rows=json.loads(store.read_text())
    guardian._EVIDENCE.update({k:v for k,v in list(rows.items())[-500:] if k.startswith("evidence_")})

@app.middleware("http")
async def boundary(request:Request,call_next):
    path=request.url.path
    if request.method=="POST" and path.startswith("/api/guardian/"):
        if path not in {"/api/guardian/diagnose","/api/guardian/actions/plan","/api/guardian/recovery/verify","/api/guardian/permits/request","/api/guardian/permits/decision","/api/guardian/permits/verify","/api/guardian/permits/owner-call"}:
            return JSONResponse({"detail":"public_execution_not_exposed"},status_code=405)
        raw=await request.body()
        if len(raw)>16384:return JSONResponse({"detail":"payload_too_large"},status_code=413)
        try: body=json.loads(raw)
        except ValueError:return JSONResponse({"detail":"invalid_json"},status_code=422)
        if not isinstance(body,dict):return JSONResponse({"detail":"object_required"},status_code=422)
        if path.startswith('/api/guardian/permits/'):
            origin=request.headers.get('origin')
            if origin and origin!=str(request.base_url).rstrip('/'):
                return JSONResponse({'detail':'cross_origin_mutation_denied'},status_code=403)
            response=await call_next(request)
            response.headers['Cache-Control']='no-store'
            response.headers['X-Content-Type-Options']='nosniff'
            return response
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

def current_inference():
    path=Path(os.environ.get('GUARDIAN_NEMOTRON_FILE',str(Path.home()/'.local/state/inneros-nebius-demo/nemotron-current.json')))
    if not path.exists():return None
    try:
        data=json.loads(path.read_text())
        if data.get('mode')=='REAL' and data.get('result',{}).get('provider_receipt',{}).get('response_id'):return data
    except (ValueError,OSError):pass
    return None

@app.get('/api/guardian/inference')
def inference_status():
    data=current_inference()
    return {'ok':bool(data),'new_paid_requests_enabled':False,'source':'CACHED_PROVIDER_RESPONSE' if data else 'UNAVAILABLE','data':data}

@app.post('/api/guardian/diagnose')
def diagnose(body:dict):
    if body.get('inference_mode')!='REAL_CACHED':return guardian.guardian_diagnose(body)
    data=current_inference()
    if not data:return JSONResponse({'detail':'real_inference_unavailable_use_local_heuristic'},status_code=409)
    if digest(body.get('telemetry'))!=data['telemetry_sha256']:return JSONResponse({'detail':'cached_response_does_not_match_telemetry'},status_code=409)
    result={**data['result'],'delivery_mode':'CACHED_PROVIDER_RESPONSE','new_paid_request':False}
    evidence=guardian._record('diagnosis',result)
    # Numeric provider usage counters are evidence, not secret bearer tokens.
    usage=data['result'].get('provider_receipt',{}).get('usage',{})
    evidence['payload']['provider_receipt']['usage']={k:v for k,v in usage.items() if k in ('prompt_tokens','completion_tokens','total_tokens') and type(v) is int}
    return {'ok':True,'evidence_id':evidence['evidence_id'],'result':evidence['payload']}

def session(request):
    value=request.cookies.get('guardian_session','')
    return value if len(value)==48 and all(c in '0123456789abcdef' for c in value) else ''

@app.post('/api/guardian/permits/request')
async def permit_request(request:Request):
    body=await request.json();record=guardian._EVIDENCE.get(str(body.get('plan_evidence_id','')),{} )
    if record.get('kind')!='action_plan':return JSONResponse({'detail':'valid_plan_evidence_required'},status_code=422)
    sid=session(request) or secrets.token_hex(24)
    row=workflow.create(sid,{'plan_evidence_id':record['evidence_id'],'plan':record,'device_ref':'ap_validation_01','dry_run':True})
    response=JSONResponse({'ok':True,'permit':public_permit(row,True)})
    response.set_cookie('guardian_session',sid,httponly=True,secure=request.url.scheme=='https',samesite='strict',max_age=1800)
    return response

@app.post('/api/guardian/permits/decision')
async def permit_decision(request:Request):
    body=await request.json()
    try:row=workflow.decide(str(body.get('id','')),session(request),str(body.get('nonce','')),str(body.get('decision','')),str(body.get('digest','')))
    except ValueError as e:return JSONResponse({'detail':str(e)},status_code=409)
    evidence=guardian._record('judge_lab_decision',public_permit(row))
    # Same protected evidence store as the existing router, no physical authority.
    store.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    tmp=store.with_suffix('.tmp');tmp.write_text(json.dumps(guardian._EVIDENCE));tmp.chmod(0o600);tmp.replace(store)
    return {'ok':True,'permit':public_permit(row),'evidence_id':evidence['evidence_id']}

@app.post('/api/guardian/permits/verify')
async def permit_verify(request:Request):
    body=await request.json()
    try:row=workflow.consume(str(body.get('id','')),session(request),str(body.get('digest','')))
    except ValueError as e:return JSONResponse({'detail':str(e)},status_code=409)
    result=guardian.guardian_verify_recovery({'device_ref':'ap_validation_01','provider':'unifi','simulation':True})
    tmp=store.with_suffix('.tmp');tmp.write_text(json.dumps(guardian._EVIDENCE));tmp.chmod(0o600);tmp.replace(store)
    return {**result,'permit':public_permit(row),'physical_mutation_applied':False}

@app.get('/api/guardian/permits/{permit_id}')
async def permit_status(permit_id:str,request:Request):
    try:row=workflow.get(permit_id,session(request))
    except ValueError as e:return JSONResponse({'detail':str(e)},status_code=404)
    call=workflow.call(permit_id)
    phone={'status':call['status'] if call else 'NOT_REQUESTED','action_approval':'BLOCKED_REQUIRES_AUTHENTICATED_OWNER_DECISION','public_dialing_enabled':False}
    if call:
        saved=json.loads(call['result']);action_id=saved.get('action_id')
        if action_id:
            from urllib.parse import quote
            try:
                import httpx
                async with httpx.AsyncClient(timeout=3,follow_redirects=False) as client:
                    response=await client.get('http://127.0.0.1:8796/v1/receipts/'+quote(action_id,safe=''))
                if response.status_code==200:
                    receipt=response.json();result=receipt.get('result') or {}
                    phone['status']='VOICEOPS_'+str(result.get('status') or 'RECEIPT_AVAILABLE').upper()
                    phone['receipt']={k:result.get(k) for k in ('status','reason','sip_status','verified')}
                    phone['approval_channel']=receipt.get('approval_channel')
                    # A call receipt never promotes this lab permit to owner approval.
                    workflow.call_result(permit_id,phone['status'],{**saved,'receipt':phone['receipt']})
            except Exception:phone['readback']='TEMPORARILY_UNAVAILABLE'
    return {'ok':True,'permit':public_permit(row),'phone':phone}

@app.post('/api/guardian/permits/owner-call')
async def owner_call(request:Request):
    # Existing Atlas internal credential; never delivered to the public browser.
    token=''
    try:
        for line in (Path.home()/'.config/ambient-guardian/skill-bridge.env').read_text().splitlines():
            key,sep,value=line.partition('=')
            if sep and key.strip()=='AMBIENT_GUARDIAN_SKILL_BRIDGE_TOKEN':token=value.strip().strip(chr(34)).strip(chr(39))
    except OSError:pass
    supplied=request.headers.get('x-guardian-owner','')
    if not token or not supplied or not secrets.compare_digest(token,supplied):return JSONResponse({'detail':'authenticated_owner_required'},status_code=403)
    body=await request.json();pid=str(body.get('permit_id',''))
    try:row=workflow.get(pid)
    except ValueError:return JSONResponse({'detail':'permit_not_found'},status_code=404)
    if row['expires']<=time.time():return JSONResponse({'detail':'proposal_expired'},status_code=409)
    if not workflow.reserve_call(pid):return JSONResponse({'detail':'call_already_requested_no_automatic_retry'},status_code=409)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=18,follow_redirects=False) as client:
            response=await client.post('http://127.0.0.1:8794/api/alexa',headers={'x-ambient-skill-bridge':token},json={'utterance':'llama a mi celular usando Grandstream','speaker_context':{'response_locale':'es-US'}})
            response.raise_for_status();data=response.json()
        prepared=data.get('prepared_action') or {}
        if prepared.get('executed') is not False or prepared.get('status')!='approval_required' or prepared.get('approval_channel')!='home_assistant_companion':raise ValueError('governed_call_preparation_not_verified')
        safe={k:prepared.get(k) for k in ('action_id','action','status','approval_task_id','expires_at','approval_channel')}
        safe['guardian_proposal_digest']=row['digest'];safe['physical_execution_authorized']=False
        workflow.call_result(pid,'AWAITING_OWNER_CALL_APPROVAL',safe)
        return {'ok':True,'phone_status':'AWAITING_OWNER_CALL_APPROVAL','proposal_digest':row['digest'],'note':'Authorize the call in the existing Home Assistant owner channel. This does not authorize a physical action.'}
    except Exception as e:
        workflow.call_result(pid,'PREPARATION_UNVERIFIED',{'error_type':type(e).__name__,'retry':False})
        return JSONResponse({'detail':'call_preparation_unverified_check_existing_owner_inbox_no_retry'},status_code=502)

app.include_router(guardian.router)
app.mount("/examples",StaticFiles(directory=ROOT/"examples"),name="recorded-evidence")

@app.get("/")
def index():return FileResponse(ROOT/"web/index.html")

@app.get("/healthz")
def health():return {"ok":True,"scope":"isolated_synthetic_lab","paid_inference_enabled":False,"physical_execution_enabled":False,"release":ROOT.name,"nemotron_provider_receipt_available":bool(current_inference()),"phone_request_policy":"EXISTING_OWNER_CREDENTIAL_AND_COMPANION_APPROVAL","guardian_physical_action_approval":"BLOCKED"}
