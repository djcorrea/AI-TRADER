"""Audit recovered monthly bytes without replacing any V2 delivery evidence."""
import json
import time

import pandas as pd

from lab.common import ROOT, dump, sha, state_path, utc
from lab.data import validate


def run():
    started = time.monotonic()
    baseline = json.loads((ROOT/'data/download_manifest.json').read_text())
    expected = {(r['symbol'],r['month']):r for r in baseline['records'] if r['status']=='OK'}
    rows = 0
    verified = []
    errors = []
    edges = {}
    for path in sorted((ROOT/'data/parquet').glob('*/1m/*.parquet')):
        symbol, month = path.parent.parent.name, path.stem
        try:
            meta = json.loads(path.with_suffix('.json').read_text())
            archive = ROOT/'data/archives'/f'{symbol}-1m-{month}.zip'
            if meta.get('status')!='OK' or sha(path)!=meta['parquet_sha256'] or sha(archive)!=meta['archive_sha256']:
                raise ValueError('Archive/Parquet checksum mismatch')
            frame = pd.read_parquet(path)
            quality = validate(frame,60000)
            if not quality['valid']:
                raise ValueError(f'Invalid candles: {quality}')
            previous = expected.get((symbol,month),{})
            item = {'symbol':symbol,'month':month,'rows':len(frame),'quality':quality,
                    'archive_sha256':meta['archive_sha256'],'parquet_sha256':meta['parquet_sha256'],
                    'baseline_archive_match':meta['archive_sha256']==previous.get('archive_sha256') if previous else None,
                    'baseline_parquet_match':meta['parquet_sha256']==previous.get('parquet_sha256') if previous else None}
            if previous and not item['baseline_archive_match']:
                errors.append({'symbol':symbol,'month':month,'reason':'Baseline archive not reproduced'})
            rows += len(frame); verified.append(item)
            edges.setdefault(symbol,[]).append((month,quality['first'],quality['last']))
        except Exception as error:
            errors.append({'symbol':symbol,'month':month,'reason':str(error)})
    present = {(r['symbol'],r['month']) for r in verified}
    missing = [{'symbol':s,'month':m} for s,m in sorted(set(expected)-present)]
    boundary_gaps = []
    for symbol,months in edges.items():
        for left,right in zip(months,months[1:]):
            missing_bars = (right[1]-left[2])//60000-1
            if missing_bars:
                boundary_gaps.append({'symbol':symbol,'after_month':left[0],'before_month':right[0],'missing_bars':missing_bars})
    report = {'status':'COMPLETE_BASELINE_AUDIT' if not missing and not errors else 'PARTIAL_REBUILD_AUDIT',
              'generated':utc(),'baseline_manifest_sha256':sha(ROOT/'data/download_manifest.json'),
              'verified_pairs':len(verified),'verified_rows':rows,'verified':verified,
              'missing_baseline_pairs':missing,'baseline_unavailable':[{'symbol':r['symbol'],'month':r['month'],'status':r['status']} for r in baseline['records'] if r['status']!='OK'],
              'boundary_gaps':boundary_gaps,'errors':errors,
              'verified_subset_valid':not errors and not any(r['quality']['gaps'] for r in verified) and not boundary_gaps,
              'baseline_reproduced':not missing and not errors,
              'elapsed_seconds':time.monotonic()-started,'real_orders':False}
    out = state_path('rebuild-audits')/f'{time.time_ns()}.json'
    dump(out,report); dump(state_path('rebuild-audits/latest.json'),{'report_path':str(out)})
    print(f"{report['status']}: {len(verified)} verified pairs; {rows:,} minute rows; {len(missing)} missing baseline pairs; {len(errors)} errors")
    return report


if __name__=='__main__':run()
