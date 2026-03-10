// ═══════════════════════════════════════════════════════════════
// NOC COMMAND — Application Logic
// ═══════════════════════════════════════════════════════════════

// ═══ MARKDOWN RENDERER ═══
function renderMarkdown(text) {
  if (!text) return '';
  let html = text;
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // Code blocks
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

  // Tables
  html = html.replace(/^\|(.+)\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.+\|\s*\n?)*)/gm, (match, header, body) => {
    const ths = header.split('|').map(h => h.trim()).filter(Boolean).map(h => `<th>${h}</th>`).join('');
    const rows = body.trim().split('\n').map(row => {
      const tds = row.split('|').map(c => c.trim()).filter(Boolean).map(c => `<td>${c}</td>`).join('');
      return `<tr>${tds}</tr>`;
    }).join('');
    return `<table><thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table>`;
  });

  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  html = html.replace(/^[═─━]{3,}$/gm, '<hr>');
  html = html.replace(/^[-*_]{3,}$/gm, '<hr>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>');
  html = html.replace(/((?:<li>.*<\/li>\s*)+)/g, '<ul>$1</ul>');

  // Tool call formatting
  html = html.replace(/^► (.+)$/gm, '<span class="tool-call-line">► $1</span>');
  html = html.replace(/^✓ (.+)$/gm, '<span class="tool-result-line">✓ $1</span>');
  html = html.replace(/\n\n/g, '</p><p>');
  html = html.replace(/<p>\s*<\/p>/g, '');
  return html;
}

// ═══ SLA TICKER ═══
let slaExposure = 0, slaInterval = null, slaRate = 0;

function startSlaTicker(alert) {
  const rates = { CRITICAL: 850, MAJOR: 350, MINOR: 100 };
  slaRate = (rates[alert.severity] || 200) / 3600;
  slaExposure = 0;
  document.getElementById('slaTicker').classList.add('on');
  document.getElementById('slaCard').style.display = '';
  slaInterval = setInterval(() => {
    slaExposure += slaRate;
    const f = '$' + Math.floor(slaExposure).toLocaleString();
    document.getElementById('slaTickerVal').textContent = f;
    document.getElementById('iSla').textContent = f;
  }, 1000);
}

function stopSlaTicker() { if (slaInterval) { clearInterval(slaInterval); slaInterval = null; } }

// ═══ DISSEMINATION ═══
function showDissemination() {
  const container = document.getElementById('disseminationContainer');
  const progress = document.getElementById('disseminationProgress');
  container.classList.add('on');
  progress.classList.add('on');

  const items = [
    { icon: 'phone', emoji: '📞', text: 'Emergency hotline activated for Life-Safety accounts', delay: 200 },
    { icon: 'email', emoji: '📧', text: 'Enterprise notification sent to 12 accounts', delay: 800 },
    { icon: 'sms', emoji: '💬', text: 'VIP SMS dispatched to 8 premium customers', delay: 1400 },
    { icon: 'email', emoji: '📧', text: 'Government compliance notification filed', delay: 2000 },
    { icon: 'push', emoji: '📱', text: 'Push notification queued for 4,200 subscribers', delay: 2600 },
    { icon: 'sms', emoji: '💬', text: 'Mass SMS blast sent to affected area', delay: 3200 },
    { icon: 'email', emoji: '📧', text: 'Status page updated: status.ourtelco.com', delay: 3800 },
  ];
  let completed = 0;
  items.forEach(item => {
    setTimeout(() => {
      const row = document.createElement('div');
      row.className = 'dissemination-row';
      row.innerHTML = `<div class="dissemination-icon ${item.icon}">${item.emoji}</div><span class="dissemination-text">${item.text}</span><span class="dissemination-status">SENT ✓</span>`;
      container.insertBefore(row, container.firstChild);
      while (container.children.length > 5) container.removeChild(container.lastChild);
      completed++;
      progress.textContent = `${completed}/${items.length} notifications dispatched`;
      if (completed === items.length) setTimeout(() => { progress.textContent = '✓ ALL NOTIFICATIONS DISPATCHED SUCCESSFULLY'; }, 500);
    }, item.delay);
  });
}

// ═══ STATE ═══
const D = {
  alerts: [], sel: null, es: null, out: {}, rawOut: {}, tab: null, t0: null, ti: null, done: new Set(),
  sessions: {},
  running: false,
  commStates: {},  // Per-communication approval state: { id: 'approved'|'rejected'|null }
  stageNode: { network_analysis: 'pn-network', approval: 'pn-approval' },
  stageMini: { resilience_check: 'pm-resilience', customer_impact: 'pm-impact', enterprise_comms: 'pm-ent', vip_comms: 'pm-vip', mass_comms: 'pm-mass' },
  stageParallel: { resilience_check: 'pp-stage2', customer_impact: 'pp-stage2', enterprise_comms: 'pp-drafters', vip_comms: 'pp-drafters', mass_comms: 'pp-drafters' },
  stageLabel: { network_analysis: 'Network Analyst', resilience_check: 'Resilience Check', customer_impact: 'Customer Impact', enterprise_comms: 'Enterprise Comms', vip_comms: 'VIP Comms', mass_comms: 'Mass Notifications', approval: 'Approval Dashboard' },
  stageWire: { 2: 'pw-1', 3: 'pw-2', 4: 'pw-3' },
};

