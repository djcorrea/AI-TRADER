import json,time,urllib.error
import pytest
from lab import data
def test_retry_after_persists_and_blocks_new_requests(tmp_path,monkeypatch):
    monkeypatch.setattr(data,'NETWORK_GATE',tmp_path/'gate.json');calls=[]
    def banned(url,timeout):
        calls.append(url)
        raise urllib.error.HTTPError(url,429,'rate limit',{'Retry-After':'120'},None)
    monkeypatch.setattr(data.urllib.request,'urlopen',banned)
    with pytest.raises(RuntimeError):data.request('https://example.test')
    assert json.loads(data.NETWORK_GATE.read_text())['not_before_epoch']>time.time()+100
    with pytest.raises(RuntimeError):data.request('https://example.test')
    assert len(calls)==1
