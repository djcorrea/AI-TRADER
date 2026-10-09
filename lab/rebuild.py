"""Incremental monthly recovery without replacing the migrated V2 manifest.

Sequential downloads bound concurrent RAM. Immutable per-run audit files live in
STATE_DIR; only verified public caches are written beneath the ignored data paths.
"""
import hashlib
import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from .common import CFG, ROOT, dump, sha, state_path, utc
from .data import parse_archive, validate, NETWORK_GATE


def rebuild(max_archives=24, max_seconds=300, end_date=None, symbols=None):
    if not 1 <= max_archives <= 720 or not 1 <= max_seconds <= CFG['max_download_seconds']:
        raise ValueError('Archive or time limit outside configured budget')
    selected = symbols or CFG['symbols']
    if not selected or any(s not in CFG['symbols'] for s in selected):
        raise ValueError('Select only configured public symbols')
    until = pd.Timestamp(end_date or CFG['end_exclusive'])
    if until.day != 1 or until > pd.Timestamp.now(tz='UTC').tz_localize(None).normalize().replace(day=1):
        raise ValueError('Exclusive end date must be the first of a completed month')
    if until <= pd.Timestamp(CFG['start']):
        raise ValueError('End date must follow start')
    baseline = json.loads((ROOT/'data/download_manifest.json').read_text())
    reference = {(r['symbol'], r['month']): r for r in baseline['records']}
    started = time.monotonic()
    deadline = started + max_seconds
    downloaded = 0
    attempts = 0
    records = []
    run_path = state_path('rebuild')/f'{time.time_ns()}.json'
    byte_limit = CFG['max_archive_bytes']
    archive_limit = 16_000_000
    disk_limit = CFG['max_disk_bytes']

    def disk_bytes():
        return sum(p.stat().st_size for p in (ROOT/'data').rglob('*') if p.is_file())

    def fetch(url, limit):
        nonlocal downloaded
        if time.monotonic() >= deadline:
            raise RuntimeError('TIME_BUDGET')
        gate = json.loads(NETWORK_GATE.read_text()) if NETWORK_GATE.exists() else {}
        if time.time() < gate.get('not_before_epoch', 0):
            raise RuntimeError('RETRY_AFTER_GATE')
        try:
            with urllib.request.urlopen(url, timeout=min(20, max(.1, deadline-time.monotonic()))) as response:
                chunks = []
                size = 0
                while True:
                    if time.monotonic() >= deadline:
                        raise RuntimeError('TIME_BUDGET')
                    allowance = min(32768, limit-size, byte_limit-downloaded)
                    if allowance <= 0:
                        raise RuntimeError('BYTE_BUDGET')
                    chunk = response.read(allowance)
                    if not chunk:
                        return b''.join(chunks)
                    downloaded += len(chunk)
                    size += len(chunk)
                    chunks.append(chunk)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            if error.code in (418, 429):
                delay = float(error.headers.get('Retry-After', 60))
                dump(NETWORK_GATE, {'not_before_epoch': time.time()+delay, 'status': error.code, 'observed': utc()})
            raise

    def save(status):
        report = {'status': status, 'generated': utc(), 'baseline_manifest_sha256': sha(ROOT/'data/download_manifest.json'),
                  'requested_period': {'start': CFG['start'], 'end_exclusive': str(until.date())},
                  'records': records, 'bytes_this_run': downloaded, 'attempts': attempts,
                  'elapsed_seconds': time.monotonic()-started, 'disk_bytes': disk_bytes(),
                  'limits': {'seconds': max_seconds, 'archives': max_archives, 'bytes': byte_limit, 'disk_bytes': disk_limit,
                             'workers': 1, 'max_uncompressed_archive_bytes': 64_000_000},
                  'strategy_approval': 'NONE', 'real_orders': False}
        dump(run_path, report)
        dump(state_path('rebuild/latest.json'), {'report_path': str(run_path)})
        return report

    for symbol in selected:
        for month in pd.period_range(CFG['start'], until-pd.Timedelta(days=1), freq='M'):
            month = str(month)
            record = {'symbol': symbol, 'month': month}
            name = f'{symbol}-1m-{month}.zip'
            out = ROOT/f'data/parquet/{symbol}/1m/{month}.parquet'
            meta = out.with_suffix('.json')
            archive = ROOT/'data/archives'/name
            previous = reference.get((symbol, month), {})
            try:
                if time.monotonic() >= deadline:
                    return save('TIME_BUDGET')
                if out.exists() or meta.exists() or archive.exists():
                    cached = json.loads(meta.read_text())
                    if cached.get('status') != 'OK' or sha(out) != cached['parquet_sha256'] or sha(archive) != cached['archive_sha256']:
                        raise ValueError('Cached checksum mismatch; existing bytes preserved')
                    quality = validate(pd.read_parquet(out), 60000)
                    if not quality['valid']:
                        raise ValueError(f'Cached candle integrity failure: {quality}')
                    record.update(cached, cache_reverified=True)
                else:
                    if attempts >= max_archives:
                        return save('ARCHIVE_BUDGET')
                    if downloaded+archive_limit+4096 > byte_limit:
                        return save('BYTE_BUDGET')
                    if disk_bytes()+archive_limit+64_000_000 > disk_limit:
                        return save('DISK_BUDGET')
                    attempts += 1
                    url = f'https://data.binance.vision/data/spot/monthly/klines/{symbol}/1m/{name}'
                    raw = fetch(url, archive_limit)
                    if raw is None:
                        record.update(status='NOT_AVAILABLE', url=url)
                        records.append(record); save('IN_PROGRESS'); continue
                    checksum = fetch(url+'.CHECKSUM', 4096)
                    digest = hashlib.sha256(raw).hexdigest()
                    if not checksum or checksum.decode().split()[0] != digest:
                        raise ValueError('Publisher checksum mismatch')
                    with zipfile.ZipFile(io.BytesIO(raw)) as zipped:
                        if len(zipped.infolist()) != 1 or sum(i.file_size for i in zipped.infolist()) > 64_000_000:
                            raise ValueError('Archive expansion budget or member count')
                    frame = parse_archive(raw)
                    quality = validate(frame, 60000)
                    if not quality['valid']:
                        raise ValueError(f'Candle integrity failure: {quality}')
                    buffer = io.BytesIO(); frame.to_parquet(buffer, index=False)
                    parquet = buffer.getvalue()
                    record.update(status='OK', url=url, retrieved=utc(), bytes=len(raw), quality=quality,
                                  archive_sha256=digest, parquet_sha256=hashlib.sha256(parquet).hexdigest())
                    metadata = json.dumps(record).encode()
                    if disk_bytes()+len(raw)+len(parquet)+len(metadata)+4096 > disk_limit:
                        return save('DISK_BUDGET')
                    out.parent.mkdir(parents=True, exist_ok=True); archive.parent.mkdir(parents=True, exist_ok=True)
                    for path, contents in [(archive, raw), (out, parquet)]:
                        temp = path.with_suffix(path.suffix+'.tmp'); temp.write_bytes(contents); temp.replace(path)
                    dump(meta, record)
                record['baseline_status'] = previous.get('status', 'NOT_IN_BASELINE')
                record['baseline_archive_match'] = (record['archive_sha256'] == previous.get('archive_sha256')) if previous.get('status') == 'OK' else None
                record['baseline_parquet_match'] = (record['parquet_sha256'] == previous.get('parquet_sha256')) if previous.get('status') == 'OK' else None
                if previous.get('status') == 'OK' and not record['baseline_archive_match']:
                    record['reproducibility'] = 'PUBLISHER_BYTES_DIFFER_FROM_BASELINE'
                records.append(record)
                save('IN_PROGRESS')
                print(f"{symbol} {month}: {record['status']}; gaps={record.get('quality',{}).get('gaps')}", flush=True)
            except Exception as error:
                records.append({**record, 'status': 'ERROR', 'error': str(error)})
                # Abort on a real error rather than hammering a denied endpoint.
                return save('BLOCKED')
    return save('REQUESTED_MONTHS_VERIFIED')
