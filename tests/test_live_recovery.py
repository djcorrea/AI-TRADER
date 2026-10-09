import pytest
from lab import paper
from test_lab import candles


def rest_rows(frame):
    cols=['t','o','h','l','c','v','ct','qv','n','tbv','tbqv']
    return [[*r,0] for r in frame[cols].to_numpy().tolist()]


def test_recovery_excludes_event_and_every_future_candle(monkeypatch):
    frame=candles(500,60000);current=frame.iloc[350].to_dict();calls=[]
    def query(path):calls.append(path);return rest_rows(frame)
    monkeypatch.setattr(paper,'public_json',query)
    recovered=paper.recover_closed_history('BTCUSDT',current)
    assert len(recovered)==350
    assert recovered[-1]['t']==current['t']-60000
    assert all(row['ct']<current['ct'] for row in recovered)
    assert f'endTime={current["ct"]}' in calls[0]


def test_recovery_keeps_true_missing_minutes_visible(monkeypatch):
    frame=candles(500,60000);current=frame.iloc[-1].to_dict()
    monkeypatch.setattr(paper,'public_json',lambda path:rest_rows(frame.drop(index=480)))
    recovered=paper.recover_closed_history('BTCUSDT',current)
    assert len(recovered)==498
    assert paper.validate(__import__('pandas').DataFrame(recovered),60000)['gaps']==1


def test_invalid_rest_history_is_not_accepted():
    frame=candles(20,60000);frame.loc[10,'h']=0
    with pytest.raises(ValueError,match='Invalid public REST'):paper.closed_rest_bars(rest_rows(frame),frame.ct.max())
