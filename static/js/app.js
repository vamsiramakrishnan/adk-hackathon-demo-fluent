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
  sessions: {},  // Cache: alertId -> { out, rawOut, done, completed }
  running: false,  // Is a pipeline currently running?
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
      <div class="acard-footer"><span>~${a.estimated_customers_affected.toLocaleString()} affected</span><span>${a.escalation_level}</span></div>
    </div>`;
  }).join('');
}

// ═══ ALERT SELECTION ═══
async function pick(id) {
  const a = D.alerts.find(x => x.alert_id === id);
  if (!a) return;

  // If clicking the already-selected alert, do nothing
  if (D.sel?.alert_id === id) return;

  // Check for cached session (previously completed pipeline)
  if (D.sessions[id]) {
    switchToAlert(a);
    restoreSession(id);
    return;
  }

  // Confirm before running pipeline (expensive operation)
  if (D.running) {
    if (!confirm(`Pipeline is running for "${D.sel.title}".\n\nAbort and analyze "${a.title}" instead?`)) return;
  }

  switchToAlert(a);
  startSlaTicker(a);
  stream(id);
}

function switchToAlert(a) {
  // Stop any running pipeline
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
  document.getElementById('disseminationContainer').classList.remove('on');
  document.getElementById('disseminationContainer').innerHTML = '';
  document.getElementById('disseminationProgress').classList.remove('on');

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

  // Rebuild tabs and show all completed output
  Object.keys(D.out).forEach(stage => {
    const label = D.stageLabel[stage] || stage;
    addTab(stage, label);
    setPipeStatus(stage, 'done');

    const nodeId = D.stageNode[stage];
    if (nodeId) { document.getElementById(nodeId).classList.add('done'); }
    const miniId = D.stageMini[stage];
    if (miniId) { document.getElementById(miniId).classList.add('done'); }
  });

  // Mark parallel brackets as done
  if (D.done.has('resilience_check') && D.done.has('customer_impact')) { document.getElementById('pp-stage2').classList.add('done'); }
  if (D.done.has('enterprise_comms') && D.done.has('vip_comms') && D.done.has('mass_comms')) { document.getElementById('pp-drafters').classList.add('done'); }
  ['pw-1','pw-2','pw-3'].forEach(id => document.getElementById(id).classList.add('done'));

  // Show first tab
  const firstStage = Object.keys(D.out)[0];
  if (firstStage) showTab(firstStage);

  showComparison();
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
const TOTAL_STAGES = 7; // network, resilience, impact, enterprise, vip, mass, approval
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
  // Tab title badge
  document.title = '[✓ READY] ' + ORIGINAL_TITLE;
  window.addEventListener('focus', () => { document.title = ORIGINAL_TITLE; }, { once: true });

  // Browser notification
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification('NOC Command', { body: 'Outage communications ready for approval', tag: 'pipeline-done' });
  }

  // Subtle audio tone
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

function stream(alertId) {
  D.running = true;
  D.t0 = Date.now();
  stagesSeen = 0;
  document.getElementById('procBar').classList.remove('error');
  document.getElementById('procBar').classList.add('on');
  document.getElementById('procLabel').textContent = 'Initializing pipeline...';
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
    // Start thinking timer — if no event arrives for 3+ seconds, show "reasoning..." animation
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

    // Cache the completed session for this alert
    D.sessions[alertId] = { out: { ...D.out }, rawOut: { ...D.rawOut }, done: [...D.done] };

    showComparison();
    setTimeout(() => {
      const approvalContent = D.rawOut['approval'] || 'Pipeline complete. Review drafted communications.';
      document.getElementById('modalBody').innerHTML = `<div class="modal-body-text">${renderMarkdown(approvalContent)}</div>`;
      document.getElementById('modalBg').classList.add('on');
    }, 600);
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

// ═══ MODAL & APPROVAL ═══
function closeModal() { document.getElementById('modalBg').classList.remove('on'); }

function approve() {
  closeModal();
  stopSlaTicker();
  const stv = document.getElementById('slaTickerVal');
  stv.style.animation = 'none'; stv.style.color = 'var(--green)';
  document.getElementById('iSla').style.color = 'var(--green)';
  document.getElementById('iSla').style.textShadow = '';
  document.getElementById('approvedBar').classList.add('on');
  ['pn-network','pn-approval'].forEach(id => { const el = document.getElementById(id); el.classList.remove('running'); el.classList.add('done'); });
  setTimeout(() => showDissemination(), 600);
}

// ═══ START ═══
init();
