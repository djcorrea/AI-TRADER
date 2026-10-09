from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
import math
from .common import CFG
@dataclass
class Filters:
    step:float=.00000001
    min_qty:float=0.
    max_qty:float=1e20
    tick:float=.00000001
    min_price:float=0.
    max_price:float=1e20
    min_notional:float=5.
    max_notional:float=1e20
    market_step:float=0.
    market_min:float=0.
    market_max:float=1e20
    assumed:bool=True
def snapshot_filters(records):
    out={}
    for s in records:
        f=Filters(assumed=False)
        for r in s.get('filters',[]):
            k=r['filterType']
            if k=='PRICE_FILTER': f.tick=float(r['tickSize']);f.min_price=float(r['minPrice']);f.max_price=float(r['maxPrice']) or 1e20
            if k=='LOT_SIZE': f.step=float(r['stepSize']);f.min_qty=float(r['minQty']);f.max_qty=float(r['maxQty']) or 1e20
            if k=='MARKET_LOT_SIZE': f.market_step=float(r['stepSize']);f.market_min=float(r['minQty']);f.market_max=float(r['maxQty']) or 1e20
            if k=='MIN_NOTIONAL': f.min_notional=float(r['minNotional'])
            if k=='NOTIONAL': f.min_notional=float(r['minNotional']);f.max_notional=float(r['maxNotional']) or 1e20
        out[s['symbol']]=f
    return out
def floor(value,step):
    if not step:return value
    d=Decimal(str(value));s=Decimal(str(step));return float((d/s).to_integral_value(rounding=ROUND_FLOOR)*s)
def ceil(value,step):
    if not step:return value
    d=Decimal(str(value));s=Decimal(str(step));return float((d/s).to_integral_value(rounding=ROUND_CEILING)*s)
def size(cash,equity,exposure,open_risk,price,stop,previous_volume,f,cfg=CFG):
    dist=price-stop+price*cfg['fee']+stop*(cfg['fee']+cfg['spread_half']+cfg['slippage'])
    if dist<=0:return 0.,'invalid_stop'
    amount=min(equity*cfg['position_cap'],max(0,equity*cfg['aggregate_cap']-exposure),cash/(1+cfg['fee']),f.max_notional)
    qty=min(amount/price,equity*cfg['risk']/dist,max(0,equity*cfg['aggregate_risk']-open_risk)/dist,
            previous_volume*cfg['participation_cap'],f.max_qty,f.market_max)
    qty=floor(qty*cfg['fill_fraction'],f.step)
    if f.market_step:qty=floor(qty,f.market_step);qty=floor(qty,f.step)
    if price<f.min_price or price>f.max_price:return 0.,'price_filter'
    if qty<=0 or qty<max(f.min_qty,f.market_min) or qty*price<f.min_notional:return 0.,'min_filter_or_balance'
    return qty,'partial' if cfg['fill_fraction']<1 else 'filled'
def intrabar(o,h,l,stop,target):
    ambiguity=l<=stop and h>=target
    if l<=stop:return min(o,stop),'stop',ambiguity
    if h>=target:return max(o,target),'target',ambiguity
    return None,None,False
def net_pnl(qty,entry,exit,fee):return qty*(exit-entry)-qty*(entry+exit)*fee
@dataclass
class Risk:
    initial:float
    day:str=''
    day_equity:float=0.
    peak:float=0.
    daily_halt:bool=False
    permanent_halt:bool=False
    orders:int=0
    def observe(self,equity,day,cfg=CFG):
        if day!=self.day:self.day=day;self.day_equity=equity;self.daily_halt=False;self.orders=0
        self.peak=max(self.peak,self.initial,equity)
        self.daily_halt |= equity<=self.day_equity*(1-cfg['daily_loss'])
        self.permanent_halt |= equity<=self.peak*(1-cfg['max_drawdown'])
        return self.daily_halt or self.permanent_halt or self.orders>=cfg['max_orders_day']