// ═══ CLOCK ═══
const tick = () => { document.getElementById('clock').textContent = new Date().toLocaleTimeString('en-US',{hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'}); };
setInterval(tick, 1000); tick();

// ═══ INITIALIZATION ═══
async function init() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
  const r = await fetch('/api/alerts');
  D.alerts = await r.json();
  document.getElementById('alertBadge').textContent = D.alerts.length;
  document.getElementById('hIncidents').textContent = D.alerts.length;
  const total = D.alerts.reduce((s,a) => s + a.estimated_customers_affected, 0);
  document.getElementById('hAtRisk').textContent = total.toLocaleString();
  if (D.alerts.some(a => a.severity === 'CRITICAL')) {
    document.getElementById('statusChip').classList.add('alert-mode');
    document.getElementById('statusText').textContent = 'CRITICAL';
  }
  renderFeed();
}

// ═══ ALERT FEED ═══
function renderFeed() {
  document.getElementById('alertFeed').innerHTML = D.alerts.map(a => {
    const sc = a.severity.toLowerCase();
    const t = new Date(a.timestamp).toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:false});
    const act = D.sel?.alert_id === a.alert_id ? 'active' : '';
    const cached = D.sessions[a.alert_id] ? '<span class="acard-cached">ANALYZED</span>' : '';
    return `<div class="acard sev-${sc} ${act}" onclick="pick('${a.alert_id}')">
      <div class="acard-row1"><span class="sev-tag ${sc}">${a.severity}</span><span class="acard-type">${a.alert_type.replace(/_/g,' ')}</span>${cached}<span class="acard-time">${t}</span></div>
      <div class="acard-title">${a.title}</div>
      <div class="acard-footer"><span class="acard-customers">~${a.estimated_customers_affected.toLocaleString()} affected</span><span>${a.escalation_level}</span></div>
    </div>`;
  }).join('');
}

// ═══ CUSTOM CONFIRM DIALOG ═══
function showConfirm(title, message, onConfirm) {
  document.getElementById('confirmTitle').textContent = title;
  document.getElementById('confirmMsg').innerHTML = message;
  document.getElementById('confirmBg').classList.add('on');

  const cancelBtn = document.getElementById('confirmCancel');
  const okBtn = document.getElementById('confirmOk');

  // Clone to remove old listeners
  const newCancel = cancelBtn.cloneNode(true);
  const newOk = okBtn.cloneNode(true);
  cancelBtn.parentNode.replaceChild(newCancel, cancelBtn);
  okBtn.parentNode.replaceChild(newOk, okBtn);

  newCancel.addEventListener('click', () => {
    document.getElementById('confirmBg').classList.remove('on');
  });
  newOk.addEventListener('click', () => {
    document.getElementById('confirmBg').classList.remove('on');
    onConfirm();
  });
}

// ═══ ALERT SELECTION ═══
async function pick(id) {
  const a = D.alerts.find(x => x.alert_id === id);
  if (!a) return;

  if (D.sel?.alert_id === id) return;

  // Check for cached session
  if (D.sessions[id]) {
    switchToAlert(a);
    restoreSession(id);
    return;
  }

  // Confirm before aborting running pipeline
  if (D.running) {
    showConfirm(
      'Abort Pipeline?',
      `A pipeline is currently running for <strong>${D.sel.title}</strong>.<br><br>Abort and analyze <strong>${a.title}</strong> instead?`,
      () => { switchToAlert(a); startSlaTicker(a); stream(id); }
    );
    return;
  }

  switchToAlert(a);
  startSlaTicker(a);
  stream(id);
}

function switchToAlert(a) {
  if (D.es) { D.es.close(); D.es = null; }
  if (D.ti) clearInterval(D.ti);
  stopSlaTicker();
  D.running = false;
  D.out = {}; D.rawOut = {}; D.tab = null; D.done = new Set();
  D.sel = a;
  renderFeed();

  // Reset pipeline visuals
  ['pn-network','pn-approval'].forEach(id => { document.getElementById(id).classList.remove('running','done'); });
  ['pm-resilience','pm-impact','pm-ent','pm-vip','pm-mass'].forEach(id => { document.getElementById(id).classList.remove('running','done'); });
  ['pw-1','pw-2','pw-3'].forEach(id => { document.getElementById(id).classList.remove('lit','done'); });
  document.getElementById('pp-stage2').classList.remove('active','done');
  document.getElementById('pp-drafters').classList.remove('active','done');

  document.getElementById('welcome').style.display = 'none';
  document.getElementById('tabsRow').className = 'tabs-row on';
  document.getElementById('tabsRow').innerHTML = '';
  document.getElementById('term').className = 'term on';
  document.getElementById('termBody').innerHTML = '';
  document.getElementById('approvedBar').classList.remove('on');
  document.getElementById('pipeStatusList').innerHTML = '';
  document.getElementById('comparisonBar').classList.remove('on');
  document.getElementById('ctaBar').classList.remove('on');
  document.getElementById('disseminationContainer').classList.remove('on');
  document.getElementById('disseminationContainer').innerHTML = '';
  document.getElementById('disseminationProgress').classList.remove('on');
  document.getElementById('execBriefBtn').style.display = 'none';

  const stv = document.getElementById('slaTickerVal');
  stv.style.animation = ''; stv.style.color = '';
  document.getElementById('iSla').style.color = '';
  document.getElementById('iSla').style.textShadow = '';

  updateImpact(a);
}

