from pathlib import Path
import json, hashlib, datetime, os
ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))

def state_path(relative):
    """Persistent runtime files; STATE_DIR must be a writable mounted volume."""
    return Path(os.environ['STATE_DIR']) / relative if os.environ.get('STATE_DIR') else ROOT / 'paper' / relative
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def dump(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    def scalar(value):
        import numpy as np
        if isinstance(value,np.generic):return value.item()
        raise TypeError(f'Unsupported JSON type: {type(value)}')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False,default=scalar), encoding='utf-8')
    os.replace(tmp, path)
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576), b''): h.update(b)
    return h.hexdigest()
def config_hash(): return sha(ROOT/'config.json')
