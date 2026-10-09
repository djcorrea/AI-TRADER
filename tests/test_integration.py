import json,hashlib,zipfile
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from lab.common import ROOT,dump
from lab.paper import Store
from lab.stats import metrics,status
from lab.backtest import simulate
from lab import api
from test_lab import ready,simulate_ml
def test_json_numpy(tmp_path):
    p=tmp_path/'x.json';dump(p,{'b':np.bool_(True),'n':np.int64(2)})
    assert json.loads(p.read_text())=={'b':True,'n':2}
def test_missing_quote_haircut():
    x=ready();x[['o','h','l','c']]=100.;x['atr']=.2;x['mid']=101.
    other=x.copy();other['ml_signal']=False
    x=x.drop(index=43).reset_index(drop=True)
    r=simulate({'BTCUSDT':x,'ETHUSDT':other},'ml','2024-01-01','2024-02-01')
    assert any(t['reason']=='missing_market_zero_recovery_assumption' for t in r['trades'])
def test_statistics_no_fake_infinite_pf():
    r={'trades':[{'entry_t':1,'exit_t':2,'net_return':-.004,'pnl_brl':-1,'symbol':'BTC'}],
        'curve':[{'t':1,'equity_brl':499}]}
    m=metrics(r);assert m['profit_factor']==0;assert status(m)=='INCONCLUSIVO';assert m['ci95_block'] is None
def test_block_bootstrap_deterministic():
    from lab.stats import block_ci
    trades=[{'exit_t':i*86400000,'net_return':(-1)**i*.01} for i in range(100)]
    assert block_ci(trades,reps=200)==block_ci(trades,reps=200)
def test_baseline_preservation():
    manifest=json.loads((ROOT/'baseline_v1/source_manifest.json').read_text())
    for relative,digest in manifest.items():
        raw=(ROOT/'baseline_v1'/relative.replace('\\','/')).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==digest
def test_api_http_and_ws(tmp_path,monkeypatch):
    monkeypatch.setattr(api,'ROOT',tmp_path);(tmp_path/'dashboard').mkdir();(tmp_path/'dashboard/index.html').write_text('<h1>fixture</h1>')
    monkeypatch.setenv('STATE_DIR',str(tmp_path/'paper'))
    with TestClient(api.app) as c:
        assert c.get('/').status_code==200
        assert c.get('/api/report').json()['status']=='RESEARCH_RUNNING'
        assert c.get('/api/models').json()['status']=='NOT_TRAINED'
        assert c.post('/api/kill',headers={'Origin':'https://external.example'}).status_code==403
        assert c.post('/api/kill',headers={'Origin':'http://127.0.0.1:4174'}).json()['kill']
        assert c.get('/api/paper').json()['kill']
        with c.websocket_connect('/ws') as ws:assert ws.receive_json()['kill']
