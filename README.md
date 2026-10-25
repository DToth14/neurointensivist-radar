[app.js](https://github.com/user-attachments/files/33916205/app.js)
/* Neurointensivist Radar: static Cloudflare Worker assets, no third-party browser dependencies. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const portals = [
    {name:'Neurocritical Care Society',type:'Specialty society career center',url:'https://www.neurocriticalcare.org/Resources-Publications/Career-Center'},
    {name:'DocCafe · Neurocritical Care',type:'Physician-only specialty listings',url:'https://www.doccafe.com/physician-jobs/specialty/neurocritical-care'},
    {name:'PracticeLink',type:'Physician recruitment listings',url:'https://www.practicelink.com/'},
    {name:'PracticeMatch',type:'Physician recruitment listings',url:'https://www.practicematch.com/'},
    {name:'NEJM CareerCenter',type:'Academic and clinical physician careers',url:'https://www.nejmcareercenter.org/'},
    {name:'USAJOBS',type:'Federal and VA openings',url:'https://www.usajobs.gov/'}
  ];
  const states = {AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',DC:'Washington, DC',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming',PR:'Puerto Rico',REMOTE:'Remote / nationwide',OTHER:'Unspecified'};
  const params = new URLSearchParams(location.search);
  const ui = {view:'jobs',search:params.get('q')||'',state:params.get('state')||'all',category:params.get('type')||'all',fresh:params.get('fresh')||'all',visa:params.get('visa')||'all',sort:params.get('sort')||'recent'};
  let data = window.RADAR_BOOTSTRAP || {meta:{mode:'starter'},jobs:[]};
  let saved = new Set();
  try { saved = new Set(JSON.parse(localStorage.getItem('ncc-radar-saved')||'[]')); } catch(_) {}
  let toastTimeout;
  const esc = value => String(value==null?'':value).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeURL = u => { try { const x = new URL(u); return ['https:','http:'].includes(x.protocol)?x.href:'#'; } catch (_) {return '#';} };
  const timeOf = value => {const dt = new Date(value||''); return Number.isFinite(dt.getTime())?dt.getTime():0;};
  const dateText = value => {const dt=new Date(value||''); return Number.isFinite(dt.getTime())?dt.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}):'Date not supplied';};
  const agoText = value => {const elapsed=Date.now()-timeOf(value);if(!timeOf(value))return 'Not yet scanned';if(elapsed<0)return 'Just scanned';const m=Math.floor(elapsed/60000);if(m<1)return 'Just now';if(m<60)return `${m} min ago`;const h=Math.floor(m/60);if(h<24)return `${h}h ago`;return `${Math.floor(h/24)}d ago`;};
  const newerThan = (val,days) => timeOf(val)>0 && (Date.now()-timeOf(val))<=days*864e5 && (Date.now()-timeOf(val))>=-864e5;
  const isNew = job => job.status==='active' && newerThan(job.first_seen,7);
  const isStarter = job => job.status==='unverified';
  const showToast = msg => {const e=$('toast');e.textContent=msg;e.classList.add('show');clearTimeout(toastTimeout);toastTimeout=setTimeout(()=>e.classList.remove('show'),2600);};
  const normal = s => String(s||'').toLowerCase();
  const initials = s => String(s||'?').replace(/[^A-Za-z0-9 ]/g,'').split(/\s+/).slice(0,2).map(x=>x[0]||'').join('').toUpperCase()||'N';
  function saveURL(){const u=new URL(location.href);u.search='';for(const [key,value] of Object.entries({q:ui.search,state:ui.state,type:ui.category,fresh:ui.fresh,visa:ui.visa,sort:ui.sort})){if(value && value!=='all' && value!=='recent')u.searchParams.set(key,value);}u.hash=`/${ui.view}`;return u.toString();}
  function syncHistory(){try{history.replaceState(null,'',saveURL());}catch(_){}}
  function currentView(){let v=location.hash.replace(/^#\/?/,'');return ['jobs','new','saved','insights','sources'].includes(v)?v:'jobs';}
  function getMatched(){
    let rows=Array.isArray(data.jobs)?data.jobs.slice():[];
    if(ui.view==='new') rows=rows.filter(isNew);
    if(ui.view==='saved') rows=rows.filter(j=>saved.has(j.id));
    if(ui.search.trim()){const terms=normal(ui.search).split(/\s+/).filter(Boolean); rows=rows.filter(j=>terms.every(t=>normal([j.title,j.company,j.location,j.description,j.category,j.source].join(' ')).includes(t)));}
    if(ui.state!=='all') rows=rows.filter(j=>j.state===ui.state);
    if(ui.category!=='all') rows=rows.filter(j=>j.category===ui.category);
    if(ui.visa!=='all') rows=rows.filter(j=>(j.visa_status||'not_stated')===ui.visa);
    if(ui.fresh==='7') rows=rows.filter(isNew);
    if(ui.fresh==='30') rows=rows.filter(j=>newerThan(j.last_seen,30) && j.status!=='unverified');
    switch(ui.sort){
      case 'posted':rows.sort((a,b)=>timeOf(b.posted_at||b.updated_at)-timeOf(a.posted_at||a.updated_at));break;
      case 'company':rows.sort((a,b)=>normal(a.company).localeCompare(normal(b.company)));break;
      case 'state':rows.sort((a,b)=>normal(a.state).localeCompare(normal(b.state)));break;
      default: rows.sort((a,b)=>timeOf(b.last_seen)-timeOf(a.last_seen)||timeOf(b.updated_at)-timeOf(a.updated_at));
    }
    return rows;
  }
  function jobCard(job){
    const fresh=isNew(job), starter=isStarter(job);
    const location=esc(job.location||'Location unspecified');
    const tags=[];
    if(fresh)tags.push('<span class="job-tag new">✧ Newly detected</span>');
    if(starter)tags.push('<span class="job-tag unverified">Starter · recheck status</span>');
    if(job.category)tags.push(`<span class="job-tag">${esc(job.category)}</span>`);
    const visaLabels={h1b_offered:'H-1B sponsorship stated',visa_offered:'Visa support stated · type unconfirmed',needs_review:'Visa mentioned · verify',no_sponsorship:'No sponsorship stated',not_stated:'Visa status not stated'};
    const visaStatus=job.visa_status||'not_stated';
    tags.push(`<span class="job-tag visa-${esc(visaStatus)}" title="Based on available posting text; verify with the employer">${esc(visaLabels[visaStatus]||visaLabels.not_stated)}</span>`);
    if(job.employment_type)tags.push(`<span class="job-tag">${esc(job.employment_type)}</span>`);
    if(job.salary && !/not disclosed/i.test(job.salary)) tags.push(`<span class="job-tag">${esc(job.salary)}</span>`);
    let dated=job.updated_at||job.posted_at||job.last_seen;
    return `<article class="job-card">
       <div class="job-card-top"><div class="company-identity"><span class="company-avatar">${esc(initials(job.company))}</span><span title="${esc(job.company)}">${esc(job.company)}</span></div><button class="save-btn ${saved.has(job.id)?'active':''}" data-save="${esc(job.id)}" aria-label="${saved.has(job.id)?'Remove saved job':'Save job'}" title="${saved.has(job.id)?'Remove saved job':'Save job'}">${saved.has(job.id)?'♥':'♡'}</button></div>
       <h3>${esc(job.title)}</h3><div class="job-meta"><span><span class="meta-ico">⌖</span>${location}</span><span><span class="meta-ico">◷</span>${dated?esc(dateText(dated)):'Date unavailable'}</span></div>
       <p class="job-desc">${esc(job.description || 'View the original employer or job board posting for the full description, eligibility and compensation.')}</p>
       <div class="job-tags">${tags.join('')}</div>
       ${job.visa_evidence?`<p class="visa-evidence"><strong>Visa language in posting:</strong> ${esc(job.visa_evidence)}</p>`:''}
       <div class="card-bottom"><span class="job-source" title="${esc((job.sources||[job.source||'Unknown']).join(', '))}">SOURCE · ${esc((job.sources||[job.source||'Unknown']).join(', '))}</span><a href="${esc(safeURL(job.url))}" target="_blank" rel="noopener noreferrer">View listing ↗</a></div>
       </article>`;
  }
  function drawCards(){
    const rows=getMatched();
    $('jobGrid').innerHTML=rows.map(jobCard).join('');
    $('shownCount').textContent=rows.length.toLocaleString();
    $('jobGrid').hidden=!rows.length;
    $('emptyState').hidden=!!rows.length;
    $('sidebarSaved').textContent=saved.size;
    $('resultsDescription').textContent= ui.view==='saved'?'Your bookmarked opportunities are stored in this browser only.':ui.view==='new'?'Roles detected in the last 7 days by connected sources.':'Search across indexed attending-level neurocritical care positions.';
    $('listingTitle').textContent=ui.view==='saved'?'Saved positions':ui.view==='new'?'Recently detected positions':'Explore open positions';
    $('starterWarning').hidden=data.meta?.mode==='live';
    document.querySelectorAll('[data-save]').forEach(button=>button.addEventListener('click',()=>toggleSave(button.dataset.save)));
  }
  function toggleSave(id){if(saved.has(id))saved.delete(id);else saved.add(id);try{localStorage.setItem('ncc-radar-saved',JSON.stringify([...saved]));}catch(_){}drawCards();showToast(saved.has(id)?'Position saved to this browser':'Position removed from saved');}
  function drawStats(){
    const jobs=data.jobs||[];
    const newCount=jobs.filter(isNew).length;
    const sCount=new Set(jobs.map(j=>j.state).filter(x=>states[x] && x!=='OTHER' && x!=='REMOTE')).size;
    const isLive=data.meta?.mode==='live';
    const last=data.meta?.generated_at;
    $('metricTotal').textContent=jobs.length.toLocaleString();
    $('metricNew').textContent=newCount.toLocaleString();
    $('metricStates').textContent=sCount.toLocaleString();
    $('metricScan').textContent=last?agoText(last):'Not yet scanned';
    $('metricScanCaption').textContent=last?`Last scan attempt: ${dateText(last)}`:'Awaiting first scan';
    $('metricTotalCaption').textContent=isLive?'Indexed from configured sources':'Verified starter examples';
    $('sidebarCount').textContent=jobs.length;
    $('sidebarNew').textContent=newCount;
    $('sidebarSaved').textContent=saved.size;
    $('statusPill').innerHTML=`<span class="dot ${isLive?'online':''}"></span>${isLive?'Monitoring active':'Starter mode'}`;
    $('statusPill').classList.toggle('live',isLive);
    $('sidebarDot').classList.toggle('online',isLive);
    $('scannerHeading').textContent=isLive?`${data.meta?.monitored_sources||0} connected sources`:'Awaiting connection';
    $('scannerSubtext').textContent=isLive?`Last run: ${agoText(last)}. Schedules may be delayed by the hosting provider.`:'Starter listings only. Connect a job API or employer board to enable new scans.';
    $('scanSummary').textContent=isLive?`Latest published scan ${agoText(last)} · refresh planned hourly`:'Starter listings · automated monitoring not yet active';
    $('sourceMeter').style.width=isLive?'100%':'0%';
    $('footerDate').textContent=isLive?`Published: ${dateText(last)}`:'Initial starter collection';
  }
  function buildStateSelect(){
    const existing=$('stateFilter').value||ui.state;
    const present=[...new Set((data.jobs||[]).map(x=>x.state).filter(Boolean))].sort((a,b)=>(states[a]||a).localeCompare(states[b]||b));
    $('stateFilter').innerHTML='<option value="all">All states</option>'+present.map(s=>`<option value="${esc(s)}">${esc(states[s]||s)}</option>`).join('');
    $('stateFilter').value=present.includes(ui.state)?ui.state:'all';ui.state=$('stateFilter').value;
  }
  function barChart(elementId,entries){
    const max=Math.max(1,...entries.map(x=>x[1]));
    $(elementId).innerHTML=entries.length?entries.map(([key,num])=>`<div class="bar-row"><div class="bar-name">${esc(key)}</div><div class="bar-track"><span style="width:${Math.max(3,num/max*100)}%"></span></div><div class="bar-number">${num}</div></div>`).join(''):'<p class="source-explainer">No matching jobs yet.</p>';
  }
  function drawInsights(){
    const byState={},byCategory={};
    (data.jobs||[]).forEach(j=>{if(j.state && j.state!=='OTHER' && j.state!=='REMOTE')byState[j.state]=(byState[j.state]||0)+1;const c=j.category||'Other';byCategory[c]=(byCategory[c]||0)+1;});
    barChart('stateChart',Object.entries(byState).sort((a,b)=>b[1]-a[1]).slice(0,15));
    barChart('categoryChart',Object.entries(byCategory).sort((a,b)=>b[1]-a[1]));
  }
  function drawSources(){
    const status=data.meta?.source_status||[];
    $('sourceHealth').innerHTML=status.length?status.map(item=>{const s=item.state||'not_configured';const label=s==='ok'?'Connected':s==='error'?'Check failed':'Not configured';const desc=s==='ok'?`${item.fetched??0} source records · ${item.matched??0} matched physician roles`:item.message||'No feed has been configured';return `<div class="health-item"><div><strong>${esc(item.source)}</strong><small>${esc(desc)}</small></div><span class="health-status ${esc(s)}">${label}</span></div>`;}).join(''):'<div class="health-item"><div><strong>No automated feeds connected yet</strong><small>Starter records are displayed. Add API credentials or public ATS boards in the project configuration.</small></div><span class="health-status">Not configured</span></div>';
    $('portalList').innerHTML=portals.map(p=>`<a class="portal" href="${esc(safeURL(p.url))}" target="_blank" rel="noopener noreferrer"><div><strong>${esc(p.name)}</strong><small>${esc(p.type)}</small></div><span>↗</span></a>`).join('');
  }
  function showView(view){
    ui.view=view;
    ['jobs','insights','sources'].forEach(id=>$(id+'View').hidden=id!==(view==='saved'||view==='new'?'jobs':view));
    document.querySelectorAll('[data-nav]').forEach(btn=>btn.classList.toggle('selected',btn.dataset.nav===view));
    if(view==='insights')drawInsights();if(view==='sources')drawSources();
    if(['jobs','saved','new'].includes(view))drawCards();
    syncHistory();
  }
  function clearFilters(){ui.search='';ui.state='all';ui.category='all';ui.fresh='all';ui.visa='all';ui.sort='recent';$('searchInput').value='';$('stateFilter').value='all';$('categoryFilter').value='all';$('freshFilter').value='all';$('visaFilter').value='all';$('sortFilter').value='recent';drawCards();syncHistory();}
  function csvCell(v){let s=String(v==null?'':v);if(/^[=+\-@]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';}
  function exportCSV(){const columns=['title','company','location','state','category','employment_type','salary','source','posted_at','first_seen','last_seen','visa_status','visa_evidence','status','url'];const rows=getMatched();const lines=[columns.join(','),...rows.map(j=>columns.map(k=>csvCell(j[k])).join(','))];const blob=new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`neurointensivist-radar-${new Date().toISOString().slice(0,10)}.csv`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);showToast(`Exported ${rows.length} listing${rows.length===1?'':'s'}`);}
  function registerEvents(){
    $('searchInput').value=ui.search;$('categoryFilter').value=ui.category;$('freshFilter').value=ui.fresh;$('visaFilter').value=ui.visa;$('sortFilter').value=ui.sort;
    $('searchInput').addEventListener('input',e=>{ui.search=e.target.value;drawCards();syncHistory()});
    [['stateFilter','state'],['categoryFilter','category'],['freshFilter','fresh'],['visaFilter','visa'],['sortFilter','sort']].forEach(([id,key])=>$(id).addEventListener('change',e=>{ui[key]=e.target.value;drawCards();syncHistory()}));
    document.querySelectorAll('[data-nav]').forEach(btn=>btn.addEventListener('click',()=>showView(btn.dataset.nav)));
    $('coverageLink').addEventListener('click',e=>{e.preventDefault();showView('sources')});
    document.querySelector('.brand').addEventListener('click',e=>{e.preventDefault();showView('jobs')});
    $('clearFilters').addEventListener('click',clearFilters);
    $('resetEmpty').addEventListener('click',clearFilters);
    $('exportBtn').addEventListener('click',exportCSV);
    $('refreshBtn').addEventListener('click',()=>location.reload());
    $('shareBtn').addEventListener('click',async()=>{const url=saveURL();try{if(navigator.share && /Mobi|Android/i.test(navigator.userAgent)){await navigator.share({title:'Neurointensivist Radar',url});return;}await navigator.clipboard.writeText(url);showToast('Dashboard link copied');}catch(e){try{const ta=document.createElement('textarea');ta.value=url;document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();showToast('Dashboard link copied');}catch(_){showToast('Copy the address in your browser to share');}}});
    window.addEventListener('hashchange',()=>showView(currentView()));
    document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();showView('jobs');$('searchInput').focus();}});
  }
  async function load(){
    try{const response=await fetch('data/jobs.json?t='+Date.now(),{cache:'no-store'});if(!response.ok)throw new Error('published data unavailable');const incoming=await response.json();if(Array.isArray(incoming.jobs)&&incoming.meta)data=incoming;}catch(_){/* Direct-opening index.html uses the embedded verified starter snapshot. */}
    buildStateSelect();drawStats();drawInsights();drawSources();showView(currentView());
  }
  registerEvents();load();
})();
