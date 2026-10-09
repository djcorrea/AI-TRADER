"""Durable local paper broker + public WebSocket collector. No exchange order methods."""
import asyncio, json, sqlite3, time, datetime
from pathlib import Path
from collections import deque
import websockets
import pandas as pd
from .common import ROOT,CFG,utc,config_hash,dump,state_path
from .common import sha
from .data import public_json,validate
from .execution import Risk,Filters,size,ceil,floor,net_pnl,snapshot_filters
from .features import make
from .features import FEATURES
from .scanner import monitor_symbols,observation
def shadow_predict(bundle,feature):
    """Research inference only. This function cannot submit or approve an order."""
    import numpy as np
    frame=pd.DataFrame([{k:feature[k] for k in FEATURES}])
    if not np.isfinite(frame.to_numpy()).all():return None
    raw=np.clip(bundle['model'].predict_proba(frame),1e-6,1-1e-6)
    p=bundle['calibrator'].predict_proba(np.log(raw))[0]
    net=float(p@np.array([bundle['mu_negative'],bundle['mu_neutral'],bundle['mu_positive']]))
    return {'p_negative':float(p[0]),'p_no_opportunity':float(p[1]),'p_positive':float(p[2]),'estimated_ev_net':net}
def load_shadow():
    """Only the predeclared inactive, config-matched and hash-verified version."""
    choices=[('v3_registry.json','v3_logistic_30m_fold2'),('registry.json','logistic_60m_fold2')]
    for registry_name,version in choices:
        registry_path=ROOT/'models'/registry_name
        if not registry_path.exists():continue
        registry=json.loads(registry_path.read_text())
        entry=next((m for m in registry if m['version']==version),None)
        path=ROOT/f'models/{version}.joblib'
        if entry and entry.get('activation') is None and entry.get('config_hash')==config_hash() and path.exists() and sha(path)==entry['model_sha256']:
            import joblib
            return joblib.load(path),version
        # A tampered preferred artifact must not silently switch model versions.
        raise RuntimeError(f'Inactive shadow registry/config/hash check failed: {version}')
    return None,None
