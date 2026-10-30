"""Explicit bounded catalog connectivity check. Never creates a completion."""
import asyncio,json,time,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime,timezone
MODEL='nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B'
URL='https://api.tokenfactory.nebius.com/v1/models'
_lock=asyncio.Lock()

def query_catalog():
    from inneros_core_runtime.nebius_nvidia_reasoning import load_nebius_api_key_from_vault
    key,_=load_nebius_api_key_from_vault()
    if not key:raise RuntimeError('existing_vault_credential_unavailable')
    request=urllib.request.Request(URL,headers={'Authorization':'Bearer '+key},method='GET')
    with urllib.request.urlopen(request,timeout=15) as response:
        status=response.status;body=json.loads(response.read(2_000_000))
    if not isinstance(body.get('data'),list):raise ValueError('invalid_provider_catalog')
    ids={x.get('id') for x in body['data'] if isinstance(x,dict)}
    return {'provider_http_status':status,'model_count':len(ids),'requested_model_available':MODEL in ids}

async def connection_check(state_dir):
    path=Path(state_dir)/'nebius-catalog-connectivity.json'
    async with _lock:
        try:
            saved=json.loads(path.read_text())
            if 0<=time.time()-saved['checked_epoch']<60:return {**saved,'delivery':'RECORDED_CONNECTION_CHECK','new_external_request':False}
        except (OSError,ValueError,KeyError):pass
        started=time.time()
        result={'checked_at':datetime.now(timezone.utc).isoformat(),'checked_epoch':started,'provider':'nebius_token_factory','method':'GET','endpoint':URL,'requested_model':MODEL,'generation_requests_sent':0,'generated_tokens':0,'inference_performed':False,'delivery':'REAL_PROVIDER_CATALOG_CHECK','new_external_request':True,'minimum_check_interval_seconds':60}
        try:result.update(await asyncio.to_thread(query_catalog));result['ok']=True
        except Exception as e:
            result.update(ok=False,error_type=type(e).__name__)
            if isinstance(e,urllib.error.HTTPError):result['provider_http_status']=e.code
        result['elapsed_seconds']=round(time.time()-started,3)
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2)+'\n');path.chmod(0o600)
        return result
