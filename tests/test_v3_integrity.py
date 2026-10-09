"""Regression checks for integrity defects found during the V2 audit."""
import json

import numpy as np
import pytest

from lab import data
from lab.common import CFG, dump, sha
from lab.execution import Filters, size
from lab.features import make
from lab.models import fit_calibrated, labels
from test_lab import candles
from test_models import dataset


def test_future_labels_do_not_bridge_missing_minutes():
    frame = candles(200, 60000).drop(index=44).reset_index(drop=True)
    labeled = labels(make(frame, 1), 15)
    assert np.isnan(labeled.loc[40, 'forward_net'])
    assert np.isnan(labeled.loc[40, 'label_end'])
    assert labeled.loc[40, 'label'] is None or np.isnan(labeled.loc[40, 'label'])
    assert np.isfinite(labeled.loc[50, 'forward_net'])


def test_features_restart_after_a_missing_minute():
    frame=candles(400,60000).drop(index=205).reset_index(drop=True)
    feature=make(frame,1)
    assert np.isnan(feature.ret1.iloc[205])
    assert feature.ema100.iloc[205:304].isna().all()
    assert np.isfinite(feature.ema100.iloc[304])


def test_calibration_requires_all_three_classes():
    from sklearn.linear_model import LogisticRegression
    fit, cal, test = dataset(600, 1), dataset(300, 2), dataset(300, 3)
    cal = cal[cal.label != 1]
    with pytest.raises(ValueError, match='Three label classes'):
        fit_calibrated(lambda: LogisticRegression(max_iter=100), fit, cal, test)


def test_cache_is_reverified_before_acquisition_reuse(tmp_path, monkeypatch):
    monkeypatch.setattr(data, 'ROOT', tmp_path)
    monkeypatch.setattr(data, 'CFG', {**CFG, 'symbols': ['BTCUSDT'],
                                    'start': '2024-01-01', 'end_exclusive': '2024-02-01'})
    monkeypatch.setattr(data, 'catalog', lambda: [])
    monkeypatch.setattr(data, 'public_json', lambda path: {'symbols': []})
    monkeypatch.setattr(data, 'aggregate', lambda: None)
    out = tmp_path/'data/parquet/BTCUSDT/1m/2024-01.parquet'
    out.parent.mkdir(parents=True)
    candles(50, 60000).to_parquet(out, index=False)
    archive = tmp_path/'data/archives/BTCUSDT-1m-2024-01.zip'
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b'archive fixture')
    dump(out.with_suffix('.json'), {'symbol': 'BTCUSDT', 'month': '2024-01',
         'status': 'OK', 'parquet_sha256': '0'*64, 'archive_sha256': sha(archive)})
    data.acquire()
    records = json.loads((tmp_path/'data/download_manifest.json').read_text())['records']
    assert records[0]['status'] == 'ERROR'
    assert 'checksum' in records[0]['error'].lower()


def test_market_and_lot_steps_are_both_satisfied():
    filters = Filters(step=.04, market_step=.03, min_notional=1.)
    quantity, _ = size(100., 100., 0., 0., 100., 98., 10000., filters)
    assert quantity > 0
    assert quantity/.04 == pytest.approx(round(quantity/.04))
    assert quantity/.03 == pytest.approx(round(quantity/.03))


@pytest.mark.parametrize('field', ['n', 'tbv', 'tbqv'])
def test_all_candle_fields_must_be_finite(field):
    frame = candles(50, 60000)
    frame[field] = frame[field].astype(float)
    frame.loc[10, field] = np.nan
    assert not data.validate(frame, 60000)['valid']
