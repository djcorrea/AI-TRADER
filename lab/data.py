"""Verified monthly archives; bounded, resumable; all timestamps normalized to UTC ms."""
import concurrent.futures, hashlib, io, json, time, urllib.request, urllib.error, zipfile
import xml.etree.ElementTree as ET
import threading
import pandas as pd
import numpy as np
import duckdb
from .common import ROOT, CFG, dump, sha, utc, state_path
COLS=['t','o','h','l','c','v','ct','qv','n','tbv','tbqv','ignore']
API='https://data-api.binance.vision'
NETWORK_GATE=state_path('retry_after.json')
NETWORK_LOCK=threading.Lock()
def request(url):
    for attempt in range(5):
        with NETWORK_LOCK:
            gate=json.loads(NETWORK_GATE.read_text(encoding='utf-8')) if NETWORK_GATE.exists() else {}
            until=gate.get('not_before_epoch',0)
        if time.time()<until:
            raise RuntimeError(f'Requests suspended by Retry-After until epoch {until}; no request sent')
        try:
            with urllib.request.urlopen(url, timeout=40) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code==404: return None
            if e.code not in (418,429,500,502,503,504): raise
            delay=float(e.headers.get('Retry-After',2**attempt))
            if e.code in (418,429):
                with NETWORK_LOCK:
                    dump(NETWORK_GATE,{'not_before_epoch':time.time()+delay,'status':e.code,'observed':utc()})
            # Never shorten Retry-After. Long bans abort rather than hammer endpoint.
            if delay>60: raise RuntimeError(f'Public API suspended for {delay}s') from e
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError):
            if attempt==4: raise
            time.sleep(2**attempt)
    raise RuntimeError('Retry limit reached')
def public_json(path): return json.loads(request(API+path))
def catalog():
    """Archive catalog includes historical symbols independently of current exchangeInfo."""
    url='https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix=data/spot/monthly/klines/'
    names=[]; marker=''
    while True:
        raw=request(url+('&marker='+marker if marker else ''))
        root=ET.fromstring(raw); ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
        prefixes=[x.text for x in root.findall('s:CommonPrefixes/s:Prefix',ns)]
        names += [x.rstrip('/').split('/')[-1] for x in prefixes]
        if root.findtext('s:IsTruncated',namespaces=ns)!='true': break
        marker=root.findtext('s:NextMarker',namespaces=ns) or prefixes[-1]
    dump(ROOT/'data/catalog.json',{'retrieved':utc(),'source':url,'symbols':names,
         'note':'Catalog is not a complete historical listing/status or liquidity record.'})
    return names
def validate(df, step):
    errors=[]
    if df.empty: return {'rows':0,'valid':False,'errors':['empty'],'gaps':0}
    if df.t.duplicated().any(): errors.append('duplicate timestamps')
    if not df.t.is_monotonic_increasing: errors.append('unsorted')
    if not np.isfinite(df[['o','h','l','c','v','qv']].to_numpy()).all(): errors.append('nonfinite')
    if (df[['o','h','l','c']]<=0).any().any(): errors.append('nonpositive price')
    if (df[['v','qv','n','tbv','tbqv']]<0).any().any(): errors.append('negative volume/trades')
    if ((df.h<df[['o','c','l']].max(axis=1))|(df.l>df[['o','c','h']].min(axis=1))).any(): errors.append('OHLC inconsistent')
    if (df.tbv>df.v+1e-6).any(): errors.append('taker volume exceeds total')
    if ((df.ct<df.t)|(df.ct>=df.t+step)).any(): errors.append('close time outside candle')
    if (df.t%step!=0).any(): errors.append('unaligned UTC candle')
    return {'rows':len(df),'valid':not errors,'errors':errors,'gaps':int((df.t.diff().dropna()!=step).sum()),
            'missing_bars':int(np.maximum(0,df.t.diff().dropna()/step-1).sum()),
            'first':int(df.t.iloc[0]),'last':int(df.t.iloc[-1])}
