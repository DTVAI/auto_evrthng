const app = document.querySelector('#app');
const state =  {
  tools:[], cases:[], dashboard: {
  }
  , view:'home', category:'all', stage:'all', query:'', tool:null, tab:'test', result:null, currentCase:null, jobs:[], jobResult:null, imported:null, pendingJobKey:null, drafts: {
  }
  , feedback:'', error:false
}
;
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ( {
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
}
[c]));
const text = x => Array.isArray(x) ? x.map(text).join(' · ') : typeof x === 'object' && x !== null ? JSON.stringify(x) : String(x ?? '');
const pretty = x => JSON.stringify(x ??  {
}
, null, 2);
const labels =  {
  READY:'Bereit', NEEDS_DATA:'Angaben fehlen', NEEDS_DECISION:'Entscheidung nötig', EXCEPTION:'Ausnahme', OPEN:'Offen', COMPLETED:'Abgeschlossen', PENDING:'Wartet', RUNNING:'In Bearbeitung', DONE:'Ausgeführt', FAILED:'Fehlgeschlagen', implemented:'Lokal verfügbar', not_implemented:'Noch nicht verfügbar'
}
;
const status = x => `<span class="tag ${x === 'READY' || x === 'COMPLETED' ? '' : x === 'EXCEPTION' ? 'bad' : 'warn'}">${esc(labels[x] || x || 'Offen')}</span>`;
const categories = () => [...new Map(state.tools.map(t => [t.category, t.category_title || t.category])).entries()];
const icon = i => ['✉','◉','◇','▦','⇄','⌘'][i % 6];
async function api(path, options= {
}
)  {
  const res=await fetch(path, {
    ...options,headers: {
      ...(options.body ?  {
        'Content-Type':'application/json','X-Toolbox-Request':'1'
      }
      :  {
      }
      ),...options.headers
    }
  }
  );
  let data;
  try {
    data=await res.json()
  }
  catch {
    data= {
      detail:'Die Antwort konnte nicht gelesen werden.'
    }
  }
  if(!res.ok) {
    let d=data.detail;
    throw new Error(Array.isArray(d)?d.map(x=>x.msg).join('; '):d || `Fehler ${res.status}`)
  }
  return data;
}
function flash(message, error=false) {
  state.feedback=message;
  state.error=error
}
function feedback() {
  return state.feedback ? `<div class="feedback ${state.error?'error':''}" role="status">${esc(state.feedback)}</div>`:''
}
function navButton(label, view, symbol, extra='') {
  return `<button data-action="navigate" data-view="${view}" class="${state.view===view?'active':''}">
<span class="nav-icon">${symbol}</span>${esc(label)}${extra}</button>`
}
function shell(content) {
  return `<div class="shell">
<aside class="sidebar">
<div class="brand">
<span class="brand-mark">✳</span>Werkraum<span style="color:#aab4ac;font-size:10px;letter-spacing:0;margin-left:auto">HR</span>
</div>
<div class="side-label">Arbeitsbereich</div>
<nav class="nav" aria-label="Hauptnavigation">${navButton('Übersicht','home','▧')}${navButton('Alle Werkzeuge','tools','▦',`<span class="side-count">${state.tools.length}</span>`)}${navButton('Vorgänge','cases','□',`<span class="side-count">${state.cases.length}</span>`)}${navButton('Prüfaufträge','jobs','◷',`<span class="side-count">${state.jobs.length}</span>`)}</nav>
<div class="side-label">Bereiche</div>
<nav class="nav" aria-label="Werkzeugbereiche">${categories().map(([id,name],i)=>`<button data-action="category" data-category="${esc(id)}" class="${state.view==='tools'&&state.category===id?'active':''}">
<span class="nav-icon">${icon(i)}</span>${esc(name)}</button>`).join('')}</nav>
<div class="sidebar-bottom">
<strong>
<span class="dot">
</span>Lokaler Arbeitsbereich</strong>Tests führen keine externen Aktionen aus.</div>
</aside>
<main class="main">
<header class="topbar">
<div class="breadcrumb">Werkraum &nbsp; / &nbsp; <strong>${esc(({home:'Übersicht',tools:'Werkzeuge',tool:'Werkzeug',cases:'Vorgänge',case:'Vorgang',jobs:'Prüfaufträge'})[state.view])}</strong>
</div>
<label class="search">
<span class="sr-only">Werkzeuge durchsuchen</span>
<input id="global-search" type="search" placeholder="Werkzeug suchen …" value="${esc(state.query)}" aria-label="Werkzeuge durchsuchen">
</label>
<div class="top-mode">
<span class="dot">
</span>Lokaler Testmodus</div>
</header>
<div class="content">${content}</div>
</main>
</div>`
}
function home() {
  let d=state.dashboard;
  return `<section class="hero">
<div class="eyebrow">Ihr HR-Werkzeugkasten</div>
<h1>Arbeit, die leichter<br>von der Hand geht.</h1>
<p>Entdecken Sie Werkzeuge für wiederkehrende Aufgaben, prüfen Sie Beispiele und behalten Sie Ihre Vorgänge im Blick.</p>
<button class="button primary" data-action="navigate" data-view="tools">Werkzeuge entdecken <span>↗</span>
</button>
</section>
<div class="stats">
<div class="stat">
<div class="stat-label">Werkzeuge</div>
<strong>${state.tools.length}</strong>
<small>Im Werkzeugkasten</small>
</div>
<div class="stat">
<div class="stat-label">Bereiche</div>
<strong>${categories().length}</strong>
<small>Für Ihren Arbeitsalltag</small>
</div>
<div class="stat">
<div class="stat-label">Lokale Tests</div>
<strong>${d.test_runs ?? 0}</strong>
<small>Bisher durchgeführt</small>
</div>
<div class="stat">
<div class="stat-label">Vorgänge</div>
<strong>${d.case_count ?? state.cases.length}</strong>
<small>Dokumentiert</small>
</div>
</div>
<div class="section-head">
<div>
<h2>Nach Bereich entdecken</h2>
<p>Finden Sie den passenden Ausgangspunkt für Ihre Aufgabe.</p>
</div>
<button class="text-link" data-action="navigate" data-view="tools">Alle Werkzeuge ansehen ↗</button>
</div>
<div class="category-grid">${categories().map(([id,name],i)=>`<button class="category-card" data-action="category" data-category="${esc(id)}">
<span class="category-icon">${icon(i)}</span>
<strong>${esc(name)} <span class="arrow">↗</span>
</strong>
<small>${state.tools.filter(t=>t.category===id).length} Werkzeuge</small>
</button>`).join('')}</div>
<div class="section-head">
<div>
<h2>Gut zu wissen</h2>
</div>
</div>
<div class="notice">
<strong>Ein sicherer Ausgangspunkt.</strong> Die Auswertung läuft lokal mit den eingegebenen Daten. Externe Adapter sind nicht eingerichtet; es werden keine Nachrichten versendet oder Änderungen in Drittsystemen vorgenommen.</div>`
}
function toolsView() {
  let stages=[...new Set(state.tools.map(t=>t.stage).filter(Boolean))].sort();
  let q=state.query.trim().toLowerCase();
  let found=state.tools.filter(t=>(state.category==='all'||t.category===state.category)&&(state.stage==='all'||t.stage===state.stage)&&(!q||[t.id,t.title,t.goal,t.category_title,t.stage].some(x=>text(x).toLowerCase().includes(q))));
  return `<div class="page-head">
<div>
<div class="eyebrow">Der Werkzeugkasten</div>
<h1>Alle Werkzeuge.</h1>
<p>Eine passende Unterstützung für jeden Schritt Ihrer Arbeit.</p>
</div>
</div>
<div class="notice">
<strong>Lokal ausprobieren.</strong> Alle Tests sind Simulationen. Externe Anbindungen und Aktionen sind nicht eingerichtet.</div>
<div class="filters" aria-label="Bereich filtern">
<button class="chip ${state.category==='all'?'active':''}" data-action="filter-category" data-category="all">Alle Bereiche</button>${categories().map(([id,name])=>`<button class="chip ${state.category===id?'active':''}" data-action="filter-category" data-category="${esc(id)}">${esc(name)}</button>`).join('')}</div>
<div class="filters" aria-label="Paket filtern">
<button class="chip ${state.stage==='all'?'active':''}" data-action="stage" data-stage="all">Alle Pakete</button>${stages.map(s=>`<button class="chip ${state.stage===s?'active':''}" data-action="stage" data-stage="${esc(s)}">${esc(s)}</button>`).join('')}<span class="result-count">${found.length} ${found.length===1?'Werkzeug':'Werkzeuge'}</span>
</div>${found.length?`<div class="tool-grid">${found.map(t=>`<button class="tool-card" data-action="open-tool" data-id="${esc(t.id)}">
<div class="tool-top">
<span class="tool-icon">${icon(categories().findIndex(([id])=>id===t.category))}</span>
<span class="tool-id">${esc(t.id)}</span>
</div>
<h3>${esc(t.title)}</h3>
<p>${esc(text(t.goal))}</p>
<div class="card-foot">
<span class="tag">${esc(t.category_title || t.category)}</span>
<span>${esc(t.stage || '')} &nbsp; ↗</span>
</div>
</button>`).join('')}</div>`:`<div class="empty">
<strong>Keine Werkzeuge gefunden.</strong>Versuchen Sie einen anderen Suchbegriff oder Filter.</div>`}`
}
function resultView(r,artifacts) {
  if(!r)return `<div class="empty">
<strong>Noch kein Ergebnis.</strong>Laden Sie ein Beispiel und führen Sie einen lokalen Test aus.</div>`;
  let as=artifacts || r.persisted_artifacts || [];
  return `<div class="result">
<div class="panel-head">
<div>
<h3>Ergebnis der lokalen Prüfung</h3>
<p>${esc(r.summary)}</p>
</div>${status(r.status)}</div>${(r.checks||[]).map(c=>`<div class="check ${c.passed?'':'fail'}">
<b>${c.passed?'✓':'!'}</b>
<div>${esc(c.label)}${c.detail?`<small>${esc(c.detail)}</small>`:''}</div>
</div>`).join('')}${(r.warnings||[]).map(w=>`<div class="feedback">${esc(w)}</div>`).join('')}<details>
<summary class="muted">Strukturierte Daten anzeigen</summary>
<pre>${esc(pretty(r.data))}</pre>
</details>${as.length?`<h3>Artefakte</h3>
<div class="actions">${as.map(a=>`<a class="button" href="${esc(a.download_url || '/api/artifacts/'+a.id+'/download')}" download>↓ ${esc(a.name)}</a>`).join('')}</div>`:''}</div>`
}
function primitiveInputs(t) {
  const sample=t.sample|| {
  }
  ;
  let draft=state.drafts[t.id+':payload'];
  let data=sample;
  try  {
    if(draft) data=JSON.parse(draft)
  }
  catch  {
  }
  const fields=Object.entries(sample).filter(([,v])=>v!==null && ['string','number','boolean'].includes(typeof v));
  if(!fields.length) return `<p>Dieses Beispiel enthält verschachtelte Daten. Bearbeiten Sie sie im JSON-Feld.</p>`;
  return `<div class="primitive-fields">${fields.map(([key,example])=>{let value=data?.[key]??example;return `<label class="field">
<span>${esc(t.help?.input_fields?.find(f=>f.path===key)?.description || key)} <small>(${esc(key)})</small></span>${typeof example==='boolean'?`<select data-primitive="${esc(key)}" data-type="boolean">
<option value="true" ${value===true?'selected':''}>Ja</option>
<option value="false" ${value===false?'selected':''}>Nein</option>
</select>`:`<input data-primitive="${esc(key)}" data-type="${typeof example}" type="${typeof example==='number'?'number':'text'}" value="${esc(value)}">`}</label>`}).join('')}</div>`;
}
function metadataContent(value) {
  if(Array.isArray(value)) return `<div class="info-list">${value.map((v,i)=>typeof v==='object' && v!==null ? `<div>
<strong>${esc(v.title || 'Schritt '+(i+1))}${v.actor?' · '+esc(v.actor):''}</strong>
<span>${esc(v.action || text(v))}</span>${v.proof?`<p>Nachweis: ${esc(v.proof)}</p>`:''}${v.on_failure?`<p>Bei Abweichungen: ${esc(v.on_failure)}</p>`:''}</div>` : `<div>
<span>• ${esc(v)}</span>
</div>`).join('')}</div>`;
  return `<p>${esc(text(value)||'Keine weiteren Angaben verfügbar.')}</p>`
}
function metadata(t) {
  return `<div class="panel">
<h3>Auf einen Blick</h3>
<div class="info-list">
<div>
<strong>Werkzeug</strong>
<span>${esc(t.id)} · ${esc(t.stage || '')}</span>
</div>
<div>
<strong>Bereich</strong>
<span>${esc(t.category_title||t.category)}</span>
</div>
<div>
<strong>Verfügbarkeit</strong>
<span>${esc(labels[t.implementation_status]||t.implementation_status)}</span>
</div>
<div>
<strong>Rahmen</strong>
<span>${esc(text(t.scope_note)||'Lokale Prüfung; externe Schritte erfolgen manuell.')}</span>
</div>
</div>
</div>
<div class="notice">
<strong>Lokaler Testmodus</strong>
<br>Es findet keine externe Aktion statt. Ergebnisse und Entwürfe müssen fachlich geprüft werden.</div>`
}
function importPreview() {
  const result=state.imported;
  if (!result || result.tool_id !== state.tool?.id) return '';
  return `<div class="result">
<h3>Importvorschau</h3>
<p>${esc(result.filename)} · ${esc(result.format)} · ${esc(result.record_count)} Datensätze</p>
<p>Quellen-Hash: ${esc(result.source_hash)}</p>${(result.warnings||[]).map(w=>`<div class="feedback">${esc(w)}</div>`).join('')}<details>
<summary>Importierte Daten anzeigen</summary>
<pre>${esc(pretty(result.data))}</pre>
</details>${result.tool_payload?`<button class="button" data-action="apply-import">In Testdaten übernehmen</button>`:'<p>Die Daten müssen manuell den Testdaten zugeordnet werden.</p>'}</div>`;
}
function localHelp(t) {
  const help=t.help;
  if(!help) return `<div class="panel"><h3>Lokale Prüfung</h3><p>Für diese Prüfung stehen noch keine weiteren Erläuterungen zur Verfügung.</p></div>`;
  return `<div class="panel"><h3>Was die lokale Prüfung tatsächlich macht</h3><p>${esc(help.what_it_checks)}</p><p>${esc(help.note)}</p><p>Erwarteter Status des synthetischen Beispiels: ${esc(labels[help.sample_status] || help.sample_status || 'unbekannt')}.</p><h3>Eingabefelder im Beispiel</h3>${help.input_fields?.length?`<div class="table-wrap"><table><thead><tr><th>Feld</th><th>Bedeutung</th><th>Beispiel</th></tr></thead><tbody>${help.input_fields.map(f=>`<tr><td><code>${esc(f.path)}</code></td><td>${esc(f.description)}</td><td><code>${esc(text(f.example))}</code></td></tr>`).join('')}</tbody></table></div>`:'<p>Keine Felder dokumentiert.</p>'}</div>`;
}
function toolView() {
  let t=state.tool;
  if(!t)return '';
  let body=state.tab==='test'?`<div class="workspace">
<div>
<div class="panel">
<div class="panel-head">
<div>
<h3>Mit Daten ausprobieren</h3>
<p>Bearbeiten Sie die JSON-Eingabe oder laden Sie das synthetische Beispiel. Der Test läuft ausschließlich lokal; echte Adapter sind nicht eingerichtet.</p>
</div>
<span class="tag blue">TEST</span>
</div>${feedback()}${primitiveInputs(t)}<label class="field">
<span>Vollständige Testdaten · JSON-Objekt</span>
<small class="muted">Verschachtelte Daten und Listen bearbeiten Sie im JSON. Änderungen oben werden hier übernommen.</small>
<textarea id="payload" spellcheck="false">${esc(pretty(t.sample || {}))}</textarea>
</label>
<div class="actions">
<button class="button" data-action="load-sample">Beispiel laden</button>
<button class="button primary" data-action="run-test">Test ausführen ↗</button>
</div>
<div class="schedule">
<h3>Lokale Datei einlesen</h3>
<p>JSON, EML oder CSV bis 800.000 Zeichen. Die Vorschau überträgt keine Daten an Drittsysteme und bestätigt keine Quelle oder Berechtigung.</p>
<label class="field">
<span>Datei auswählen</span>
<input id="import-file" type="file" accept=".json,.eml,.csv">
</label>
<button class="button" data-action="import-file">Datei lokal einlesen</button>${importPreview()}</div>
<div class="schedule">
<h3>Lokalen Test vormerken</h3>
<p>Der Prüfauftrag wird gespeichert und nur durch den lokalen Worker verarbeitet. Er führt keine externen Aktionen aus.</p>
<label class="field">
<span>Fällig am (UTC, optional)</span>
<input id="job-due" type="datetime-local">
</label>
<button class="button" data-action="schedule-job">Prüfauftrag anlegen</button>
</div>${resultView(state.result)}</div>
<div class="panel">
<h3>Als Vorgang dokumentieren</h3>
<p>Speichern Sie die aktuellen Eingaben als Vorgang. Eine Quellenreferenz kann helfen, denselben Vorgang wiederzufinden.</p>
<label class="field">
<span>Titel *</span>
<input id="case-title" placeholder="z. B. Prüfung für Team A">
</label>
<label class="field">
<span>Quellenreferenz (optional)</span>
<input id="source-ref" placeholder="z. B. Ticket-123">
</label>
<label class="field">
<span>Betreff-ID (optional)</span>
<input id="subject-id" placeholder="Interne Kennung">
</label>
<button class="button" data-action="create-case">Vorgang anlegen ↗</button>
</div>
</div>
<aside>${metadata(t)}</aside>
</div>`:state.tab==='how'?`<div class="workspace">
<div>
<div class="panel">
<h3>Ursprüngliches Prozessziel</h3>
<p>${esc(text(t.goal))}</p>
</div>${localHelp(t)}${[['Eingaben im Prozessziel',t.inputs],['Zuständigkeit',t.authority],['So gehen Sie vor',t.steps],['Wann ist es abgeschlossen?',t.completion],['Bei Abweichungen',t.recovery]].map(([title,val])=>`<div class="panel">
<h3>${title}</h3>${metadataContent(val)}</div>`).join('')}</div>
<aside>${metadata(t)}</aside>
</div>`:`<div class="panel">
<div class="panel-head">
<div>
<h3>Vorgänge zu ${esc(t.id)}</h3>
<p>Gespeicherte Eingaben, Freigaben und Nachweise.</p>
</div>
</div>${caseList(state.cases.filter(c=>c.tool_id===t.id))}</div>`;
  return `<button class="text-link back" data-action="navigate" data-view="tools">← Zurück zu den Werkzeugen</button>
<div class="page-head">
<div class="detail-title">
<span class="tool-icon">✳</span>
<div>
<div class="eyebrow">${esc(t.category_title||t.category)} &nbsp; / &nbsp; ${esc(t.id)}</div>
<h1>${esc(t.title)}</h1>
<p>${esc(text(t.goal))}</p>
</div>
</div>
<span class="tag blue">${esc(t.stage||'')}</span>
</div>
<div class="tabs" role="tablist">${[['test','Anwenden & testen'],['how','So funktioniert’s'],['cases','Vorgänge']].map(([id,label])=>`<button role="tab" aria-selected="${state.tab===id}" class="${state.tab===id?'active':''}" data-action="tab" data-tab="${id}">${label}</button>`).join('')}</div>${body}`
}
function caseList(cases) {
  return cases.length?cases.map(c=>`<div class="case-row">
<button data-action="open-case" data-id="${c.id}">
<strong>${esc(c.title)}</strong>
<small>${esc(c.tool_id)} · Revision ${c.revision} · ${esc(c.source_ref||'Ohne Quellenreferenz')}</small>
</button>${status(c.status)}<button class="text-link" data-action="open-case" data-id="${c.id}" style="flex:none">Öffnen ↗</button>
</div>`).join(''):`<div class="empty">
<strong>Noch keine Vorgänge vorhanden.</strong>Ein Vorgang kann direkt bei einem Werkzeug angelegt werden.</div>`
}
function casesView() {
  return `<div class="page-head">
<div>
<div class="eyebrow">Dokumentation</div>
<h1>Ihre Vorgänge.</h1>
<p>Prüfungen, Freigaben und Nachweise an einem Ort.</p>
</div>
<button class="button" data-action="navigate" data-view="tools">Werkzeug auswählen ↗</button>
</div>
<div class="panel">${caseList(state.cases)}</div>`
}
function caseView() {
  let c=state.currentCase;
  if(!c)return '';
  let approval=c.approvals?.some(a=>a.revision===c.revision&&a.payload_hash===c.payload_hash);
  let proof=c.evidence?.some(e=>e.revision===c.revision&&e.kind==='independent_readback'&&e.reference?.trim()&&e.observed_hash===c.payload_hash);
  return `<button class="text-link back" data-action="navigate" data-view="cases">← Alle Vorgänge</button>
<div class="page-head">
<div>
<div class="eyebrow">Vorgang #${c.id} &nbsp; / &nbsp; ${esc(c.tool_id)}</div>
<h1>${esc(c.title)}</h1>
<p>Revision ${c.revision} · ${esc(c.source_ref||'Ohne Quellenreferenz')} ${c.subject_id?'· '+esc(c.subject_id):''}</p>
</div>${status(c.status)}</div>${feedback()}<div class="workspace">
<div>
<div class="panel">
<h3>Eingaben bearbeiten</h3>
<p>Eine Änderung erstellt eine neue Revision. Freigabe und Nachweis müssen dann erneut für diese Revision vorliegen.</p>
<label class="field">
<span>Titel</span>
<input id="edit-title" value="${esc(c.title)}">
</label>
<label class="field">
<span>Aktuelle Eingaben · JSON-Objekt</span>
<textarea id="edit-payload" spellcheck="false">${esc(pretty(c.payload))}</textarea>
</label>
<button class="button" data-action="save-case">Neue Revision speichern</button>${resultView(c.result,c.artifacts)}</div>
<div class="panel">
<h3>Freigabe der aktuellen Revision</h3>
<p>Die Freigabe wird an den Inhalt dieser Revision und ihren Hash gebunden.</p>
<label class="field">
<span>Kommentar (optional)</span>
<input id="approval-comment" placeholder="Vermerk zur Freigabe">
</label>
<button class="button" data-action="approve">Revision ${c.revision} freigeben</button>
</div>
<div class="panel">
<h3>Manuelle Bestätigung einer unabhängigen Rücklesung</h3>
<p>Sie bestätigen hier selbst eine tatsächlich unabhängig durchgeführte Rücklesung. Die Anwendung prüft keine externe Quelle automatisch. Für den Abschluss muss das beobachtete JSON das vollständige aktuelle Eingabeobjekt exakt wiedergeben; dies ist eine Einschränkung dieses lokalen Nachweisverfahrens.</p>
<label class="field">
<span>Art der manuellen Bestätigung</span>
<select id="evidence-kind">
<option value="independent_readback">Unabhängige Rücklesung (manuell bestätigt)</option>
</select>
</label>
<label class="field">
<span>Explizite Quellenreferenz *</span>
<input id="evidence-ref" placeholder="z. B. Beleg oder Fundstelle der Rücklesung">
</label>
<label class="field">
<span>Beobachteter Zustand · JSON-Objekt *</span>
<textarea id="evidence-observed" spellcheck="false" placeholder="{}">
</textarea>
</label>
<button class="button" data-action="evidence">Nachweis speichern</button>
</div>
<div class="panel history">
<h3>Verlauf & Revisionen</h3>${[['Revisionen',c.revisions],['Freigaben',c.approvals],['Nachweise',c.evidence],['Ereignisse',c.events]].map(([name,rows])=>`<details>
<summary>${name} (${rows?.length||0})</summary>
<pre>${esc(pretty(rows||[]))}</pre>
</details>`).join('')}</div>
</div>
<aside>
<div class="panel">
<h3>Abschluss prüfen</h3>
<p>Der Abschluss erfordert eine bereite lokale Prüfung, eine Freigabe und einen passenden externen Nachweis für diese Revision.</p>
<div class="check ${c.result?.status==='READY'?'':'fail'}">
<b>${c.result?.status==='READY'?'✓':'○'}</b> Lokale Prüfung bereit</div>
<div class="check ${approval?'':'fail'}">
<b>${approval?'✓':'○'}</b> Aktuelle Revision freigegeben</div>
<div class="check ${proof?'':'fail'}">
<b>${proof?'✓':'○'}</b> Manuelle Rücklesung passend bestätigt</div>
<p style="margin-top:16px;word-break:break-all">Inhalts-Hash: ${esc(c.payload_hash)}</p>
<button class="button primary" data-action="complete">Vorgang abschließen</button>
</div>
<div class="notice">
<strong>Externe Schritte bleiben manuell.</strong>
<br>Diese Anwendung führt keine Änderungen in Drittsystemen aus.</div>
</aside>
</div>`
}
function jobsView() {
  return `<div class="page-head">
<div>
<div class="eyebrow">Lokale Ausführung</div>
<h1>Prüfaufträge.</h1>
<p>Gespeicherte lokale Prüfungen und ihre Ergebnisse.</p>
</div>
<button class="button" data-action="refresh-jobs">↻ Aktualisieren</button>
</div>
<div class="notice">
<strong>Nur lokale Tests.</strong> Aufträge werden durch den lokalen Worker verarbeitet. Start: <code>python -m app.worker</code>. Es werden keine externen Aktionen ausgeführt.</div>
<div class="panel" style="margin-top:16px">${state.jobs.length?state.jobs.map(j=>`<div class="case-row">
<div style="flex:1">
<strong>${esc(j.tool_id)} · Auftrag #${j.id}</strong>
<small>Fällig: ${esc(j.due_at || 'sofort')} · Versuche: ${j.attempts}</small>
</div>${status(j.status)}${j.run_id?`<button class="text-link" data-action="open-run" data-id="${j.run_id}" style="flex:none">Ergebnis ↗</button>`:''}</div>`).join(''):`<div class="empty">
<strong>Noch keine Prüfaufträge.</strong>Ein lokaler Test kann bei einem Werkzeug vorgemerkt werden.</div>`}${state.jobResult?resultView(state.jobResult):''}</div>`
}
function render() {
  app.innerHTML=shell(( {
    home,tools:toolsView,tool:toolView,cases:casesView,case:caseView,jobs:jobsView
  }
  )[state.view]());
  let key=state.view==='tool'&&state.tool?state.tool.id:state.view==='case'&&state.currentCase?'case-'+state.currentCase.id:null;
  if(key) {
    for(const el of app.querySelectorAll('input[id],textarea[id]')) {
      const value=state.drafts[key+':'+el.id];
      if(value!==undefined && el.type!=='file')el.value=value
    }
  }
}
function parseObject(id) {
  let v;
  try {
    v=JSON.parse(document.getElementById(id).value)
  }
  catch(e) {
    throw new Error(`Ungültiges JSON: ${e.message}`)
  }
  if(!v||Array.isArray(v)||typeof v!=='object')throw new Error('Bitte ein JSON-Objekt eingeben.');
  return v
}
async function refresh() {
  [state.cases,state.dashboard,state.jobs]=await Promise.all([api('/api/cases'),api('/api/dashboard'),api('/api/jobs')])
}
async function openCase(id) {
  state.currentCase=await api('/api/cases/'+id);
  state.view='case';
  state.feedback=''
}
app.addEventListener('input',e=> {
  let key=state.view==='tool'&&state.tool?state.tool.id:state.view==='case'&&state.currentCase?'case-'+state.currentCase.id:null;
  if(state.view==='tool' && (e.target.id==='payload' || e.target.id==='job-due' || e.target.dataset.primitive)) state.pendingJobKey=null;
  if(key&&e.target.id&&e.target.id!=='global-search'&&e.target.type!=='file') state.drafts[key+':'+e.target.id]=e.target.value;
  if(e.target.dataset.primitive) {
    try  {
      let editor=document.getElementById('payload');
      let data=JSON.parse(editor.value);
      let v=e.target.value;
      if(e.target.dataset.type==='boolean')v=v==='true';
      if(e.target.dataset.type==='number')v=Number(v);
      data[e.target.dataset.primitive]=v;
      editor.value=pretty(data);
      state.drafts[state.tool.id+':payload']=editor.value
    }
    catch {
      flash('Bitte zuerst das JSON korrigieren.',true);
      let f=document.querySelector('.feedback[role=status]');
      if(f)f.textContent=state.feedback
    }
  }
  if(e.target.id==='payload') {
    try {
      let data=JSON.parse(e.target.value);
      for(const input of app.querySelectorAll('[data-primitive]'))if(Object.hasOwn(data,input.dataset.primitive))input.value=String(data[input.dataset.primitive])
    }
    catch {
    }
  }
  if(e.target.id==='global-search') {
    state.query=e.target.value;
    state.view='tools';
    render();
    let input=document.getElementById('global-search');
    input.focus();
    input.setSelectionRange(input.value.length,input.value.length)
  }
}
);
app.addEventListener('click',async e=> {
  let b=e.target.closest('[data-action]');
  if(!b)return;
  let action=b.dataset.action;
  const mutating=['schedule-job','run-test','create-case','save-case','approve','evidence','complete','import-file'].includes(action);
  if(mutating && b.disabled) return;
  if(mutating) b.disabled=true;
  try {
    if(action==='navigate') {
      state.view=b.dataset.view;
      state.feedback='';
      if(state.view==='tools') {
        state.category='all';
        state.stage='all'
      }
    }
    else if(action==='category'||action==='filter-category') {
      state.view='tools';
      state.category=b.dataset.category;
      state.stage='all'
    }
    else if(action==='stage') {
      state.stage=b.dataset.stage
    }
    else if(action==='open-tool') {
      state.pendingJobKey=null;
      state.tool=await api('/api/tools/'+encodeURIComponent(b.dataset.id));
      state.view='tool';
      state.tab='test';
      state.result=null;
      state.feedback=''
    }
    else if(action==='tab') {
      state.tab=b.dataset.tab;
      state.feedback=''
    }
    else if(action==='load-sample') {
      state.pendingJobKey=null;
      state.drafts[state.tool.id+':payload']=pretty(state.tool.sample|| {
      }
      );
      render();
      return
    }
    else if(action==='refresh-jobs') {
      state.jobs=await api('/api/jobs');
      state.jobResult=null
    }
    else if(action==='open-run') {
      state.jobResult=await api('/api/runs/'+b.dataset.id)
    }
    else if(action==='import-file') {
      let file=document.getElementById('import-file').files[0];
      if(!file) throw new Error('Bitte eine Datei auswählen.');
      let format=file.name.split('.').pop().toLowerCase();
      if(!['json','eml','csv'].includes(format)) throw new Error('Bitte eine JSON-, EML- oder CSV-Datei auswählen.');
      let content=await file.text();
      if(content.length>800000) throw new Error('Die Datei darf höchstens 800.000 Zeichen enthalten.');
      state.imported={...await api('/api/imports',{method:'POST',body:JSON.stringify({format,content,filename:file.name,tool_id:state.tool.id})}),tool_id:state.tool.id};
      flash('Datei lokal eingelesen. Bitte Vorschau und Zuordnung prüfen.');
    }
    else if(action==='apply-import') {
      state.pendingJobKey=null;
      if(!state.imported?.tool_payload) throw new Error('Keine Werkzeugdaten zum Übernehmen vorhanden.');
      state.drafts[state.tool.id+':payload']=pretty(state.imported.tool_payload);
      state.drafts[state.tool.id+':source-ref']=state.imported.source_ref || 'sha256:'+state.imported.source_hash;
      flash('Importierte Daten und Quellenreferenz übernommen. Bitte vor der Prüfung kontrollieren.');
    }
    else if(action==='schedule-job') {
      let payload=parseObject('payload');
      let due=document.getElementById('job-due').value;
      let body= {
        tool_id:state.tool.id,payload,due_at:due?new Date(due+'Z').toISOString():null,idempotency_key:state.pendingJobKey ||= crypto.randomUUID()
      }
      ;
      await api('/api/jobs', {
        method:'POST',body:JSON.stringify(body)
      }
      );
      state.pendingJobKey=null;
      state.jobs=await api('/api/jobs');
      flash('Lokaler Prüfauftrag angelegt. Der Worker verarbeitet ihn zur angegebenen Zeit.')
    }
    else if(action==='run-test') {
      let payload=parseObject('payload');
      let result=await api('/api/tools/'+encodeURIComponent(state.tool.id)+'/test', {
        method:'POST',body:JSON.stringify(payload)
      }
      );
      state.result=result;
      let raw=pretty(payload);
      render();
      document.getElementById('payload').value=raw;
      return
    }
    else if(action==='create-case') {
      let payload=parseObject('payload');
      let title=document.getElementById('case-title').value.trim();
      if(!title)throw new Error('Bitte einen Titel für den Vorgang eingeben.');
      let c=await api('/api/tools/'+encodeURIComponent(state.tool.id)+'/cases', {
        method:'POST',body:JSON.stringify( {
          title,payload,source_ref:document.getElementById('source-ref').value.trim()||null,subject_id:document.getElementById('subject-id').value.trim()||null
        }
        )
      }
      );
      await refresh();
      await openCase(c.id);
      flash('Vorgang geöffnet. Bei gleicher Quellenreferenz wird der bestehende Vorgang verwendet.')
    }
    else if(action==='open-case') {
      await openCase(b.dataset.id)
    }
    else if(action==='save-case') {
      let c=state.currentCase;
      state.currentCase=await api('/api/cases/'+c.id, {
        method:'PATCH',body:JSON.stringify( {
          revision:c.revision,title:document.getElementById('edit-title').value.trim(),payload:parseObject('edit-payload')
        }
        )
      }
      );
      delete state.drafts['case-'+c.id+':edit-title'];
      delete state.drafts['case-'+c.id+':edit-payload'];
      await refresh();
      flash('Neue Revision gespeichert und lokal geprüft.')
    }
    else if(action==='approve') {
      let c=state.currentCase;
      state.currentCase=await api('/api/cases/'+c.id+'/approve', {
        method:'POST',body:JSON.stringify( {
          revision:c.revision,comment:document.getElementById('approval-comment').value
        }
        )
      }
      );
      flash('Freigabe für die aktuelle Revision gespeichert.')
    }
    else if(action==='evidence') {
      let c=state.currentCase;
      let kind=document.getElementById('evidence-kind').value.trim(),reference=document.getElementById('evidence-ref').value.trim();
      if(!kind||!reference)throw new Error('Bitte Art und Referenz des Nachweises eingeben.');
      state.currentCase=await api('/api/cases/'+c.id+'/evidence', {
        method:'POST',body:JSON.stringify( {
          revision:c.revision,kind,reference,observed:parseObject('evidence-observed')
        }
        )
      }
      );
      flash('Nachweis gespeichert.')
    }
    else if(action==='complete') {
      let c=state.currentCase;
      state.currentCase=await api('/api/cases/'+c.id+'/complete', {
        method:'POST',body:JSON.stringify( {
          revision:c.revision
        }
        )
      }
      );
      await refresh();
      flash('Vorgang abgeschlossen.')
    }
    render();
    window.scrollTo( {
      top:0,behavior:'smooth'
    }
    )
  }
  catch(err) {
    flash(err.message,true);
    let existing=document.querySelector('.feedback[role=status]');
    if(existing) {
      existing.textContent=err.message;
      existing.className='feedback error'
    }
    else {
      let target=document.querySelector('.content');
      target.insertAdjacentHTML('afterbegin',feedback())
    }
  } finally { if(mutating) b.disabled=false; }
}
);
try {
  [state.tools,state.cases,state.dashboard,state.jobs]=await Promise.all([api('/api/tools'),api('/api/cases'),api('/api/dashboard'),api('/api/jobs')]);
  render()
}
catch(err) {
  app.innerHTML=`<div class="initial">
<strong>Werkraum konnte nicht geladen werden.</strong>
<p>${esc(err.message)}</p>
<p>Bitte prüfen Sie, ob der lokale Server läuft, und laden Sie die Seite erneut.</p>
</div>`
}