function restoreSession(alertId) {
  const s = D.sessions[alertId];
  D.out = { ...s.out };
  D.rawOut = { ...s.rawOut };
  D.done = new Set(s.done);

  Object.keys(D.out).forEach(stage => {
    const label = D.stageLabel[stage] || stage;
    addTab(stage, label);
    setPipeStatus(stage, 'done');
    const nodeId = D.stageNode[stage];
    if (nodeId) { document.getElementById(nodeId).classList.add('done'); }
    const miniId = D.stageMini[stage];
    if (miniId) { document.getElementById(miniId).classList.add('done'); }
  });

  if (D.done.has('resilience_check') && D.done.has('customer_impact')) { document.getElementById('pp-stage2').classList.add('done'); }
  if (D.done.has('enterprise_comms') && D.done.has('vip_comms') && D.done.has('mass_comms')) { document.getElementById('pp-drafters').classList.add('done'); }
  ['pw-1','pw-2','pw-3'].forEach(id => document.getElementById(id).classList.add('done'));

  const firstStage = Object.keys(D.out)[0];
  if (firstStage) showTab(firstStage);

  showComparison();
  showCtaBar();
}

// ═══ IMPACT PANEL UPDATE ═══
function updateImpact(a) {
  const sev = document.getElementById('iSev');
  sev.textContent = a.severity; sev.className = 'icard-val';
  if (a.severity === 'CRITICAL') sev.classList.add('red');
  else if (a.severity === 'MAJOR') sev.classList.add('amber');
  else sev.classList.add('cyan');

  const esc = document.getElementById('iEsc');
  esc.textContent = a.escalation_level; esc.className = 'icard-val';
  if (a.escalation_level.includes('SEV1')) esc.classList.add('red');
  else if (a.escalation_level.includes('SEV2')) esc.classList.add('amber');

  document.getElementById('iCust').textContent = a.estimated_customers_affected.toLocaleString();
  document.getElementById('iEtr').textContent = a.preliminary_etr;
  document.getElementById('iType').textContent = a.alert_type.replace(/_/g, ' ');
  document.getElementById('dZones').innerHTML = (a.affected_zones||[]).map(z => `<span class="zone-tag">${z}</span>`).join('');
  document.getElementById('dServices').innerHTML = (a.services_impacted||[]).map(s => `<span class="svc-tag">${s.replace(/_/g,' ')}</span>`).join('');

  const fd = a.field_dispatch || {};
  document.getElementById('dDispatch').innerHTML = `
    <div class="detail-row"><span class="dl">Crew</span><span class="dv">${fd.crew_id||'—'}</span></div>
    <div class="detail-row"><span class="dl">ETA</span><span class="dv">${fd.eta_to_site||'—'}</span></div>
    <div class="detail-row"><span class="dl">Status</span><span class="dv" style="color:var(--amber)">${fd.status||'—'}</span></div>`;

  document.getElementById('dRelated').innerHTML = (a.related_alerts||[]).map(r =>
    `<div style="margin-bottom:6px;font-size:10px;"><span style="color:var(--amber);font-family:var(--font-mono);font-size:9px;">${r.type}</span><br><span style="color:var(--text-muted)">${r.description}</span></div>`
  ).join('') || '<span style="color:var(--text-ghost);font-size:11px">None</span>';
}

// ═══ SSE STREAMING ═══
const TOTAL_STAGES = 7;
let stagesSeen = 0;
let thinkingTimer = null;
const ORIGINAL_TITLE = document.title;

function clearThinkingTimer() { if (thinkingTimer) { clearTimeout(thinkingTimer); thinkingTimer = null; } }

function startThinkingTimer(stageLabel) {
  clearThinkingTimer();
  let dots = 0;
  const baseText = `${stageLabel} reasoning`;
  thinkingTimer = setInterval(() => {
    dots = (dots + 1) % 4;
    document.getElementById('procLabel').textContent = baseText + '.'.repeat(dots + 1);
  }, 800);
}

function updateStageCount() {
  document.getElementById('procStageCount').textContent = `${stagesSeen}/${TOTAL_STAGES}`;
}

function cancelPipeline() {
  if (D.es) { D.es.close(); D.es = null; }
  if (D.ti) clearInterval(D.ti);
  clearThinkingTimer();
  D.running = false;
  document.getElementById('procLabel').textContent = 'Pipeline cancelled';
  setTimeout(() => document.getElementById('procBar').classList.remove('on'), 1500);
}

