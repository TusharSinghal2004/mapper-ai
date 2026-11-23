import json, pathlib, shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
rows=[]
for part in 'abc': rows+=json.loads((ROOT.parent/f'research-{part}.json').read_text(encoding='utf-8-sig'))
def repair(v):
    if isinstance(v,str):
        try:
            if '\u00e2' in v: return v.encode('cp1252').decode('utf-8')
        except (UnicodeError,LookupError): pass
        return v
    if isinstance(v,list): return [repair(x) for x in v]
    if isinstance(v,dict): return {k:repair(x) for k,x in v.items()}
    return v
rows=repair(rows)
categories=['CRM and Sales','Support and Helpdesk','Communications and Messaging','Marketing, Ads, Email and Social','Ecommerce','Data, SEO and Scraping','Developer, Infra and Data','Productivity and Project Management','Finance and Fintech','AI, Research and Media']
for r in rows:
    r['category']=categories[(r['id']-1)//10]
    r['checkedAt']='2026-11-23'
    r['verification']='AI documentation review; no human audit or authenticated vendor test'
(ROOT/'data/first-pass.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
reviews=[]
def review(id,outcome,before,after,url):
    reviews.append(dict(id=id,name=rows[id-1]['name'],outcome=outcome,before=before,after=after,url=url))
review(11,'confirmed','New API token creation disabled; legacy token retirement scheduled.','Official migration timeline confirms October 27, 2026 creation block and April 30, 2027 final retirement.','https://developer.zendesk.com/documentation/authentication/oauth-migration/')
review(31,'confirmed','Cloud-project access replaces legacy developer tokens.','Migration body confirms September 9, 2026 sunset; stale page summary still describes old onboarding.','https://developers.google.com/google-ads/api/docs/api-policy/developer-token')
review(53,'confirmed','Paid-plan access with limited free test queries.','Official introduction confirms eligible paid plans and limited tests; key management requires workspace owner/admin.','https://docs.ahrefs.com/en/api/docs/introduction')
review(86,'strengthened','Sandbox keys self-serve; production setup separate.','Added explicit production app assessment requirement; sandbox access is not production approval.','https://help.developer.intuit.com/s/question/0D5TR00001b3Iav0AE/im-building-a-private-readonly-quickbooks-api-app-for-my-own-company-is-there-a-simplified-production-approval-process-for-internaluse-apps-or-must-i-complete-the-full-security-and-compliance-assessment')
rows[85]['accessNote']='Self-serve developer sandbox; production credentials require app assessment questionnaire and company authorization.'
rows[85]['sources'].append(reviews[-1]['url'])
review(88,'confirmed','Customer token and partner OAuth require account/admin access.','Brex quickstart explicitly requires a customer account and admin dashboard access.','https://developer.brex.com/guides/quickstart')
rows[87]['sources'].append(reviews[-1]['url'])
review(89,'confirmed','Customer admin or requested sandbox; OAuth.','Official overview separates customer, partner, and sandbox paths; authorization guide confirms client-credentials and authorization-code flows.','https://docs.ramp.com/developer-api/v1/scopes')
rows[88]['sources'].append(reviews[-1]['url'])
review(91,'confirmed','Enterprise license and user IAM role required.','Official notebook-management API requires licensed authenticated user. Consumer product remains separate.','https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks')
review(92,'confirmed with caveat','OAuth MCP; exact tier eligibility unknown.','Official page confirms OAuth and custom-client URL; FAQ says no public API key and directs unsupported clients to support. Tier eligibility remains unknown.','https://help.otter.ai/hc/en-us/articles/35287607569687-Otter-MCP-Server')
review(94,'confirmed','Self-serve API key rather than assignment OAuth hint.','October 2026 official help confirms x-api-key and a shared API/MCP monthly quota.','https://help.consensus.app/en/articles/16516328-the-consensus-api')
review(97,'confirmed','Account sign-in and active paid subscription for CLI/MCP.','Official integration help confirms account authorization without API key and a paid subscription requirement.','https://higgsfield.ai/creator-hub/help-center/integrations/how-do-i-connect-higgsfield-to-ai-agent')
verification={'date':'2026-11-23','reviewer':'Independent AI documentation review, not a human','sampleMethod':'Ten targeted high-risk records; not a random or representative sample','summary':'Ten selected records were revisited against official documentation: nine retained their assessment (one with an explicit eligibility caveat), and QuickBooks gained a concrete production assessment gate. Research-agent follow-up also recovered official MCP evidence for Sentry and systeme.io. These are documented refinements, not a statistical accuracy estimate.','humanReviewed':0,'authenticatedTests':0,'reviews':reviews}
assert len(rows)==100 and [r['id'] for r in rows]==list(range(1,101))
for r in rows:
    assert all(k in r for k in ['name','auth','access','api','mcp','verdict','sources','confidence'])
    assert all(u.startswith('https://') for u in r['sources'])
for dest in [ROOT/'data/apps.json',ROOT/'dist/apps.json']: dest.write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
(ROOT/'dist/verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
evidence=ROOT/'data/evidence';evidence.mkdir(exist_ok=True)
for path in ROOT.parent.glob('research*evidence.json'): shutil.copy2(path,evidence/path.name)
print('Validated 100 unique IDs, 10 categories, required fields, source URL format; assembled final records.')
