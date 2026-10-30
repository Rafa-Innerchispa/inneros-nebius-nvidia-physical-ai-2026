"""Read existing InnerOS collectors. Never probe a customer network or mutate devices."""
import asyncio,hashlib,json,os,re,sqlite3,sys,time,secrets
from pathlib import Path
from datetime import datetime,timezone
import httpx

CATALOG={'casa':{'label':'Casa Rafael','categories':['network','cameras','servers','energy']},'bellini':{'label':'Bellini','categories':['network']}}
QUERIES={'network':('unifi_status','What about my Wi-Fi?'),'cameras':('camera_status','What about my cameras?'),'servers':('fleet_status','What about my servers?'),'energy':('energy_resilience','show me the energy resilience status and energy saving plan')}
STATES={'on','off','online','offline','connected','disconnected','unavailable','unknown','idle','recording','streaming','true','false','home','not_home','ok','healthy','running','stopped'}
def now():return datetime.now(timezone.utc).isoformat()
def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def timestamp(value):
    try:
        dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if dt.tzinfo is None:return None
        return dt.astimezone(timezone.utc).isoformat()
    except (ValueError,TypeError):return None
def scalar(value):
    if type(value) in (bool,int):return value
    if type(value) is float:return value if abs(value)<1e12 else None
    s=str(value or '').strip().lower()
    if s in STATES:return s
    if re.fullmatch(r'-?\d{1,10}(?:\.\d{1,6})?',s):return float(s)
    return 'not_published'
def public_ref(value):return 'asset_'+hashlib.sha256(str(value).encode()).hexdigest()[:10]
def sanitize_home(category,raw):
    items=[]
    if category in ('network','cameras'):
        # Strict site separation: external connectors never leak into home results.
        entities=[x for x in raw.get('entities',[]) if isinstance(x,dict) and 'bellini' not in (str(x.get('entity_id',''))+' '+str(x.get('label',''))).lower()]
        for index,x in enumerate(entities[:40],1):
            unit=x.get('unit','');unit=unit if unit in ('%','ms','s','W','V','A','kWh','Wh','Mbps','Mbit/s','°C','dBm','B','MB','GB','h','min','') else ''
            items.append({'ref':public_ref(x.get('entity_id')),'label':('Network signal ' if category=='network' else 'Camera / recorder signal ')+str(index),'kind':str(x.get('entity_id','')).partition('.')[0] if str(x.get('entity_id','')).partition('.')[0] in ('sensor','binary_sensor','camera','switch') else 'signal','state':scalar(x.get('state')),'unit':unit,'source_updated_at':timestamp(x.get('last_updated'))})
    elif category=='servers':
        for i,x in enumerate(raw.get('nodes') or [],1):
            items.append({'ref':public_ref(x.get('id',i)),'label':'InnerOS server '+str(i),'kind':'server','state':'reachable' if x.get('ok') is True else 'not_reachable' if x.get('ok') is False else 'unknown','source_updated_at':None})
    else:
        metrics={'grid_present':'Grid detected','battery_mode':'Battery mode','outage_active':'Outage detected','battery_capacity_percent':'Battery charge','output_power_w':'Inverter output load','battery_voltage_v':'Battery voltage','remaining_hours':'Estimated backup hours'}
        for key,label in metrics.items():
            if raw.get(key) is not None:items.append({'ref':key,'label':label,'kind':'energy','state':scalar(raw[key]),'unit':'%' if key.endswith('percent') else 'W' if key.endswith('_w') else 'V' if key.endswith('_v') else 'h' if key=='remaining_hours' else '', 'source_updated_at':None})
    return items
def sanitize_bellini(raw):
    updated=timestamp(raw.get('timestamp'));counts={};items=[]
    for x in raw.get('targets',[])[:40]:
        kind=x.get('device_type');kind=kind if kind in ('gateway','pbx','nvr','switch','ap','host','camera') else 'device'
        counts[kind]=counts.get(kind,0)+1
        ping=x.get('icmp') or {};latency=ping.get('rtt_avg_ms')
        items.append({'ref':public_ref(x.get('asset_id')),'label':kind.upper()+' '+str(counts[kind]),'kind':kind,'state':'reachable' if x.get('online') is True else 'not_reachable' if x.get('online') is False else 'unknown','latency_ms':latency if type(latency) in (int,float) else None,'source_updated_at':updated})
    return items,updated

async def mongo_read(collection,query,projection):
    # Reuse canonical configured Mongo access in an isolated read-only process.
    core=Path.home()/'inneros/inneros_core/platform'
    code="import json,sys;from raphiia_openai import mongo_store;q=json.loads(sys.argv[1]);r=mongo_store.get_db()[q['collection']].find_one(q['query'],q['projection']);print(json.dumps(r or {},default=str))"
    env={**os.environ,'PYTHONPATH':str(core),'PYTHONDONTWRITEBYTECODE':'1'}
    process=await asyncio.create_subprocess_exec(str(core/'venv/bin/python'),'-c',code,json.dumps({'collection':collection,'query':query,'projection':projection}),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,env=env,cwd=str(core))
    try:out,_=await asyncio.wait_for(process.communicate(),10)
    except asyncio.TimeoutError:
        process.kill();await process.wait();raise RuntimeError('existing_source_timeout')
    if process.returncode:raise RuntimeError('existing_source_unavailable')
    return json.loads(out)

