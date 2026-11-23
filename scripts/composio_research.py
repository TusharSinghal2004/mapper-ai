"""Refresh source evidence using the real Composio SDK and hosted MCP workbench.

No vendor accounts are connected. The remote code only reads the public URLs
already in the research dataset. Fresh evidence never overwrites reviewed claims.
"""
import argparse
import asyncio
import base64
import contextlib
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
import pathlib
import re
import sys
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATUS = ROOT / 'dist/composio-status.json'
MARKER = 'ATLAS_DOCUMENTS_JSON='

@contextlib.contextmanager
def research_lock():
    """Share one run lock between the command line and the local page."""
    with (ROOT/'.research.lock').open('a+b') as handle:
        handle.seek(0,2)
        if not handle.tell(): handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as error: raise BlockingIOError('Another research run is active.') from error
        try: yield
        finally:
            handle.seek(0)
            if os.name=='nt': msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(handle,fcntl.LOCK_UN)

def is_running():
    try:
        with research_lock(): return False
    except BlockingIOError: return True

# This fixed program runs inside Composio's sandbox through an MCP tool call.
# Only the JSON list of known public documentation URLs changes between batches.
FETCH_CODE = r'''
import base64, concurrent.futures, hashlib, html, json, re, urllib.request, zlib
def atlas_fetch(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'IntegrationAtlasResearch/2.0'})
        with urllib.request.urlopen(req, timeout=18) as response:
            raw = response.read(1500000)
            page = raw.decode('utf-8', errors='replace')
            page = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', page, flags=re.S|re.I)
            plain = html.unescape(re.sub(r'<[^>]+>', ' ', page))
            plain = re.sub(r'\s+', ' ', plain).strip()
            return {'url':url,'finalUrl':response.url,'status':response.status,'sha256':hashlib.sha256(raw).hexdigest(),'text':plain[:12000],'error':None}
    except Exception as error:
        return {'url':url,'status':None,'text':'','error':str(error)[:400]}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    atlas_documents = list(pool.map(atlas_fetch, json.loads(ATLAS_URLS_JSON)))
atlas_payload = json.dumps(atlas_documents).encode('utf-8')
atlas_encoded = base64.b64encode(zlib.compress(atlas_payload)).decode('ascii')
print('ATLAS_META_JSON='+json.dumps({'size':len(atlas_encoded),'sha256':hashlib.sha256(atlas_payload).hexdigest()}))
print('ATLAS_CHUNK='+atlas_encoded[:10000])
'''

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')

def save(path, value):
    # Atomic replacement keeps the local page from reading half-written JSON.
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)

def redact(value, key):
    if isinstance(value, str): return value.replace(key, '[redacted]') if key else value
    if isinstance(value, list): return [redact(v, key) for v in value]
    if isinstance(value, dict):
        return {k: ('[redacted]' if k.lower() in ('authorization','x-api-key','headers','mcp_url') else redact(v, key)) for k,v in value.items()}
    return value

def unpack_stdout(result):
    """Decode the MCP envelope. The stdout is data, never executable code."""
    for block in result.content:
        if getattr(block, 'type', '') != 'text': continue
        try:
            envelope = json.loads(block.text)
            if not envelope.get('successful', False):
                raise RuntimeError('Composio workbench returned an unsuccessful tool result.')
            if envelope.get('data',{}).get('error'):
                raise RuntimeError('The remote documentation program failed.')
            return envelope.get('data', {}).get('stdout', ''), envelope.get('log_id')
        except json.JSONDecodeError:
            continue
    raise RuntimeError('The workbench did not return a valid result.')

def marker_value(stdout, marker):
    for line in stdout.splitlines():
        if line.startswith(marker): return line[len(marker):]
    raise ValueError('Required output marker was missing or truncated.')

def mention_checks(row, documents):
    """Find review leads, not verified conclusions about authentication."""
    patterns = {'OAuth':r'\boauth(?:\s*2(?:\.0)?)?\b','API key':r'\bapi[ -]?key\b','Basic':r'\bbasic authentication\b','MCP':r'\b(?:mcp|model context protocol)\b'}
    findings=[]
    for label, pattern in patterns.items():
        for doc in documents:
            match=re.search(pattern,doc.get('text',''),re.I)
            if match:
                findings.append({'term':label,'url':doc['url'],'excerpt':doc['text'][max(0,match.start()-65):match.end()+100],'interpretation':'Mention found; a reviewer must check whether it supports this app claim.'})
                break
    return findings

