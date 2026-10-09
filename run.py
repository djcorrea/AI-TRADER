import argparse,asyncio,os
from lab.common import CFG,ROOT
def main():
    p=argparse.ArgumentParser(description='Public-only QUANT AI V2')
    p.add_argument('command',choices=['data','aggregate','research','paper','serve','cloud','discovery','audit','rebuild','research-v3'])
    p.add_argument('--max-archives',type=int,default=24)
    p.add_argument('--symbols',nargs='+',help='Configured symbols for an incremental rebuild')
    p.add_argument('--max-rows',type=int,default=100000)
    p.add_argument('--max-seconds',type=int,default=300)
    p.add_argument('--end-date',help='Exclusive end date for monthly public archives; does not alter frozen V2 config')
    p.add_argument('--duration',type=int,default=0);p.add_argument('--port',type=int,default=int(os.environ.get('PORT',4174)));p.add_argument('--host',default=os.environ.get('HOST','127.0.0.1'));p.add_argument('--resume',action='store_true')
    a=p.parse_args()
    if CFG['real_trading_enabled']:raise RuntimeError('Real trading is unsupported and prohibited')
    if a.command=='research-v3':
        from lab.research_v3 import run
        r=run(a.max_seconds);print(f"V3 research: {r['status']}; no strategy activated")
    elif a.command=='rebuild':
        from lab.rebuild import rebuild
        r=rebuild(a.max_archives,a.max_seconds,a.end_date,a.symbols)
        print(f"Rebuild {r['status']}: {len(r['records'])} records; {r['bytes_this_run']} downloaded bytes")
    elif a.command=='data':
        from lab.data import acquire;acquire(a.end_date)
    elif a.command=='aggregate':
        from lab.data import aggregate;aggregate()
    elif a.command=='research':
        from lab.orchestrator import run;run(a.resume)
    elif a.command=='paper':
        from lab.paper import collect;asyncio.run(collect(a.duration))
    elif a.command=='serve':
        import uvicorn;uvicorn.run('lab.api:app',host=a.host,port=a.port)
    elif a.command=='cloud':
        from lab.cloud import run;run(a.port,a.host)
    elif a.command=='discovery':
        from lab.market_opportunity_discovery import build
        result=build(a.max_rows,a.max_seconds);print(f"Retrospective map built for {len(result['symbols'])} symbols; no strategy approved")
    elif a.command=='audit':
        from audit_v2 import run;run()
if __name__=='__main__':main()
