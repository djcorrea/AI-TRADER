"""Recompute statistics from saved trade/equity evidence without rerunning execution."""
import json
import pandas as pd
from lab.common import ROOT,dump,utc,sha
from lab.stats import metrics,status
def run():
    rows=json.loads((ROOT/'results/experiments.json').read_text(encoding='utf-8'))
    report=json.loads((ROOT/'results/report.json').read_text(encoding='utf-8'))
    for m in report.get('buy_hold',{}).values():
        m['ci95_block']=None;m['ci_familywise']=None;m['p_adjusted_bootstrap']=None
        m['confidence_rule']='Few one-shot holdings are not an independent trade sample'
    for row in rows:
        key=row['id'];trades=pd.read_parquet(ROOT/f'results/{key}_trades.parquet').to_dict('records')
        curve=pd.read_parquet(ROOT/f'results/{key}_equity.parquet').to_dict('records')
        result={'trades':trades,'curve':curve,'risk_halted':row['metrics'].get('risk_halted',False)}
        row['metrics']=metrics(result,tests=120)
        row['status']=status(row['metrics'],report['buy_hold'].get(row['period']))
    dump(ROOT/'results/experiments.json',rows)
    report['statistics_recomputed']=utc();report['statistics_sha256']=sha(ROOT/'lab/stats.py')
    report['confidence_minimum']='28 calendar days, 8 trading days; otherwise confidence unavailable'
    dump(ROOT/'results/report.json',report)
    print(f'Recomputed {len(rows)} experiment metrics from recorded evidence.')
if __name__=='__main__':run()
