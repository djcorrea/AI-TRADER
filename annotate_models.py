"""Annotate actual evaluated coverage directly from stored predictions."""
import json
import pandas as pd
from lab.common import ROOT,dump
def run():
    doc=json.loads((ROOT/'results/models.json').read_text(encoding='utf-8'))
    reg=json.loads((ROOT/'models/registry.json').read_text(encoding='utf-8'))
    for row in doc['results']:
        version=f'{row["model"]}_{row["horizon_minutes"]}m_fold{row["fold"]}'
        x=pd.read_parquet(ROOT/f'models/{version}_predictions.parquet',columns=['t','symbol','label_end'])
        row['actual_test_first_available_ms']=int(x.t.min()+59999)
        row['actual_test_last_available_ms']=int(x.t.max()+59999)
        row['actual_last_label_end_ms']=int(x.label_end.max())
        row['symbols_evaluated']=sorted(x.symbol.unique().tolist())
        for entry in reg:
            if entry['version']==version:entry['metrics']=row
    dump(ROOT/'results/models.json',doc);dump(ROOT/'models/registry.json',reg)
    print('Actual model coverage annotated for 36 fits.')
if __name__=='__main__':run()
