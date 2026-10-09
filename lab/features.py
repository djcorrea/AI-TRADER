import numpy as np
import pandas as pd
from .common import CFG
FEATURES=['ret1','ret4','ret16','atrn','rv','slope','adx','z','rsi','volume_z','taker_ratio','autocorr','btc_relative','eth_relative']
def make(df, minutes=15):
    x=df.copy(); c=x.c; ret=np.log(c).diff()
    x['ret1']=ret; x['ret4']=np.log(c/c.shift(4));x['ret16']=np.log(c/c.shift(16))
    x['ema20']=c.ewm(span=20,adjust=False,min_periods=20).mean()
    x['ema100']=c.ewm(span=100,adjust=False,min_periods=100).mean()
    tr=pd.concat([x.h-x.l,(x.h-c.shift()).abs(),(x.l-c.shift()).abs()],axis=1).max(axis=1)
    x['atr']=tr.rolling(14,min_periods=14).mean();x['atrn']=x.atr/c
    x['rv']=ret.rolling(20).std(ddof=0);x['slope']=x.ema20.pct_change(4)
    up=x.h.diff(); down=-x.l.diff()
    plus=up.where((up>down)&(up>0),0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    minus=down.where((down>up)&(down>0),0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    x['adx']=((plus-minus).abs()/(plus+minus).replace(0,np.nan)*100).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    x['mid']=c.rolling(20).mean();sd=c.rolling(20).std(ddof=0)
    x['z']=(c-x.mid)/sd.replace(0,np.nan)
    gain=c.diff().clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    loss=(-c.diff().clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    x['rsi']=100-100/(1+gain/loss.replace(0,1e-15))
    x['prior_high']=x.h.shift().rolling(20).max();x['prior_low']=x.l.shift().rolling(20).min()
    vmean=x.v.shift().rolling(20).mean();vsd=x.v.shift().rolling(20).std(ddof=0)
    x['volume_z']=(x.v-vmean)/vsd.replace(0,np.nan)
    x['taker_ratio']=x.tbv/x.v.replace(0,np.nan)
    x['autocorr']=ret.rolling(20).corr(ret.shift())
    x['compression']=x.rv<x.rv.shift().rolling(100).quantile(.25)
    x['regime']=np.select([x.volume_z>5,(x.adx>25)&(x.slope>0),(x.adx>25)&(x.slope<0),x.atrn>.02],
                          ['anomaly','trend_up','trend_down','high_vol'],default='range')
    # Eligibility requires 30 complete days, uses volume known at the closed feature bar.
    n=CFG['history_days']*24*60//minutes
    x['daily_qv']=x.qv.rolling(n,min_periods=n).mean()*(24*60/minutes)
    x['history_ok']=(x.t-x.t.shift(n-1)==(n-1)*minutes*60000)
    # Reset eligibility across gaps. Feature values may cross a gap but are ineligible until warmup rebuilt.
    x['btc_relative']=0.; x['eth_relative']=0.
    return x
def cross(series):
    for base,name in [('BTCUSDT','btc_relative'),('ETHUSDT','eth_relative')]:
        if base not in series: continue
        reference=series[base].set_index('t').ret16
        for s,x in series.items(): x[name]=x.ret16-x.t.map(reference)
    daily=pd.concat([x[['t','daily_qv','ret16']].assign(symbol=s) for s,x in series.items()])
    daily['liquidity_rank']=daily.groupby('t').daily_qv.rank(method='first',ascending=False)
    daily['momentum_rank']=daily.groupby('t').ret16.rank(pct=True)
    for s,x in series.items():
        d=daily[daily.symbol==s].set_index('t')
        x['eligible']=x.history_ok & (x.daily_qv>=CFG['min_daily_quote_volume']) & (x.t.map(d.liquidity_rank)<=CFG['universe_top_n'])
        x['momentum_rank']=x.t.map(d.momentum_rank)
    return series
