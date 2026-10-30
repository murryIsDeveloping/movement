// Loaded before the main script in index.html. Uses its globals (poses, state, live, paused, esc, fmtU), capture.js's
// beep, figure.js's figureSVG and library.js's presetOf at call time.
// ---------- drill: full-screen random prompts for a set time, scores each pose ----------
// Learn mode is the same screen taking the poses in order, with no clock: each one stays up, with its figure, notes and
// a live checklist of its conditions, until it has been hit LEARN_REPS times (or skipped).
let drill = null;
let sendBefore = null;   // send keys as it was before the drill turned it off; null when no drill
const DRILL_READY = 3, DRILL_TICK_SHOW = 1;   // seconds
const LEARN_REPS = 3, LEARN_REST = 1.5;   // hits before moving on; seconds of neutral between them
// the drill's own settings, set on its setup screen: [default, min, max] for length (minutes), rest and time to hit (seconds)
const DRILL_SETTINGS = { minutes: [1, 0.5, 60], rest: [3, 0, 30], hit: [10, 2, 60] };
const DRILL_KEY = 'movement.drill', DRILL_INPUTS = { minutes: 'drillMin', rest: 'drillRest', hit: 'drillHit' };

// saved settings, each clamped to its range; a missing or broken one is its default
function drillSettings(from = null) {
  let saved = from;
  if (!saved) try { saved = JSON.parse(localStorage.getItem(DRILL_KEY)) || {}; } catch { saved = {}; }
  return Object.fromEntries(Object.entries(DRILL_SETTINGS).map(([k, [def, lo, hi]]) => {
    const v = parseFloat(saved[k]);
    return [k, Number.isFinite(v) ? Math.min(hi, Math.max(lo, v)) : def];
  }));
}

const drillable = i => poses[i] && poses[i].enabled !== false && poses[i].conditions.length;

// active poses in list order, for learn mode
const learnPool = () => poses.map((p, i) => i).filter(drillable);

// the overlay has the focus, so a pose's key would land in this page (space scrolls it). "again" keeps the first value.
function drillKeysOff() {
  if (sendBefore === null) { sendBefore = document.getElementById('send').checked; if (sendBefore) setSend(false); }
}

// the drill button: length, rest and time to hit first, then start
function openDrillSetup() {
  if (drill) return;
  drillKeysOff();
  const el = document.getElementById('drill'), s = drillSettings();
  for (const [k, id] of Object.entries(DRILL_INPUTS)) document.getElementById(id).value = s[k];
  el.classList.add('open', 'setup'); el.classList.remove('learn');
  el.querySelector('.clock').textContent = '';
  drill = { el, phase: 'setup' };
  document.getElementById('drillStart').focus();
}

// learn: a list of pose indices to go through in order; null for the timed random drill, with the settings from the
// setup screen when it's open, or the saved ones ("again")
function startDrill(learn = null) {
  if (drill && drill.phase !== 'setup') return;   // already running: a second timer would outlive endDrill
  let cfg = drillSettings();
  if (drill && drill.phase === 'setup') {
    cfg = drillSettings(Object.fromEntries(Object.entries(DRILL_INPUTS).map(([k, id]) => [k, document.getElementById(id).value])));
    try { localStorage.setItem(DRILL_KEY, JSON.stringify(cfg)); } catch {}
  }
  const pool = learn ? learn.filter(drillable) : poses.map((p, i) => i).filter(drillable);
  if (!pool.length) { endDrill(); restoreSend(); alert(`no enabled poses to ${learn ? 'learn' : 'drill'}`); return; }   // "again" after the poses went
  drill = null;
  try { audio = audio || new AudioContext(); } catch {}
  drillKeysOff();
  const el = document.getElementById('drill');
  el.querySelector('img').src = '/stream';
  el.classList.add('open'); el.classList.remove('setup');
  el.classList.toggle('learn', !!learn);
  el.querySelector('.cue .fig').innerHTML = '';
  el.querySelector('.cue').style.display = '';
  const now = performance.now();
  drill = { el, pool, learn: !!learn, step: 0, reps: 0, phase: 'ready', phaseAt: now, clock: null,
            rest: learn ? LEARN_REST : cfg.rest, hit: learn ? Infinity : cfg.hit,   // learning has no time limit: skip gives up
            endAt: learn ? Infinity : now + (DRILL_READY + cfg.minutes * 60) * 1000,
            target: -1, figFor: -1, seenOff: false, wasActive: [], results: [],
            rec: { mode: learn ? 'learn' : 'drill', settings: learn ? null : cfg, started: new Date().toISOString(),
                   poses: JSON.parse(JSON.stringify(poses)), events: [], frames: [] } };
  drill.timer = setInterval(drillTick, 50);
  drillTick();
}

