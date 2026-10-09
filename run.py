import argparse,asyncio,os
from lab.common import CFG,ROOT
def main():
    p=argparse.ArgumentParser(description='Public-only QUANT AI V2')
    p.add_argument('command',choices=['data','aggregate','research','paper','serve','cloud'])
    p.add_argument('--duration',type=int,default=0);p.add_argument('--port',type=int,default=int(os.environ.get('PORT',4174)));p.add_argument('--host',default=os.environ.get('HOST','127.0.0.1'));p.add_argument('--resume',action='store_true')
    a=p.parse_args()
    if CFG['real_trading_enabled']:raise RuntimeError('Real trading is unsupported and prohibited')
    if a.command=='data':
        from lab.data import acquire;acquire()
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
if __name__=='__main__':main()