async def run(args):
    try:
        with research_lock(): return await _run(args)
    except BlockingIOError:
        print('Another Composio research check is already running. Wait for it to finish.')
        return 3

async def _run(args):
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    key = os.environ.get('COMPOSIO_API_KEY','').strip()
    if not key:
        save(STATUS, {'status':'needs_key','message':'Add COMPOSIO_API_KEY to the local .env file to run Composio research.','sdkUsed':False,'mcpUsed':False})
        print('No Composio key configured. Add it to .env.'); return 2
    from composio import Composio
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    import httpx

    rows=json.loads((ROOT/'data/apps.json').read_text(encoding='utf-8-sig'))
    if args.ids:
        requested={int(v) for v in args.ids.split(',')}
        rows=[r for r in rows if r['id'] in requested]
    rows=rows[:args.limit]
    if not rows: raise ValueError('No apps selected')
    urls=list(dict.fromkeys(u for r in rows for u in r['sources']))
    if any(not u.startswith('https://') for u in urls): raise ValueError('Only HTTPS documentation URLs are allowed.')
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output=ROOT/'data/composio-runs'/stamp
    output.mkdir(parents=True,exist_ok=True)
    state={'status':'running','startedAt':now(),'appsRequested':len(rows),'appsCompleted':0,'urlsRequested':len(urls),'urlsRetrieved':0,'toolCallsSucceeded':0,'sdkUsed':False,'mcpUsed':False,'sdkVersion':importlib.metadata.version('composio'),'mcpVersion':importlib.metadata.version('mcp'),'transport':'Composio SDK session → MCP → COMPOSIO_REMOTE_WORKBENCH','message':'Connecting to Composio and collecting official documentation.','runId':stamp,'claimAccuracy':'Not measured by page retrieval'}
    save(STATUS,state)
    client=Composio(api_key=key)
    session=None
    documents={}
    failures=[]
    try:
        # Explicitly deny access to all app toolkits. Only the hosted workbench
        # performs fixed read-only documentation fetches; no connected accounts.
        session=await asyncio.to_thread(client.create,user_id=os.environ.get('COMPOSIO_USER_ID','integration-atlas-research'),toolkits={'enable':[]},mcp=True)
        state['sdkUsed']=True
        async with httpx.AsyncClient(headers=session.mcp.headers,follow_redirects=False,timeout=180) as http:
            async with streamable_http_client(session.mcp.url,http_client=http) as (read,write,_):
                async with ClientSession(read,write) as mcp:
                    await mcp.initialize()
                    tools=(await mcp.list_tools()).tools
                    state['mcpUsed']=True
                    names=[t.name for t in tools]
                    save(output/'mcp-tools.json',{'toolNames':names,'calledTools':['COMPOSIO_REMOTE_WORKBENCH']})
                    if 'COMPOSIO_REMOTE_WORKBENCH' not in names: raise RuntimeError('Composio research workbench is unavailable.')
                    state['composioSessionId']=session.session_id
                    async def call_workbench(code, index, label):
                        result=await mcp.call_tool('COMPOSIO_REMOTE_WORKBENCH',{'code_to_execute':code,'thought':label,'current_step':'READING_PUBLIC_DOCUMENTATION','current_step_metric':f'{index}/{len(urls)} source URLs'})
                        serial=state['toolCallsSucceeded']+1
                        save(output/f'tool-call-{serial}.json',redact(result.model_dump(mode='json'),key))
                        if result.isError: raise RuntimeError('MCP returned a tool error.')
                        stdout,log_id=unpack_stdout(result)
                        state['toolCallsSucceeded']+=1
                        state.setdefault('composioLogIds',[]).append(log_id)
                        return stdout
                    for index in range(0,len(urls),18):
                        batch=urls[index:index+18]
                        # repr produces a Python string literal; scraped content is
                        # never used as executable code or as a tool instruction.
                        code='ATLAS_URLS_JSON='+repr(json.dumps(batch))+'\n'+FETCH_CODE
                        try:
                            stdout=await call_workbench(code,index,'Read official public documentation for the research study.')
                            metadata=json.loads(marker_value(stdout,'ATLAS_META_JSON='))
                            encoded=marker_value(stdout,'ATLAS_CHUNK=')
                            # Small chunks avoid Composio's stdout preview limit.
                            while len(encoded)<metadata['size']:
                                offset=len(encoded)
                                chunk=await call_workbench(f"print('ATLAS_CHUNK='+atlas_encoded[{offset}:{offset+10000}])",index,'Retrieve the next chunk of the collected documentation.')
                                encoded+=marker_value(chunk,'ATLAS_CHUNK=')
                            payload=zlib.decompress(base64.b64decode(encoded,validate=True))
                            if hashlib.sha256(payload).hexdigest()!=metadata['sha256']:raise ValueError('Evidence transfer hash mismatch')
                            batch_docs=json.loads(payload)
                            # Only accept results for the exact URLs we requested.
                            for doc in batch_docs:
                                if doc.get('url') in batch: documents[doc['url']]=doc
                        except Exception as error:
                            failures.append({'batch':index//18+1,'errorType':type(error).__name__,'message':redact(str(error),key)[:300]})
                        state['urlsRetrieved']=sum(d.get('status')==200 for d in documents.values())
                        state['appsCompleted']=sum(bool(r['sources']) and any(documents.get(u,{}).get('status')==200 for u in r['sources']) for r in rows)
                        state['message']=f"Collected {state['urlsRetrieved']} of {len(urls)} source pages through Composio MCP."
                        save(STATUS,state)
                        print(state['message'],flush=True)
        records=[]
        for row in rows:
            docs=[documents[u] for u in row['sources'] if u in documents]
            record={'id':row['id'],'name':row['name'],'sourcesRequested':len(row['sources']),'sourcesRetrieved':sum(d['status']==200 for d in docs),'reviewLeads':mention_checks(row,docs),'documents':docs,'reviewStatus':'New evidence collected; reviewed claims unchanged.'}
            if args.extract:
                from research import extract
                try:
                    record['candidateFindings']=await asyncio.to_thread(extract,row,docs)
                    record['quoteChecks']=[{'field':c.get('field'),'quoteFound':bool(c.get('quote')) and c.get('quote','') in documents.get(c.get('url'),{}).get('text','')} for c in record['candidateFindings'].get('claims',[])]
                except Exception as error: record['extractionError']=type(error).__name__
            records.append(record)
        state['status']='completed' if not failures and state['appsCompleted']==len(rows) else 'partial'
        state['completedAt']=now()
        state['message']=f"Composio SDK + MCP collected evidence for {state['appsCompleted']} of {len(rows)} apps. Retrieved {state['urlsRetrieved']} of {len(urls)} pages. No findings were automatically changed."
        state['failures']=failures
        state['appsWithoutRetrievedEvidence']=[{'id':r['id'],'name':r['name'],'reason':'No source URL recorded' if not r['sources'] else 'No source returned HTTP 200 in this run'} for r in rows if not r['sources'] or not any(documents.get(u,{}).get('status')==200 for u in r['sources'])]
        save(output/'results.json',redact({'summary':state,'apps':records},key))
        save(ROOT/'dist/composio-results.json',redact({'summary':state,'apps':records},key))
        if len(rows)==100:save(ROOT/'dist/composio-full-results.json',redact({'summary':state,'apps':records},key))
        save(output/'documents.json',redact(documents,key))
        return 0 if state['toolCallsSucceeded'] else 1
    except Exception as error:
        state.update(status='failed',completedAt=now(),message='Composio research could not finish. Check the local run log and project permissions.',errorType=type(error).__name__)
        save(output/'error.json',redact({'type':type(error).__name__,'message':str(error)[:600]},key))
        return 1
    finally:
        if session:
            try:
                await asyncio.to_thread(session.delete)
                state['temporarySessionDeleted']=True
            except Exception:
                state['temporarySessionDeleted']=False
        save(STATUS,state)
        if len(rows)==100:save(ROOT/'dist/composio-full-run.json',state)
        print(state['message'],flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--limit',type=int,default=5)
    p.add_argument('--ids',help='Comma-separated app IDs')
    p.add_argument('--extract',action='store_true',help='Also propose structured findings using OPENAI_API_KEY; never overwrite reviewed records.')
    args=p.parse_args()
    if not 1<=args.limit<=100:p.error('--limit must be between 1 and 100')
    return asyncio.run(run(args))

if __name__=='__main__': sys.exit(main())
