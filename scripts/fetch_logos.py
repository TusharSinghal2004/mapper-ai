"""Download app marks for local/static hosting, with an explicit unknown fallback."""
import concurrent.futures
import hashlib
import html
import json
import pathlib
import urllib.parse
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
GROUPS=[
 'salesforce hubspot pipedrive attio twenty podio zohocrm close copper dealcloud',
 'zendesk intercom freshdesk front pylon liveagent plain helpscout gorgias gladly',
 'slack twilio zohocliq lark pumble discord telegram whatsapp aircall vonage',
 'googleads facebookads linkedin_ads gohighlevel mailchimp klaviyo systeme_io pinterest threads sendgrid',
 'shopify woocommerce bigcommerce salesforce_commerce_cloud magento squarespace ecwid gumroad amazon_selling_partner fanbasis',
 'dataforseo se_ranking ahrefs mrscraper apify firecrawl brightdata sherlock waterfall clay',
 'github vercel netlify cloudflare supabase neo4j snowflake mongodb datadog sentry',
 'notion airtable linear jira asana monday clickup coda smartsheet harvest',
 'stripe plaid binance UNKNOWN ipayx quickbooks xero brex ramp pitchbook',
 'notebooklm otter fathom consensus reducto devin higgsfield mermaid transcriptapi grain'
]
DOMAINS=[
 'salesforce.com hubspot.com pipedrive.com attio.com twenty.com podio.com zoho.com close.com copper.com dealcloud.com',
 'zendesk.com intercom.com freshdesk.com front.com usepylon.com liveagent.com plain.com helpscout.com gorgias.com gladly.com',
 'slack.com twilio.com zoho.com larksuite.com pumble.com discord.com telegram.org whatsapp.com aircall.io vonage.com',
 'ads.google.com facebook.com linkedin.com gohighlevel.com mailchimp.com klaviyo.com systeme.io pinterest.com threads.com sendgrid.com',
 'shopify.com woocommerce.com bigcommerce.com salesforce.com business.adobe.com squarespace.com ecwid.com gumroad.com sell.amazon.com fanbasis.com',
 'dataforseo.com seranking.com ahrefs.com mrscraper.com apify.com firecrawl.dev brightdata.com sherlockproject.xyz waterfall.io clay.com',
 'github.com vercel.com netlify.com cloudflare.com supabase.com neo4j.com snowflake.com mongodb.com datadoghq.com sentry.io',
 'notion.so airtable.com linear.app atlassian.com asana.com monday.com clickup.com coda.io smartsheet.com getharvest.com',
 'stripe.com plaid.com binance.com UNKNOWN ipayx.ai quickbooks.intuit.com xero.com brex.com ramp.com pitchbook.com',
 'notebooklm.google.com otter.ai fathom.video consensus.app reducto.ai devin.ai higgsfield.ai mermaid.js.org transcriptapi.com grain.com'
]

def fetch(url):
    request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 IntegrationAtlas','Accept':'image/avif,image/webp,image/svg+xml,image/*;q=0.8'})
    with urllib.request.urlopen(request,timeout=15) as r:
        data=r.read(500000)
        mime=r.headers.get_content_type()
        if not mime.startswith('image/') or len(data)<50:raise ValueError('No usable image returned')
        return data,mime

def main():
    folder=ROOT/'dist/assets/logos';folder.mkdir(parents=True,exist_ok=True)
    rows=json.loads((ROOT/'dist/apps.json').read_text(encoding='utf-8'))
    slugs=' '.join(GROUPS).split();domains=' '.join(DOMAINS).split()
    assert len(slugs)==len(domains)==len(rows)==100
    default,_=fetch('https://logos.composio.dev/api/integration-atlas-no-such-app')
    default_hash=hashlib.sha256(default).digest()
    try:
        globe,_=fetch('https://www.google.com/s2/favicons?domain=integration-atlas-no-such-app.invalid&sz=128')
        globe_hash=hashlib.sha256(globe).digest()
    except Exception:globe_hash=None
    def get_logo(row):
        i=row['id']-1
        if slugs[i]!='UNKNOWN':
            candidates=[('logo','https://logos.composio.dev/api/'+slugs[i]),('site-icon','https://www.google.com/s2/favicons?domain='+urllib.parse.quote(domains[i])+'&sz=128')]
            for kind,url in candidates:
                try:
                    data,mime=fetch(url)
                    digest=hashlib.sha256(data).digest()
                    if digest in (default_hash,globe_hash):continue
                    suffix={'image/svg+xml':'.svg','image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp','image/x-icon':'.ico','image/vnd.microsoft.icon':'.ico','image/gif':'.gif'}.get(mime)
                    if not suffix:continue
                    path=folder/(str(row['id'])+suffix);path.write_bytes(data)
                    return str(row['id']),{'path':path.relative_to(ROOT/'dist').as_posix(),'kind':kind,'source':url,'domain':domains[i],'sha256':hashlib.sha256(data).hexdigest()}
                except Exception:pass
        initials=''.join(word[0] for word in row['name'].split()[:2]).upper()
        path=folder/(str(row['id'])+'.svg')
        path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><title>'+html.escape(row['name'])+' — logo unavailable</title><rect width="64" height="64" rx="14" fill="#253957"/><text x="32" y="40" text-anchor="middle" font-family="Arial,sans-serif" font-size="23" font-weight="700" fill="#ffffff">'+html.escape(initials)+'</text></svg>',encoding='utf-8')
        return str(row['id']),{'path':path.relative_to(ROOT/'dist').as_posix(),'kind':'initials','source':None,'note':'Initials placeholder; verified vendor logo unavailable.'}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        logos=dict(pool.map(get_logo,rows))
    (ROOT/'dist/logos.json').write_text(json.dumps(logos,indent=2),encoding='utf-8')
    print(json.dumps({'logos':sum(v['kind']=='logo' for v in logos.values()),'siteIcons':sum(v['kind']=='site-icon' for v in logos.values()),'initialsFallbacks':[rows[int(k)-1]['name'] for k,v in logos.items() if v['kind']=='initials']}))

if __name__=='__main__':main()
