import sys
from pathlib import Path
from fastapi.testclient import TestClient
from lab import api
from lab.common import state_path
from lab.paper import Store
from lab.cloud import commands
import run

def test_port_host_environment(monkeypatch):
    import uvicorn
    calls=[]
    monkeypatch.setenv('PORT','8089');monkeypatch.setenv('HOST','0.0.0.0')
    monkeypatch.setattr(sys,'argv',['run.py','serve'])
    monkeypatch.setattr(uvicorn,'run',lambda *a,**k:calls.append(k))
    run.main()
    assert calls==[{'host':'0.0.0.0','port':8089}]

def test_persistent_state_reopen(tmp_path,monkeypatch):
    monkeypatch.setenv('STATE_DIR',str(tmp_path))
    p=state_path('paper.sqlite');assert p==tmp_path/'paper.sqlite'
    a=Store(p);a.put('kill',True);a.close()
    b=Store(p);assert b.get('kill') is True;b.close()
    with TestClient(api.app) as c:assert c.get('/api/paper').json()['kill'] is True

def test_remote_control_disabled(tmp_path,monkeypatch):
    monkeypatch.setenv('STATE_DIR',str(tmp_path));monkeypatch.delenv('ALLOW_REMOTE_CONTROL',raising=False)
    with TestClient(api.app,client=('203.0.113.1',1234)) as c:
        assert c.get('/health').json()=={'status':'ok','real_trading':False}
        assert c.post('/api/kill').status_code==403

def test_cloud_only_continuous_services():
    c=commands(8000,'0.0.0.0')
    assert [x[2] for x in c]==['serve','paper']
    assert all('research' not in x and 'data' not in x for x in c)

def test_https_dashboard():
    from lab.common import ROOT
    text=(ROOT/'dashboard/index.html').read_text(encoding='utf-8')
    assert "location.protocol==='https:'?'wss://':'ws://'" in text
