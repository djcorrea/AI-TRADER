"""Bounded retrospective pilot on audited BTC/ETH/SOL, with isolated outputs.

Predeclared rules and splits. This pilot cannot activate a strategy or replace V2.
"""
import json
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss, log_loss

from .common import ROOT, CFG, dump, sha, state_path, utc
from .data import validate
from .features import make, cross, FEATURES
from .backtest import simulate, buy_hold
from .stats import metrics, status
from .models import labels, purge_train, fit_calibrated

RULES = ('trend', 'pullback', 'compression', 'breakout', 'mean_regime', 'range')
PERIODS = {'discovery': ('2024-03-01','2025-01-01'),
           'validation': ('2025-01-01','2025-07-01'),
           'retrospective_test': ('2025-07-01','2026-01-01')}


def prepare():
    audit_pointer = state_path('rebuild-audits/latest.json')
    audit = json.loads(__import__('pathlib').Path(json.loads(audit_pointer.read_text())['report_path']).read_text())
    checked = {(r['symbol'],r['month']) for r in audit['verified']
               if r['baseline_archive_match'] and not r['quality']['gaps']}
    sources, minutes, bars = {}, {}, {}
    for symbol in CFG['ml_symbols']:
        frames, provenance = [], []
        for month in pd.period_range(CFG['start'],pd.Timestamp(CFG['end_exclusive'])-pd.Timedelta(days=1),freq='M'):
            month = str(month)
            if (symbol,month) not in checked:
                raise RuntimeError(f'Unaudited required pilot source: {symbol} {month}')
            p = ROOT/f'data/parquet/{symbol}/1m/{month}.parquet'
            meta = json.loads(p.with_suffix('.json').read_text())
            archive = ROOT/'data/archives'/f'{symbol}-1m-{month}.zip'
            if sha(p)!=meta['parquet_sha256'] or sha(archive)!=meta['archive_sha256']:
                raise RuntimeError('Source changed after audit')
            frames.append(pd.read_parquet(p));provenance.append({'month':month,'parquet_sha256':sha(p),'archive_sha256':sha(archive)})
        frame = pd.concat(frames,ignore_index=True)
        q = validate(frame,60000)
        if not q['valid'] or q['gaps']:
            raise RuntimeError(f'Non-contiguous pilot history: {symbol}')
        minutes[symbol] = make(frame,1)
        grouped = frame.assign(bucket=frame.t//900000*900000).groupby('bucket',sort=True)
        coarse = grouped.agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last'),v=('v','sum'),qv=('qv','sum'),
                             n=('n','sum'),tbv=('tbv','sum'),tbqv=('tbqv','sum'),count=('t','size'))
        coarse = coarse[coarse['count']==15].drop(columns='count').reset_index().rename(columns={'bucket':'t'})
        coarse['ct']=coarse.t+899999
        bars[symbol]=make(coarse,15);sources[symbol]=provenance
    cross(minutes);cross(bars)
    return minutes,bars,sources


