"""Retrospective diagnostics. Future outcomes are never executable signals."""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .common import CFG, ROOT, dump, sha, state_path, utc
from .data import validate
from .features import make

HORIZONS = (5, 15, 30, 60, 240)


def break_even(fee, spread_half, slippage):
    for value in (fee, spread_half, slippage):
        if not np.isfinite(value) or not 0 <= value < 1:
            raise ValueError('Costs must be finite nonnegative fractions below one')
    impact = spread_half + slippage
    if impact >= 1:
        raise ValueError('Combined impact must be below one')
    return (1+impact)*(1+fee)/((1-impact)*(1-fee))-1


def cost_scenarios():
    base = {'fee': CFG['fee'], 'spread_half': CFG['spread_half'], 'slippage': CFG['slippage']}
    scenarios = [('TAKER', base, 1.),
                 ('MAKER_OPTIMISTIC', {'fee': CFG['fee'], 'spread_half': 0., 'slippage': 0.}, 1.),
                 ('MAKER_PARTIAL', {'fee': CFG['fee'], 'spread_half': 0., 'slippage': 0.}, .5),
                 ('CONSERVATIVE', {'fee': .0015, 'spread_half': .001, 'slippage': .001}, 1.),
                 ('ADVERSE', {'fee': .002, 'spread_half': .002, 'slippage': .002}, .5)]
    return [{'name': name, **cost, 'break_even_gross_return': break_even(**cost),
             'assumed_fill_fraction': fill, 'source': 'SCENARIO_ASSUMPTION',
             'fee_reference': 'https://www.binance.com/en/fee/trading',
             'fee_verified_for_account': False,
             'note': 'Maker queue, fills and account tier are unobserved. This is not strategy PNL.'}
            for name, cost, fill in scenarios]


def diagnostics(frame, symbol, horizons=HORIZONS):
    quality = validate(frame, 60000)
    if not quality['valid']:
        raise ValueError(f'Invalid source candles: {quality["errors"]}')
    x = make(frame, 1)
    dates = pd.to_datetime(x.ct, unit='ms', utc=True)
    prior_volume = x.v.shift().rolling(20).mean()
    volume_relative = x.v/prior_volume.replace(0, np.nan)
    threshold = break_even(CFG['fee'], CFG['spread_half'], CFG['slippage'])
    outputs = []
    for horizon in horizons:
        if horizon <= 0:
            raise ValueError('Horizon must be positive')
        contiguous = pd.Series(True, index=x.index)
        future_high = pd.Series(-np.inf, index=x.index)
        future_low = pd.Series(np.inf, index=x.index)
        first_touch = pd.Series(np.nan, index=x.index)
        for minute in range(1, horizon+1):
            contiguous &= x.t.shift(-minute).eq(x.t+minute*60000)
            highs, lows = x.h.shift(-minute), x.l.shift(-minute)
            future_high = pd.concat([future_high, highs], axis=1).max(axis=1)
            future_low = pd.concat([future_low, lows], axis=1).min(axis=1)
            first_touch = first_touch.mask(first_touch.isna() & (highs >= x.c*1.01), minute)
        forward = x.c.shift(-horizon)/x.c-1
        valid = contiguous & forward.notna() & x.atrn.notna() & volume_relative.notna()
        row = pd.DataFrame({'symbol': symbol, 'available_t': x.ct,
                            'label_end': x.ct.shift(-horizon), 'horizon_minutes': horizon,
                            'regime': x.regime, 'hour_utc': dates.dt.hour,
                            'weekday_utc': dates.dt.dayofweek,
                            'volatility': np.select([x.atrn < .001, x.atrn < .003],
                                                    ['LOW', 'MEDIUM'], default='HIGH'),
                            'volume': np.select([volume_relative < .5, volume_relative > 2],
                                                ['LOW', 'HIGH'], default='NORMAL'),
                            'forward_return': forward, 'mfe': future_high/x.c-1,
                            'mae': future_low/x.c-1, 'first_touch_1pct_minutes': first_touch,
                            'close_above_1pct': forward >= .01,
                            'touch_above_1pct': future_high >= x.c*1.01,
                            'close_above_assumed_cost': forward > threshold,
                            'relative_volume': volume_relative})
        outputs.append(row[valid].copy())
    return pd.concat(outputs, ignore_index=True) if outputs else pd.DataFrame()


def aggregate_diagnostics(rows):
    if rows.empty:
        return pd.DataFrame()
    keys = ['symbol', 'regime', 'hour_utc', 'weekday_utc', 'horizon_minutes', 'volatility', 'volume']
    return rows.groupby(keys, observed=True).agg(
        observations=('forward_return', 'size'), mean_forward_return=('forward_return', 'mean'),
        median_forward_return=('forward_return', 'median'), mean_mfe=('mfe', 'mean'),
        mean_mae=('mae', 'mean'), frequency_close_1pct=('close_above_1pct', 'mean'),
        frequency_touch_1pct=('touch_above_1pct', 'mean'),
        frequency_above_assumed_cost=('close_above_assumed_cost', 'mean'),
        median_time_to_1pct=('first_touch_1pct_minutes', 'median'),
        first_available_t=('available_t', 'min'), last_label_end=('label_end', 'max')
    ).reset_index()


