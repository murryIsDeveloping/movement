// Loaded before the main script in index.html. Uses its globals (poses, state, live, paused, esc, fmtU), capture.js's
// beep, figure.js's figureSVG and library.js's presetOf at call time.
// ---------- drill: full-screen random prompts for a set time, scores each pose ----------
// Learn mode is the same screen taking the poses in order, with no clock: each one stays up, with its figure, notes and
// a live checklist of its conditions, until it's done (or skipped).
// Each prompt is a hold or a set of reps. Whether a pose is held or repped is the routine's choice, not the pose's: a
// squat's conditions are its bottom position, so holding them is a held squat and entering them N times is N squats.
// Only poses that need motion (jump, jog, punch) can't be held.
let drill = null;
let sendBefore = null;   // send keys as it was before the drill turned it off; null when no drill
const DRILL_READY = 3, DRILL_TICK_SHOW = 1;   // seconds
const LEARN_REPS = 3, LEARN_HOLD = 5, LEARN_REST = 1.5;   // learn's targets; seconds of neutral between poses
const HOLD_GRACE = 1;   // seconds a hold may drop out (a wobble, a tracking blip) before it starts over
// the drill's own settings, set on its setup screen: [default, min, max] for length (minutes), rest, time to hit and
// hold (seconds), reps, and whether poses that can be held are (1) or repped (0)
const DRILL_SETTINGS = { minutes: [1, 0.5, 60], rest: [3, 0, 30], hit: [10, 2, 60], hold: [10, 2, 120], reps: [5, 1, 50], holdable: [1, 0, 1] };
const DRILL_KEY = 'movement.drill';
const DRILL_INPUTS = { minutes: 'drillMin', rest: 'drillRest', hit: 'drillHit', hold: 'drillHold', reps: 'drillReps', holdable: 'drillHoldable' };

// saved settings, each clamped to its range; a missing or broken one is its default
function drillSettings(from = null) {
  let saved = from;
  if (!saved) try { saved = JSON.parse(localStorage.getItem(DRILL_KEY)) || {}; } catch { saved = {}; }
  return Object.fromEntries(Object.entries(DRILL_SETTINGS).map(([k, [def, lo, hi]]) => {
    const v = parseFloat(saved[k]);
    return [k, Number.isFinite(v) ? Math.min(hi, Math.max(lo, v)) : def];
  }));
}

// ---------- coaching: what to fix while the prompted pose isn't hit ----------
// per feature, what to say when its value needs to go up (op '>') and down ('<'). Left and right are the user's own,
// which the mirrored preview's are too.
const COACH = {
  hip_rise: ['jump higher', 'keep your hips down'],
  hip_drop: ['squat lower', 'stand taller'],
  step_cadence: ['jog faster', 'slow your steps'],
  clap: ['clap your hands together', 'pull your hands apart'],
  wrists_distance: ['spread your hands apart', 'bring your hands closer together'],
  wrist_low: ['reach lower', 'raise your hands'],
  lean: ['lean to your right', 'lean to your left'],
  head_tilt: ['tilt your head to your right', 'tilt your head to your left'],
};
for (const s of ['left', 'right']) Object.assign(COACH, {
  [`${s}_knee_lift`]: [`lift your ${s} knee higher`, `lower your ${s} knee`],
  [`${s}_knee_angle`]: [`straighten your ${s} leg`, `bend your ${s} knee more`],
  [`${s}_knee_out`]: [`open your ${s} knee out to the side`, `bring your ${s} knee in`],
  [`${s}_arm_raise`]: [`raise your ${s} arm higher`, `lower your ${s} arm`],
  [`${s}_arm_angle`]: [`straighten your ${s} arm`, `bend your ${s} elbow more`],
  [`${s}_wrist_out`]: [`reach your ${s} hand further out`, `bring your ${s} hand in`],
  [`${s}_wrist_up`]: [`lift your ${s} hand higher`, `lower your ${s} hand`],
  [`${s}_wrist_vx`]: [`swipe your ${s} hand to your right`, `swipe your ${s} hand to your left`],
  [`${s}_wrist_vy`]: [`push your ${s} hand up, fast`, `pull your ${s} hand down, fast`],
  [`${s}_punch`]: [`punch harder with your ${s}`, `slow your ${s} arm`],
});
// movements, not positions: coached only once the position is right, since they read 0 until you move
const COACH_MOVES = /^(hip_rise|step_cadence|clap)$|_(vx|vy|punch)$/;
const COACH_SHOW = 1, COACH_SAY = 2, COACH_GAP = 2.5, COACH_REPEAT = 5;   // seconds into the prompt; between spoken cues
const VOICE_KEY = 'movement.voice';

