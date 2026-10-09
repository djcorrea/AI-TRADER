import json,time,asyncio,os,secrets
from fastapi import FastAPI,WebSocket,HTTPException,Request
from fastapi.responses import FileResponse
from .common import ROOT,CFG,state_path
from .paper import Store
app=FastAPI(title='QUANT AI V2 • local public data laboratory')
def read(relative,default=None):
    p=ROOT/relative
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default
def paper_state():
    store=Store(state_path('paper.sqlite'))
    try:
        service=store.get('service',{'status':'not_started'})
        if service.get('status')=='running':
            from datetime import datetime
            if time.time()-datetime.fromisoformat(service['updated']).timestamp()>30:service['status']='stale_or_offline'
        events=[{'received':r[0],'kind':r[1],'payload':json.loads(r[2])} for r in store.db.execute("SELECT received,kind,payload FROM events WHERE kind!='raw_feed' ORDER BY id DESC LIMIT 25")]
        symbols=store.get('monitor_symbols',service.get('symbols',CFG['symbols']))
        scanner=[store.get('scanner_'+s) for s in symbols if store.get('scanner_'+s)]
        scanner.sort(key=lambda row: (row.get('quote_volume_candle') or 0),reverse=True)
        for row in scanner:
            row['stale']=time.time()*1000-row['candle_close_ms']>120000
        connectivity=store.get('connectivity','unavailable')
        age=time.time()-service.get('last_message_epoch',0)
        feed={'healthy':connectivity=='connected' and service.get('status')=='running' and 0<=age<=30,
              'last_message_age_seconds':round(age,3) if service.get('last_message_epoch') else None,
              'fresh_quotes':service.get('fresh_quotes',0),'monitored_symbols':len(symbols),
              'fully_fresh':service.get('fresh_quotes',0)==len(symbols) and bool(symbols)}
        return {'service':service,'feed_health':feed,'broker':store.get('broker',{}),'kill':store.get('kill',False),'connectivity':connectivity,
            'clock_drift_ms':store.get('clock_drift_ms'), 'scanner':scanner,'events':events,
            'raw_messages_retained':store.db.execute("SELECT count(*) FROM events WHERE kind='raw_feed'").fetchone()[0]}
    finally:store.close()
@app.get('/')
def index():return FileResponse(ROOT/'dashboard/index.html')
@app.get('/health')
def health():return {'status':'ok','real_trading':False,'feed':paper_state()['feed_health']}
@app.get('/api/report')
def report():return read('results/report.json',{'status':'RESEARCH_RUNNING'})
@app.get('/api/experiments')
def experiments():return read('results/experiments.json',[])
@app.get('/api/models')
def models():return read('results/models.json',{'status':'NOT_TRAINED'})
@app.get('/api/quality')
def quality():return read('data/quality.json',{})
@app.get('/api/audit')
def audit():return read('reports/v3_audit.json',{'status':'NOT_RUN','pending':['V2 audit not run in this environment']})
@app.get('/api/research-v3')
def research_v3():return read('reports/v3_research_pilot.json',{'status':'NOT_RUN'})
@app.get('/api/data-rebuild')
def data_rebuild():return read('reports/v3_rebuild_summary.json',{'status':'NOT_RUN'})
@app.get('/api/opportunities')
def opportunities(symbol:str|None=None,horizon:int|None=None,regime:str|None=None,limit:int=100):
    from .market_opportunity_discovery import read_map
    return read_map(symbol,horizon,regime,limit)
@app.get('/api/paper')
def paper():return paper_state()
@app.post('/api/kill')
def kill(request:Request):
    # A reverse proxy's client address or Origin header is not authentication.
    if os.environ.get('ALLOW_REMOTE_CONTROL')!='1':raise HTTPException(403,'Administrative HTTP controls disabled')
    token=os.environ.get('CONTROL_TOKEN')
    authorization=request.headers.get('authorization','')
    supplied=authorization[7:] if authorization.startswith('Bearer ') else ''
    if not token or not secrets.compare_digest(supplied,token):raise HTTPException(401,'Authentication required')
    origin=request.headers.get('origin')
    if origin and origin!=os.environ.get('CONTROL_ORIGIN'):raise HTTPException(403,'Origin denied')
    store=Store(state_path('paper.sqlite'));store.put('kill',True);store.log('kill',{'reason':'dashboard'});store.close()
    return {'kill':True,'action':'Stop new simulated entries; liquidate paper positions when a fresh quote is available.'}
@app.websocket('/ws')
async def updates(ws:WebSocket):
    await ws.accept()
    try:
        while True:await ws.send_json(paper_state());await asyncio.sleep(3)
    except Exception:pass
