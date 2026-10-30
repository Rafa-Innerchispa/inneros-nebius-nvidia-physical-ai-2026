"""Durable judge decisions: lab consent is NEVER production authorization."""
import hashlib,json,secrets,sqlite3,time
from pathlib import Path

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class LabWorkflow:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS permits (id TEXT PRIMARY KEY, session TEXT, nonce TEXT, digest TEXT, proposal TEXT, expires REAL, status TEXT, created REAL, decided REAL, consumed REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS calls (permit_id TEXT PRIMARY KEY, status TEXT, result TEXT, created REAL)')
        self.path.chmod(0o600)
    def db(self):
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row;return db
    def create(self,session,proposal,now=None):
        now=time.time() if now is None else now
        with self.db() as db:
            row=db.execute('SELECT * FROM permits WHERE session=? AND digest=? AND expires>? AND status=?',(session,digest(proposal),now,'PENDING')).fetchone()
            if row:return dict(row)
            row={'id':'lab_'+secrets.token_hex(12),'session':session,'nonce':secrets.token_urlsafe(24),'digest':digest(proposal),'proposal':json.dumps(proposal),'expires':now+300,'status':'PENDING','created':now,'decided':None,'consumed':None}
            db.execute('INSERT INTO permits VALUES (:id,:session,:nonce,:digest,:proposal,:expires,:status,:created,:decided,:consumed)',row)
            return row
    def get(self,id,session=None,now=None):
        now=time.time() if now is None else now
        with self.db() as db:
            db.execute("UPDATE permits SET status='EXPIRED' WHERE id=? AND expires<=? AND status IN ('PENDING','APPROVED')",(id,now))
            row=db.execute('SELECT * FROM permits WHERE id=?',(id,)).fetchone()
        if not row or (session is not None and not secrets.compare_digest(row['session'],session)):raise ValueError('permit_not_found_for_this_session')
        return dict(row)
    def decide(self,id,session,nonce,decision,proposal_digest,now=None):
        now=time.time() if now is None else now;row=self.get(id,session,now)
        if decision not in ('approve','reject'):raise ValueError('invalid_decision')
        if row['status']!='PENDING':raise ValueError('permit_expired_or_already_decided')
        if not secrets.compare_digest(row['nonce'],nonce) or not secrets.compare_digest(row['digest'],proposal_digest):raise ValueError('permit_binding_mismatch')
        with self.db() as db:
            n=db.execute("UPDATE permits SET status=?,decided=? WHERE id=? AND status='PENDING' AND expires>?",('APPROVED' if decision=='approve' else 'REJECTED',now,id,now)).rowcount
        if n!=1:raise ValueError('permit_already_decided')
        return self.get(id,session,now)
    def consume(self,id,session,proposal_digest,now=None):
        now=time.time() if now is None else now;row=self.get(id,session,now)
        if row['status']!='APPROVED' or not secrets.compare_digest(row['digest'],proposal_digest):raise ValueError('lab_consent_required')
        with self.db() as db:
            if db.execute("UPDATE permits SET status='CONSUMED',consumed=? WHERE id=? AND status='APPROVED' AND expires>?",(now,id,now)).rowcount!=1:raise ValueError('permit_already_consumed')
        return self.get(id,session,now)
    def reserve_call(self,id):
        with self.db() as db:
            try:db.execute('INSERT INTO calls VALUES (?,?,?,?)',(id,'PREPARING','{}',time.time()))
            except sqlite3.IntegrityError:return False
        return True
    def call_result(self,id,status,result):
        with self.db() as db:db.execute('UPDATE calls SET status=?,result=? WHERE permit_id=?',(status,json.dumps(result),id))
    def call(self,id):
        with self.db() as db:row=db.execute('SELECT * FROM calls WHERE permit_id=?',(id,)).fetchone()
        return dict(row) if row else None

def public_permit(row,include_nonce=False):
    safe={k:row[k] for k in ('id','digest','expires','status','created','decided','consumed')}
    safe.update(scope='JUDGE_LAB_ONLY',owner_authenticated=False,physical_execution_authorized=False)
    if include_nonce:safe['nonce']=row['nonce']
    return safe
