"""Open -> entry -> intrabar exit -> close mark -> next-bar decisions. No same-bar recycling."""
import copy, datetime, math
import numpy as np
import pandas as pd
from .common import CFG
from .execution import Filters,floor,ceil,size,intrabar,net_pnl,Risk
from .strategies import signals
def simulate(series,name,start,end,filters=None,variant=1.,scenario=None):
    cfg=dict(CFG);cfg.update(scenario or {})
    lower=int(pd.Timestamp(start,tz='UTC').timestamp()*1000);upper=int(pd.Timestamp(end,tz='UTC').timestamp()*1000)
    minutes=cfg.get('interval_minutes',15);step=minutes*60000
    data={}; idx={};sigs={}
    for s,df in series.items():
        data[s]=df.to_records(index=False);idx[s]={int(r['t']):i for i,r in enumerate(data[s])};sigs[s]=signals(df,name,variant,cfg.get('random_seed',CFG['seed']))
    timeline=sorted({t for indexes in idx.values() for t in indexes if lower<=t<upper})
    initial=cfg['initial_brl']/cfg['brl_per_usdt'];cash=initial;pos={};trades=[];curve=[];orders=[]
    risk=Risk(initial);last_t=None;outage=False;flatten=False
    impact=cfg['spread_half']+cfg['slippage'];fee=cfg['fee'];fx=cfg['brl_per_usdt']
    def equity():return cash+sum(p['qty']*p['mark'] for p in pos.values())
    def close(s,raw,t,reason,ambiguous=False):
        nonlocal cash
        p=pos.pop(s);price=floor(raw*(1-impact),p['filter'].tick)
        cash+=p['qty']*price*(1-fee);pnl=net_pnl(p['qty'],p['entry'],price,fee)
        trades.append({'symbol':s,'strategy':name,'entry_t':p['entry_t'],'exit_t':t,'qty':p['qty'],
            'entry':p['entry'],'exit':price,'pnl_usdt':pnl,'pnl_brl':pnl*fx,
            'net_return':pnl/(p['qty']*p['entry']),'reason':reason,'intrabar_ambiguous':bool(ambiguous),
            'fee_usdt':p['qty']*(p['entry']+price)*fee,'regime':p['regime'],
            'filters_assumed':p['filter'].assumed,'costs_assumed':True})
    for t in timeline:
        rows={s:data[s][ids[t]] for s,ids in idx.items() if t in ids}
        for s,p in list(pos.items()):
            if s not in rows and t-p['last_t']>=step:
                # Missing market quote cannot justify a fabricated sale at stale price.
                # Conservative zero recovery haircut; flagged, not a historical fill.
                close(s,0.,t,'missing_market_zero_recovery_assumption')
        # An availability stress blocks local execution. Exchange protection is NOT assumed.
        blocked=cfg.get('outage',False) and (t//step)%(30*24*4)<24
        if blocked:
            outage=True
            for s,p in pos.items():
                if s in rows:p['mark']=rows[s]['c']
            curve.append({'t':t+step,'equity_brl':equity()*fx,'execution_unavailable':True});continue
        # At open use only current opens, never the current high/low/close for sizing.
        for s,p in list(pos.items()):
            if s not in rows:continue
            r=rows[s];p['mark']=r['o']
            if outage or flatten or t-p['last_t']>step or (last_t and t-last_t>step):close(s,r['o'],t,'circuit_recovery')
            elif t-p['entry_t']>=p['max_hold']*step:close(s,r['o'],t,'time')
        recovering=outage or flatten;outage=False;flatten=False
        day=datetime.datetime.fromtimestamp(t/1000,datetime.timezone.utc).date().isoformat()
        halted=risk.observe(equity(),day,cfg)
        if halted:
            for s in list(pos):
                if s in rows:close(s,rows[s]['o'],t,'risk_open')
        before=equity();opening_cash=cash
        # Intrabar proceeds are not available before open entries; time/recovery exits occur at open.
        for s,r in rows.items():
            if halted or recovering or s in pos or len(pos)>=cfg['max_positions']:continue
            i=idx[s][t];j=i-1-cfg['latency_bars']
            if j<0 or not sigs[s][j]:continue
            prev=data[s][j]
            if r['t']-prev['t']!=(cfg['latency_bars']+1)*step:continue
            f=(filters or {}).get(s,Filters())
            entry=ceil(r['o']*(1+impact),f.tick)
            stop=floor(prev['c']-2*variant*prev['atr'],f.tick)
            if stop<=0 or stop>=entry:continue
            # Stable target fixed with the signal bar; no current-bar rolling mean.
            target=prev['mid'] if name in ('mean_regime','range') else entry+3*variant*prev['atr']
            if target<=entry:continue
            exposure=sum(p['qty']*p['mark'] for p in pos.values())
            open_risk=sum(p['qty']*(p['entry']-p['stop']+p['entry']*(2*fee+2*impact)) for p in pos.values())
            qty,status=size(min(cash,opening_cash),before,exposure,open_risk,entry,stop,prev['v'],f,cfg)
            orders.append({'t':t,'symbol':s,'status':status,'qty':qty})
            if not qty:continue
            cost=qty*entry*(1+fee);cash-=cost;opening_cash-=cost;risk.orders+=1
            pos[s]={'qty':qty,'entry':entry,'entry_t':t,'stop':stop,'target':target,'filter':f,
                    'mark':entry,'peak':entry,'regime':prev['regime'],'last_t':t,
                    'max_hold':cfg.get('ml_horizon_minutes',16*minutes)//minutes if name=='ml' else 16 if name not in ('mean_regime','range') else 8}
            if risk.orders>=cfg['max_orders_day']:break
        for s,p in list(pos.items()):
            if s not in rows:continue
            r=rows[s];raw,reason,amb=intrabar(r['o'],r['h'],r['l'],p['stop'],p['target'])
            if reason:close(s,raw,t+step-1,reason,amb)
            else:
                p['mark']=r['c'];p['last_t']=t;p['peak']=max(p['peak'],r['c'])
                if name not in ('mean_regime','range') and math.isfinite(r['atr']):
                    p['stop']=max(p['stop'],floor(p['peak']-3*variant*r['atr'],p['filter'].tick))
        # Guard trips on close and liquidates at NEXT available open (gap risk is retained).
        flatten=risk.observe(equity(),day,cfg)
        curve.append({'t':t+step,'equity_brl':equity()*fx,'execution_unavailable':False})
        last_t=t
    for s in list(pos):
        r=next((r for r in reversed(data[s]) if lower<=r['t']<upper),None)
        if r is not None:close(s,r['c'],int(r['ct']),'end_of_data')
    if curve:curve[-1]['equity_brl']=cash*fx
    return {'trades':trades,'curve':curve,'orders':orders,'ending_brl':cash*fx,
            'risk_halted':risk.permanent_halt,'scenario':scenario or {},'strategy':name}
def buy_hold(series,start,end,filters=None):
    """Executable one-shot equal weights; leftover cash, filters, complete equity path."""
    lo=int(pd.Timestamp(start,tz='UTC').timestamp()*1000);hi=int(pd.Timestamp(end,tz='UTC').timestamp()*1000)
    eligible={s:x[(x.t>=lo)&(x.t<hi)] for s,x in series.items()}
    # Baseline universe fixed from information available BEFORE the first period bar.
    names=[s for s,x in eligible.items() if len(x) and bool(series[s].loc[series[s].t<x.t.iloc[0],'eligible'].tail(1).any())]
    names=sorted(names,key=lambda s:float(series[s].loc[series[s].t<lo,'daily_qv'].iloc[-1]),reverse=True)[:3]
    if not names:return {'curve':[{'t':lo,'equity_brl':500.}], 'trades':[], 'ending_brl':500.}
    fx=CFG['brl_per_usdt'];fee=CFG['fee'];imp=CFG['spread_half']+CFG['slippage'];cash=500/fx;pos={};trades=[]
    for s in names:
        x=eligible[s];f=(filters or {}).get(s,Filters());p=ceil(x.o.iloc[0]*(1+imp),f.tick)
        q=floor((500/fx/len(names))/(p*(1+fee)),f.step)
        if q*p<f.min_notional:continue
        cash-=q*p*(1+fee);pos[s]=(q,p,x.set_index('t').c,x.t.iloc[0],x.ct.iloc[-1])
    timeline=sorted({int(t) for s in names for t in eligible[s].t});marks={s:p[1] for s,p in pos.items()};curve=[]
    for t in timeline:
        for s,(q,p,cs,_,_) in pos.items():
            if t in cs.index:marks[s]=float(cs[t])
        curve.append({'t':t+900000,'equity_brl':(cash+sum(pos[s][0]*m for s,m in marks.items()))*fx})
    for s,(q,p,cs,entry_t,exit_t) in pos.items():
        f=(filters or {}).get(s,Filters());exit=floor(float(cs.iloc[-1])*(1-imp),f.tick);cash+=q*exit*(1-fee)
        pnl=net_pnl(q,p,exit,fee)
        trades.append({'symbol':s,'entry_t':int(entry_t),'exit_t':int(exit_t),'pnl_brl':pnl*fx,'net_return':pnl/(q*p)})
    if curve:curve[-1]['equity_brl']=cash*fx
    return {'curve':curve,'trades':trades,'ending_brl':cash*fx}