// the unmet condition furthest from its threshold (in its feature's range), positions before movements; '' when all hold
function coachCue(i) {
  const conds = (state[i] || {}).conds || [];
  let best = null;
  poses[i].conditions.forEach((c, ci) => {
    const x = live[c.feature];
    // knee angle is blank while the ankle is out of frame: no fix will help until the feet are in view
    if (!conds[ci] && x === undefined && c.feature.endsWith('_knee_angle')) best = { score: 20, cue: 'step back so your feet are in view' };
    if (conds[ci] || x === undefined || !COACH[c.feature]) return;
    const [lo, hi] = (info[c.feature] || {}).range || [0, 1];
    const score = (COACH_MOVES.test(c.feature) ? 0 : 10) + Math.abs(x - c.value) / (hi - lo);
    if (!best || score > best.score) best = { score, cue: COACH[c.feature][c.op === '>' ? 0 : 1] };
  });
  return best ? best.cue : '';
}

const voiceOn = () => document.getElementById('coachVoice').checked;

function say(text) {
  if (!voiceOn() || !window.speechSynthesis) return;
  speechSynthesis.cancel();   // the newest cue wins over one still being read out
  speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}

// shown after COACH_SHOW, so moving into the pose doesn't flicker cues; spoken after COACH_SAY, a new cue at most every
// COACH_GAP and the same one again every COACH_REPEAT
function coachTick(now, since) {
  const d = drill, el = d.el.querySelector('.coach');
  const cue = d.phase === 'prompt' && since >= COACH_SHOW ? coachCue(d.target) : '';
  el.textContent = cue;
  if (!cue || since < COACH_SAY) return;
  const gap = (now - (d.saidAt ?? -Infinity)) / 1000;
  if (gap >= (cue === d.said ? COACH_REPEAT : COACH_GAP)) {
    say(cue);
    d.said = cue; d.saidAt = now;
    drillEvent('coach', poses[d.target].name, { cue });
  }
}

const drillable = i => poses[i] && poses[i].enabled !== false && poses[i].conditions.length;

// a condition only met while moving (jump, jog, punch), not a stillness band like "hand not moving" (vy < 1.5)
const needsMotion = c => COACH_MOVES.test(c.feature) && (c.op === '>' ? c.value > 0 : c.value < 0);
const canHold = i => !poses[i].conditions.some(needsMotion);
// a movement that stays on while you keep it up (jog, stride): kept going for seconds, as reps would mean stopping each time
const sustained = i => poses[i].conditions.some(needsMotion) && poses[i].conditions.filter(needsMotion).every(c => c.feature === 'step_cadence');

// what the prompt asks: hold (or keep a movement going) for `goal` seconds, or `goal` reps
function drillGoal(i) {
  const d = drill, hold = (canHold(i) && (d.learn || d.cfg.holdable)) || sustained(i);
  return hold ? { kind: 'hold', goal: d.learn ? LEARN_HOLD : d.cfg.hold, moving: sustained(i) }
    : { kind: 'reps', goal: d.learn ? LEARN_REPS : d.cfg.reps, moving: false };
}

// while prompting: what's asked, and how far along
const progressText = d => d.kind === 'hold'
  ? (d.held ? `${d.moving ? 'keep going' : 'holding'} · ${Math.ceil(d.goal - d.held)}s left` : `${d.moving ? 'keep it up' : 'hold'} ${d.goal}s`)
  : `${d.count}/${d.goal} reps`;

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
  drillPlan();
  document.getElementById('drillStart').focus();
}

