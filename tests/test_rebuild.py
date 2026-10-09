import hashlib
import io
import json
import zipfile

from lab import rebuild
from lab.common import CFG, dump, sha
from test_lab import candles


def test_rebuild_preserves_baseline_and_rechecks_cache(tmp_path,monkeypatch):
    monkeypatch.setattr(rebuild,'ROOT',tmp_path)
    monkeypatch.setattr(rebuild,'state_path',lambda p:tmp_path/'state'/p)
    monkeypatch.setattr(rebuild,'CFG',{**CFG,'start':'2024-01-01','end_exclusive':'2024-02-01','symbols':['BTCUSDT']})
    monkeypatch.setattr(rebuild,'NETWORK_GATE',tmp_path/'state/retry_after.json')
    frame=candles(50,60000)
    source=frame.assign(ignore=0).rename(columns={'ct':'close_time'})
    source=source[['t','o','h','l','c','v','close_time','qv','n','tbv','tbqv','ignore']]
    zipped=io.BytesIO()
    with zipfile.ZipFile(zipped,'w') as z:z.writestr('fixture.csv',source.to_csv(index=False,header=False))
    raw=zipped.getvalue();digest=hashlib.sha256(raw).hexdigest()
    baseline=tmp_path/'data/download_manifest.json'
    dump(baseline,{'records':[{'symbol':'BTCUSDT','month':'2024-01','status':'OK','archive_sha256':digest}]})
    original=sha(baseline)
    class Response(io.BytesIO):pass
    monkeypatch.setattr(rebuild.urllib.request,'urlopen',lambda url,**kw:Response((digest+' fixture.zip').encode() if url.endswith('.CHECKSUM') else raw))
    report=rebuild.rebuild(1,10)
    assert report['status']=='REQUESTED_MONTHS_VERIFIED'
    assert report['records'][0]['baseline_archive_match'] is True
    assert sha(baseline)==original
    monkeypatch.setattr(rebuild.urllib.request,'urlopen',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('cache must not download')))
    assert rebuild.rebuild(1,10)['records'][0]['cache_reverified'] is True
    parquet=tmp_path/'data/parquet/BTCUSDT/1m/2024-01.parquet'
    parquet.write_bytes(b'corrupted-fixture')
    assert rebuild.rebuild(1,10)['status']=='BLOCKED'
    assert parquet.read_bytes()==b'corrupted-fixture'


def test_streaming_download_never_exceeds_byte_budget(tmp_path,monkeypatch):
    monkeypatch.setattr(rebuild,'ROOT',tmp_path)
    monkeypatch.setattr(rebuild,'state_path',lambda p:tmp_path/'state'/p)
    monkeypatch.setattr(rebuild,'NETWORK_GATE',tmp_path/'gate.json')
    monkeypatch.setattr(rebuild,'CFG',{**CFG,'start':'2024-01-01','end_exclusive':'2024-02-01','symbols':['BTCUSDT'],'max_archive_bytes':16_004_096})
    dump(tmp_path/'data/download_manifest.json',{'records':[]})
    monkeypatch.setattr(rebuild.urllib.request,'urlopen',lambda *a,**kw:io.BytesIO(b'x'*16_000_001))
    report=rebuild.rebuild(1,10)
    assert report['status']=='BLOCKED'
    assert report['bytes_this_run']==16_000_000
    assert not (tmp_path/'data/archives').exists()
