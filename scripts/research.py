"""Evidence refresh and optional structured extraction. Python 3.12, standard library."""
import argparse, concurrent.futures, datetime, hashlib, json, os, pathlib, re, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
def fetch(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'IntegrationAtlasResearch/1.0 (public documentation audit)'})
        with urllib.request.urlopen(req, timeout=25) as response:
            raw = response.read(2_000_000)
            html = raw.decode('utf-8', errors='replace')
            plain = re.sub('<[^>]+>', ' ', re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', html, flags=re.S))
            plain = re.sub(r'\s+', ' ', plain).strip()
            return {'url':url,'finalUrl':response.url,'status':response.status,'sha256':hashlib.sha256(raw).hexdigest(),'text':plain[:60000], 'error':None}
    except Exception as error:
        return {'url':url,'status':None,'text':'','error':str(error)}

def extract(row, documents):
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        raise SystemExit('Set OPENAI_API_KEY to use --extract. Fetch-only mode needs no key.')
    prompt = 'Research this integration from ONLY the supplied fetched documents. Return JSON with auth, credentialAccess, productionGate, apiSurface, mcp, verdict, blocker, claims (each with field, value, url, exact short supporting quote). Use unknown for unsupported claims. A successful HTTP fetch does not verify a claim. Never infer no MCP from missing evidence. App: '+row['name']+'\n'+json.dumps(documents)
    payload = json.dumps({'model':os.environ.get('RESEARCH_MODEL','gpt-4.1-mini'),'messages':[{'role':'user','content':prompt}],'response_format':{'type':'json_object'},'temperature':0}).encode()
    request = urllib.request.Request('https://api.openai.com/v1/chat/completions',data=payload,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=120) as response:
        return json.loads(json.load(response)['choices'][0]['message']['content'])

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--limit',type=int)
    parser.add_argument('--ids',help='Comma-separated app IDs')
    parser.add_argument('--extract',action='store_true')
    parser.add_argument('--transport',choices=['direct','composio'],default='direct',help='Use direct HTTP or the Composio SDK + MCP evidence workflow.')
    args=parser.parse_args()
    if args.transport=='composio':
        import asyncio
        from composio_research import run
        if args.limit is None: args.limit=100
        if not 1<=args.limit<=100: parser.error('--limit must be between 1 and 100')
        raise SystemExit(asyncio.run(run(args)))
    rows=json.loads((ROOT/'data/apps.json').read_text(encoding='utf-8'))
    if args.ids: rows=[r for r in rows if r['id'] in [int(i) for i in args.ids.split(',')]]
    if args.limit: rows=rows[:args.limit]
    output=ROOT/'data/runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output.mkdir(parents=True,exist_ok=True)
    urls=list(dict.fromkeys(u for row in rows for u in row['sources']))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        docs=dict(zip(urls,pool.map(fetch,urls)))
    (output/'documents.json').write_text(json.dumps(docs,indent=2),encoding='utf-8')
    findings=[]
    for row in rows:
        sources=[docs[url] for url in row['sources']]
        result={'id':row['id'],'name':row['name'],'fetched':sum(d['status']==200 for d in sources),'sources':len(sources)}
        if args.extract:
            try:
                result['extraction']=extract(row,sources)
                result['quoteChecks']=[{'field':c.get('field'),'supported':bool(c.get('quote')) and c.get('quote','') in docs.get(c.get('url'),{}).get('text','')} for c in result['extraction'].get('claims',[])]
            except Exception as error: result['extractionError']=str(error)
        findings.append(result)
    (output/'results.json').write_text(json.dumps(findings,indent=2),encoding='utf-8')
    print(json.dumps({'run':str(output),'apps':len(rows),'urls':len(urls),'successfulFetches':sum(d['status']==200 for d in docs.values()),'claimAccuracy':'not measured by URL fetch'}))
if __name__=='__main__': main()
