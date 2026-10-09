"""One API and one collector share a local volume. No training at startup."""
import os,signal,subprocess,sys,time

def commands(port,host):
    return [[sys.executable,'run.py','serve','--port',str(port),'--host',host],
            [sys.executable,'run.py','paper']]

def run(port,host):
    if not os.environ.get('STATE_DIR'):
        raise RuntimeError('cloud requires STATE_DIR pointing to persistent storage')
    children=[];stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        for cmd in commands(port,host):children.append(subprocess.Popen(cmd))
        while not stopping:
            if any(p.poll() is not None for p in children):
                raise RuntimeError('Cloud child exited; supervisor stops for platform restart')
            time.sleep(.5)
    finally:
        for p in children:
            if p.poll() is None:p.terminate()
        for p in children:
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.kill();p.wait()