def verified_recent_minutes(symbol, max_rows):
    frames, sources, count = [], [], 0
    for path in reversed(sorted((ROOT/f'data/parquet/{symbol}/1m').glob('*.parquet'))):
        meta_path = path.with_suffix('.json')
        if not meta_path.exists():
            raise ValueError(f'Missing source manifest: {path.name}')
        meta = json.loads(meta_path.read_text())
        if meta.get('status') != 'OK' or sha(path) != meta.get('parquet_sha256'):
            raise ValueError(f'Parquet checksum mismatch: {path.name}')
        archive = ROOT/'data/archives'/f'{symbol}-1m-{path.stem}.zip'
        if not archive.exists() or sha(archive) != meta.get('archive_sha256'):
            raise ValueError(f'Archive checksum mismatch: {archive.name}')
        frame = pd.read_parquet(path)
        frames.append(frame); count += len(frame)
        sources.append({'file': str(path.relative_to(ROOT)), 'sha256': meta['parquet_sha256'],
                        'archive_sha256': meta['archive_sha256'], 'url': meta.get('url')})
        if count >= max_rows:
            break
    if not frames:
        return pd.DataFrame(), []
    frame = pd.concat(list(reversed(frames)), ignore_index=True).tail(max_rows).reset_index(drop=True)
    return frame, sources


def build(max_rows=100000, max_seconds=300):
    if not 500 <= max_rows <= 250000 or not 0 < max_seconds <= 1800:
        raise ValueError('Rows must be 500..250000 and runtime 1..1800 seconds')
    started = time.monotonic()
    out = state_path('opportunities')
    # Separate immutable runs: old research evidence remains available.
    run_id = time.time_ns()
    directory = out/str(run_id)
    sources, completed, skipped = {}, [], []
    for symbol in CFG['symbols']:
        if time.monotonic()-started >= max_seconds:
            skipped.append({'symbol': symbol, 'reason': 'TIME_BUDGET'}); continue
        frame, provenance = verified_recent_minutes(symbol, max_rows)
        if frame.empty:
            skipped.append({'symbol': symbol, 'reason': 'NO_MINUTE_DATA'}); continue
        directory.mkdir(parents=True, exist_ok=True)
        groups = aggregate_diagnostics(diagnostics(frame, symbol))
        if groups.empty:
            skipped.append({'symbol': symbol, 'reason': 'INSUFFICIENT_CONTIGUOUS_DATA'}); continue
        groups.to_parquet(directory/f'{symbol}.parquet', index=False)
        completed.append(symbol); sources[symbol] = provenance
    if not completed:
        raise RuntimeError('No verified contiguous minute datasets; rebuild public candles before discovery')
    report = {'status': 'RETROSPECTIVE_DIAGNOSTICS', 'generated': utc(), 'run_id': str(run_id),
              'dataset_directory': str(directory), 'symbols': completed, 'skipped': skipped,
              'source_hashes': sources, 'max_rows_per_symbol': max_rows,
              'elapsed_seconds': time.monotonic()-started, 'horizons_minutes': list(HORIZONS),
              'cost_scenarios': cost_scenarios(), 'strategy_approval': 'NONE',
              'known_research_period': {'start': '2024-01-01', 'end_exclusive': '2026-01-01'},
              'final_virgin_test': False,
              'limitations': ['Overlapping outcomes are dependent observations, not independent trades.',
                              'MFE/MAE use future OHLC only for retrospective diagnostics.',
                              'First touch uses candle resolution; intrabar sequence is unknown.',
                              'Close price comparisons do not model executable entries or fills.',
                              'Current manual universe and historical filters remain incomplete.',
                              'Fee and maker assumptions are not verified account-specific fees.',
                              'Post-2025 periods are not classified as virgin without an exposure ledger.']}
    dump(out/'report.json', report)
    return report


def read_map(symbol=None, horizon=None, regime=None, limit=100):
    import duckdb
    path = state_path('opportunities/report.json')
    if not path.exists():
        return {'status': 'UNAVAILABLE', 'rows': [], 'cost_scenarios': cost_scenarios(),
                'reason': 'Minute candles have not been rebuilt and audited in this environment'}
    report = json.loads(path.read_text())
    directory = Path(report['dataset_directory']).resolve()
    if not directory.is_relative_to(state_path('opportunities').resolve()):
        raise ValueError('Invalid opportunity dataset location')
    clauses, params = [], []
    for name, value in [('symbol', symbol), ('horizon_minutes', horizon), ('regime', regime)]:
        if value is not None:
            clauses.append(f'{name}=?'); params.append(value)
    expression = str(directory/'*.parquet').replace("'", "''")
    where = ' WHERE '+' AND '.join(clauses) if clauses else ''
    sql = f"SELECT * FROM read_parquet('{expression}')"+where+' ORDER BY observations DESC LIMIT ?'
    with duckdb.connect() as connection:
        frame = connection.execute(sql, [*params, min(max(int(limit), 1), 200)]).df()
    records = json.loads(frame.to_json(orient='records'))
    return {**report, 'rows': records, 'returned_rows': len(records),
            'limited_preview': True, 'interpretation': 'RETROSPECTIVE OPPORTUNITY; NOT A BUY SIGNAL'}
