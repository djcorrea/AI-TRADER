import json
import pandas as pd
import pytest
from lab import research_v3
from lab.common import sha, ROOT
from test_models import dataset


def test_pilot_outputs_are_isolated_and_never_activate(tmp_path,monkeypatch):
    baseline={str(p):sha(p) for p in [ROOT/'results/report.json',ROOT/'models/registry.json',ROOT/'config.json']}
    data=dataset(600,1)
    data['available_t']=1704067200000+pd.RangeIndex(len(data))*60000
    data['label_end']=data.available_t+30*60000
    data['forward_net']=.003
    data['t']=data.available_t-59999
    monkeypatch.setattr(research_v3,'prepare',lambda:({'BTCUSDT':data},{'BTCUSDT':data},{'BTCUSDT':[]}))
    monkeypatch.setattr(research_v3,'labels',lambda frame,horizon:frame)
    monkeypatch.setattr(research_v3,'state_path',lambda p:tmp_path/p)
    result={'trades':[],'curve':[{'t':1704067200000,'equity_brl':500.}],'ending_brl':500.}
    monkeypatch.setattr(research_v3,'simulate',lambda *a,**kw:result)
    monkeypatch.setattr(research_v3,'buy_hold',lambda *a,**kw:result)
    monkeypatch.setattr(research_v3,'status',lambda *a,**kw:'CANDIDATA_RETROSPECTIVA')
    report=research_v3.run(30)
    assert report['status']=='RETROSPECTIVE_PILOT_COMPLETED'
    assert report['strategy_approval']=='NONE' and report['paper_candidates']==[]
    directory=json.loads((tmp_path/'v3-research/latest.json').read_text())['directory']
    entries=json.loads((__import__('pathlib').Path(directory)/'experiments.json').read_text())
    assert len(entries)==39
    assert all(e['status']=='INCONCLUSIVO_PROSPECTIVE_REQUIRED' for e in entries)
    assert all(e['variant']==1 for e in entries if e['period']!='discovery')
    assert all(sha(__import__('pathlib').Path(p))==digest for p,digest in baseline.items())


def test_pilot_respects_configured_time_limit():
    with pytest.raises(ValueError):research_v3.run(1801)


def test_pilot_requires_audited_sources(tmp_path,monkeypatch):
    monkeypatch.setattr(research_v3,'state_path',lambda p:tmp_path/p)
    with pytest.raises(FileNotFoundError):research_v3.prepare()
