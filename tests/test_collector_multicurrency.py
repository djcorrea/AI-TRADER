"""Local feed fixtures exercise collector wiring, not market profitability."""
import asyncio
import json
import time

import websockets

from lab import paper
from test_lab import candles


def test_collector_processes_thirty_symbols_and_bounds_memory(tmp_path, monkeypatch):
    symbols=list(paper.CFG['symbols'])
    monkeypatch.setenv('STATE_DIR',str(tmp_path/'state'))
    monkeypatch.setattr(paper,'ROOT',tmp_path)
    target=int(time.time()*1000)//60000*60000-60000
    frame=candles(500,60000)
    frame['t']=target-500*60000+frame.index*60000
    frame['ct']=frame.t+59999
    def public_json(path):
        if path.endswith('/time'):return {'serverTime':int(time.time()*1000)}
        if path.endswith('/exchangeInfo'):
            return {'symbols':[dict(symbol=s,status='TRADING',quoteAsset='USDT') for s in symbols]}
        if '/klines?' in path:
            columns=['t','o','h','l','c','v','ct','qv','n','tbv','tbqv']
            return [[*r,0] for r in frame[columns].to_numpy().tolist()]
        raise AssertionError(f'Unexpected public request: {path}')
    monkeypatch.setattr(paper,'public_json',public_json)
    async def scenario():
        async def feed(socket):
            for s in symbols:
                await socket.send(json.dumps({'s':s,'b':'100','a':'100.1'}))
                k={'t':target,'T':target+59999,'o':'100','h':'101','l':'99','c':'100',
                   'v':'10000','q':'2000000','n':50,'V':'5000','Q':'1000000','x':True}
                await socket.send(json.dumps({'s':s,'k':k}))
            await asyncio.sleep(3)
        native_connect=websockets.connect
        async with websockets.serve(feed,'127.0.0.1',0) as server:
            port=server.sockets[0].getsockname()[1]
            def fixture_connect(url,**kwargs):
                assert url.startswith('wss://data-stream.binance.vision/')
                assert all(s.lower()+'@kline_1m' in url for s in symbols)
                return native_connect(f'ws://127.0.0.1:{port}',proxy=None,**kwargs)
            monkeypatch.setattr(paper.websockets,'connect',fixture_connect)
            await paper.collect(duration=2)
    asyncio.run(scenario())
    store=paper.Store(tmp_path/'state/paper.sqlite')
    assert store.get('monitor_symbols')==symbols
    assert all(store.get('scanner_'+s)['decision']=='NO_TRADE' for s in symbols)
    assert store.db.execute("SELECT count(*) FROM events WHERE kind='closed_candle'").fetchone()[0]==30
    assert store.db.execute("SELECT count(*) FROM events WHERE kind='paper_fill'").fetchone()[0]==0
    assert not store.get('broker')['positions']
    store.close()
