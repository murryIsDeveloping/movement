// Loaded before the main script in index.html. Uses its globals (poses, state, esc) and capture.js's beep at call time.
// ---------- drill: full-screen prompts for a minute, scores each pose ----------
let drill = null;
const DRILL_READY = 3, DRILL_LENGTH = 60, DRILL_REST = 3, DRILL_TIMEOUT = 10, DRILL_TICK_SHOW = 1;   // seconds

function startDrill() {
  const pool = poses.map((p, i) => i).filter(i => poses[i].enabled !== false && poses[i].conditions.length);
  if (!pool.length) { alert('no enabled poses to drill'); return; }
  try { audio = audio || new AudioContext(); } catch {}
  const el = document.getElementById('drill');
  el.querySelector('img').src = '/stream';
  el.classList.add('open');
  const now = performance.now();
  drill = { el, pool, phase: 'ready', phaseAt: now, clock: null, endAt: now + (DRILL_READY + DRILL_LENGTH) * 1000,
            target: -1, seenOff: false, wasActive: [], results: [],
            rec: { started: new Date().toISOString(), poses: JSON.parse(JSON.stringify(poses)), events: [], frames: [] } };
  drill.timer = setInterval(drillTick, 50);
  drillTick();
}

// every camera frame while drilling (the server batches them per broadcast): features and which poses are on,
// so a recording shows why a pose did or didn't fire. Times are the app's clock, shared with the events.
function drillFrame(m) {
  if (!drill || drill.phase === 'done') return;
  for (const fr of m.frames || []) { drill.rec.frames.push(fr); drill.clock = fr.t; }
}

function drillEvent(type, pose, extra = {}) { drill.rec.events.push({ t: drill.clock, type, pose, ...extra }); }

function saveDrill() {
  const d = drill;
  if (d.saved || !d.results.length) return;
  d.saved = true;
  d.rec.results = d.results;
  fetch('/recording', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d.rec) })
    .then(r => r.json()).then(j => { const s = d.el.querySelector('.saved'); if (s) s.textContent = 'saved ' + j.path; })
    .catch(() => {});
}

function endDrill() {
  if (!drill) return;
  saveDrill();   // stopped early: keep what was done
  clearInterval(drill.timer);
  drill.el.classList.remove('open');
  drill.el.querySelector('img').removeAttribute('src');   // closes the second MJPEG stream
  drill = null;
}

function drillPrompt(now) {
  const choices = drill.pool.length > 1 ? drill.pool.filter(i => i !== drill.target) : drill.pool;
  drill.target = choices[Math.floor(Math.random() * choices.length)];
  drill.phase = 'prompt'; drill.phaseAt = now;
  drill.seenOff = false;   // the target must go off then on, so a hold left over from last time doesn't count
  drill.wrong = new Set();
  drill.wasActive = state.map(s => !!(s && s.active));
  drillEvent('prompt', poses[drill.target].name);
  beep(660, 80);
}

