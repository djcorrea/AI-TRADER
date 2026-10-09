import time
from fastapi.testclient import TestClient
from lab import api
from lab.paper import Store
from lab.scanner import monitor_symbols, observation


def test_scanner_excludes_delisted_and_nonspot_candidates():
    records = [dict(symbol='AUSDT', status='TRADING', quoteAsset='USDT'),
               dict(symbol='BUSDT', status='BREAK', quoteAsset='USDT'),
               dict(symbol='CUSDT', status='TRADING', quoteAsset='USDT', isSpotTradingAllowed=False)]
    assert monitor_symbols(records, ['AUSDT','BUSDT','CUSDT','AUSDT']) == ['AUSDT']


def test_multicurrency_api_reads_all_monitored_symbols(tmp_path, monkeypatch):
    monkeypatch.setenv('STATE_DIR',str(tmp_path))
    store=Store(tmp_path/'paper.sqlite')
    names=[f'COIN{i}USDT' for i in range(30)]
    store.put('monitor_symbols',names)
    for i,s in enumerate(names):
        store.put('scanner_'+s,dict(symbol=s,candle_close_ms=int(time.time()*1000),quote_volume_candle=i))
    store.close()
    with TestClient(api.app) as client:
        scan=client.get('/api/paper').json()['scanner']
        assert len(scan)==30
        assert scan[0]['symbol']==names[-1]
        assert all(not row['stale'] for row in scan)


def test_scanner_never_turns_unavailable_spread_into_zero():
    candle=dict(ct=59999,c=100.,v=1000.,qv=100000.)
    feature=dict(regime='range',rsi=50.,atrn=.001)
    result=observation('BTCUSDT',candle,feature,500.,None,1000)
    assert result['spread'] is None and result['relative_volume']==2.
    assert result['decision']=='NO_TRADE'
    quote=dict(ask=100.1,bid=100.,received=999.)
    assert observation('BTCUSDT',candle,feature,500.,quote,1000)['spread']>0
    assert observation('BTCUSDT',candle,feature,500.,quote,1005)['spread'] is None