function notifyComplete() {
  document.title = '[✓ READY] ' + ORIGINAL_TITLE;
  window.addEventListener('focus', () => { document.title = ORIGINAL_TITLE; }, { once: true });
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification('NOC Command', { body: 'Outage communications ready for approval', tag: 'pipeline-done' });
  }
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.frequency.value = 660; osc.type = 'sine';
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
    osc.start(); osc.stop(ctx.currentTime + 0.4);
  } catch(e) {}
}

function showCtaBar() {
  const elapsed = D.t0 ? Math.floor((Date.now() - D.t0) / 1000) : 0;
  const elapsedStr = elapsed < 60 ? `${elapsed}s` : `${Math.floor(elapsed/60)}m ${elapsed%60}s`;
  document.getElementById('ctaSub').textContent = `7 agents completed in ${elapsedStr}`;
  document.getElementById('ctaBar').classList.add('on');
  document.getElementById('execBriefBtn').style.display = '';
}

function stream(alertId) {
  D.running = true;
  D.t0 = Date.now();
  stagesSeen = 0;
  document.getElementById('procBar').classList.remove('error');
  document.getElementById('procBar').classList.add('on');
  document.getElementById('procLabel').textContent = 'Initializing pipeline...';
  document.getElementById('ctaBar').classList.remove('on');
  updateStageCount();

  D.ti = setInterval(() => {
    const s = Math.floor((Date.now() - D.t0) / 1000);
    document.getElementById('procElapsed').textContent = `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;
  }, 1000);

  const es = new EventSource(`/api/run/${alertId}`);
  D.es = es;

  es.addEventListener('pipeline_start', () => {
    document.getElementById('procLabel').textContent = 'Pipeline activated — awaiting first agent...';
  });

  es.addEventListener('stage_start', e => {
    const d = JSON.parse(e.data);
    clearThinkingTimer();
    stagesSeen++;
    updateStageCount();
    const remaining = TOTAL_STAGES - stagesSeen;
    document.getElementById('procLabel').textContent = `${d.label} processing...` + (remaining > 0 ? ` (${remaining} stages remaining)` : '');

    const nodeId = D.stageNode[d.stage];
    if (nodeId) { const el = document.getElementById(nodeId); if (!el.classList.contains('done')) el.classList.add('running'); }

    const miniId = D.stageMini[d.stage];
    if (miniId) { document.getElementById(miniId).classList.add('running'); const bracket = D.stageParallel[d.stage]; if (bracket) document.getElementById(bracket).classList.add('active'); }

    if (d.order > 1 && D.stageWire[d.order]) document.getElementById(D.stageWire[d.order]).classList.add('lit');

    if (!D.out[d.stage]) { D.out[d.stage] = ''; D.rawOut[d.stage] = ''; addTab(d.stage, d.label); }
    showTab(d.stage);
    setPipeStatus(d.stage, 'running');
  });

  es.addEventListener('text', e => {
    const d = JSON.parse(e.data);
    clearThinkingTimer();
    const stageLabel = D.stageLabel[d.stage] || d.stage;
    document.getElementById('procLabel').textContent = `${stageLabel} generating response...`;
    D.rawOut[d.stage] = (D.rawOut[d.stage]||'') + d.text;
    D.out[d.stage] = renderMarkdown(D.rawOut[d.stage]);
    if (D.tab === d.stage) { const b = document.getElementById('termBody'); b.innerHTML = D.out[d.stage]; b.scrollTop = b.scrollHeight; }
  });

  es.addEventListener('tool_call', e => {
    const d = JSON.parse(e.data);
    clearThinkingTimer();
    const friendlyTool = d.tool.replace(/_/g, ' ');
    document.getElementById('procLabel').textContent = `Calling ${friendlyTool}...`;
    const args = Object.entries(d.args).map(([k,v])=>`${k}="${v}"`).join(', ');
    D.rawOut[d.stage] = (D.rawOut[d.stage]||'') + `\n► ${d.tool}(${args})\n`;
    D.out[d.stage] = renderMarkdown(D.rawOut[d.stage]);
    if (D.tab === d.stage) { const b = document.getElementById('termBody'); b.innerHTML = D.out[d.stage]; b.scrollTop = b.scrollHeight; }
  });

  es.addEventListener('tool_result', e => {
    const d = JSON.parse(e.data);
    const stageLabel = D.stageLabel[d.stage] || d.stage;
    document.getElementById('procLabel').textContent = `${stageLabel} analyzing results...`;
    startThinkingTimer(stageLabel);
    D.rawOut[d.stage] = (D.rawOut[d.stage]||'') + `✓ ${d.tool} returned\n\n`;
    D.out[d.stage] = renderMarkdown(D.rawOut[d.stage]);
    if (D.tab === d.stage) { const b = document.getElementById('termBody'); b.innerHTML = D.out[d.stage]; b.scrollTop = b.scrollHeight; }
  });

  es.addEventListener('stage_done', e => {
    const d = JSON.parse(e.data);
    D.done.add(d.stage);

    const nodeId = D.stageNode[d.stage];
    if (nodeId) { const el = document.getElementById(nodeId); el.classList.remove('running'); el.classList.add('done'); }
    const miniId = D.stageMini[d.stage];
    if (miniId) { const el = document.getElementById(miniId); el.classList.remove('running'); el.classList.add('done'); }

    if (['resilience_check','customer_impact'].every(s => D.done.has(s))) { document.getElementById('pp-stage2').classList.remove('active'); document.getElementById('pp-stage2').classList.add('done'); }
    if (['enterprise_comms','vip_comms','mass_comms'].every(s => D.done.has(s))) { document.getElementById('pp-drafters').classList.remove('active'); document.getElementById('pp-drafters').classList.add('done'); }

    const dot = document.querySelector(`.tab[data-s="${d.stage}"] .tab-dot`);
    if (dot) dot.className = 'tab-dot done';
    setPipeStatus(d.stage, 'done');
  });

  es.addEventListener('done', () => {
    D.running = false;
    clearThinkingTimer();
    document.getElementById('procBar').classList.remove('on');
    if (D.ti) clearInterval(D.ti);
    ['pw-1','pw-2','pw-3'].forEach(id => { const el = document.getElementById(id); el.classList.remove('lit'); el.classList.add('done'); });
    notifyComplete();

    D.sessions[alertId] = { out: { ...D.out }, rawOut: { ...D.rawOut }, done: [...D.done] };
    renderFeed();

    showComparison();
    showCtaBar();

    // Auto-open approval modal after a brief pause
    setTimeout(() => openApproval(), 800);
  });

  es.addEventListener('error', e => { clearThinkingTimer(); try { const d = JSON.parse(e.data); document.getElementById('procLabel').textContent = `Error: ${d.error}`; document.getElementById('procBar').classList.add('error'); } catch(err) { document.getElementById('procLabel').textContent = 'Connection interrupted — retrying...'; } });
  es.onerror = () => { if (es.readyState === EventSource.CLOSED) { clearThinkingTimer(); D.running = false; document.getElementById('procLabel').textContent = 'Connection lost'; document.getElementById('procBar').classList.remove('on'); if (D.ti) clearInterval(D.ti); } };
}

// ═══ COMPARISON ═══
function showComparison() {
  if (!D.sel) return;
  const customers = D.sel.estimated_customers_affected;
  const isCrit = D.sel.severity === 'CRITICAL';
  const callRate = isCrit ? 0.15 : 0.08;
  const reduction = isCrit ? 0.40 : 0.50;
  const callsBefore = Math.floor(customers * callRate);
  const callsAfter = Math.floor(callsBefore * (1 - reduction));
  const costBefore = Math.floor(callsBefore * (isCrit ? 6 : 4) / 60 * 45);
  const costAfter = Math.floor(callsAfter * (isCrit ? 6 : 4) / 60 * 45);
  const elapsed = D.t0 ? Math.floor((Date.now() - D.t0) / 1000) : 0;
  const elapsedStr = elapsed < 60 ? `${elapsed}s` : `${Math.floor(elapsed/60)}m ${elapsed%60}s`;

  document.getElementById('compCallsBefore').textContent = callsBefore.toLocaleString() + ' calls';
  document.getElementById('compCostBefore').textContent = '$' + costBefore.toLocaleString();
  document.getElementById('compTimeAfter').textContent = elapsedStr;
  document.getElementById('compCallsAfter').textContent = callsAfter.toLocaleString() + ' calls';
  document.getElementById('compCostAfter').textContent = '$' + costAfter.toLocaleString();
  document.getElementById('comparisonBar').classList.add('on');
}

// ═══ TABS ═══
function addTab(stage, label) {
  const row = document.getElementById('tabsRow');
  const t = document.createElement('div');
  t.className = 'tab'; t.dataset.s = stage;
  t.innerHTML = `<span class="tab-dot"></span>${label}`;
  t.onclick = () => showTab(stage);
  row.appendChild(t);
}

function showTab(stage) {
  D.tab = stage;
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.s === stage));
  document.getElementById('termBody').innerHTML = D.out[stage] || '';
  document.getElementById('termTitle').textContent = `${D.stageLabel[stage]||stage} — output`;
  document.getElementById('termBody').scrollTop = 999999;
}

// ═══ PIPELINE STATUS ═══
function setPipeStatus(stage, status) {
  const list = document.getElementById('pipeStatusList');
  let row = list.querySelector(`[data-ps="${stage}"]`);
  if (!row) { row = document.createElement('div'); row.className = 'ps-row'; row.dataset.ps = stage; list.appendChild(row); }
  row.innerHTML = `<div class="ps-dot ${status}"></div><span class="ps-label">${D.stageLabel[stage]||stage}</span><span class="ps-status ${status}">${status.toUpperCase()}</span>`;
}

// ═══ COMMUNICATION CARD PARSING ═══
// Extracts individual communications from agent output for per-message approval
function parseCommCards() {
  const cards = [];
  let id = 0;

  // Enterprise communications
  const entRaw = D.rawOut['enterprise_comms'] || '';
  if (entRaw) {
    // Split by subject lines or numbered items
    const entBlocks = splitCommBlocks(entRaw, 'enterprise');
    entBlocks.forEach(block => {
      cards.push({
        id: id++, type: 'enterprise', severity: 'critical',
        recipient: block.recipient || 'Enterprise Account',
        channel: block.channel || 'EMAIL',
        meta: block.meta || 'Priority: Critical',
        preview: block.text,
        state: null
      });
    });
  }

  // VIP communications
  const vipRaw = D.rawOut['vip_comms'] || '';
  if (vipRaw) {
    const vipBlocks = splitCommBlocks(vipRaw, 'vip');
    vipBlocks.forEach(block => {
      cards.push({
        id: id++, type: 'vip', severity: 'high',
        recipient: block.recipient || 'VIP Customer',
        channel: block.channel || 'SMS + EMAIL',
        meta: block.meta || 'Priority: High',
        preview: block.text,
        state: null
      });
    });
  }

  // Mass communications
  const massRaw = D.rawOut['mass_comms'] || '';
  if (massRaw) {
    const massBlocks = splitCommBlocks(massRaw, 'mass');
    massBlocks.forEach(block => {
      cards.push({
        id: id++, type: 'mass', severity: 'mass',
        recipient: block.recipient || 'Mass Notification',
        channel: block.channel || 'MULTI-CHANNEL',
        meta: block.meta || 'Priority: Standard',
        preview: block.text,
        state: null
      });
    });
  }

  // If no blocks could be parsed, create one card per stage
  if (cards.length === 0) {
    if (entRaw) cards.push({ id: id++, type: 'enterprise', severity: 'critical', recipient: 'Enterprise Communications', channel: 'EMAIL', meta: 'All enterprise accounts', preview: entRaw, state: null });
    if (vipRaw) cards.push({ id: id++, type: 'vip', severity: 'high', recipient: 'VIP Communications', channel: 'SMS + EMAIL', meta: 'All VIP customers', preview: vipRaw, state: null });
    if (massRaw) cards.push({ id: id++, type: 'mass', severity: 'mass', recipient: 'Mass Notifications', channel: 'MULTI-CHANNEL', meta: 'All affected subscribers', preview: massRaw, state: null });
  }

  return cards;
}

function splitCommBlocks(raw, type) {
  const blocks = [];
  // Try to split by numbered communications or subject lines
  const sections = raw.split(/(?=(?:\d+\.\s*\*\*|#{1,3}\s+|SUBJECT|Subject|To:|TO:))/);

  if (sections.length <= 1) {
    // Can't split — return as single block
    const recipient = extractRecipient(raw, type);
    const channel = extractChannel(raw);
    blocks.push({ recipient, channel, meta: `Type: ${type}`, text: raw });
    return blocks;
  }

  sections.forEach(section => {
    const trimmed = section.trim();
    if (trimmed.length < 20) return;
    const recipient = extractRecipient(trimmed, type);
    const channel = extractChannel(trimmed);
    blocks.push({ recipient, channel, meta: `Type: ${type}`, text: trimmed });
  });

  return blocks.length > 0 ? blocks : [{ recipient: extractRecipient(raw, type), channel: extractChannel(raw), meta: `Type: ${type}`, text: raw }];
}

function extractRecipient(text, type) {
  // Try to find a name or account reference
  const nameMatch = text.match(/(?:Dear|To:|Account:|for)\s+([A-Z][A-Za-z\s&.'-]{2,30})/);
  if (nameMatch) return nameMatch[1].trim();

  const subjectMatch = text.match(/(?:SUBJECT|Subject)[:\s]+(.{5,50})/);
  if (subjectMatch) return subjectMatch[1].trim();

  const labels = { enterprise: 'Enterprise Account', vip: 'VIP Customer', mass: 'Mass Notification' };
  return labels[type] || 'Communication';
}

function extractChannel(text) {
  const lower = text.toLowerCase();
  if (lower.includes('sms') && lower.includes('email')) return 'SMS + EMAIL';
  if (lower.includes('sms')) return 'SMS';
  if (lower.includes('push')) return 'PUSH';
  if (lower.includes('status page')) return 'STATUS PAGE';
  return 'EMAIL';
}

// ═══ RICH APPROVAL MODAL ═══
function openApproval() {
  const cards = parseCommCards();
  D.commStates = {};
  cards.forEach(c => { D.commStates[c.id] = null; });

  // Comms pane
  const commsHtml = cards.map(c => {
    const sevClass = `sev-${c.severity}`;
    const dotClass = c.severity === 'critical' ? 'critical' : c.severity === 'high' ? 'high' : c.severity === 'medium' ? 'medium' : 'mass';
    return `<div class="comm-card ${sevClass}" id="cc-${c.id}" data-id="${c.id}">
      <div class="comm-card-head" onclick="toggleCommCard(${c.id})">
        <div class="comm-sev-dot ${dotClass}"></div>
        <div class="comm-card-info">
          <div class="comm-card-recipient">${escHtml(c.recipient)}</div>
          <div class="comm-card-meta"><span>${escHtml(c.meta)}</span></div>
        </div>
        <div class="comm-card-channel">${escHtml(c.channel)}</div>
        <div class="comm-card-actions">
          <div class="comm-action approve-one" onclick="event.stopPropagation(); approveComm(${c.id})" title="Approve">✓</div>
          <div class="comm-action reject-one" onclick="event.stopPropagation(); rejectComm(${c.id})" title="Reject">✕</div>
        </div>
        <div class="comm-chevron">▼</div>
      </div>
      <div class="comm-card-body">
        <div class="comm-preview">${escHtml(c.preview)}</div>
      </div>
    </div>`;
  }).join('');

  document.getElementById('modalPaneComms').innerHTML = commsHtml;
  document.getElementById('modalTotal').textContent = cards.length;
  document.getElementById('modalApproved').textContent = '0';
  updateApprovalCounter();

  // Brief pane
  document.getElementById('modalPaneBrief').innerHTML = buildExecBriefHtml();

  // Raw pane
  const approvalContent = D.rawOut['approval'] || 'Pipeline complete. Review drafted communications.';
  document.getElementById('modalPaneRaw').innerHTML = `<div class="modal-body-text">${renderMarkdown(approvalContent)}</div>`;

  // Reset tabs to first
  switchModalTab('comms', document.querySelector('.modal-tab'));

  document.getElementById('modalBg').classList.add('on');
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function toggleCommCard(id) {
  const el = document.getElementById(`cc-${id}`);
  el.classList.toggle('expanded');
}

function approveComm(id) {
  D.commStates[id] = 'approved';
  const el = document.getElementById(`cc-${id}`);
  el.classList.add('approved');
  el.classList.remove('rejected');
  const actions = el.querySelectorAll('.comm-action');
  actions[0].classList.add('approved');
  actions[1].classList.remove('rejected');
  updateApprovalCounter();
}

function rejectComm(id) {
  D.commStates[id] = 'rejected';
  const el = document.getElementById(`cc-${id}`);
  el.classList.add('rejected');
  el.classList.remove('approved');
  const actions = el.querySelectorAll('.comm-action');
  actions[0].classList.remove('approved');
  actions[1].classList.add('rejected');
  updateApprovalCounter();
}

function updateApprovalCounter() {
  const total = Object.keys(D.commStates).length;
  const approved = Object.values(D.commStates).filter(s => s === 'approved').length;
  document.getElementById('modalApproved').textContent = approved;
  document.getElementById('modalTotal').textContent = total;
  document.getElementById('approvalCounter').textContent = `${approved} / ${total} approved`;
}

function switchModalTab(pane, btn) {
  document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.modal-pane').forEach(p => p.classList.remove('active'));
  const paneId = pane === 'comms' ? 'modalPaneComms' : pane === 'brief' ? 'modalPaneBrief' : 'modalPaneRaw';
  document.getElementById(paneId).classList.add('active');
}

function closeModal() { document.getElementById('modalBg').classList.remove('on'); }

function approve() {
  closeModal();
  stopSlaTicker();
  const stv = document.getElementById('slaTickerVal');
  stv.style.animation = 'none'; stv.style.color = 'var(--green)';
  document.getElementById('iSla').style.color = 'var(--green)';
  document.getElementById('iSla').style.textShadow = '';
  document.getElementById('approvedBar').classList.add('on');
  document.getElementById('ctaBar').classList.remove('on');
  ['pn-network','pn-approval'].forEach(id => { const el = document.getElementById(id); el.classList.remove('running'); el.classList.add('done'); });
  setTimeout(() => showDissemination(), 600);
}

// ═══ EXECUTIVE BRIEF ═══
function buildExecBriefHtml() {
  const a = D.sel;
  if (!a) return '<p style="color:var(--text-ghost)">No alert selected</p>';

  const customers = a.estimated_customers_affected;
  const isCrit = a.severity === 'CRITICAL';
  const callRate = isCrit ? 0.15 : 0.08;
  const reduction = isCrit ? 0.40 : 0.50;
  const callsBefore = Math.floor(customers * callRate);
  const callsAfter = Math.floor(callsBefore * (1 - reduction));
  const costBefore = Math.floor(callsBefore * (isCrit ? 6 : 4) / 60 * 45);
  const costAfter = Math.floor(callsAfter * (isCrit ? 6 : 4) / 60 * 45);
  const costSaved = costBefore - costAfter;
  const elapsed = D.t0 ? Math.floor((Date.now() - D.t0) / 1000) : 0;
  const elapsedStr = elapsed < 60 ? `${elapsed}s` : `${Math.floor(elapsed/60)}m ${elapsed%60}s`;
  const slaStr = '$' + Math.floor(slaExposure).toLocaleString();
  const churnRisk = isCrit ? '2.4%' : '1.1%';
  const churnReduced = isCrit ? '0.3%' : '0.2%';

  return `
    <div class="exec-metrics">
      <div class="exec-metric highlight">
        <div class="exec-metric-val">${customers.toLocaleString()}</div>
        <div class="exec-metric-label">Customers Affected</div>
      </div>
      <div class="exec-metric highlight">
        <div class="exec-metric-val">${slaStr}</div>
        <div class="exec-metric-label">SLA Exposure</div>
      </div>
      <div class="exec-metric">
        <div class="exec-metric-val">$${costSaved.toLocaleString()}</div>
        <div class="exec-metric-label">Call Center Savings</div>
      </div>
      <div class="exec-metric">
        <div class="exec-metric-val">${elapsedStr}</div>
        <div class="exec-metric-label">Response Time</div>
      </div>
    </div>

    <div class="exec-section">
      <div class="exec-section-title">Incident Summary</div>
      <div class="exec-section-body">
        <strong>${a.title}</strong> — A <strong>${a.severity.toLowerCase()}</strong> ${a.alert_type.replace(/_/g, ' ').toLowerCase()} incident
        affecting approximately <strong>${customers.toLocaleString()} customers</strong> across
        ${(a.affected_zones||[]).length} network zones. Escalation level: <strong>${a.escalation_level}</strong>.
        Preliminary estimated time to resolution: <strong>${a.preliminary_etr}</strong>.
      </div>
    </div>

    <div class="exec-section">
      <div class="exec-section-title">Business Risk Assessment</div>
      <div class="exec-risk-grid">
        <div class="exec-risk-item ${isCrit ? 'high' : 'medium'}">
          <div class="exec-risk-label">SLA Breach Risk</div>
          <div class="exec-risk-val">${isCrit ? 'HIGH' : 'MODERATE'}</div>
        </div>
        <div class="exec-risk-item ${isCrit ? 'high' : 'medium'}">
          <div class="exec-risk-label">Churn Risk (Without Action)</div>
          <div class="exec-risk-val">+${churnRisk}</div>
        </div>
        <div class="exec-risk-item low">
          <div class="exec-risk-label">Churn Risk (With NOC Command)</div>
          <div class="exec-risk-val">-${churnReduced}</div>
        </div>
        <div class="exec-risk-item low">
          <div class="exec-risk-label">Call Volume Reduction</div>
          <div class="exec-risk-val">${Math.round(reduction * 100)}%</div>
        </div>
      </div>
    </div>

    <div class="exec-section">
      <div class="exec-section-title">Cost Impact</div>
      <div class="exec-section-body">
        Without proactive communication, projected inbound call volume is <strong>${callsBefore.toLocaleString()} calls</strong>
        at an estimated cost of <strong>$${costBefore.toLocaleString()}</strong>.
        With NOC Command proactive outreach, call volume reduces to <strong>${callsAfter.toLocaleString()} calls</strong>,
        saving <strong>$${costSaved.toLocaleString()}</strong> in call center costs alone.
        Response time was <strong>${elapsedStr}</strong> vs. industry average of <strong>45-90 minutes</strong>.
      </div>
    </div>

    <div class="exec-section">
      <div class="exec-section-title">Response Timeline</div>
      <div class="exec-timeline">
        <div class="exec-tl-item done"><div class="exec-tl-time">${elapsedStr}</div><div class="exec-tl-label">AI Analysis</div></div>
        <div class="exec-tl-item active"><div class="exec-tl-time">NOW</div><div class="exec-tl-label">Pending Approval</div></div>
        <div class="exec-tl-item"><div class="exec-tl-time">+2 min</div><div class="exec-tl-label">Notifications Sent</div></div>
        <div class="exec-tl-item"><div class="exec-tl-time">${a.preliminary_etr || 'TBD'}</div><div class="exec-tl-label">Resolution</div></div>
      </div>
    </div>
  `;
}

function openExecBrief() {
  document.getElementById('execBody').innerHTML = buildExecBriefHtml();
  document.getElementById('execBg').classList.add('on');
}

function closeExecBrief() {
  document.getElementById('execBg').classList.remove('on');
}

function copyExecBrief() {
  const a = D.sel;
  if (!a) return;
  const customers = a.estimated_customers_affected;
  const isCrit = a.severity === 'CRITICAL';
  const elapsed = D.t0 ? Math.floor((Date.now() - D.t0) / 1000) : 0;
  const elapsedStr = elapsed < 60 ? `${elapsed}s` : `${Math.floor(elapsed/60)}m ${elapsed%60}s`;

  const text = [
    `EXECUTIVE BRIEF — ${a.title}`,
    `Severity: ${a.severity} | Escalation: ${a.escalation_level}`,
    `Customers Affected: ${customers.toLocaleString()}`,
    `SLA Exposure: $${Math.floor(slaExposure).toLocaleString()}`,
    `Response Time: ${elapsedStr} (vs 45-90 min industry avg)`,
    `ETR: ${a.preliminary_etr}`,
    ``,
    `Proactive communication drafted and pending approval.`,
  ].join('\n');

  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('.modal-exec .btn-outline');
    const orig = btn.textContent;
    btn.textContent = 'COPIED!';
    setTimeout(() => { btn.textContent = orig; }, 1500);
  });
}

// ═══ START ═══
init();