class Store:
    def __init__(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path,check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('CREATE TABLE IF NOT EXISTS state(k TEXT PRIMARY KEY,v TEXT); CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,received REAL,kind TEXT,payload TEXT); CREATE TABLE IF NOT EXISTS processed(symbol TEXT,t INTEGER,PRIMARY KEY(symbol,t));')
        self.db.execute('CREATE INDEX IF NOT EXISTS events_kind_id ON events(kind,id)')
        self.db.execute('CREATE INDEX IF NOT EXISTS events_received ON events(received)')
    def get(self,k,default=None):
        r=self.db.execute('SELECT v FROM state WHERE k=?',(k,)).fetchone();return json.loads(r[0]) if r else default
    def put(self,k,v):
        with self.db:self.db.execute('INSERT OR REPLACE INTO state VALUES(?,?)',(k,json.dumps(v)))
    def log(self,kind,payload):
        with self.db:self.db.execute('INSERT INTO events(received,kind,payload) VALUES(?,?,?)',(time.time(),kind,json.dumps(payload)))
    def atomic_broker_event(self,kind,payload,state):
        # A crash cannot persist a fill without its matching cash/position state.
        with self.db:
            self.db.execute('INSERT INTO events(received,kind,payload) VALUES(?,?,?)',(time.time(),kind,json.dumps(payload)))
            self.db.execute('INSERT OR REPLACE INTO state VALUES(?,?)',('broker',json.dumps(state)))
    def claim(self,s,t):
        try:
            with self.db:self.db.execute('INSERT INTO processed VALUES(?,?)',(s,t))
            return True
        except sqlite3.IntegrityError:return False
    def trim(self,limit=100000):
        with self.db:
            self.db.execute("DELETE FROM events WHERE kind='raw_feed' AND id <= (SELECT COALESCE(MAX(id),0)-? FROM events)",(limit,))
            self.db.execute("DELETE FROM events WHERE received<? AND kind!='paper_fill'",(time.time()-90*86400,))
            self.db.execute('DELETE FROM processed WHERE t<?',(int((time.time()-7*86400)*1000),))
    def close(self):self.db.close()
class PaperBroker:
    def __init__(self,store,cfg=None):
        self.store=store;self.cfg=dict(CFG);self.cfg.update(cfg or {})
        self.state=store.get('broker',{'cash':self.cfg['initial_brl']/self.cfg['brl_per_usdt'],'positions':{},'peak':self.cfg['initial_brl']/self.cfg['brl_per_usdt'],'day':'','day_equity':0.,'daily_halt':False,'permanent_halt':False,'orders':0,'pending':[]})
        self.save()
    def save(self):self.store.put('broker',self.state)
    def record_event(self,kind,payload,state):
        try:self.store.atomic_broker_event(kind,payload,state)
        except Exception:
            # Do not continue with a fill that the database rolled back.
            self.state=self.store.get('broker',self.state)
            raise
    def equity(self):return self.state['cash']+sum(p['qty']*p['mark'] for p in self.state['positions'].values())
    def guard(self,now):
        day=datetime.datetime.fromtimestamp(now,datetime.timezone.utc).date().isoformat();s=self.state;eq=self.equity()
        if s['day']!=day:s.update(day=day,day_equity=eq,daily_halt=False,orders=0)
        s['peak']=max(s['peak'],eq)
        s['daily_halt'] |= eq<=s['day_equity']*(1-self.cfg['daily_loss'])
        s['permanent_halt'] |= eq<=s['peak']*(1-self.cfg['max_drawdown'])
        return s['daily_halt'] or s['permanent_halt'] or s['orders']>=self.cfg['max_orders_day'] or self.store.get('kill',False)
    def submit(self,symbol,signal,quote,filters=None,approved=False,now=None):
        now=now or time.time();s=self.state;cfg=self.cfg
        reason=None
        if not approved:reason='no_approved_strategy'
        elif self.guard(now):reason='risk_or_kill'
        elif not self.store.get('clock_execution_ok',True):reason='clock_circuit'
        elif now-quote['received']>3:reason='stale_quote'
        elif quote['ask']<=quote['bid'] or (quote['ask']/quote['bid']-1)>.003:reason='spread_or_invalid_quote'
        elif symbol in s['positions'] or len(s['positions'])>=cfg['max_positions']:reason='exposure_or_duplicate'
        elif abs(quote['ask']/signal['price']-1)>.02:reason='price_divergence'
        elif signal.get('daily_qv',0)<cfg['min_daily_quote_volume']:reason='liquidity'
        if reason:self.store.log('blocked',{'symbol':symbol,'reason':reason,'timestamp':utc()});self.save();return False
        f=filters or Filters();price=ceil(quote['ask']*(1+cfg['slippage']),f.tick)
        exposure=sum(p['qty']*p['mark'] for p in s['positions'].values())
        open_risk=sum(p['qty']*(p['entry']-p['stop']+p['entry']*(2*cfg['fee']+2*cfg['spread_half']+2*cfg['slippage'])) for p in s['positions'].values())
        q,status=size(s['cash'],self.equity(),exposure,open_risk,price,signal['stop'],signal['volume'],f,cfg)
        if not q:self.store.log('cancelled',{'symbol':symbol,'reason':status});return False
        s['cash']-=q*price*(1+cfg['fee']);s['orders']+=1
        s['positions'][symbol]={'qty':q,'entry':price,'mark':quote['bid'],'stop':signal['stop'],'target':signal['target'],
            'entry_timestamp':now,'strategy':signal.get('strategy','research'),'model_version':signal.get('model_version'),
            'regime':signal.get('regime'),'fee':q*price*cfg['fee'],'tick':f.tick}
        self.record_event('paper_fill',{'timestamp':utc(),'symbol':symbol,'side':'BUY','price':price,'qty':q,'status':status,
            'spread_observed':quote['ask']-quote['bid'],'slippage_assumed':cfg['slippage'],'fee':q*price*cfg['fee'],
            'config_version':config_hash(),**signal},self.state);return True
    def tick(self,symbol,quote,now=None,force_reason=None):
        now=now or time.time();p=self.state['positions'].get(symbol)
        if not p:return
        if now-quote['received']>3:return # stale prices cannot create a realizable fill
        p['mark']=quote['bid'];halt=self.guard(now)
        reason=force_reason or ('kill_or_risk' if halt else 'stop' if quote['bid']<=p['stop'] else 'target' if quote['bid']>=p['target'] else 'time' if now-p['entry_timestamp']>=3600 else None)
        if reason:
            price=floor(quote['bid']*(1-self.cfg['slippage']),p['tick']);fee=p['qty']*price*self.cfg['fee']
            self.state['cash']+=p['qty']*price-fee;del self.state['positions'][symbol]
            self.record_event('paper_fill',{'timestamp':utc(),'symbol':symbol,'side':'SELL','price':price,'qty':p['qty'],
                'fee':fee,'net_pnl_usdt':net_pnl(p['qty'],p['entry'],price,self.cfg['fee']),'reason':reason,
                'spread_observed':quote['ask']-quote['bid'],'slippage_assumed':self.cfg['slippage'],**{k:p[k] for k in ('strategy','regime','model_version')}},self.state)
        self.save()
def parse_kline(k):
    return {'t':int(k['t']),'ct':int(k['T']),'o':float(k['o']),'h':float(k['h']),'l':float(k['l']),'c':float(k['c']),
        'v':float(k['v']),'qv':float(k['q']),'n':int(k['n']),'tbv':float(k['V']),'tbqv':float(k['Q'])}
async def collect(duration=0,symbols=None):
    candidates=list(symbols or CFG.get('scanner_symbols',CFG['symbols']))[:100]
    symbols=list(candidates);store=Store(state_path('paper.sqlite'));broker=PaperBroker(store)
    quotes={};bars={s:deque(maxlen=500) for s in symbols};start=time.monotonic();attempt=0;received=0;last_flush=0
    shadow,shadow_version=load_shadow();shadow_loaded=shadow is not None
    # REST warmup is public; a gap never silently carries signals into a reconnect.
    async def warmup():
        nonlocal symbols
        exchange=await asyncio.to_thread(public_json,'/api/v3/exchangeInfo')
        symbols=monitor_symbols(exchange['symbols'],candidates)
        if not symbols:raise RuntimeError('No currently listed public Spot candidates')
        store.put('monitor_symbols',symbols)
        samples=[]
        for _ in range(3):
            before=time.time()*1000;clock=await asyncio.to_thread(public_json,'/api/v3/time');after=time.time()*1000
            samples.append((after-before,clock['serverTime']-(before+after)/2))
        rtt,offset=min(samples)
        store.put('clock_drift_ms',offset);store.put('clock_rtt_ms',rtt)
        store.put('clock_offset_ms',offset)
        # Offset corrects exchange timestamps without modifying the user's OS clock.
        # A slow/uncertain clock sample blocks paper execution, but observation may continue.
        store.put('clock_execution_ok',rtt<3000 and abs(offset)<60000)
        if not store.get('clock_execution_ok'):store.log('clock_circuit',{'offset_ms':offset,'rtt_ms':rtt})
        for s in symbols:
            rows=await asyncio.to_thread(public_json,f'/api/v3/klines?symbol={s}&interval=1m&limit=500')
            bars[s].clear()
            for k in rows:
                if int(k[6])<clock['serverTime']:bars[s].append(dict(zip(['t','o','h','l','c','v','ct','qv','n','tbv','tbqv'],[int(k[0]),*map(float,k[1:6]),int(k[6]),float(k[7]),int(k[8]),float(k[9]),float(k[10])])))
    store.put('service',{'status':'starting','started':utc(),'symbols':symbols,'real_orders':False})
    try:
        while not duration or time.monotonic()-start<duration:
            try:
                store.put('connectivity','recovering');await warmup()
                stream='/'.join(f'{s.lower()}@bookTicker/{s.lower()}@kline_1m' for s in symbols)
                url='wss://data-stream.binance.vision/stream?streams='+stream
                async with websockets.connect(url,ping_interval=20,ping_timeout=20,close_timeout=5,max_queue=64) as ws:
                    store.log('connected',{'timestamp':utc(),'attempt':attempt});store.put('connectivity','connected');attempt=0
                    force_recovery=set(broker.state['positions'])
                    while not duration or time.monotonic()-start<duration:
                        try:raw=await asyncio.wait_for(ws.recv(),timeout=2)
                        except asyncio.TimeoutError:
                            if store.get('kill',False):
                                for s,q in quotes.items():broker.tick(s,q)
                            if quotes and time.time()-max(q['received'] for q in quotes.values())>30:raise RuntimeError('stale feed')
                            continue
                        packet=json.loads(raw);d=packet.get('data',packet);received+=1;store.log('raw_feed',packet)
                        if 'b' in d and 'a' in d:
                            s=d['s'];q={'bid':float(d['b']),'ask':float(d['a']),'received':time.time()};quotes[s]=q
                            broker.tick(s,q,force_reason='connection_recovery' if s in force_recovery else None);force_recovery.discard(s)
                        elif 'k' in d and d['k']['x']:
                            s=d['s'];r=parse_kline(d['k'])
                            if not validate(pd.DataFrame([r]),60000)['valid']:
                                store.log('invalid_live_candle',{'symbol':s,'t':r['t']});bars[s].clear();continue
                            if bars[s] and r['t']<=bars[s][-1]['t']:continue
                            if bars[s] and r['t']-bars[s][-1]['t']!=60000:
                                bars[s].clear();store.log('gap',{'symbol':s,'t':r['t']})
                            bars[s].append(r)
                            if not store.claim(s,r['t']):continue
                            store.log('closed_candle',{'symbol':s,'received':utc(),'candle':r})
                            if len(bars[s])<200:continue
                            f=make(pd.DataFrame(list(bars[s])),1).iloc[-1]
                            previous_volume=float(pd.DataFrame(list(bars[s]))['v'].iloc[-21:-1].mean())
                            scan=observation(s,r,f,previous_volume,quotes.get(s),time.time())
                            scan['available_utc']=utc()
                            store.put('scanner_'+s,scan);store.log('scanner',scan)
                            # Infer only when every asset's CLOSED candle has the same timestamp.
                            shadow_symbols=[z for z in CFG['ml_symbols'] if z in symbols]
                            if shadow_loaded and {'BTCUSDT','ETHUSDT'}.issubset(shadow_symbols) and len(shadow_symbols)==len(CFG['ml_symbols']) and all(bars[z] and bars[z][-1]['t']==r['t'] for z in shadow_symbols):
                                if store.claim('SHADOW_MODEL_'+shadow_version,r['t']):
                                    fs={z:make(pd.DataFrame(list(bars[z])),1).iloc[-1].copy() for z in shadow_symbols}
                                    for z,fz in fs.items():
                                        fz['btc_relative']=fz.ret16-fs['BTCUSDT'].ret16
                                        fz['eth_relative']=fz.ret16-fs['ETHUSDT'].ret16
                                        prediction=shadow_predict(shadow,fz)
                                        if prediction:
                                            observed=store.get('scanner_'+z,{})
                                            observed.update(shadow_model=shadow_version,model_status='INACTIVE / NOT APPROVED / TRAINED BEFORE JULY 2025',
                                                estimate_type='Model estimate, not observed profit',**prediction)
                                            store.put('scanner_'+z,observed)
                                            store.log('shadow_prediction',{'symbol':z,'available':utc(),'candle_t':r['t'],'version':shadow_version,**prediction})
                        if time.time()-last_flush>5:
                            store.put('service',{'status':'running','updated':utc(),'symbols':symbols,'messages':received,'real_orders':False,
                                'last_message_epoch':time.time(),'fresh_quotes':sum(time.time()-q['received']<=3 for q in quotes.values()),
                                'paper_pnl_brl':(broker.equity()*CFG['brl_per_usdt']-CFG['initial_brl']),'active_positions':len(broker.state['positions']),
                                'mode':'prospective observation; promotion blocked','elapsed_seconds':time.monotonic()-start})
                            store.trim();last_flush=time.time()
            except asyncio.CancelledError:raise
            except Exception as e:
                attempt+=1;store.log('connection_error',{'error':str(e),'attempt':attempt});store.put('connectivity','disconnected')
                # Interruptible and bounded reconnection delay; kill stored independently.
                await asyncio.sleep(min(30,2**min(attempt,5)))
        store.put('service',{**store.get('service',{}),'status':'stopped','updated':utc(),'messages':received})
    finally:broker.save();store.close()
