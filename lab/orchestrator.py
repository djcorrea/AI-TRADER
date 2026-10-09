import time,json
import pandas as pd
from .common import ROOT,CFG,dump,utc,config_hash,sha
from .data import load
from .features import make,cross
from .execution import snapshot_filters
from .strategies import FAMILIES,RULES
from .backtest import simulate,buy_hold
from .stats import metrics,status
from .models import ml_run
def run(resume=False):
    start=time.monotonic();series={}
    for s in CFG['symbols']:
        df=load(s)
        if len(df):series[s]=make(df)
    if not series:raise RuntimeError('No validated datasets. Run data command first.')
    cross(series)
    snapshot=ROOT/'data/exchange_snapshot.json'
    filters=snapshot_filters(json.loads(snapshot.read_text(encoding='utf-8'))['data']['symbols']) if snapshot.exists() else {}
    periods={'discovery':('2024-03-01','2025-01-01'), 'validation':('2025-01-01','2025-07-01'),
             'retrospective_holdout':('2025-07-01','2026-01-01')}
    entries=[];benchmark={};count=0
    source_files=['lab/backtest.py','lab/execution.py','lab/features.py','lab/strategies.py','config.json']
    fingerprint={p:sha(ROOT/p) for p in source_files}
    checkpoint=ROOT/'research/checkpoint.json'
    prior=[]
    if resume and checkpoint.exists():
        saved=json.loads(checkpoint.read_text(encoding='utf-8'))
        if saved['sources']!=fingerprint:raise RuntimeError('Checkpoint source mismatch: rerun without resume')
        if (ROOT/'results/experiments.json').exists():prior=json.loads((ROOT/'results/experiments.json').read_text(encoding='utf-8'))
    dump(checkpoint,{'sources':fingerprint,'config_hash':config_hash(),'started':utc()})
    (ROOT/'results').mkdir(exist_ok=True)
    def experiment(name,period,variant=1.,scenario=None,alternate=None):
        nonlocal count
        if count>=CFG['max_experiments'] or time.monotonic()-start>CFG['max_research_seconds']:raise RuntimeError('research budget reached; partial records preserved')
        count+=1
        key=f'{count:03}_{name}_{period}'
        cached=next((e for e in prior if e['id']==key and e['variant']==variant and e['scenario']==(scenario or {})),None)
        if cached:
            entries.append(cached);print(f'Resumed {key}',flush=True);return cached
        result=simulate(alternate or series,name,*periods[period],filters,variant,scenario)
        m=metrics(result,tests=120);decision=status(m,benchmark.get(period))
        pd.DataFrame(result['trades']).to_parquet(ROOT/f'results/{key}_trades.parquet',index=False)
        # Store sampled equity for dashboard; full equity remains parquet.
        pd.DataFrame(result['curve']).to_parquet(ROOT/f'results/{key}_equity.parquet',index=False)
        entry={'id':key,'strategy':name,'period':period,'variant':variant,'scenario':scenario or {},'metrics':m,
            'status':decision,'curve':result['curve'][::max(1,len(result['curve'])//300)],
            'hypothesis':RULES.get(name,'seeded random / cash control'),
            'orders_filled':sum(o['qty']>0 for o in result['orders']),'orders_cancelled':sum(o['qty']==0 for o in result['orders'])}
        entries.append(entry);dump(ROOT/'results/experiments.json',entries)
        print(f'{key}: {m["net_return"]:.2%}, n={m["trades"]}, {decision}',flush=True)
        return entry
    for period,(lo,hi) in periods.items():
        bh=buy_hold(series,lo,hi,filters);benchmark[period]=metrics(bh)
        benchmark[period]['note']='Equal weight on causally eligible initial universe; min notional may leave all cash. Full allocation baseline differs from risk-capped candidates.'
        pd.DataFrame(bh['curve']).to_parquet(ROOT/f'results/buy_hold_{period}.parquet',index=False)
    for name in FAMILIES:
        if name=='ml':continue
        # Sensitivity only in discovery; fixed variant 1 remains main specification.
        for variant in (.9,1.,1.1):experiment(name,'discovery',variant)
        for period in ('validation','retrospective_holdout'):experiment(name,period)
        experiment(name,'retrospective_holdout',scenario={'fee':.0015,'spread_half':.001,'slippage':.001,'fill_fraction':.5})
        experiment(name,'retrospective_holdout',scenario={'outage':True,'latency_bars':2})
    for seed in (20261009,20261010,20261011):
        # Ex ante random rate .01; similar holding/risk rules, NOT claimed exact matched frequency.
        # Random signal seed is changed via per-series column, deterministic for this run.
        for period in ('validation','retrospective_holdout'):
            e=experiment('random',period,scenario={'random_seed':seed});e['random_seed']=seed
    ml=ml_run();count+=len(ml)
    # Model probabilities from the fold frozen before July are aligned to CLOSED 15m bars.
    # Label outcomes are explicitly excluded from the strategy input.
    minute_series={s:make(load(s,'1m'),1) for s in CFG['ml_symbols'] if not load(s,'1m').empty}
    cross(minute_series)
    for horizon in CFG['ml_horizons_minutes']:
        path=ROOT/f'models/logistic_{horizon}m_fold2_predictions.parquet'
        if not path.exists():continue
        predictions=pd.read_parquet(path,columns=['t','symbol','p_positive_net','ev_net'])
        for s,x in minute_series.items():
            p=predictions[predictions.symbol==s].set_index('t')
            m=p.reindex(x.t)
            x['ml_signal']=(m.ev_net.to_numpy()>.002)&(m.p_positive_net.to_numpy()>.55)
        experiment('ml','retrospective_holdout',scenario={'ml_horizon_minutes':horizon,'interval_minutes':1},alternate=minute_series)
    dump(ROOT/'results/experiments.json',entries)
    frozen=utc()
    report={'generated':frozen,'config':CFG,'config_hash':config_hash(),'source_hashes':fingerprint,'symbols_observed':list(series),
        'periods':periods,'experiments_completed':count,'backtests':len(entries),'model_fits':len(ml),
        'cash':{'net_return':0.,'max_drawdown':0.,'trades':0},'buy_hold':benchmark,
        'promotion':'BLOCKED','promotion_blockers':CFG['promotion_blockers'],
        'prospective_final':{'start_after':frozen,'status':'NO_OBSERVATIONS_YET','model_versions':'See registry; no active model'},
        'microstructure':'UNAVAILABLE: no historical book depth/spread','news':'DISABLED: no validated timestamped feed',
        'pbo_dsr':'NOT_ESTIMATED: dependence and trial return matrix not sufficient for justified estimate',
        'limitations':['Manual candidate universe: historical volume ranking reduces but does not eliminate selection bias',
            'Current filters are proxies, not historically point-in-time filters',
            'Historical spread/slippage/partial fills are scenario assumptions, not observed execution',
            'Both intrabar barriers touched: stop wins and ambiguity logged; market gaps may exceed risk limit',
            '2024-2025 has already been seen in V1; chronological holdout is retrospective and not pristine',
            'No FX conversion cost, taxes, hosting or downtime of the PC priced into returns',
            'ML sample cap and stride; conditional net payoff assumptions may change under a new regime',
            'No full combinatorial purged CV or HMM; synchronized expanding folds with purge and embargo used',
            'Block confidence and Bonferroni guard do not establish stationarity or guarantee future returns'],
        'elapsed_seconds':time.monotonic()-start,
        'data_quality':json.loads((ROOT/'data/quality.json').read_text())}
    dump(ROOT/'results/report.json',report)
    dump(ROOT/'research/strategy_registry.json',[{'name':n,'rule':RULES[n],'activation':None,'promotion':'BLOCKED','rollback_to':None,'frozen':frozen,
        'stop':'2 ATR at signal close; 3 ATR trail updated after close','target':'3 ATR or mean at signal time','max_hold':'16 bars trend / 8 reversion',
        'risk_per_trade':.005,'position_cap':.25,'aggregate_cap':.5} for n in RULES])
    print(f'Done: {count} experiments. Promotion blocked.',flush=True)
