import numpy as np
import pandas as pd
from .common import CFG
def block_ci(trades,reps=4000,tests=120):
    if len(trades)<2:return None,None,None
    x=pd.DataFrame(trades);x['day']=x.exit_t//86400000
    day=x.groupby('day').agg(total=('net_return','sum'),n=('net_return','size'))
    trading_days=len(day)
    day=day.reindex(range(int(day.index.min()),int(day.index.max())+1),fill_value=0)
    a=day[['total','n']].to_numpy();length=len(a);block=min(7,length)
    # A handful of clustered days is not an independent sample, even with many trades.
    # Whole-period blocks would produce a misleading zero-width confidence interval.
    if length<28 or trading_days<8:return None,None,None
    rng=np.random.default_rng(CFG['seed']);est=[]
    for _ in range(reps):
        starts=rng.integers(0,length,size=(length+block-1)//block)
        ids=((starts[:,None]+np.arange(block))%length).ravel()[:length]
        total,n=a[ids].sum(axis=0)
        if n:est.append(total/n)
    if not est:return None,None,None
    ordinary=np.quantile(est,[.025,.975]).tolist()
    corrected=np.quantile(est,[.025/tests,1-.025/tests]).tolist()
    p=(1+sum(v<=0 for v in est))/(1+len(est))
    return ordinary,corrected,min(1,p*tests)
def metrics(result,tests=120):
    ts=result['trades'];curve=result['curve'];eq=np.array([500.]+[r['equity_brl'] for r in curve])
    dd=float((eq/np.maximum.accumulate(eq)-1).min())
    pnl=np.array([t['pnl_brl'] for t in ts]);rets=np.array([t['net_return'] for t in ts])
    win=float(pnl[pnl>0].sum());loss=float(-pnl[pnl<0].sum())
    ci,corrected,p=block_ci(ts,tests=tests)
    bysymbol={};byregime={}
    if ts:
        f=pd.DataFrame(ts)
        for key,dest in [('symbol',bysymbol),('regime',byregime)]:
            if key in f:
                for s,g in f.groupby(key): dest[str(s)]={'n':len(g),'net_pnl_brl':float(g.pnl_brl.sum()),'expectancy':float(g.net_return.mean())}
    return {'trades':len(ts),'net_return':float(eq[-1]/500-1),'net_pnl_brl':float(eq[-1]-500),
        'ending_brl':float(eq[-1]),'max_drawdown':dd,'profit_factor':win/loss if loss else None,
        'expectancy':float(rets.mean()) if len(ts) else None,'ci95_block':ci,
        'ci_familywise':corrected,'p_adjusted_bootstrap':p,'bootstrap_block_days':7,
        'confidence_rule':'IC indisponivel se menos de 28 dias calendarios ou 8 dias com negocios',
        'wins':int((pnl>0).sum()),'intrabar_ambiguous':sum(t.get('intrabar_ambiguous',False) for t in ts),
        'by_symbol':bysymbol,'by_regime':byregime,'risk_halted':result.get('risk_halted',False)}
def status(m,bh=None):
    if m['trades']<100:return 'INCONCLUSIVO'
    if m['expectancy']<=0 or m['net_return']<=0:return 'REJEITADA'
    if m['ci_familywise'] is None or m['ci_familywise'][0]<=0:return 'INCONCLUSIVO'
    if m['profit_factor'] is None or m['profit_factor']<1.3:return 'INCONCLUSIVO'
    if m['max_drawdown']<-.12:return 'REJEITADA'
    if bh is not None and m['net_return']<=max(0,bh['net_return']):return 'REJEITADA'
    return 'CANDIDATA_RETROSPECTIVA'
