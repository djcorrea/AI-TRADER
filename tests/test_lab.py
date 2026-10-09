import io,json,zipfile,copy
import numpy as np
import pandas as pd
import pytest
from lab.common import CFG
from lab.features import make,cross,FEATURES
from lab.data import validate,parse_archive
from lab.execution import Filters,size,floor,ceil,intrabar,net_pnl,Risk,snapshot_filters
from lab.backtest import simulate
from lab.models import labels,purge_train
from lab.paper import Store,PaperBroker,parse_kline
from lab.news import NewsEvent,causal_news
def candles(n=3300,step=900000):
    rng=np.random.default_rng(8);c=100*np.exp(np.cumsum(rng.normal(.00001,.001,n)));o=np.r_[c[0],c[:-1]]
    t=1704067200000+np.arange(n)*step
    return pd.DataFrame({'t':t,'ct':t+step-1,'o':o,'h':np.maximum(o,c)*1.002,'l':np.minimum(o,c)*.998,
        'c':c,'v':np.repeat(10000.,n),'qv':np.repeat(2000000.,n),'n':np.repeat(50,n),'tbv':np.repeat(5000.,n),'tbqv':np.repeat(1000000.,n)})
def ready(n=100):
    d=make(candles(n));d['eligible']=True;d['momentum_rank']=.9;d['ml_signal']=False
    d.loc[40,'ml_signal']=True
    return d
def simulate_ml(x,**kwargs):return simulate({'BTCUSDT':x},'ml','2024-01-01','2024-02-01',**kwargs)
def test_feature_prefix_invariance():
    d=candles(500);full=make(d);prefix=make(d.iloc[:400])
    for c in FEATURES+['ema20','ema100','prior_high','mid','regime']:
        pd.testing.assert_series_equal(full[c].iloc[:400],prefix[c])
def test_future_mutation_not_features():
    d=candles(500);a=make(d);d.loc[400:,'c']*=5;b=make(d)
    pd.testing.assert_frame_equal(a.iloc[:400],b.iloc[:400])
def test_data_integrity():assert validate(candles(50),900000)['valid']
@pytest.mark.parametrize('field,value',[('c',-1),('v',-1),('h',1),('tbv',20000),('ct',0)])
def test_data_invalid(field,value):
    d=candles(50);d.loc[10,field]=value;assert not validate(d,900000)['valid']
def test_duplicates_gaps():
    d=candles(50);assert validate(d.drop(index=10),900000)['missing_bars']==1
    assert not validate(pd.concat([d,d.iloc[:1]]),900000)['valid']
def test_archive_microseconds():
    raw=b'1735689600000000,1,2,0.5,1.5,20,1735689659999999,25,10,10,12,0\n'
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:z.writestr('x.csv',raw)
    d=parse_archive(b.getvalue());assert d.t.iloc[0]==1735689600000;assert validate(d,60000)['valid']
def test_closed_feature_prior_high():
    d=candles(40);d.loc[30,'h']=99999;x=make(d);assert x.prior_high.iloc[30]<99999;assert x.prior_high.iloc[31]==99999
def test_future_label_isolation():
    x=make(candles(200,60000));y=labels(x,15)
    pd.testing.assert_frame_equal(x[FEATURES],y[FEATURES]);assert 'forward_net' not in FEATURES
def test_labels_latency_and_fees():
    x=candles(200,60000);x[['o','h','l','c']]=100.
    y=labels(make(x),15);impact=CFG['spread_half']+CFG['slippage']
    expected=(1-impact)/(1+impact)*(1-CFG['fee'])/(1+CFG['fee'])-1
    assert y.forward_net.dropna().iloc[0]==pytest.approx(expected)
    assert y.label_end.iloc[40]==x.ct.iloc[56]
def test_purge_embargo():
    y=labels(make(candles(500,60000)),60);cut=int(y.available_t.iloc[350]);train=purge_train(y,cut,3600000)
    assert (train.label_end<cut-3600000).all();assert (train.available_t<cut-3600000).all()
def test_cross_symbol_same_cutoff():
    a=make(candles());b=make(candles());cross({'BTCUSDT':a,'ETHUSDT':b})
    assert a.eligible.iloc[:2879].sum()==0
    pd.testing.assert_series_equal(a.btc_relative,a.ret16-a.ret16,check_names=False)
def test_decimal_filters():assert floor(.123456,.001)==.123;assert ceil(.123001,.001)==.124
def test_min_filters_and_balance():
    f=Filters(step=.01,min_notional=5.)
    assert size(1.,100.,0.,0.,100.,98.,1000.,f)[0]==0
    q,_=size(100.,100.,0.,0.,100.,98.,1000.,f);assert q*100*(1+CFG['fee'])<=100;assert q*100<=25
def test_partial_fill():
    f=Filters(min_notional=1.);a,_=size(100,100,0,0,100,95,1000,f)
    b,status=size(100,100,0,0,100,95,1000,f,{**CFG,'fill_fraction':.5})
    assert b==pytest.approx(a/2,abs=1e-8);assert status=='partial'
def test_exposure_and_aggregate_risk():
    assert size(100,100,50,0,100,98,1000,Filters())[0]==0
    assert size(100,100,0,1,100,98,1000,Filters())[0]==0
