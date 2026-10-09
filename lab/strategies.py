"""Fixed preregistered candidates. No post-holdout parameter search."""
import numpy as np
FAMILIES=['trend','pullback','breakout','mean_regime','cross_momentum','relative_btc','compression','range','volume_anomaly','hybrid','ml']
RULES={
 'trend':'EMA20>EMA100, slope>0, ADX>25; trend continuation',
 'pullback':'trend_up and RSI crosses above 40; continuation after retracement',
 'breakout':'close>previous 20-bar high and ATRn<.03; volatility expansion',
 'mean_regime':'range, z<-2, RSI<30; reversion only in range regime',
 'cross_momentum':'top momentum quintile, ret16>0 and trend_up; relative leadership',
 'relative_btc':'BTC-relative ret16>.01 and trend_up; outperform BTC',
 'compression':'prior compression and close>prior high; expansion after compression',
 'range':'range, close<prior low and z<-1.5; range bounce',
 'volume_anomaly':'volume_z>3, positive return, taker buy>.6; demand anomaly',
 'hybrid':'trend breakout or range reversion; causal regime switch',
 'ml':'chronological calibrated model positive probability and positive EV lower bound',
 'microstructure':'DISABLED: historical order-book spread and depth not available'
}
def signals(x,name,variant=1.,seed=20261009):
    up=(x.ema20>x.ema100)&(x.slope>0)&(x.adx>25)
    br=(x.c>x.prior_high)&(x.atrn<.03)
    mr=(x.regime=='range')&(x.z < -2*variant)&(x.rsi<30)
    values={
        'trend':up & (x.ret1>0),
        'pullback':up&(x.rsi.shift()<=40*variant)&(x.rsi>40*variant),
        'breakout':br,
        'mean_regime':mr,
        'cross_momentum':(x.momentum_rank>=.8)&(x.ret16>0)&up,
        'relative_btc':(x.btc_relative>.01*variant)&up,
        'compression':x.compression.shift(fill_value=False)&br,
        'range':(x.regime=='range')&(x.c<x.prior_low)&(x.z< -1.5*variant),
        'volume_anomaly':(x.volume_z>3*variant)&(x.ret1>0)&(x.taker_ratio>.6),
        'hybrid':(up&br)|mr,
        'ml':x.get('ml_signal',False),
        'random':np.random.default_rng(seed).random(len(x))<.01,
        'cash':np.zeros(len(x),dtype=bool),
        'buy_hold':np.ones(len(x),dtype=bool),
    }
    sig=values[name]
    return np.asarray(sig & x.eligible & x.atr.notna(),dtype=bool)
