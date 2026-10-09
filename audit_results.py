"""Independent numerical reconciliation and contract checks of stored evidence."""
import json,math,collections
import numpy as np
import pandas as pd
from lab.common import ROOT,CFG,dump,sha,utc
from lab.execution import snapshot_filters,Filters
def run():
    entries=json.loads((ROOT/'results/experiments.json').read_text(encoding='utf-8'));errors=[];reconciled=[]
    snapshot=json.loads((ROOT/'data/exchange_snapshot.json').read_text(encoding='utf-8'))
    filters=snapshot_filters(snapshot['data']['symbols']);fx=CFG['brl_per_usdt']
    for e in entries:
        key=e['id'];tr=pd.read_parquet(ROOT/f'results/{key}_trades.parquet');eq=pd.read_parquet(ROOT/f'results/{key}_equity.parquet')
        end=float(eq.equity_brl.iloc[-1]);total=float(tr.pnl_brl.sum()) if len(tr) else 0.
        if abs(end-500-total)>1e-6:errors.append({'id':key,'reason':'cash/trade PNL does not reconcile','delta':end-500-total})
        if not np.isfinite(eq.equity_brl).all() or (eq.equity_brl<0).any():errors.append({'id':key,'reason':'equity invalid'})
        if len(tr):
            if tr[['symbol','entry_t']].duplicated().any():errors.append({'id':key,'reason':'duplicate fills'})
            if (tr.exit_t<tr.entry_t).any():errors.append({'id':key,'reason':'exit before entry'})
            fee=e['scenario'].get('fee',CFG['fee'])
            recomputed=(tr.qty*(tr.exit-tr.entry)-tr.qty*(tr.entry+tr.exit)*fee)*fx
            if not np.allclose(recomputed,tr.pnl_brl,atol=1e-7,rtol=1e-9):errors.append({'id':key,'reason':'fee/PnL discrepancy'})
            for r in tr.to_dict('records'):
                f=filters.get(r['symbol'],Filters())
                if r['qty']*r['entry']+1e-8<f.min_notional:errors.append({'id':key,'reason':'entry min notional violation'})
                if f.step and abs(r['qty']/f.step-round(r['qty']/f.step))>1e-6:errors.append({'id':key,'reason':'lot precision violation'})
        reconciled.append({'id':key,'ending_brl':end,'sum_trade_pnl_brl':total,'rows':len(tr),
            'trades_sha256':sha(ROOT/f'results/{key}_trades.parquet'),'equity_sha256':sha(ROOT/f'results/{key}_equity.parquet')})
    report=json.loads((ROOT/'results/report.json').read_text(encoding='utf-8'))
    if report['promotion']!='BLOCKED':errors.append({'reason':'Unexpected promotion'})
    models=json.loads((ROOT/'models/registry.json').read_text(encoding='utf-8'))
    for m in models:
        if m['activation'] is not None:errors.append({'reason':'unexpected active model'})
        if m['metrics']['train_label_end_max']>=int(pd.Timestamp(m['train_end'],tz='UTC').timestamp()*1000):errors.append({'reason':'train label crosses validation'})
        if sha(ROOT/f'models/{m["version"]}.joblib')!=m['model_sha256']:errors.append({'reason':'model hash mismatch'})
    record={'at':utc(),'valid':not errors,'errors':errors,'experiments_reconciled':len(entries),'model_versions_verified':len(models),'evidence':reconciled,
        'what_is_verified':'Stored arithmetic, filters, duplicate fills, chronological label cutoff, hashes and disabled promotion',
        'what_is_not_proven':'Historical fill realism, stationarity, complete survivorship or profitability'}
    dump(ROOT/'reports/results_audit.json',record)
    if errors:raise RuntimeError(f'AUDIT FAILED: {errors[:3]}')
    print(f'Reconciliation passed for {len(entries)} backtests and {len(models)} models.')
if __name__=='__main__':run()
