import json,time,asyncio,os
from fastapi import FastAPI,WebSocket,HTTPException,Request
from fastapi.responses import FileResponse
from .common import ROOT,state_path
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
        return {'service':service,'broker':store.get('broker',{}),'kill':store.get('kill',False),'connectivity':store.get('connectivity','unavailable'),
            'clock_drift_ms':store.get('clock_drift_ms'), 'scanner':[store.get('scanner_'+s) for s in ['BTCUSDT','ETHUSDT','SOLUSDT'] if store.get('scanner_'+s)],'events':events,
            'raw_messages_retained':store.db.execute("SELECT count(*) FROM events WHERE kind='raw_feed'").fetchone()[0]}
    finally:store.close()
@app.get('/')
def index():return FileResponse(ROOT/'dashboard/index.html')
@app.get('/health')
def health():return {'status':'ok','real_trading':False}
@app.get('/api/report')
def report():return read('results/report.json',{'status':'RESEARCH_RUNNING'})
@app.get('/api/experiments')
def experiments():return read('results/experiments.json',[])
@app.get('/api/models')
def models():return read('results/models.json',{'status':'NOT_TRAINED'})
@app.get('/api/quality')
def quality():return read('data/quality.json',{})
@app.get('/api/paper')
def paper():return paper_state()
@app.post('/api/kill')
def kill(request:Request):
    # Remote controls are disabled by default. Explicit configured origin only.
    origin=request.headers.get('origin')
    local=request.client and request.client.host in ('127.0.0.1','::1','testclient')
    allowed=('http://127.0.0.1:4174','http://localhost:4174')
    if os.environ.get('CONTROL_ORIGIN'):allowed=(*allowed,os.environ['CONTROL_ORIGIN'])
    if not local and os.environ.get('ALLOW_REMOTE_CONTROL')!='1':raise HTTPException(403,'Remote controls disabled')
    if origin and origin not in allowed:raise HTTPException(403,'Origin denied')
    if not local and origin!=os.environ.get('CONTROL_ORIGIN'):raise HTTPException(403,'Configured origin required')
    store=Store(state_path('paper.sqlite'));store.put('kill',True);store.log('kill',{'reason':'dashboard'});store.close()
    return {'kill':True,'action':'Stop new simulated entries; liquidate paper positions when a fresh quote is available.'}
@app.websocket('/ws')
async def updates(ws:WebSocket):
    await ws.accept()
    try:
        while True:await ws.send_json(paper_state());await asyncio.sleep(3)
    except Exception:pass
