"""Read-only delivery integrity audit, independent from acquisition."""
import json,time
import pandas as pd
import duckdb
from lab.common import ROOT,dump,sha,utc
from lab.data import validate
def run():
    manifest=json.loads((ROOT/'data/download_manifest.json').read_text(encoding='utf-8'))
    errors=[];checked=0;start=time.monotonic()
    for r in manifest['records']:
        if r['status']!='OK':continue
        file=ROOT/f'data/parquet/{r["symbol"]}/1m/{r["month"]}.parquet'
        archive=ROOT/'data/archives'/f'{r["symbol"]}-1m-{r["month"]}.zip'
        if sha(file)!=r['parquet_sha256']:errors.append({'file':str(file),'reason':'parquet hash mismatch'})
        if sha(archive)!=r['archive_sha256']:errors.append({'file':str(archive),'reason':'archive hash mismatch'})
        checked+=1
    derived=[]
    for p in sorted((ROOT/'data/derived').glob('*.parquet')):
        interval=p.stem.split('_')[-1];step={'5m':300000,'15m':900000,'1h':3600000,'4h':14400000}[interval]
        q=validate(pd.read_parquet(p),step);derived.append({'file':p.name,'sha256':sha(p),'quality':q})
        if not q['valid']:errors.append({'file':p.name,'reason':q['errors']})
    with duckdb.connect(str(ROOT/'data/lab.duckdb'),read_only=True) as db:
        count=db.execute('SELECT count(*) FROM bars').fetchone()[0]
    dump(ROOT/'reports/data_audit.json',{'at':utc(),'archive_and_parquet_pairs_verified':checked,'derived':derived,
        'duckdb_15m_rows':count,'errors':errors,'valid':not errors,'elapsed_seconds':time.monotonic()-start})
    if errors:raise RuntimeError('DATA INTEGRITY FAILED: tests invalidated')
    print(f'Integrity passed: {checked} archive/Parquet pairs, {len(derived)} derived datasets, {count} database rows.')
if __name__=='__main__':run()