// every camera frame while drilling (the server batches them per broadcast): features and which poses are on,
// so a recording shows why a pose did or didn't fire. Times are the app's clock, shared with the events.
function drillFrame(m) {
  if (!drill || !drill.rec || drill.phase === 'done') return;
  for (const fr of m.frames || []) { drill.rec.frames.push(fr); drill.clock = fr.t; }
}

function drillEvent(type, pose, extra = {}) { drill.rec.events.push({ t: drill.clock, type, pose, ...extra }); }

function saveDrill() {
  const d = drill;
  // no rec: closed on the setup screen. No frames: the packaged app (no recording) or nothing happened.
  if (d.saved || !d.rec || !d.rec.frames.length) return;
  d.saved = true;
  d.rec.results = d.results;
  fetch('/recording', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d.rec) })
    .then(r => r.ok ? r.json() : null).then(j => { const s = d.el.querySelector('.saved'); if (s && j) s.textContent = 'saved ' + j.path; })
    .catch(() => {});
}

function endDrill(again = false) {
  if (!drill) return;
  saveDrill();   // stopped early: keep what was done
  if (!again) restoreSend();
  clearInterval(drill.timer);
  drill.el.classList.remove('open', 'setup');
  drill.el.querySelector('img').removeAttribute('src');   // closes the second MJPEG stream
  drill = null;
}

// back on only if it's still off: another tab may have turned it on meanwhile. A reload mid-drill leaves it off.
function restoreSend() {
  if (sendBefore && !document.getElementById('send').checked) setSend(true);
  sendBefore = null;
}

function drillPrompt(now) {
  if (drill.learn) drill.target = drill.pool[drill.step];
  else {
    const choices = drill.pool.length > 1 ? drill.pool.filter(i => i !== drill.target) : drill.pool;
    drill.target = choices[Math.floor(Math.random() * choices.length)];
  }
  if (drill.figFor !== drill.target) {   // only on a new pose: replacing the svg restarts its animation
    drill.el.querySelector('.cue .fig').innerHTML = figureSVG(poses[drill.target].conditions, false);
    drill.figFor = drill.target;
  }
  drill.phase = 'prompt'; drill.phaseAt = now;
  drill.seenOff = false;   // the target must go off then on, so a hold left over from last time doesn't count
  drill.wrong = new Set();
  drill.wasActive = state.map(s => !!(s && s.active));
  drillEvent('prompt', poses[drill.target].name);
  beep(660, 80);
}

// learn: on to the next pose, or the results after the last one
function learnNext(now) {
  drill.step++; drill.reps = 0;
  if (drill.step >= drill.pool.length) { drill.phase = 'done'; beep(440, 300); renderDrillResults(); }
  else drillPrompt(now);
}