def test_price_max_filter():assert size(100,100,0,0,100,98,1000,Filters(max_price=90))[1]=='price_filter'
def test_snapshot_all_filters():
    f=snapshot_filters([{'symbol':'X','filters':[{'filterType':'PRICE_FILTER','tickSize':'.01','minPrice':'.01','maxPrice':'100'},
        {'filterType':'LOT_SIZE','stepSize':'.1','minQty':'.1','maxQty':'20'},
        {'filterType':'MARKET_LOT_SIZE','stepSize':'.2','minQty':'.2','maxQty':'10'},
        {'filterType':'MIN_NOTIONAL','minNotional':'3'},{'filterType':'NOTIONAL','minNotional':'5','maxNotional':'50'}]}])['X']
    assert f.tick==.01 and f.step==.1 and f.market_step==.2 and f.min_notional==5 and f.max_notional==50
def test_stop_target_adverse():assert intrabar(100,110,90,95,105)==(95,'stop',True)
def test_stop_gap():assert intrabar(90,94,88,95,105)[0]==90
def test_fee_not_double():assert net_pnl(2,100,110,.001)==pytest.approx(19.58)
def test_daily_and_permanent_guard():
    r=Risk(100);assert not r.observe(100,'a');assert r.observe(97,'a');assert not r.observe(97,'b')
    assert r.observe(89,'b');assert r.observe(100,'c')
def test_execution_delay():
    x=ready();r=simulate_ml(x);assert r['trades'];assert r['trades'][0]['entry_t']==int(x.t.iloc[42])
def test_open_sizing_future_close_invariant():
    x=ready();a=simulate_ml(x);y=x.copy();y.loc[42,'c']=y.loc[42,'c']*1.2;y.loc[42,'h']=max(y.loc[42,'h'],y.loc[42,'c'])
    b=simulate_ml(y);assert a['orders'][0]['qty']==b['orders'][0]['qty']
def test_deterministic_simulation():assert simulate_ml(ready())==simulate_ml(ready())
def test_cash_pnl_reconciliation():
    r=simulate_ml(ready());assert r['ending_brl']-500==pytest.approx(sum(t['pnl_brl'] for t in r['trades']),abs=1e-8)
def test_risk_blocks_and_marks():
    x=ready();x.loc[42:,'c']=80;x.loc[42:,'l']=79;x.loc[42:,'o']=80;x.loc[42:,'h']=82
    r=simulate_ml(x);assert all(v['equity_brl']>=0 for v in r['curve'])
def test_gap_no_entry():
    x=ready().drop(index=41).reset_index(drop=True);assert not simulate_ml(x)['trades']
def test_persistence_duplicate_recovery(tmp_path):
    p=tmp_path/'paper.sqlite';s=Store(p);s.put('kill',True);assert s.claim('BTC',1);assert not s.claim('BTC',1);s.close()
    s=Store(p);assert s.get('kill');assert not s.claim('BTC',1);s.close()
def signal():return {'price':100.,'stop':98.,'target':105.,'volume':10000.,'daily_qv':20000000.,'regime':'trend_up'}
def quote(now=1000):return {'bid':100.,'ask':100.05,'received':now}
def test_no_approval_no_trade(tmp_path):
    s=Store(tmp_path/'p');b=PaperBroker(s);assert not b.submit('BTC',signal(),quote(),now=1000);assert b.equity()==pytest.approx(500/CFG['brl_per_usdt'])
def test_kill_prevents_entry(tmp_path):
    s=Store(tmp_path/'p');s.put('kill',True);b=PaperBroker(s);assert not b.submit('BTC',signal(),quote(),approved=True,now=1000)
def test_stale_and_spread_blocks(tmp_path):
    s=Store(tmp_path/'p');b=PaperBroker(s);assert not b.submit('BTC',signal(),quote(),approved=True,now=1005)
    q=quote();q['ask']=105.;assert not b.submit('BTC',signal(),q,approved=True,now=1000)
def test_paper_fill_recovery_kill_pnl(tmp_path):
    path=tmp_path/'p';s=Store(path);b=PaperBroker(s);assert b.submit('BTC',signal(),quote(),approved=True,now=1000);b.save();s.close()
    s=Store(path);b=PaperBroker(s);assert 'BTC' in b.state['positions'];s.put('kill',True);b.tick('BTC',quote(1001),now=1001)
    assert not b.state['positions'];assert b.equity()<500/CFG['brl_per_usdt']
    entries=s.db.execute("SELECT payload FROM events WHERE kind='paper_fill'").fetchall();pnl=json.loads(entries[-1][0])['net_pnl_usdt']
    assert b.equity()-500/CFG['brl_per_usdt']==pytest.approx(pnl)
def test_connectivity_recovery_flatten(tmp_path):
    s=Store(tmp_path/'p');b=PaperBroker(s);assert b.submit('BTC',signal(),quote(),approved=True,now=1000)
    b.tick('BTC',quote(1002),now=1002,force_reason='connection_recovery');assert not b.state['positions']
def test_retention_bound(tmp_path):
    s=Store(tmp_path/'p')
    for i in range(20):s.log('raw_feed',{'i':i})
    s.trim(10);assert s.db.execute('SELECT count(*) FROM events').fetchone()[0]==10
def test_news_available_not_published_only():
    a=NewsEvent(100,200,'x','source');assert not causal_news([a],150);assert causal_news([a],201)==[a]
    assert not causal_news([NewsEvent(1,2,'mock','test',True)],10)
