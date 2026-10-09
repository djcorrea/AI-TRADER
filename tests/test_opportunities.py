import numpy as np
import pytest
from fastapi.testclient import TestClient

from lab import api
from lab.market_opportunity_discovery import aggregate_diagnostics, break_even, diagnostics, read_map
from test_lab import candles


def test_map_uses_future_only_for_explicit_diagnostics():
    frame=candles(400,60000)
    rows=diagnostics(frame,'BTCUSDT',horizons=(5,15))
    assert not rows.empty
    row=rows[rows.horizon_minutes==5].iloc[0]
    i=int(np.flatnonzero(frame.ct.to_numpy()==row.available_t)[0])
    assert row.forward_return==pytest.approx(frame.c.iloc[i+5]/frame.c.iloc[i]-1)
    assert row.mfe==pytest.approx(frame.h.iloc[i+1:i+6].max()/frame.c.iloc[i]-1)
    assert row.mae==pytest.approx(frame.l.iloc[i+1:i+6].min()/frame.c.iloc[i]-1)
    groups=aggregate_diagnostics(rows)
    assert groups.observations.sum()==len(rows)
    assert 'decision' not in rows and 'signal' not in rows


def test_gap_invalidates_every_future_diagnostic_crossing_it():
    frame=candles(400,60000).drop(index=205).reset_index(drop=True)
    rows=diagnostics(frame,'BTCUSDT',horizons=(15,))
    missing_start=candles(400,60000).t.iloc[205]
    assert not ((rows.available_t<missing_start)&(rows.label_end>=missing_start)).any()


def test_break_even_matches_independent_cash_reconciliation():
    gross=break_even(.001,.0005,.0005)
    quantity=100/(100*1.001*1.001)
    proceeds=quantity*(100*(1+gross)*.999)*.999
    assert proceeds==pytest.approx(100)
    with pytest.raises(ValueError):break_even(-.001,0,0)


def test_unavailable_map_does_not_fabricate_zero_results(tmp_path,monkeypatch):
    monkeypatch.setenv('STATE_DIR',str(tmp_path))
    result=read_map()
    assert result['status']=='UNAVAILABLE' and not result['rows']
    with TestClient(api.app) as client:
        response=client.get('/api/opportunities').json()
        assert response['status']=='UNAVAILABLE'
        assert all(x['source']=='SCENARIO_ASSUMPTION' for x in response['cost_scenarios'])


def test_persisted_map_query_is_bounded_and_parameterized(tmp_path,monkeypatch):
    from lab.common import dump
    monkeypatch.setenv('STATE_DIR',str(tmp_path))
    directory=tmp_path/'opportunities/fixture';directory.mkdir(parents=True)
    grouped=aggregate_diagnostics(diagnostics(candles(400,60000),'BTCUSDT',horizons=(5,15)))
    grouped.to_parquet(directory/'BTCUSDT.parquet',index=False)
    dump(tmp_path/'opportunities/report.json',{'status':'TEST_FIXTURE','dataset_directory':str(directory)})
    result=read_map(symbol='BTCUSDT',horizon=5,limit=2)
    assert len(result['rows'])==2
    assert all(x['horizon_minutes']==5 for x in result['rows'])
    assert read_map(symbol="BTCUSDT' OR 1=1--")['rows']==[]
