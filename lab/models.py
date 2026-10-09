"""Synchronized expanding walk-forward; purged label end + embargo. Training-only scaler/calibration."""
import time, math
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, log_loss,confusion_matrix
from lightgbm import LGBMClassifier
from .common import ROOT,CFG,dump,utc,config_hash,sha
from .features import make,FEATURES
from .data import load
def labels(x,horizon):
    """Features at closed minute i; wait full minute; entry i+2 open; exit i+1+h close.
    Triple barrier is conservative when both touched. Thresholds .6%, net after friction.
    Actual targets must be available before training cutoff. This is a label, not a fill claim.
    """
    impact=CFG['spread_half']+CFG['slippage'];fee=CFG['fee']
    x=x.copy();entry=x.o.shift(-2)*(1+impact);last=x.c.shift(-(horizon+1))*(1-impact)
    net=last/entry*(1-fee)/(1+fee)-1
    x['forward_net']=net;x['label_end']=x.ct.shift(-(horizon+1))
    x['label']=np.select([net>.002,net<-.002],[1,-1],default=0)
    # Barrier first-touch labels; adverse tie, future label data never features.
    upper=x.o.shift(-2)*1.006;lower=x.o.shift(-2)*.994
    hit=np.zeros(len(x),dtype=int);touch=np.full(len(x),horizon+1,dtype=int)
    for j in range(2,horizon+2):
        high=x.h.shift(-j).to_numpy();low=x.l.shift(-j).to_numpy()
        active=(hit==0);down=active&(low<=lower.to_numpy());up=active&(high>=upper.to_numpy())&~down
        hit[down]=-1;hit[up]=1;touch[down|up]=j
    x['barrier_label']=hit
    x['available_t']=x.ct
    return x
def purge_train(df,cutoff,embargo_ms):
    return df[(df.available_t<cutoff-embargo_ms)&(df.label_end<cutoff-embargo_ms)]
def fit_calibrated(factory,fit,cal,test):
    model=factory();model.fit(fit[FEATURES],fit.label.astype(int))
    classes=list(model.classes_)
    if classes!=[-1,0,1]:raise ValueError('Three label classes required; insufficient sample')
    raw_cal=np.clip(model.predict_proba(cal[FEATURES]),1e-6,1-1e-6)
    # Multinomial logistic calibration on chronological training tail only.
    calibrator=LogisticRegression(C=.1,max_iter=250).fit(np.log(raw_cal),cal.label.astype(int))
    raw=np.clip(model.predict_proba(test[FEATURES]),1e-6,1-1e-6)
    calibrated=calibrator.predict_proba(np.log(raw))
    return model,calibrator,calibrated