def run(max_seconds=900):
    if not 1<=max_seconds<=CFG['max_research_seconds']:
        raise ValueError('Research budget exceeds frozen configuration')
    started=time.monotonic()
    minutes,bars,sources=prepare()
    directory=state_path('v3-research')/str(time.time_ns());directory.mkdir(parents=True)
    manifest={'status':'RUNNING','created':utc(),'sources':sources,
              'source_hashes':{p:sha(ROOT/p) for p in ('lab/research_v3.py','lab/backtest.py','lab/models.py','lab/features.py','lab/execution.py','lab/strategies.py','config.json')},
              'universe':list(bars),'periods':PERIODS,'rules':list(RULES),'discovery_variants':[.9,1.,1.1],
              'validation_and_test_variant':1.,'ml_horizon_minutes':30,'ml_model':'standardized_logistic_C_0.1',
              'ml_max_fit_rows':20000,'ml_max_calibration_rows':5000,'ml_max_test_rows':10000,
              'maximum_tests':120,'max_seconds':max_seconds,'final_virgin_test':False,
              'strategy_approval':'NONE','paper_candidates':[],'real_orders':False,
              'limitations':['Pilot universe restricted to BTC/ETH/SOL, not a historical full-market universe.',
                             '2024-2025 already exposed in V1/V2; chronological out-of-sample is retrospective.',
                             'Historical filters, spreads, queue and account fees are assumptions.',
                             'Predictive label outcomes overlap and are not portfolio PNL.',
                             'Prospective eligibility and execution latency still require validation.']}
    dump(directory/'manifest.json',manifest)
    entries=[];ml=[];benchmarks={}

    def checkpoint():
        dump(directory/'experiments.json',entries);dump(directory/'models.json',ml)
        manifest['elapsed_seconds']=time.monotonic()-started
        dump(directory/'manifest.json',manifest)
        dump(state_path('v3-research/latest.json'),{'directory':str(directory)})

    def budget():
        if time.monotonic()-started>=max_seconds:
            raise TimeoutError('Research time budget; completed artifacts retained')
        if len(entries)>=CFG['max_experiments']:
            raise TimeoutError('Experiment budget')

    def experiment(rule,period,variant=1.,scenario=None):
        budget()
        result=simulate(bars,rule,*PERIODS[period],variant=variant,scenario=scenario)
        measured=metrics(result,tests=120)
        decision=status(measured,benchmarks[period]['buy_hold'])
        # The pilot's retrospective status never bypasses prospective requirements.
        if decision=='CANDIDATA_RETROSPECTIVA':decision='INCONCLUSIVO_PROSPECTIVE_REQUIRED'
        key=f'{len(entries)+1:03}_{rule}_{period}'
        pd.DataFrame(result['trades']).to_parquet(directory/f'{key}_trades.parquet',index=False)
        pd.DataFrame(result['curve']).to_parquet(directory/f'{key}_equity.parquet',index=False)
        entries.append({'id':key,'rule':rule,'period':period,'variant':variant,'scenario':scenario or {},'metrics':measured,'status':decision})
        checkpoint();print(f"V3 {key}: {measured['net_return']:.2%}, {measured['trades']} trades, {decision}",flush=True)

    try:
        for period,dates in PERIODS.items():
            budget()
            result=buy_hold(bars,*dates)
            benchmarks[period]={'cash':{'net_return':0.,'ending_brl':CFG['initial_brl'],'trades':0},'buy_hold':metrics(result)}
            pd.DataFrame(result['curve']).to_parquet(directory/f'buy_hold_{period}.parquet',index=False)
        manifest['benchmarks']=benchmarks
        for rule in RULES:
            for variant in (.9,1.,1.1):experiment(rule,'discovery',variant)
            for period in ('validation','retrospective_test'):experiment(rule,period)
            experiment(rule,'retrospective_test',scenario={'fee':.0015,'spread_half':.001,'slippage':.001,'fill_fraction':.5})
        for period in PERIODS:experiment('random',period,scenario={'random_seed':CFG['seed']})
        pieces=[]
        for symbol,frame in minutes.items():
            labeled=labels(frame,30).iloc[::15].copy();labeled['symbol']=symbol
            pieces.append(labeled.dropna(subset=FEATURES+['forward_net','label_end']))
        labeled=pd.concat(pieces).sort_values(['available_t','symbol']).reset_index(drop=True)
        for fold,(begin,end) in enumerate([('2025-01-01','2025-04-01'),('2025-04-01','2025-07-01'),('2025-07-01','2026-01-01')]):
            budget()
            cutoff=int(pd.Timestamp(begin,tz='UTC').timestamp()*1000);until=int(pd.Timestamp(end,tz='UTC').timestamp()*1000)
            train=purge_train(labeled,cutoff,30*60000)
            cut=int(train.available_t.quantile(.8))
            fit=purge_train(train,cut,30*60000).tail(20000)
            calibration=train[train.available_t>=cut].tail(5000)
            test=labeled[(labeled.available_t>=cutoff)&(labeled.available_t<until)&(labeled.label_end<until)].head(10000)
            if len(fit)<1000 or len(calibration)<200 or len(test)<200:
                ml.append({'fold':fold,'status':'INCONCLUSIVE_INSUFFICIENT_DATA'});checkpoint();continue
            try:
                factory=lambda:make_pipeline(StandardScaler(),LogisticRegression(C=.1,max_iter=250,random_state=CFG['seed']))
                model,calibrator,probabilities=fit_calibrated(factory,fit,calibration,test)
            except ValueError as error:
                ml.append({'fold':fold,'status':'INCONCLUSIVE_MISSING_CLASSES','reason':str(error)});checkpoint();continue
            means=np.array([fit.loc[fit.label==label,'forward_net'].mean() for label in (-1,0,1)])
            ev=probabilities@means;p=probabilities[:,2];candidate=(ev>.002)&(p>.55)
            constant=np.full(len(test),(fit.label==1).mean())
            bundle=directory/f'logistic_30m_fold{fold}.joblib'
            joblib.dump({'model':model,'calibrator':calibrator,'features':FEATURES,'mu_negative':means[0],'mu_neutral':means[1],'mu_positive':means[2]},bundle)
            prediction=test[['t','symbol','forward_net','label_end']].copy()
            prediction['p_positive_net']=p;prediction['ev_net']=ev;prediction['candidate']=candidate
            prediction.to_parquet(directory/f'logistic_30m_fold{fold}_predictions.parquet',index=False)
            ml.append({'fold':fold,'begin':begin,'end':end,'fit_rows':len(fit),'calibration_rows':len(calibration),'test_rows':len(test),
                       'fit_label_end_max':int(fit.label_end.max()),'calibration_first':int(calibration.available_t.min()),
                       'calibration_label_end_max':int(calibration.label_end.max()),'test_first':int(test.available_t.min()),
                       'test_label_end_max':int(test.label_end.max()),'brier':float(brier_score_loss(test.label==1,p)),
                       'null_brier':float(brier_score_loss(test.label==1,constant)),
                       'multiclass_log_loss':float(log_loss(test.label,probabilities,labels=[-1,0,1])),
                       'predictive_candidates':int(candidate.sum()),'model_sha256':sha(bundle),
                       'status':'INCONCLUSIVE_PREDICTIVE_ONLY','activation':None})
            checkpoint();print(f'V3 ML fold {fold}: {candidate.sum()} predictive candidates, inactive',flush=True)
        manifest['status']='RETROSPECTIVE_PILOT_COMPLETED'
    except TimeoutError as error:
        manifest.update(status='PARTIAL_TIME_OR_EXPERIMENT_BUDGET',stopped_reason=str(error))
    checkpoint()
    return manifest
