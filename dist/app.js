const $ = s => document.querySelector(s);
const esc = s => String(s ?? 'Not yet clear').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const text = v => Array.isArray(v) ? v.join(', ') : typeof v === 'object' ? JSON.stringify(v) : v;
const labels = {
  verdict: {buildable:'Looks ready to build',conditional:'Possible, with conditions',unknown:'Not yet clear',local:'Runs on your computer'},
  access: {'self-serve':'Sign up yourself',trial:'Try it first',paid:'Paid account needed',gated:'Approval or special access',unknown:'Not yet clear'}
};
const accessHelp = {
  'self-serve':'A developer can get started by signing up. Some features may need extra permission or payment.',
  trial:'A trial offers a starting point. Continued use may require a paid account.',
  paid:'A paid account is needed. Check that the plan includes the tools you want.',
  gated:'Ask the app company or your account administrator for access.',
  unknown:'We could not confirm a reliable way to get access.'
};
const examples = [
  'Find customer records or help update a sales pipeline.',
  'Find support tickets or help prepare a reply.',
  'Read or send messages within the permissions granted.',
  'Help with campaigns, email, or performance reports.',
  'Help manage products, orders, or store information.',
  'Gather web data or help research search performance.',
  'Help with software projects, infrastructure, or monitoring.',
  'Find information or help manage tasks and projects.',
  'Help review financial records or permitted payment workflows.',
  'Help with research, documents, meetings, or media.'
];
let apps = [], logos = {}, localReady = false, pollTimer;
function render() {
  const query = $('#search').value.toLowerCase().trim();
  const rows = apps.filter(r => JSON.stringify(r).toLowerCase().includes(query) &&
    ['category','verdict','access'].every(k => !$('#'+k).value || r[k] === $('#'+k).value));
  $('#count').textContent = rows.length + ' of ' + apps.length + ' apps';
  $('#empty').hidden = rows.length > 0;
  $('#rows').innerHTML = rows.map(r => {
    const refs = '<small class="field-evidence">App references: '+(r.sources.length ? r.sources.map((u,i)=>'<a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer" aria-label="'+esc(r.name)+' documentation reference '+(i+1)+'">['+(i+1)+']</a>').join(' ') : 'Missing — needs follow-up')+'</small>';
    const sources = r.sources.map((u,i) => '<a class="source-url" href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">['+(i+1)+'] '+esc(u)+'</a>').join('');
    const cell=(label,body,reference=true)=>'<td><span class="field-label">'+label+'</span>'+body+(reference?refs:'')+'</td>';
    const mark=logos[String(r.id)];
    const fallback=r.name.split(/\s+/).slice(0,2).map(w=>w[0]).join('').toUpperCase();
    const picture=mark ? '<img class="app-logo" src="'+esc(mark.path)+'" alt="'+esc(r.name)+(mark.kind==='initials'?' initials placeholder':mark.kind==='site-icon'?' site icon':' logo')+'" width="60" height="60" loading="lazy" decoding="async">' : '<span class="app-initials">'+esc(fallback)+'</span>';
    return '<tr data-app-id="'+r.id+'"><td class="app-heading"><div class="app-identity"><div class="app-logo-tile" title="'+esc(mark?.kind==='initials'?'Logo unavailable — initials shown':r.name)+'">'+picture+'</div><div class="app-title"><b>'+esc(r.name)+'</b><span class="app-category">'+esc(r.category)+'</span><p>'+esc(r.description)+'</p>'+(mark?.kind==='initials'?'<span class="logo-note">Logo unconfirmed · initials shown</span>':'')+'</div></div><small>Checked '+esc(r.checkedAt || '2026-11-23')+' · '+esc(r.confidence)+' research confidence</small></td>'+
      cell('Auth method(s) · how software signs in','<div class="auth-methods">'+r.auth.map(a=>'<span class="badge auth-method">'+esc(a)+'</span>').join('')+'</div>')+
      cell('Self-serve or gated · getting access','<span class="badge">'+esc(labels.access[r.access] || r.access)+'</span><p>'+esc(r.accessNote)+'</p>')+
      cell('API surface · available software tools','<p>'+esc(text(r.api))+'</p>')+
      cell('Existing MCP · AI tool connector','<p>'+esc(text(r.mcp))+'</p>')+
      cell('Buildability · can we make a toolkit?','<span class="badge '+esc(['buildable','conditional','unknown','local'].includes(r.verdict)?r.verdict:'unknown')+'">'+esc(labels.verdict[r.verdict] || r.verdict)+'</span><p><strong>Main blocker / condition:</strong> '+esc(r.blocker)+'</p><small>This verdict is our assessment from the documented requirements.</small>')+
      cell('Evidence · original documentation',(sources || '<p class="missing-evidence">No usable official source found. Vendor identity and documentation need follow-up.</p>')+'<p class="evidence-note">'+esc(text(r.evidenceNotes))+'</p><small>Shared app references; support for each individual detail still needs a human check.</small>',false)+'</tr>';
  }).join('');
}
function showOverview() {
  const n = value => apps.filter(r => r.verdict === value).length;
  $('#metrics').innerHTML = [[apps.length,'apps researched'],[n('buildable'),'look ready to build'],[n('conditional'),'need conditions met'],[n('unknown'),'need more research']].map(([v,t])=>'<div class="metric"><b>'+v+'</b><span>'+t+'</span></div>').join('');
  const oauth = apps.filter(r=>/oauth/i.test(text(r.auth))).length;
  const easy = apps.filter(r=>['self-serve','trial'].includes(r.access)).length;
  $('#insights').innerHTML =
    '<article class="insight"><h3>Getting started is often possible.</h3><p>'+easy+' apps have a sign-up or trial route. That gives developers a starting point, but it does not guarantee permission to use real customer data.</p></article>'+
    '<article class="insight"><h3>Signing in is only part of the job.</h3><p>'+oauth+' apps mention OAuth: the familiar “sign in and allow access” flow. Paid plans, administrator permissions, and company approval can still stand in the way.</p></article>'+
    '<article class="insight"><h3>Some tools work differently.</h3><p>'+n('local')+' tools run on a computer rather than through an online account. They need a safe way to run commands. Their setup is different from connecting a cloud app.</p></article>';
  $('#queues').innerHTML = [
    ['Start building','Notion, Linear, GitHub, Firecrawl, and Consensus have documented ways for developers to get started. Begin with a small task, such as reading information.'],
    ['Check permission first','For advertising and finance apps, confirm account access and production approval before promising a working connection. Brex and Ramp are examples.'],
    ['Ask for more evidence','Paygent Connect needs a clear vendor identity. Fanbasis and Gumroad need stronger documentation before we can be confident about their access requirements.'],
    ['Run on a computer','Mermaid CLI and Sherlock can be turned into local tools. They need safe command execution rather than the usual online sign-in.']
  ].map(([h,p])=>'<article><b>'+h+'</b><p>'+p+'</p></article>').join('');
  const cats = [...new Set(apps.map(r=>r.category))];
  $('#category-summary').innerHTML = '<table><thead><tr><th>Type of app</th><th>Free sign-up or trial</th><th>Payment or approval</th><th>Access unclear</th></tr></thead><tbody>'+
    cats.map(c=>{const rs=apps.filter(r=>r.category===c);return '<tr><td>'+esc(c)+'</td><td>'+rs.filter(r=>['self-serve','trial'].includes(r.access)).length+'</td><td>'+rs.filter(r=>['paid','gated'].includes(r.access)).length+'</td><td>'+rs.filter(r=>r.access==='unknown').length+'</td></tr>'}).join('')+'</tbody></table>';
}
async function loadRunStatus() {
  try {
    const r = await fetch('composio-status.json?t='+Date.now());
    if (!r.ok) throw Error('No record');
    const s = await r.json();
    const good = s.status === 'completed';
    let proof=s, evidenceFile='composio-results.json';
    try {const full=await fetch('composio-full-run.json?t='+Date.now());if(full.ok){proof=await full.json();evidenceFile='composio-full-results.json'}} catch {}
    $('#run-proof').innerHTML = proof.mcpUsed && proof.toolCallsSucceeded ?
      '<p><strong>Yes — the Composio SDK and MCP were used.</strong> The '+esc(proof.appsRequested)+'-app run collected source pages for <strong>'+esc(proof.appsCompleted)+' apps</strong>. It retrieved '+esc(proof.urlsRetrieved)+' of '+esc(proof.urlsRequested)+' pages through '+esc(proof.toolCallsSucceeded)+' successful tool calls.</p>'+
      ((proof.appsWithoutRetrievedEvidence || []).length ? '<p><strong>Still missing pages for:</strong> '+proof.appsWithoutRetrievedEvidence.map(a=>esc(a.name)).join(', ')+'. These are retrieval gaps, not proof that the apps cannot be connected.</p>' : '')+
      '<p><a href="'+evidenceFile+'">View the saved Composio evidence</a></p><p class="small">The tool used was COMPOSIO_REMOTE_WORKBENCH: a hosted workspace that ran our page-reader. Each transfer was checked for missing or changed data. Collecting a page does not verify every claim on it.</p>' :
      '<p><strong>'+esc(s.status==='running'?'Composio research is running.':'Composio live run has not completed yet.')+'</strong> '+esc(s.message || '')+'</p>';
    if (!localReady) $('#composio-status').textContent = good ? 'A recorded Composio run is available. Use the local research server to run another check.' : (s.message || 'Composio setup needs a local project key.');
    return s;
  } catch {
    $('#run-proof').textContent = 'No completed Composio run is recorded yet.';
    return null;
  }
}
async function checkLocal() {
  if (!['localhost','127.0.0.1'].includes(location.hostname)) {
    $('#run-message').textContent = 'To run a fresh check, download the source and start the local research server. This hosted page shows the saved results.';
    return;
  }
  try {
    const response = await fetch('/api/health');
    if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) return;
    const health = await response.json();
    if (health.service !== 'integration-atlas-local') return;
    localReady = true;
    $('#run-research').disabled = !health.composioConfigured || health.running;
    $('#composio-status').textContent = health.running ? 'Research in progress. This can take a few minutes.' :
      health.composioConfigured ? 'Composio key found. Ready to run a real research check.' : 'Add your Composio project key to .env to enable research.';
    if (health.running) startPolling();
  } catch {}
}
function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(async()=>{
    const s = await loadRunStatus();
    if (s && s.status !== 'running') {
      clearInterval(pollTimer); pollTimer = null;
      $('#run-message').textContent = s.message || 'Research finished. See the saved evidence.';
      await checkLocal();
    }
  },2500);
}
$('#run-research').addEventListener('click',async()=>{
  $('#run-research').disabled = true;
  try {
    const response = await fetch('/api/research',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:5})});
    const result = await response.json();
    if (!response.ok) throw Error(result.message || 'Could not start the research.');
    $('#run-message').textContent = result.message;
    $('#composio-status').textContent = 'Research in progress. The results will appear here.';
    startPolling();
  } catch(error) { $('#run-message').textContent = error.message; await checkLocal(); }
});
async function start() {
  const response = await fetch('apps.json');
  if (!response.ok) throw Error('Data unavailable');
  apps = await response.json();
  try { const marks=await fetch('logos.json'); if(marks.ok)logos=await marks.json(); } catch {}
  for (const key of ['category','verdict','access']) {
    [...new Set(apps.map(r=>r[key]))].sort().forEach(value=>{
      const option=document.createElement('option');
      option.value=value; option.textContent=labels[key]?.[value] || value;
      $('#'+key).append(option);
    });
  }
  document.querySelectorAll('input,select').forEach(e=>e.addEventListener('input',render));
  render(); showOverview();
  try {
    const v = await (await fetch('verification.json')).json();
    const retrieval = v.retrieval;
    $('#verification').innerHTML = '<p>We revisited <strong>'+v.reviews.length+' selected app records</strong>. Most assessments stayed the same. QuickBooks gained a more specific requirement: a production app assessment.</p>'+
      (retrieval?'<p>We also collected pages automatically: <strong>'+retrieval.http200+' of '+retrieval.urls+' source links</strong> returned a successful response. The failed links remain in the saved log.</p>':'');
    $('#audits').innerHTML = v.reviews.map(a=>'<article class="audit"><b>'+esc(a.name)+' · '+esc(a.outcome)+'</b><p>First answer: '+esc(a.before)+'</p><p>After checking: '+esc(a.after)+'</p><a href="'+esc(a.url)+'" target="_blank" rel="noopener noreferrer">Read the original instructions</a></article>').join('');
  } catch { $('#verification').textContent = 'The check history could not be loaded.'; }
  await loadRunStatus(); await checkLocal();
}
start().catch(()=>{$('#count').textContent='The app list could not be loaded. Open the site through the local server.'});