function drillSkip() {
  const d = drill;
  if (!d || !d.learn || d.phase === 'done' || d.phase === 'ready') return;
  const now = performance.now();
  if (d.phase === 'prompt') {
    d.results.push({ name: poses[d.target].name, hit: false, time: (now - d.phaseAt) / 1000, wrong: [...d.wrong], ret: [] });
    drillEvent('skip', poses[d.target].name);
  }
  learnNext(now);
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
    if (since >= d.rest && !state.some(s => s && s.active)) {
      if (d.learn && d.reps >= LEARN_REPS) learnNext(now); else drillPrompt(now);
    }
  }
  else if (d.phase === 'prompt') {
    firing.forEach(n => { d.wrong.add(n); drillEvent('wrong', n, { prompted: poses[d.target].name }); });
    if (!active(d.target)) d.seenOff = true;
    const hit = d.seenOff && active(d.target);
    if (hit || since >= d.hit) {
      d.results.push({ name: poses[d.target].name, hit, time: since, wrong: [...d.wrong], ret: [] });
      drillEvent(hit ? 'hit' : 'miss', poses[d.target].name, { time: +since.toFixed(2) });
      if (hit) d.reps++;
      d.phase = 'return'; d.phaseAt = now;
      if (hit) beep(1200, 150); else beep(220, 250);
    }
  }
  if (d.phase === 'done') return;

  const left = Math.max(0, Math.ceil((d.endAt - now) / 1000));
  const last = d.results[d.results.length - 1];
  let big = '', sub = '', cls = '';
  if (d.phase === 'ready') { big = Math.ceil(DRILL_READY - since); sub = 'get ready'; }
  else if (d.phase === 'prompt') {
    big = esc(poses[d.target].name);
    sub = d.learn ? esc((presetOf(poses[d.target].preset) || {}).notes || '') : `${Math.ceil(d.hit - since)}s`;
  }
  else if (since < DRILL_TICK_SHOW) {
    if (last.hit) { big = '✓'; cls = 'ok'; sub = `${esc(last.name)} in ${last.time.toFixed(1)}s`; }
    else { big = '✗'; cls = 'bad'; sub = `${esc(last.name)} timed out`; }
    if (last.wrong.length) sub += ` · also fired: ${last.wrong.map(esc).join(', ')}`;
  } else {
    const still = poses.filter((p, i) => active(i)).map(p => esc(p.name));
    big = 'neutral';
    sub = since >= d.rest && still.length ? `still firing: ${still.join(', ')}` : 'arms down, stand still';
  }
  if (d.phase === 'return' && last.ret.length) sub += ` · fired on return: ${last.ret.map(esc).join(', ')}`;
  el.querySelector('.big').innerHTML = big;
  el.querySelector('.big').className = 'big ' + cls;
  el.querySelector('.sub').innerHTML = sub;
  // the figure shows while prompting; learning keeps it up between reps too, as the same pose comes next
  el.querySelector('.cue').style.visibility = d.phase === 'prompt' || (d.learn && d.phase === 'return') ? '' : 'hidden';
  el.querySelector('.checks').innerHTML = d.learn && d.target >= 0 ? learnChecks(d.target) : '';
  el.querySelector('.clock').textContent = d.phase === 'ready' ? ''
    : d.learn ? `pose ${d.step + 1}/${d.pool.length} · ${d.reps}/${LEARN_REPS}`
    : `${left >= 60 ? `${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')}` : left + 's'} · ${d.results.filter(r => r.hit).length}/${d.results.length}`;
  el.querySelector('.results').innerHTML = '';
}

// each condition of the pose with its live value, ticked while it holds
function learnChecks(i) {
  const conds = (state[i] || {}).conds || [];
  return poses[i].conditions.map((c, ci) => `<tr class="${conds[ci] ? 'ok' : ''}"><td>${conds[ci] ? '✓' : '·'}</td>
    <td>${esc(c.feature.replace(/_/g, ' '))} ${c.op === '>' ? '&gt;' : '&lt;'} ${fmtU(c.feature, c.value)}</td>
    <td class="n">${fmtU(c.feature, live[c.feature])}</td></tr>`).join('');
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
  el.querySelector('.cue').style.display = 'none';
  el.classList.remove('learn');   // hides skip
  const rows = Object.entries(by).map(([name, s]) => `<tr>
      <td>${esc(name)}</td><td class="n">${s.hits}/${s.tries}</td>
      <td class="n">${s.hits ? (s.time / s.hits).toFixed(1) + 's' : '–'}</td>
      <td>${counts(s.wrong)}</td><td>${counts(s.ret)}</td></tr>`).join('');
  el.querySelector('.results').innerHTML = `<table class="trace">
      <tr><th>pose</th><th>hit</th><th>avg time</th><th>also fired while prompted</th><th>fired on return</th></tr>${rows}</table>
    <div class="bar" style="justify-content:center"><button class="primary again">again</button><button class="close">close</button></div>
    <p class="small saved" style="text-align:center"></p>`;
  saveDrill();
  const pool = d.learn ? d.pool : null;
  el.querySelector('.again').onclick = () => { endDrill(true); startDrill(pool); };
  el.querySelector('.close').onclick = () => endDrill();
}