// Under the setup's hold and reps: which active poses each one applies to with the settings as they stand, since a pose
// is held, repped or kept up by its kind and the positions choice. A row no pose uses is dimmed.
function drillPlan() {
  const val = id => document.getElementById(id).value, holdable = val('drillHoldable') === '1';
  const names = list => list.length > 4 ? `${list.slice(0, 3).join(', ')} +${list.length - 3} more` : list.join(', ');
  const kept = [], held = [], reps = [];
  poses.forEach((p, i) => {
    if (!drillable(i)) return;
    (sustained(i) ? kept : canHold(i) && holdable ? held : reps).push(esc(p.name));
  });
  const lines = [held.length && `<b>held ${esc(val('drillHold'))} s:</b> ${names(held)}`,
    reps.length && `<b>${esc(val('drillReps'))} reps:</b> ${names(reps)}`,
    kept.length && `<b>kept up ${esc(val('drillHold'))} s:</b> ${names(kept)}`].filter(Boolean);
  document.getElementById('drillPlan').innerHTML = lines.length ? lines.join('<br>') : 'no enabled poses to drill';
  document.getElementById('drillHold').closest('label').classList.toggle('unused', !held.length && !kept.length);
  document.getElementById('drillReps').closest('label').classList.toggle('unused', !reps.length);
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
  drill = { el, pool, learn: !!learn, cfg, step: 0, phase: 'ready', phaseAt: now, clock: null,
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
  if (window.speechSynthesis) speechSynthesis.cancel();
  // wipe what this run showed: the next one starts paused if you're out of frame, and a paused tick redraws none of it
  for (const sel of ['.coach', '.big', '.sub', '.clock', '.checks', '.results', '.cue .fig']) drill.el.querySelector(sel).innerHTML = '';
  drill.el.querySelector('.big').className = 'big';
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
  Object.assign(drill, drillGoal(drill.target));
  drill.phase = 'prompt'; drill.phaseAt = now;
  drill.seenOff = false;   // the target must go off then on, so a hold left over from last time doesn't count
  drill.on = false;        // target on (after seenOff) last tick: a rep is it turning on
  drill.held = 0; drill.offFor = 0; drill.count = 0; drill.lastRepAt = now;
  drill.wrong = new Set();
  drill.wasActive = state.map(s => !!(s && s.active));
  drill.said = null; drill.saidAt = null;
  drillEvent('prompt', poses[drill.target].name, { kind: drill.kind, goal: drill.goal });
  beep(660, 80);
  say(`${poses[drill.target].name}, ${drill.kind === 'hold' ? `${drill.moving ? 'keep it up' : 'hold'} ${drill.goal} seconds` : `${drill.goal} reps`}`);   // eyes can stay off the screen
}

// learn: on to the next pose, or the results after the last one
function learnNext(now) {
  drill.step++;
  if (drill.step >= drill.pool.length) { drill.phase = 'done'; beep(440, 300); renderDrillResults(); }
  else drillPrompt(now);
}

function drillSkip() {
  const d = drill;
  if (!d || !d.learn || d.phase === 'done' || d.phase === 'ready') return;
  const now = performance.now();
  if (d.phase === 'prompt') {
    drillResult(false, (now - d.phaseAt) / 1000);
    drillEvent('skip', poses[d.target].name);
  }
  learnNext(now);
}

// got: seconds held or reps done when the prompt ended
function drillResult(hit, time) {
  const d = drill;
  d.results.push({ name: poses[d.target].name, hit, time, wrong: [...d.wrong], ret: [],
                   kind: d.kind, goal: d.goal, got: d.kind === 'hold' ? +d.held.toFixed(1) : d.count });
}

// the prompted pose this tick: a hold's seconds, or a rep when it turns on. Returns 'hit', 'miss' or ''.
function drillProgress(now, since, dt) {
  const d = drill, name = poses[d.target].name, on = !!(state[d.target] && state[d.target].active);
  if (!on) d.seenOff = true;
  const counts = d.seenOff && on, was = d.on;
  d.on = counts;
  if (d.kind === 'hold') {
    if (counts) {
      if (!d.held) { drillEvent('hold_start', name); beep(880, 60); }
      d.held += dt / 1000; d.offFor = 0;
    } else if (d.held && (d.offFor += dt / 1000) > HOLD_GRACE) {
      drillEvent('hold_lost', name, { held: +d.held.toFixed(1) });
      d.held = 0; beep(330, 120);
    }
    // time to hit is for getting into the pose, with the hold's own length on top; a hold underway may finish
    return d.held >= d.goal ? 'hit' : !d.held && since >= d.hit + d.goal ? 'miss' : '';
  }
  if (counts && !was) {
    d.count++; d.lastRepAt = now;
    drillEvent('rep', name, { n: d.count });
    if (d.count < d.goal) { beep(1000, 60); say(String(d.count)); }
  }
  // time to hit is per rep
  return d.count >= d.goal ? 'hit' : (now - d.lastRepAt) / 1000 >= d.hit ? 'miss' : '';
}

function drillTick() {
  const d = drill, now = performance.now(), el = d.el;
  const active = i => !!(state[i] && state[i].active);
  const dt = now - (d.lastTick ?? now);
  d.lastTick = now;
  if (paused && d.phase !== 'done') {
    // out of frame: the clocks stop, so stepping up to the camera doesn't eat the prompt or the minute
    d.phaseAt += dt; d.endAt += dt; d.lastRepAt += dt;
    el.querySelector('.big').className = 'big bad';
    el.querySelector('.big').textContent = 'Paused';
    el.querySelector('.sub').textContent = paused.length ? `not fully in frame: ${paused.join(', ')}` : 'no body: step into view';
    el.querySelector('.coach').textContent = '';
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
      if (d.learn) learnNext(now); else drillPrompt(now);
    }
  }
  else if (d.phase === 'prompt') {
    firing.forEach(n => { d.wrong.add(n); drillEvent('wrong', n, { prompted: poses[d.target].name }); });
    const end = drillProgress(now, since, dt);
    if (end) {
      drillResult(end === 'hit', since);
      drillEvent(end, poses[d.target].name, { time: +since.toFixed(2) });
      d.phase = 'return'; d.phaseAt = now;
      if (end === 'hit') beep(1200, 150); else beep(220, 250);
    }
  }
  if (d.phase === 'done') return;

  const left = Math.max(0, Math.ceil((d.endAt - now) / 1000));
  const last = d.results[d.results.length - 1];
  let big = '', sub = '', cls = '';
  if (d.phase === 'ready') { big = Math.ceil(DRILL_READY - since); sub = 'get ready'; }
  else if (d.phase === 'prompt') {
    big = esc(poses[d.target].name);
    if (d.kind === 'hold' && d.held) cls = 'ok';   // green while holding
    // drill: time left to get into the pose (or for the next rep); a hold underway has its own countdown
    const toGo = d.kind === 'hold' ? d.hit + d.goal - since : d.hit - (now - d.lastRepAt) / 1000;
    sub = d.learn ? esc((presetOf(poses[d.target].preset) || {}).notes || '')
      : `${progressText(d)}${d.kind === 'hold' && d.held ? '' : ` · ${Math.ceil(toGo)}s`}`;
  }
  else if (since < DRILL_TICK_SHOW) {
    const goal = last.kind === 'hold' ? `held ${last.goal}s` : `${last.goal} reps`;
    if (last.hit) { big = '✓'; cls = 'ok'; sub = `${esc(last.name)}: ${goal} in ${last.time.toFixed(1)}s`; }
    else { big = '✗'; cls = 'bad'; sub = `${esc(last.name)} timed out${last.kind === 'reps' ? ` at ${last.got}/${last.goal} reps` : ''}`; }
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
  // the phase may have changed above, so not `since`. Reps are coached from the last one, so not mid-set.
  coachTick(now, (now - (d.kind === 'reps' ? d.lastRepAt : d.phaseAt)) / 1000);
  // the figure shows while prompting; learning keeps it up between reps too, as the same pose comes next
  el.querySelector('.cue').style.visibility = d.phase === 'prompt' || (d.learn && d.phase === 'return') ? '' : 'hidden';
  el.querySelector('.checks').innerHTML = d.learn && d.target >= 0 ? learnChecks(d.target) : '';
  el.querySelector('.clock').textContent = d.phase === 'ready' ? ''
    : d.learn ? `pose ${d.step + 1}/${d.pool.length}${d.phase === 'prompt' ? ' · ' + progressText(d) : ''}`
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
  el.querySelector('.coach').textContent = '';
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