function drillTick() {
  const d = drill, now = performance.now(), el = d.el;
  const active = i => !!(state[i] && state[i].active);
  const dt = now - (d.lastTick ?? now);
  d.lastTick = now;
  if (paused && d.phase !== 'done') {
    // out of frame: the clocks stop, so stepping up to the camera doesn't eat the prompt or the minute
    d.phaseAt += dt; d.endAt += dt;
    el.querySelector('.big').className = 'big bad';
    el.querySelector('.big').textContent = 'Paused';
    el.querySelector('.sub').textContent = paused.length ? `not fully in frame: ${paused.join(', ')}` : 'no body: step into view';
    return;
  }
  const since = (now - d.phaseAt) / 1000;
  if (d.phase !== 'done' && d.phase !== 'ready' && now >= d.endAt) {
    d.phase = 'done'; beep(440, 300); renderDrillResults(); return;
  }
  // other poses that switch on while prompting (the ones this pose gets mistaken for) or on the way back to neutral
  const firing = [];
  if (d.phase === 'prompt' || d.phase === 'return') {
    poses.forEach((p, i) => {
      if (i !== d.target && active(i) && !d.wasActive[i]) firing.push(p.name);
    });
    d.wasActive = state.map(s => !!(s && s.active));
  }
  if (d.phase === 'ready' && since >= DRILL_READY) drillPrompt(now);
  else if (d.phase === 'return') {
    const last = d.results[d.results.length - 1];
    firing.forEach(n => { if (!last.ret.includes(n)) last.ret.push(n); drillEvent('return_wrong', n, { from: last.name }); });
    // the next prompt waits for neutral: nothing firing, so every pose starts from the same place
    if (since >= DRILL_REST && !state.some(s => s && s.active)) drillPrompt(now);
  }
  else if (d.phase === 'prompt') {
    firing.forEach(n => { d.wrong.add(n); drillEvent('wrong', n, { prompted: poses[d.target].name }); });
    if (!active(d.target)) d.seenOff = true;
    const hit = d.seenOff && active(d.target);
    if (hit || since >= DRILL_TIMEOUT) {
      d.results.push({ name: poses[d.target].name, hit, time: since, wrong: [...d.wrong], ret: [] });
      drillEvent(hit ? 'hit' : 'miss', poses[d.target].name, { time: +since.toFixed(2) });
      d.phase = 'return'; d.phaseAt = now;
      if (hit) beep(1200, 150); else beep(220, 250);
    }
  }
  if (d.phase === 'done') return;

  const left = Math.max(0, Math.ceil((d.endAt - now) / 1000));
  const last = d.results[d.results.length - 1];
  let big = '', sub = '', cls = '';
  if (d.phase === 'ready') { big = Math.ceil(DRILL_READY - since); sub = 'get ready'; }
  else if (d.phase === 'prompt') { big = esc(poses[d.target].name); sub = `${Math.ceil(DRILL_TIMEOUT - since)}s`; }
  else if (since < DRILL_TICK_SHOW) {
    if (last.hit) { big = '✓'; cls = 'ok'; sub = `${esc(last.name)} in ${last.time.toFixed(1)}s`; }
    else { big = '✗'; cls = 'bad'; sub = `${esc(last.name)} timed out`; }
    if (last.wrong.length) sub += ` · also fired: ${last.wrong.map(esc).join(', ')}`;
  } else {
    const still = poses.filter((p, i) => active(i)).map(p => esc(p.name));
    big = 'neutral';
    sub = since >= DRILL_REST && still.length ? `still firing: ${still.join(', ')}` : 'arms down, stand still';
  }
  if (d.phase === 'return' && last.ret.length) sub += ` · fired on return: ${last.ret.map(esc).join(', ')}`;
  el.querySelector('.big').innerHTML = big;
  el.querySelector('.big').className = 'big ' + cls;
  el.querySelector('.sub').innerHTML = sub;
  el.querySelector('.clock').textContent = d.phase === 'ready' ? '' : `${left}s · ${d.results.filter(r => r.hit).length}/${d.results.length}`;
  el.querySelector('.results').innerHTML = '';
}

function renderDrillResults() {
  const d = drill, el = d.el;
  const by = {};
  d.results.forEach(r => {
    const s = by[r.name] = by[r.name] || { tries: 0, hits: 0, time: 0, wrong: {}, ret: {} };
    s.tries++;
    if (r.hit) { s.hits++; s.time += r.time; }
    r.wrong.forEach(w => { s.wrong[w] = (s.wrong[w] || 0) + 1; });
    r.ret.forEach(w => { s.ret[w] = (s.ret[w] || 0) + 1; });
  });
  const counts = c => Object.entries(c).map(([w, n]) => `${esc(w)}${n > 1 ? ' ×' + n : ''}`).join(', ') || '–';
  const hits = d.results.filter(r => r.hit).length;
  el.querySelector('.big').className = 'big';
  el.querySelector('.big').textContent = `${hits}/${d.results.length}`;
  el.querySelector('.sub').textContent = 'done';
  el.querySelector('.clock').textContent = '';
  const rows = Object.entries(by).map(([name, s]) => `<tr>
      <td>${esc(name)}</td><td class="n">${s.hits}/${s.tries}</td>
      <td class="n">${s.hits ? (s.time / s.hits).toFixed(1) + 's' : '–'}</td>
      <td>${counts(s.wrong)}</td><td>${counts(s.ret)}</td></tr>`).join('');
  el.querySelector('.results').innerHTML = `<table class="trace">
      <tr><th>pose</th><th>hit</th><th>avg time</th><th>also fired while prompted</th><th>fired on return</th></tr>${rows}</table>
    <div class="bar" style="justify-content:center"><button class="primary again">again</button><button class="close">close</button></div>
    <p class="small saved" style="text-align:center"></p>`;
  saveDrill();
  el.querySelector('.again').onclick = () => { endDrill(); startDrill(); };
  el.querySelector('.close').onclick = endDrill;
}