class LiveInfrastructure:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.locks={}
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS observations (id TEXT PRIMARY KEY,site TEXT,category TEXT,digest TEXT,body TEXT,created REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS live_calls (id TEXT PRIMARY KEY,snapshot_id TEXT,digest TEXT,session TEXT,status TEXT,created REAL,expires REAL,action_id TEXT,result TEXT)')
        self.path.chmod(0o600)
    def db(self):
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row;return db
    def get(self,id):
        with self.db() as db:row=db.execute('SELECT * FROM observations WHERE id=?',(id,)).fetchone()
        if not row:raise ValueError('snapshot_not_found')
        return dict(row)
    async def observe(self,site,category):
        if site not in CATALOG or category not in CATALOG[site]['categories']:raise ValueError('site_or_category_not_allowed')
        key=(site,category)
        async with self.locks.setdefault(key,asyncio.Lock()):
            with self.db() as db:previous=db.execute('SELECT * FROM observations WHERE site=? AND category=? ORDER BY created DESC LIMIT 1',key).fetchone()
            if previous and time.time()-previous['created']<20:
                return {**json.loads(previous['body']),'delivery':'RECENT_COLLECTOR_RESPONSE','response_age_seconds':round(time.time()-previous['created'],1)}
            started=now();source_updated=None
            if site=='bellini':
                raw=await mongo_read('bellini_guardian_state',{'site_id':'bellini-i-ii'},{'_id':0,'targets':1,'timestamp':1})
                items,source_updated=sanitize_bellini(raw);source='InnerOS Bellini Network Guardian → MongoDB'
            else:
                topic,query=QUERIES[category]
                async with httpx.AsyncClient(timeout=30,follow_redirects=False) as client:
                    response=await client.post('http://127.0.0.1:8794/api/alexa',json={'utterance':query});response.raise_for_status();data=response.json()
                if data.get('prepared_action') is not None:raise RuntimeError('read_source_returned_action')
                raw=data.get(topic) or {}
                if raw.get('configured') is False or raw.get('truth')=='UNAVAILABLE':raise RuntimeError('existing_source_not_configured_or_unavailable')
                items=sanitize_home(category,raw);source='Atlas → '+('Home Assistant' if category in ('network','cameras') else 'InnerOS fleet' if category=='servers' else 'InnerOS energy history / inverter bridge')
            if not items:raise RuntimeError('no_verified_source_readings')
            age=max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(source_updated)).total_seconds()) if source_updated else None
            unavailable=sum(x['state'] in ('unavailable','unknown','not_reachable','offline','disconnected') for x in items)
            result={'ok':True,'mode':'REAL_READ_ONLY','site':site,'site_label':CATALOG[site]['label'],'category':category,'source':source,'collected_at':started,'source_observed_at':source_updated,'source_age_seconds':round(age,1) if age is not None else None,'freshness':'STALE' if age is not None and age>180 else 'RECENT_SOURCE_SAMPLE' if age is not None else 'SOURCE_UPDATE_TIMES_PER_SIGNAL','signals':items,'summary':{'signal_count':len(items),'unavailable_or_unreachable_signals':unavailable},'limitations':['Reachability is from the existing monitor, not proof of hardware failure.','A Home Assistant entity update timestamp is not a new physical probe.','No new Nemotron inference has been performed for this reading.'],'physical_mutation_applied':False,'inference_mode':'NOT_REQUESTED','delivery':'COLLECTED_FROM_EXISTING_SOURCE'}
            result['snapshot_digest']=digest(result);result['snapshot_id']='obs_'+secrets.token_hex(12)
            with self.db() as db:
                if db.execute('SELECT count(*) FROM observations').fetchone()[0]>=3000:raise RuntimeError('observation_storage_limit')
                db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?)',(result['snapshot_id'],site,category,result['snapshot_digest'],json.dumps(result),time.time()))
            return result
    def reserve_call(self,snapshot_id,session):
        snapshot=self.get(snapshot_id);current=time.time()
        if current-snapshot['created']>300:raise ValueError('refresh_reading_before_requesting_call')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM live_calls WHERE created>?',(current-600,)).fetchone():raise ValueError('owner_call_request_cooldown_10_minutes')
            id='call_'+secrets.token_hex(12)
            db.execute('INSERT INTO live_calls VALUES (?,?,?,?,?,?,?,?,?)',(id,snapshot_id,snapshot['digest'],session,'PREPARING',current,current+300,'','{}'))
        return id,snapshot
    def save_call(self,id,status,result):
        expiry=timestamp(result.get('expires_at'))
        with self.db() as db:
            db.execute('UPDATE live_calls SET status=?,action_id=?,result=? WHERE id=?',(status,result.get('action_id',''),json.dumps(result),id))
            if expiry:db.execute('UPDATE live_calls SET expires=? WHERE id=?',(datetime.fromisoformat(expiry).timestamp(),id))
    async def call_status(self,id,session):
        with self.db() as db:row=db.execute('SELECT * FROM live_calls WHERE id=?',(id,)).fetchone()
        if not row or not secrets.compare_digest(row['session'],session):raise ValueError('call_request_not_found')
        status=row['status'];authority={}
        if row['action_id']:
            try:
                authority=await mongo_read('ambient_guardian_mobile_approvals',{'action_id':row['action_id']},{'_id':0,'status':1,'authorized_at':1,'finished_at':1,'evidence.executed':1,'evidence.verified':1})
                status=str(authority.get('status') or status).upper()
            except Exception:pass
        if time.time()>row['expires'] and status in ('PREPARING','AWAITING_OWNER_APPROVAL','AWAITING_OWNER_CALL_APPROVAL'):status='EXPIRED'
        return {'ok':True,'request_id':id,'status':status,'snapshot_id':row['snapshot_id'],'snapshot_digest':row['digest'],'expires_at_epoch':row['expires'],'authorized_at':authority.get('authorized_at'),'finished_at':authority.get('finished_at'),'executed':(authority.get('evidence') or {}).get('executed',False),'verified':(authority.get('evidence') or {}).get('verified',False),'approval_channel':'home_assistant_companion','physical_device_action_authorized':False}
