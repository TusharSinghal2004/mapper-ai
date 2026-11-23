"""Local case-study viewer and one-click Composio evidence refresh."""
import json
import os
import pathlib
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from composio_research import is_running

ROOT=pathlib.Path(__file__).resolve().parents[1]
job=None
lock=threading.Lock()

def configured():
    # Read afresh so saving .env enables the button without restarting.
    from dotenv import dotenv_values
    values=dotenv_values(ROOT/'.env')
    return bool(os.environ.get('COMPOSIO_API_KEY') or values.get('COMPOSIO_API_KEY'))

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/'dist'),**kwargs)
    def reply(self,status,data):
        body=json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if urlsplit(self.path).path=='/api/health':
            return self.reply(200,{'service':'integration-atlas-local','composioConfigured':configured(),'running':is_running() or bool(job and job.poll() is None)})
        if urlsplit(self.path).path.startswith('/api/'):
            return self.reply(404,{'message':'Unknown action'})
        return super().do_GET()
    def do_POST(self):
        global job
        if self.headers.get('Host') not in ('localhost:8000','127.0.0.1:8000'):
            return self.reply(403,{'message':'Use the localhost address.'})
        origin=self.headers.get('Origin')
        if origin and origin not in ('http://localhost:8000','http://127.0.0.1:8000'):
            return self.reply(403,{'message':'Research can only be started from the local page.'})
        if urlsplit(self.path).path!='/api/research':return self.reply(404,{'message':'Unknown action'})
        if not configured():return self.reply(409,{'message':'Add your Composio key to the local .env file first.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=128:raise ValueError()
            payload=json.loads(self.rfile.read(length))
            if payload!={'limit':5}:raise ValueError()
        except (ValueError,TypeError,json.JSONDecodeError):return self.reply(400,{'message':'The page can run a five-app sample. Use the command line for all 100.'})
        with lock:
            if is_running() or (job and job.poll() is None):return self.reply(409,{'message':'A research check is already running.'})
            from composio_research import save, STATUS
            save(STATUS,{'status':'running','message':'Starting the Composio SDK + MCP check.','appsRequested':5})
            logdir=ROOT/'data/composio-runs';logdir.mkdir(exist_ok=True)
            # The child writes only summary counts to stdout; no credentials.
            with (logdir/'local-trigger.log').open('w',encoding='utf-8') as log:
                job=subprocess.Popen([sys.executable,str(ROOT/'scripts/research.py'),'--transport','composio','--limit','5','--ids','11,31,53,86,94'],cwd=ROOT,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        self.reply(202,{'message':'Checking Zendesk, Google Ads, Ahrefs, QuickBooks, and Consensus through Composio. The results will appear here.'})

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',8000),Handler)
    print('Integration Atlas is running at http://localhost:8000',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
