import pandas as pd
from lab.backtest import simulate
from lab.execution import Filters,size
from test_lab import ready,simulate_ml
def test_target_signal_time_not_current_mean():
    x=ready();x[['o','h','l','c']]=100.;x['atr']=.5;x['mid']=100.5;x['regime']='range';x['rsi']=20.;x['z']=0.;x.loc[40,'z']=-3.
    a=simulate({'BTCUSDT':x},'mean_regime','2024-01-01','2024-02-01')
    y=x.copy();y.loc[42:,'mid']=100.001
    b=simulate({'BTCUSDT':y},'mean_regime','2024-01-01','2024-02-01')
    assert a['trades']==b['trades'];assert a['trades']
def test_intrabar_proceeds_never_size_same_open():
    a=ready();a[['o','h','l','c']]=100.;a['atr']=1.;a['mid']=102.;a.loc[40,'ml_signal']=True
    b=a.copy();b['ml_signal']=False;b.loc[41,'ml_signal']=True
    # A target first touches after B's open entry. A's target cannot finance B at that open.
    a.loc[43,'h']=104.;a.loc[43,'c']=104.
    baseline=simulate({'BTCUSDT':a,'ETHUSDT':b},'ml','2024-01-01','2024-02-01')
    changed=a.copy();changed.loc[43,'h']=140.;changed.loc[43,'c']=130.
    future=simulate({'BTCUSDT':changed,'ETHUSDT':b},'ml','2024-01-01','2024-02-01')
    orders_a=[o for o in baseline['orders'] if o['symbol']=='ETHUSDT'];orders_b=[o for o in future['orders'] if o['symbol']=='ETHUSDT']
    assert orders_a==orders_b;assert orders_a
def test_future_closed_volume_not_participation_sizing():
    x=ready();a=simulate_ml(x);y=x.copy();y.loc[42,'v']=1e9
    b=simulate_ml(y);assert a['orders'][0]['qty']==b['orders'][0]['qty']
def test_market_lot_quantity_max():
    f=Filters(step=.001,market_step=.01,market_max=.1,min_notional=1)
    qty,_=size(100,100,0,0,100,98,10000,f)
    assert qty<=.1;assert round(qty/.01)==qty/.01
