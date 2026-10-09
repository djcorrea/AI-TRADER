"""Read-only reconciliation of V2 evidence. Writes separate V3 audit outputs."""
import collections
import json

import numpy as np
import pandas as pd

from lab.common import CFG, ROOT, dump, sha, utc


def run():
    data_summary=ROOT/'reports/v3_rebuild_summary.json'
    rebuilt=json.loads(data_summary.read_text()) if data_summary.exists() else {}
    entries = json.loads((ROOT/'results/experiments.json').read_text())
    models = json.loads((ROOT/'results/models.json').read_text())['results']
    registry = json.loads((ROOT/'models/registry.json').read_text())
    errors, reasons, halts = [], collections.Counter(), 0
    initial, fx = CFG['initial_brl'], CFG['brl_per_usdt']
    for entry in entries:
        key = entry['id']
        trades = pd.read_parquet(ROOT/f'results/{key}_trades.parquet')
        curve = pd.read_parquet(ROOT/f'results/{key}_equity.parquet')
        equity = np.r_[initial, curve.equity_brl.to_numpy()]
        pnls = trades.pnl_brl.to_numpy() if len(trades) else np.array([])
        loss = -pnls[pnls < 0].sum()
        expected = {'net_pnl_brl': equity[-1]-initial,
                    'max_drawdown': float((equity/np.maximum.accumulate(equity)-1).min()),
                    'profit_factor': float(pnls[pnls > 0].sum()/loss) if loss else None}
        for metric, value in expected.items():
            actual = entry['metrics'][metric]
            if (value is None) != (actual is None) or (value is not None and not np.isclose(value, actual, atol=1e-9)):
                errors.append({'id': key, 'reason': f'{metric} mismatch'})
        if not np.isclose(equity[-1]-initial, pnls.sum(), atol=1e-6):
            errors.append({'id': key, 'reason': 'cash does not reconcile'})
        if len(trades):
            fee = entry['scenario'].get('fee', CFG['fee'])
            computed = trades.qty*(trades.exit-trades.entry)*fx-trades.qty*(trades.entry+trades.exit)*fee*fx
            if not np.allclose(computed, pnls, atol=1e-7, rtol=1e-9):
                errors.append({'id': key, 'reason': 'fees/PnL mismatch'})
            reasons.update(trades.reason.value_counts().to_dict())
        halts += bool(entry['metrics']['risk_halted'])
    by_version = {f"{row['model']}_{row['horizon_minutes']}m_fold{row['fold']}": row for row in models}
    for record in registry:
        version = record['version']
        if sha(ROOT/f'models/{version}.joblib') != record['model_sha256']:
            errors.append({'id': version, 'reason': 'model checksum mismatch'})
        prediction = pd.read_parquet(ROOT/f'models/{version}_predictions.parquet')
        row = by_version[version]
        brier = float(((prediction.p_positive_net-(prediction.forward_net > .002).astype(float))**2).mean())
        candidates = int(((prediction.p_positive_net > .55) & (prediction.ev_net > .002)).sum())
        if not np.isclose(brier, row['brier'], atol=1e-12) or candidates != row['candidates']:
            errors.append({'id': version, 'reason': 'predictive metrics mismatch'})
        if record['activation'] is not None:
            errors.append({'id': version, 'reason': 'unexpected model activation'})
    report = {'generated': utc(), 'status': 'INVALID' if errors else 'PARTIAL_AUDIT',
              'source_hashes': {p:sha(ROOT/p) for p in ['audit_v2.py','lab/features.py','lab/models.py','lab/execution.py','lab/backtest.py','config.json']},
              'arithmetic_valid': not errors, 'errors': errors, 'backtests_reconciled': len(entries),
              'model_versions_verified': len(registry),
              'statuses': dict(collections.Counter(x['status'] for x in entries)),
              'permanent_risk_halts': halts, 'exit_reasons': dict(reasons),
              'brier_improved_models': sum(x['brier'] < x['null_brier'] for x in models),
              'predictive_candidates': sum(x['candidates'] for x in models),
              'holdout_predictive_candidates': sum(x['candidates'] for x in models if x['fold'] == 2),
              'historical_candles_verified_in_cloud': rebuilt.get('verified_rows',0),
              'historical_data_audit_snapshot': rebuilt,
              'strategy_approval': 'NONE', 'real_capital_used_brl': 0,
              'pending': ([] if rebuilt.get('baseline_reproduced') else ['Complete original candle rebuild and hash verification'])+[
                          'Measure the impact of integrity corrections on reruns',
                          'Current account fee, historical filters and order book are unverified',
                          'Unseen prospective observations and paper eligibility are pending'],
              'interpretation': 'Arithmetic consistency does not prove fills or profitability'}
    dump(ROOT/'reports/v3_audit.json', report)
    if errors:
        raise RuntimeError(f'Audit failed: {errors[:3]}')
    print(f"Partial audit: {len(entries)} backtests, {len(registry)} models, {rebuilt.get('verified_rows',0):,} recovered candles; full replay/prospective validation pending")
    return report


if __name__ == '__main__':
    run()