def parse_archive(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        df=pd.read_csv(z.open(z.namelist()[0]),header=None,names=COLS)
    if str(df.t.iloc[0]) in ('open_time','open time'): df=df.iloc[1:].copy()
    df=df.apply(pd.to_numeric,errors='raise')
    for col in ('t','ct'):
        df[col]=np.where(df[col]>10**14,df[col]//1000,df[col]).astype('int64')
    df['n']=df.n.astype('int64')
    return df.drop(columns='ignore')
def acquire():
    start=time.monotonic(); (ROOT/'data/archives').mkdir(parents=True,exist_ok=True)
    try: catalog()
    except Exception as e: dump(ROOT/'data/catalog_error.json',{'error':str(e)})
    try: dump(ROOT/'data/exchange_snapshot.json',{'retrieved':utc(),'data':public_json('/api/v3/exchangeInfo')})
    except Exception as e: dump(ROOT/'data/exchange_error.json',{'error':str(e)})
    months=pd.period_range(CFG['start'], pd.Timestamp(CFG['end_exclusive'])-pd.Timedelta(days=1),freq='M')
    jobs=[(s,str(m)) for s in CFG['symbols'] for m in months]
    downloaded=[0]; records=[]
    import threading
    lock=threading.Lock()
    def one(job):
        symbol,month=job; name=f'{symbol}-1m-{month}.zip'
        out=ROOT/f'data/parquet/{symbol}/1m/{month}.parquet'
        meta=out.with_suffix('.json')
        if out.exists() and meta.exists(): return json.loads(meta.read_text())
        if time.monotonic()-start>CFG['max_download_seconds']: return {'symbol':symbol,'month':month,'status':'TIME_BUDGET'}
        # Conservative upper bound per in-flight archive prevents overrun of byte budget.
        with lock:
            if downloaded[0]+15_000_000>CFG['max_archive_bytes']: return {'symbol':symbol,'month':month,'status':'BYTE_BUDGET'}
        url=f'https://data.binance.vision/data/spot/monthly/klines/{symbol}/1m/{name}'
        try:
            raw=request(url)
            if raw is None: return {'symbol':symbol,'month':month,'status':'NOT_AVAILABLE','url':url}
            with lock: downloaded[0]+=len(raw)
            checksum=request(url+'.CHECKSUM')
            if checksum is None or checksum.decode().split()[0]!=hashlib.sha256(raw).hexdigest(): raise ValueError('archive checksum failure')
            df=parse_archive(raw); quality=validate(df,60000)
            if not quality['valid']: raise ValueError(str(quality['errors']))
            # The budget includes persistent outputs and archive cache.
            with lock:
                disk=sum(p.stat().st_size for p in (ROOT/'data').rglob('*') if p.is_file())
                if disk+len(raw)+df.memory_usage().sum()>CFG['max_disk_bytes']: raise RuntimeError('disk budget')
            out.parent.mkdir(parents=True,exist_ok=True)
            tmp=out.with_suffix('.tmp'); df.to_parquet(tmp,index=False); tmp.replace(out)
            (ROOT/'data/archives'/name).write_bytes(raw)
            r={'symbol':symbol,'month':month,'status':'OK','url':url,'retrieved':utc(),
               'archive_sha256':hashlib.sha256(raw).hexdigest(),'parquet_sha256':sha(out),'bytes':len(raw),'quality':quality}
            dump(meta,r); return r
        except Exception as e: return {'symbol':symbol,'month':month,'status':'ERROR','error':str(e),'url':url}
    with concurrent.futures.ThreadPoolExecutor(max_workers=CFG['download_workers']) as pool:
        for i,r in enumerate(pool.map(one,jobs)):
            records.append(r)
            if (i+1)%24==0: print(f'Archives {i+1}/{len(jobs)}: {r["symbol"]}',flush=True)
    dump(ROOT/'data/download_manifest.json',{'generated':utc(),'records':records,'bytes_this_run':downloaded[0],
         'candidate_selection':'manual historical candidates; survivors and delisted examples; incomplete universe',
         'elapsed_s':time.monotonic()-start})
    aggregate()
def aggregate():
    quality={};
    for symbol in CFG['symbols']:
        files=sorted((ROOT/f'data/parquet/{symbol}/1m').glob('*.parquet'))
        if not files: continue
        df=pd.concat([pd.read_parquet(p) for p in files],ignore_index=True).sort_values('t')
        quality[symbol]=validate(df,60000)
        if not quality[symbol]['valid']: continue
        for interval,mins in [('5m',5),('15m',15),('1h',60),('4h',240)]:
            grouped=df.assign(bucket=df.t//(mins*60000)*(mins*60000)).groupby('bucket',sort=True)
            out=grouped.agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last'),v=('v','sum'),
                qv=('qv','sum'),n=('n','sum'),tbv=('tbv','sum'),tbqv=('tbqv','sum'),count=('t','size'))
            # Incomplete bars removed rather than quietly filled. Gaps remain visible.
            out=out[out['count']==mins].drop(columns='count').reset_index().rename(columns={'bucket':'t'})
            out['ct']=out.t+mins*60000-1
            dest=ROOT/f'data/derived/{symbol}_{interval}.parquet';dest.parent.mkdir(parents=True,exist_ok=True)
            out.to_parquet(dest,index=False)
        print(f'Aggregated {symbol}: {len(df):,} minutes',flush=True)
    dump(ROOT/'data/quality.json',quality)
    index_db()
def index_db():
    with duckdb.connect(str(ROOT/'data/lab.duckdb')) as db:
        path=str(ROOT/'data/derived/*_15m.parquet').replace('\\','/').replace("'","''")
        db.execute(f"CREATE OR REPLACE VIEW bars AS SELECT *, regexp_extract(filename, '([^/]+)_([^_]+)\\.parquet$', 1) symbol FROM read_parquet('{path}', filename=true)")
def load(symbol,interval='15m'):
    if interval=='1m':
        paths=sorted((ROOT/f'data/parquet/{symbol}/1m').glob('*.parquet'))
        if not paths: return pd.DataFrame()
        return pd.concat([pd.read_parquet(p) for p in paths],ignore_index=True).sort_values('t').reset_index(drop=True)
    path=ROOT/f'data/derived/{symbol}_{interval}.parquet'
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()