def ml_run():
    start=time.monotonic();prepared={}
    for s in CFG['ml_symbols']:
        d=load(s,'1m')
        if not d.empty:prepared[s]=make(d,1)
    if not prepared:dump(ROOT/'results/models.json',{'status':'UNAVAILABLE'});return []
    # Cross asset features align timestamps; all train/test cuts shared across symbols.
    for base,col in [('BTCUSDT','btc_relative'),('ETHUSDT','eth_relative')]:
        if base in prepared:
            ref=prepared[base].set_index('t').ret16
            for s,x in prepared.items():x[col]=x.ret16-x.t.map(ref)
    factories={'logistic':lambda:make_pipeline(StandardScaler(),LogisticRegression(C=.1,max_iter=250,random_state=CFG['seed'])),
        'random_forest':lambda:RandomForestClassifier(n_estimators=80,max_depth=5,min_samples_leaf=100,n_jobs=2,random_state=CFG['seed']),
        'lightgbm':lambda:LGBMClassifier(n_estimators=100,num_leaves=15,max_depth=4,min_child_samples=100,learning_rate=.03,verbosity=-1,n_jobs=2,random_state=CFG['seed'])}
    folds=[('2025-01-01','2025-04-01'),('2025-04-01','2025-07-01'),('2025-07-01','2026-01-01')]
    results=[];registry=[]
    data_hashes={s:[sha(p) for p in sorted((ROOT/f'data/parquet/{s}/1m').glob('*.parquet'))] for s in prepared}
    for horizon in CFG['ml_horizons_minutes']:
        pieces=[]
        for s,x in prepared.items():
            y=labels(x,horizon).iloc[::CFG['ml_sample_stride']].copy();y['symbol']=s
            pieces.append(y.dropna(subset=FEATURES+['forward_net','label_end']))
        df=pd.concat(pieces).sort_values(['available_t','symbol']).reset_index(drop=True)
        for fold,(begin,end) in enumerate(folds):
            if time.monotonic()-start>CFG['max_research_seconds']:break
            cutoff=int(pd.Timestamp(begin,tz='UTC').timestamp()*1000);until=int(pd.Timestamp(end,tz='UTC').timestamp()*1000)
            train=purge_train(df,cutoff,horizon*60000)
            # Last training quarter calibrates probabilities; label purge between fit/calibrate.
            calibration_cut=int(train.available_t.quantile(.8))
            fit=purge_train(train,calibration_cut,horizon*60000)
            cal=train[train.available_t>=calibration_cut]
            fit=fit.iloc[-CFG['ml_max_train_rows']:];cal=cal.iloc[-20000:]
            test=df[(df.available_t>=cutoff)&(df.available_t<until)&(df.label_end<until)].iloc[:CFG['ml_max_test_rows']]
            if len(fit)<1000 or len(cal)<200 or len(test)<200:continue
            for name,factory in factories.items():
                model,calibrator,probs=fit_calibrated(factory,fit,cal,test)
                p=probs[:,2]
                positive=fit.forward_net[fit.label==1];negative=fit.forward_net[fit.label==-1];neutral=fit.forward_net[fit.label==0]
                # Conditional payoffs ALREADY net. Do not subtract costs a second time.
                mu_pos=float(positive.mean());mu_negative=float(negative.mean());mu_neutral=float(neutral.mean())
                ev=probs@np.array([mu_negative,mu_neutral,mu_pos])
                candidate=(ev>.002)&(p>.55)
                freq,mean=calibration_curve((test.label==1).astype(int),p,n_bins=10,strategy='uniform')
                constant=np.repeat(float((fit.label==1).mean()),len(test))
                row={'model':name,'horizon_minutes':horizon,'fold':fold,'begin':begin,'end':end,
                    'fit_rows':len(fit),'calibration_rows':len(cal),'test_rows':len(test),'train_label_end_max':int(fit.label_end.max()),
                    'fit_first_ms':int(fit.available_t.min()),'fit_last_ms':int(fit.available_t.max()),
                    'calibration_first_ms':int(cal.available_t.min()),'calibration_last_ms':int(cal.available_t.max()),
                    'test_first_ms':int(test.available_t.min()),'test_last_ms':int(test.available_t.max()),
                    'brier':float(brier_score_loss(test.label==1,p)),'null_brier':float(brier_score_loss(test.label==1,constant)),
                    'multiclass_log_loss':float(log_loss(test.label,probs,labels=[-1,0,1])),
                    'confusion_matrix':confusion_matrix(test.label,np.array([-1,0,1])[probs.argmax(axis=1)],labels=[-1,0,1]).tolist(),
                    'calibration':{'predicted':mean.tolist(),'observed':freq.tolist()},
                    'candidates':int(candidate.sum()),'candidate_label_net_mean':float(test.forward_net[candidate].mean()) if candidate.any() else None,
                    'label_positive_rate':float((test.label==1).mean()),'barrier_counts':test.barrier_label.value_counts().to_dict(),
                    'status':'INCONCLUSIVO','note':'Predictive evaluation only; overlapping label returns are not portfolio PNL.'}
                version=f'{name}_{horizon}m_fold{fold}';dest=ROOT/f'models/{version}.joblib';dest.parent.mkdir(parents=True,exist_ok=True)
                joblib.dump({'model':model,'calibrator':calibrator,'features':FEATURES,'mu_positive':mu_pos,'mu_negative':mu_negative,'mu_neutral':mu_neutral},dest)
                registry.append({'version':version,'created':utc(),'activation':None,'promotion':'BLOCKED','rollback_to':None,
                    'config_hash':config_hash(),'model_sha256':sha(dest),'train_end':begin,'metrics':row,
                    'data_hashes':data_hashes})
                # Prospective predictions are stored separately from backtest trade logs.
                out=test[['t','symbol','forward_net','label_end']].copy();out['p_positive_net']=p;out['p_negative_net']=probs[:,0];out['p_no_opportunity']=probs[:,1];out['ev_net']=ev;out['candidate']=candidate
                out.to_parquet(ROOT/f'models/{version}_predictions.parquet',index=False)
                results.append(row);print(f'ML {version}: Brier {row["brier"]:.4f}, candidates {row["candidates"]}',flush=True)
    dump(ROOT/'results/models.json',{'results':results,'elapsed_s':time.monotonic()-start,
         'label_classes':{'positive':1,'negative':-1,'no_opportunity':0},'classifier':'three-class calibrated probability: negative, no-opportunity, positive',
         'final_status':'No prospective final observations yet'})
    dump(ROOT/'models/registry.json',registry)
    return results
