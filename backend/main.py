"""Seamless Payments demo API. All payment rails and identities are simulated."""
import os, sqlite3, secrets, uuid, hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

DB = os.getenv('DATABASE_PATH', 'seamless.db')
SECRET = os.getenv('JWT_SECRET', 'local-demo-secret-change-before-deploy')
ALGO = 'HS256'; pwd = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto'); bearer = HTTPBearer(auto_error=False)
app = FastAPI(title='Seamless Payments API', version='1.0.0', description='Simulated Indian payment ecosystem')
cors_origins = [origin.strip() for origin in os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',') if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_methods=['*'], allow_headers=['*'])

def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def now(): return datetime.now(timezone.utc).isoformat()
def row(r): return dict(r) if r else None
def init():
    c=db(); c.executescript('''
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, pin TEXT, phone TEXT, role TEXT DEFAULT 'user', created TEXT);
    CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY, user_id INTEGER, bank TEXT, label TEXT, number TEXT, ifsc TEXT, balance REAL, color TEXT, FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS beneficiaries(id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, vpa TEXT, bank TEXT, verified INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS transactions(id TEXT PRIMARY KEY, user_id INTEGER, recipient TEXT, vpa TEXT, amount REAL, rail TEXT, status TEXT, risk_score INTEGER, risk_level TEXT, risk_reason TEXT, account_id INTEGER, idempotency TEXT UNIQUE, reference TEXT, created TEXT);
    CREATE TABLE IF NOT EXISTS disputes(id INTEGER PRIMARY KEY, user_id INTEGER, transaction_id TEXT, reason TEXT, status TEXT, created TEXT);
    CREATE TABLE IF NOT EXISTS merchants(id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, category TEXT, vpa TEXT, created TEXT);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT, detail TEXT, created TEXT);
    CREATE TABLE IF NOT EXISTS otp(id INTEGER PRIMARY KEY, user_id INTEGER, code TEXT, expires TEXT, used INTEGER DEFAULT 0);
    ''')
    if not c.execute('SELECT 1 FROM users LIMIT 1').fetchone():
        c.execute('INSERT INTO users(name,email,password,pin,phone,role,created) VALUES(?,?,?,?,?,?,?)',('Aarav Mehta','demo@seamless.in',pwd.hash('Seamless@123'),pwd.hash('1234'),' +91 98765 43210','user',now()))
        uid=c.execute('SELECT id FROM users').fetchone()[0]
        accounts=[('State Bank of India','Savings • 4821','4821','SBIN0001234',82450,'#155eef'),('HDFC Bank','Salary • 1904','1904','HDFC0000912',142800,'#7f56d9'),('ICICI Bank','Savings • 6630','6630','ICIC0004410',36720,'#f79009')]
        for a in accounts: c.execute('INSERT INTO accounts(user_id,bank,label,number,ifsc,balance,color) VALUES(?,?,?,?,?,?,?)',(uid,*a))
        for b in [('Priya Sharma','priya@okaxis','Axis Bank'),('Rohan Kapoor','rohan@okhdfcbank','HDFC Bank'),('Maya Iyer','maya@oksbi','State Bank of India')]: c.execute('INSERT INTO beneficiaries(user_id,name,vpa,bank) VALUES(?,?,?,?)',(uid,*b))
        merchants=[('Blue Tokai Coffee','Food & beverage','bluetokai@okicici'),('The Whole Truth','Shopping','wholetruth@okhdfcbank'),('Urban Company','Services','urbancompany@okaxis')]
        for m in merchants: c.execute('INSERT INTO merchants(user_id,name,category,vpa,created) VALUES(?,?,?,?,?)',(uid,*m,now()))
        samples=[('Priya Sharma','priya@okaxis',1250,'UPI','success'),('Blue Tokai Coffee','bluetokai@okicici',420,'UPI','success'),('Maya Iyer','maya@oksbi',3500,'IMPS','success'),('Uber India','uber@okhdfcbank',612,'UPI','success'),('Rohan Kapoor','rohan@okhdfcbank',2000,'NEFT','pending'),('Whole Foods Market','wholefoods@paytm',2890,'UPI','success')]
        aid=c.execute('SELECT id FROM accounts ORDER BY id LIMIT 1').fetchone()[0]
        for i,(n,v,a,r,s) in enumerate(samples): c.execute('INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),uid,n,v,a,r,s,8,'low','Typical amount and known pattern',aid,'seed-'+str(i),'SP'+str(10001+i), (datetime.now(timezone.utc)-timedelta(hours=i*8)).isoformat()))
        c.commit()
    c.close()
init()

class Register(BaseModel): name:str; email:EmailStr; password:str=Field(min_length=8); phone:str=''
class Login(BaseModel): email:EmailStr; password:str
class Verify(BaseModel): code:str
class Payment(BaseModel): recipient:str=Field(min_length=2); vpa:str; amount:float=Field(gt=0,le=500000); rail:str; account_id:int; pin:str; otp:Optional[str]=None; idempotency_key:str
class Beneficiary(BaseModel): name:str; vpa:str; bank:str
class Dispute(BaseModel): transaction_id:str; reason:str
class Merchant(BaseModel): name:str; category:str; vpa:str

def current(creds:HTTPAuthorizationCredentials=Depends(bearer)):
    if not creds: raise HTTPException(401,'Please sign in')
    try: payload=jwt.decode(creds.credentials,SECRET,algorithms=[ALGO]); uid=int(payload['sub'])
    except (JWTError,ValueError,KeyError): raise HTTPException(401,'Session expired')
    c=db(); u=row(c.execute('SELECT id,name,email,phone,role FROM users WHERE id=?',(uid,)).fetchone()); c.close()
    if not u: raise HTTPException(401,'User not found')
    return u
def audit(c,uid,action,detail): c.execute('INSERT INTO audit(user_id,action,detail,created) VALUES(?,?,?,?)',(uid,action,detail,now()))
def token(u): return jwt.encode({'sub':str(u['id']),'exp':datetime.now(timezone.utc)+timedelta(hours=12)},SECRET,algorithm=ALGO)

@app.get('/api/health')
def health(): return {'status':'ok','mode':'simulation'}
@app.post('/api/auth/register')
def register(x:Register):
    c=db()
    try: c.execute('INSERT INTO users(name,email,password,pin,phone,created) VALUES(?,?,?,?,?,?)',(x.name,x.email,pwd.hash(x.password),pwd.hash('1234'),x.phone,now())); uid=c.execute('SELECT last_insert_rowid()').fetchone()[0]; c.commit()
    except sqlite3.IntegrityError: c.close(); raise HTTPException(409,'Email already registered')
    u=row(c.execute('SELECT id,name,email,phone,role FROM users WHERE id=?',(uid,)).fetchone()); c.close(); return {'token':token(u),'user':u}
@app.post('/api/auth/login')
def login(x:Login):
    c=db(); r=c.execute('SELECT * FROM users WHERE email=?',(x.email,)).fetchone(); c.close()
    if not r or not pwd.verify(x.password,r['password']): raise HTTPException(401,'Email or password is incorrect')
    u={'id':r['id'],'name':r['name'],'email':r['email'],'phone':r['phone'],'role':r['role']}; return {'token':token(u),'user':u}
@app.post('/api/auth/otp')
def request_otp(u=Depends(current)):
    code='123456'; c=db(); c.execute('INSERT INTO otp(user_id,code,expires) VALUES(?,?,?)',(u['id'],pwd.hash(code),(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat())); audit(c,u['id'],'otp.requested','Simulated OTP issued'); c.commit(); c.close(); return {'message':'OTP sent (simulation)','demo_code':code}
@app.get('/api/dashboard')
def dashboard(u=Depends(current)):
    c=db(); accounts=[dict(x) for x in c.execute('SELECT * FROM accounts WHERE user_id=?',(u['id'],))]; tx=[dict(x) for x in c.execute('SELECT * FROM transactions WHERE user_id=? ORDER BY created DESC LIMIT 8',(u['id'],))]
    total=c.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND status='success' AND created>=datetime('now','-30 days')",(u['id'],)).fetchone()[0]
    counts=c.execute('SELECT COUNT(*) n, SUM(CASE WHEN status="flagged" THEN 1 ELSE 0 END) flagged FROM transactions WHERE user_id=?',(u['id'],)).fetchone(); c.close()
    return {'accounts':accounts,'transactions':tx,'total_balance':sum(a['balance'] for a in accounts),'monthly_spend':total,'transaction_count':counts['n'],'flagged_count':counts['flagged'] or 0,'spending':[{'month':m,'amount':a} for m,a in [('May',32100),('Jun',28400),('Jul',39600),('Aug',31800),('Sep',45200),('Oct',total or 27450)]]}
@app.get('/api/accounts')
def accounts(u=Depends(current)):
    c=db(); data=[dict(x) for x in c.execute('SELECT * FROM accounts WHERE user_id=?',(u['id'],))]; c.close(); return data
@app.post('/api/accounts')
def add_account(data:dict,u=Depends(current)):
    bank=data.get('bank',''); allowed=['State Bank of India','HDFC Bank','ICICI Bank','Axis Bank','Kotak Mahindra Bank','Punjab National Bank']
    if bank not in allowed: raise HTTPException(400,'Choose a supported simulated bank')
    c=db(); c.execute('INSERT INTO accounts(user_id,bank,label,number,ifsc,balance,color) VALUES(?,?,?,?,?,?,?)',(u['id'],bank,'Savings • '+str(secrets.randbelow(9000)+1000),'****'+str(secrets.randbelow(9000)+1000),data.get('ifsc','SIMU0000001'),data.get('opening_balance',25000),'#155eef')); audit(c,u['id'],'account.linked',bank); c.commit(); a=row(c.execute('SELECT * FROM accounts WHERE id=last_insert_rowid()').fetchone()); c.close(); return a
@app.get('/api/beneficiaries')
def beneficiaries(u=Depends(current)):
    c=db(); data=[dict(x) for x in c.execute('SELECT * FROM beneficiaries WHERE user_id=?',(u['id'],))]; c.close(); return data
@app.post('/api/beneficiaries')
def add_beneficiary(x:Beneficiary,u=Depends(current)):
    c=db(); c.execute('INSERT INTO beneficiaries(user_id,name,vpa,bank) VALUES(?,?,?,?)',(u['id'],x.name,x.vpa,x.bank)); audit(c,u['id'],'beneficiary.added',x.vpa); c.commit(); r=row(c.execute('SELECT * FROM beneficiaries WHERE id=last_insert_rowid()').fetchone()); c.close(); return r
def score(c,uid,vpa,amount):
    risk=5; why=[]
    known=c.execute('SELECT 1 FROM beneficiaries WHERE user_id=? AND vpa=?',(uid,vpa)).fetchone()
    if not known: risk+=28; why.append('First payment to this beneficiary')
    if amount>=50000: risk+=36; why.append('High value transaction')
    elif amount>=20000: risk+=19; why.append('Amount is above your usual range')
    count=c.execute("SELECT COUNT(*) FROM transactions WHERE user_id=? AND created>datetime('now','-1 hour')",(uid,)).fetchone()[0]
    if count>=4: risk+=24; why.append('Unusually high payment frequency')
    if amount>=10000 and not known: risk+=16; why.append('New beneficiary and elevated amount')
    risk=min(100,risk); return risk,('high' if risk>=70 else 'medium' if risk>=35 else 'low'),('; '.join(dict.fromkeys(why)) if why else 'Typical amount and known pattern')
@app.post('/api/payments')
def payment(x:Payment,u=Depends(current)):
    if x.rail not in ['UPI','IMPS','NEFT','RTGS']: raise HTTPException(400,'Unsupported payment rail')
    c=db(); existing=c.execute('SELECT * FROM transactions WHERE idempotency=? AND user_id=?',(x.idempotency_key,u['id'])).fetchone()
    if existing: c.close(); return dict(existing)
    account=c.execute('SELECT * FROM accounts WHERE id=? AND user_id=?',(x.account_id,u['id'])).fetchone()
    if not account: c.close(); raise HTTPException(404,'Source account not found')
    if x.amount>account['balance']: c.close(); raise HTTPException(400,'Insufficient available balance')
    user=c.execute('SELECT pin FROM users WHERE id=?',(u['id'],)).fetchone()
    if not pwd.verify(x.pin,user['pin']): c.close(); raise HTTPException(401,'Transaction PIN is incorrect')
    risk,level,reason=score(c,u['id'],x.vpa,x.amount)
    if level=='high':
        valid=c.execute('SELECT * FROM otp WHERE user_id=? AND used=0 ORDER BY id DESC LIMIT 1',(u['id'],)).fetchone()
        if not valid or not pwd.verify(x.otp or '',valid['code']) or valid['expires']<now(): c.close(); raise HTTPException(428,detail={'message':'Additional OTP verification required','risk_score':risk,'risk_level':level,'risk_reason':reason})
        c.execute('UPDATE otp SET used=1 WHERE id=?',(valid['id'],))
    status='flagged' if level=='high' else 'success'; txid=str(uuid.uuid4()); ref='SP'+str(secrets.randbelow(89999999)+10000000)
    c.execute('INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(txid,u['id'],x.recipient,x.vpa,x.amount,x.rail,status,risk,level,reason,x.account_id,x.idempotency_key,ref,now()))
    if status=='success': c.execute('UPDATE accounts SET balance=balance-? WHERE id=?',(x.amount,x.account_id))
    audit(c,u['id'],'payment.'+status,f'{x.rail} {x.amount:.2f} to {x.vpa}; risk={risk}; {reason}'); c.commit(); result=row(c.execute('SELECT * FROM transactions WHERE id=?',(txid,)).fetchone()); c.close(); return result
@app.get('/api/transactions')
def transactions(status:Optional[str]=None,rail:Optional[str]=None,q:Optional[str]=None,u=Depends(current)):
    sql='SELECT * FROM transactions WHERE user_id=?'; args=[u['id']]
    if status and status!='all': sql+=' AND status=?'; args.append(status)
    if rail and rail!='all': sql+=' AND rail=?'; args.append(rail)
    if q: sql+=' AND (recipient LIKE ? OR vpa LIKE ? OR reference LIKE ?)'; args += [f'%{q}%']*3
    sql+=' ORDER BY created DESC'; c=db(); data=[dict(x) for x in c.execute(sql,args)]; c.close(); return data
@app.post('/api/disputes')
def dispute(x:Dispute,u=Depends(current)):
    c=db()
    if not c.execute('SELECT 1 FROM transactions WHERE id=? AND user_id=?',(x.transaction_id,u['id'])).fetchone(): c.close(); raise HTTPException(404,'Transaction not found')
    c.execute('INSERT INTO disputes(user_id,transaction_id,reason,status,created) VALUES(?,?,?, ?,?)',(u['id'],x.transaction_id,x.reason,'under_review',now())); audit(c,u['id'],'dispute.opened',x.transaction_id); c.commit(); r=row(c.execute('SELECT * FROM disputes WHERE id=last_insert_rowid()').fetchone()); c.close(); return r
@app.get('/api/disputes')
def disputes(u=Depends(current)):
    c=db(); d=[dict(x) for x in c.execute('SELECT * FROM disputes WHERE user_id=? ORDER BY created DESC',(u['id'],))]; c.close(); return d
@app.get('/api/merchants')
def merchants(u=Depends(current)):
    c=db(); d=[dict(x) for x in c.execute('SELECT * FROM merchants WHERE user_id=?',(u['id'],))]; c.close(); return d
@app.post('/api/merchants')
def add_merchant(x:Merchant,u=Depends(current)):
    c=db(); c.execute('INSERT INTO merchants(user_id,name,category,vpa,created) VALUES(?,?,?,?,?)',(u['id'],x.name,x.category,x.vpa,now())); audit(c,u['id'],'merchant.registered',x.name); c.commit(); r=row(c.execute('SELECT * FROM merchants WHERE id=last_insert_rowid()').fetchone()); c.close(); return r
@app.get('/api/security')
def security(u=Depends(current)):
    c=db(); d=[dict(x) for x in c.execute('SELECT * FROM audit WHERE user_id=? ORDER BY created DESC LIMIT 30',(u['id'],))]; risk=[dict(x) for x in c.execute("SELECT * FROM transactions WHERE user_id=? AND risk_level!='low' ORDER BY created DESC",(u['id'],))]; c.close(); return {'events':d,'flagged':risk}
@app.get('/api/admin')
def admin(u=Depends(current)):
    c=db(); d={'users':c.execute('SELECT COUNT(*) FROM users').fetchone()[0],'payments':c.execute('SELECT COUNT(*) FROM transactions').fetchone()[0],'volume':c.execute('SELECT COALESCE(SUM(amount),0) FROM transactions WHERE status="success"').fetchone()[0],'flagged':c.execute('SELECT COUNT(*) FROM transactions WHERE status="flagged"').fetchone()[0],'disputes':c.execute('SELECT COUNT(*) FROM disputes').fetchone()[0]}; c.close(); return d
