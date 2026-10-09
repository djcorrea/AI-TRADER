import sqlite3
import pytest
from lab.paper import Store,PaperBroker
from test_lab import signal,quote
def test_broker_memory_restored_on_failed_fill(tmp_path):
    s=Store(tmp_path/'paper.sqlite');b=PaperBroker(s);before=b.equity()
    s.db.execute("CREATE TRIGGER fail_state BEFORE INSERT ON state WHEN NEW.k='broker' BEGIN SELECT RAISE(ABORT,'injected failure'); END")
    with pytest.raises(sqlite3.IntegrityError):b.submit('BTC',signal(),quote(),approved=True,now=1000)
    assert b.equity()==before;assert not b.state['positions']
    s.close()
def test_fill_and_state_atomic_rollback(tmp_path):
    s=Store(tmp_path/'paper.sqlite');s.put('broker',{'cash':100.})
    s.db.execute("CREATE TRIGGER fail_state BEFORE INSERT ON state WHEN NEW.k='broker' BEGIN SELECT RAISE(ABORT,'injected failure'); END")
    with pytest.raises(sqlite3.IntegrityError):s.atomic_broker_event('paper_fill',{'qty':1},{'cash':90.})
    assert s.get('broker')['cash']==100.
    assert s.db.execute("SELECT count(*) FROM events WHERE kind='paper_fill'").fetchone()[0]==0
    s.close()
def test_journal_survives_raw_retention(tmp_path):
    s=Store(tmp_path/'paper.sqlite');s.log('paper_fill',{'qty':1})
    for i in range(30):s.log('raw_feed',{'i':i})
    s.trim(10)
    assert s.db.execute("SELECT count(*) FROM events WHERE kind='paper_fill'").fetchone()[0]==1
    assert s.db.execute("SELECT count(*) FROM events WHERE kind='raw_feed'").fetchone()[0]==10
    s.close()
