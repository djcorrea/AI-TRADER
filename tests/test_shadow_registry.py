import json
import pytest
from lab import paper
from lab.common import ROOT,sha


def test_predeclared_v3_shadow_is_inactive_and_verified():
    bundle,version=paper.load_shadow()
    assert version=='v3_logistic_30m_fold2'
    assert bundle['features']==paper.FEATURES
    registry=json.loads((ROOT/'models/v3_registry.json').read_text())[0]
    assert registry['activation'] is None and registry['promotion']=='BLOCKED'
    assert registry['mode']=='SHADOW_ONLY'


def test_tampered_preferred_shadow_never_loads(tmp_path,monkeypatch):
    monkeypatch.setattr(paper,'ROOT',tmp_path)
    (tmp_path/'models').mkdir()
    p=tmp_path/'models/v3_logistic_30m_fold2.joblib';p.write_bytes(b'not-a-model')
    (tmp_path/'models/v3_registry.json').write_text(json.dumps([{'version':'v3_logistic_30m_fold2','activation':None,
          'config_hash':paper.config_hash(),'model_sha256':'0'*64}]))
    with pytest.raises(RuntimeError,match='check failed'):paper.load_shadow()
