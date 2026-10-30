// Loaded before the main script in index.html. Uses its globals (poses, info, live, state, rangeOf, esc) at call time.
// ---------- capture: record a movement, scrub frames, pick conditions ----------
let capture = null;
const COUNTDOWN = 3, RECORD = 4, TRIGGER_HOLD = 250;   // ms the trigger pose must hold
const TRIGGER_KEY = 'movement.captureTrigger';

let audio = null;
// after: seconds from now, on the audio clock, which a hidden tab doesn't throttle the way it does setTimeout
function beep(freq = 880, ms = 120, after = 0) {
  try {
    const o = audio.createOscillator(), g = audio.createGain(), t = audio.currentTime + after;
    o.frequency.value = freq; g.gain.value = 0.2;
    o.connect(g).connect(audio.destination);
    o.start(t); o.stop(t + ms / 1000);
  } catch {}
}

function startCapture(pi, slot) {
  if (capture) endCapture();
  const el = document.createElement('div');
  el.className = 'capture';
  capture = { pi, el, frames: [], recording: false, rest: null, sel: 0, trigger: null };
  slot.appendChild(el);
  let saved = '';
  try { saved = localStorage.getItem(TRIGGER_KEY) || ''; } catch {}
  const opts = poses.filter((q, i) => i !== pi && q.enabled !== false)
    .map(q => `<option value="${esc(q.name)}" ${q.name === saved ? 'selected' : ''}>when "${esc(q.name)}" fires</option>`).join('');
  el.innerHTML = `<h3>Capture: stand still, then do the movement when it says GO</h3>
    <div class="bar"><span class="small">start</span>
      <select class="trig"><option value="">now</option>${opts}</select>
      <button class="primary go">start</button><button class="cancel">cancel</button></div>
    <div class="status"></div>`;
  el.querySelector('.cancel').onclick = endCapture;
  el.querySelector('.go').onclick = () => {
    try { audio = audio || new AudioContext(); } catch {}
    const t = el.querySelector('.trig').value;
    try { localStorage.setItem(TRIGGER_KEY, t); } catch {}
    el.querySelector('.trig').disabled = el.querySelector('.go').disabled = true;
    if (!t) { countdown(); return; }
    capture.trigger = { i: poses.findIndex((q, i) => i !== capture.pi && q.name === t), name: t, seenOff: false, since: null };
    el.querySelector('.status').textContent = `get in position, then do "${t}"`;
  };
}

// Fire on a fresh activation of the trigger pose, held briefly so a flicker doesn't start it.
function checkTrigger() {
  const tr = capture && capture.trigger;
  if (!tr) return;
  tr.i = poses.findIndex((q, i) => i !== capture.pi && q.name === tr.name);   // by name: a delete, undo or move shifts indexes
  if (!(state[tr.i] || {}).active) { tr.seenOff = true; tr.since = null; return; }
  if (!tr.seenOff) return;
  tr.since = tr.since || performance.now();
  if (performance.now() - tr.since >= TRIGGER_HOLD) { capture.trigger = null; countdown(); }
}

function countdown() {
  const st = capture.el.querySelector('.status');
  let n = COUNTDOWN;
  st.textContent = `get ready… ${n}`; beep(660);
  capture.timer = setInterval(() => {
    n -= 1;
    if (n > 0) { st.textContent = `get ready… ${n}`; beep(660); return; }
    clearInterval(capture.timer);
    capture.rest = { ...live };
    capture.recording = true;
    st.textContent = 'GO — recording'; beep(1320, 250);
    capture.timer = setTimeout(() => { capture.recording = false; beep(440, 300); renderCapture(); }, RECORD * 1000);
  }, 1000);
}

function endCapture() {
  if (!capture) return;
  clearInterval(capture.timer); clearTimeout(capture.timer);
  capture.el.remove(); capture = null;
}

function renderCapture() {
  const c = capture, p = poses[c.pi];
  const feats = Object.keys(info);
  if (c.frames.length < 5) { c.el.querySelector('.status').textContent = 'no body tracked during recording — try again'; return; }
  // peak deviation from rest per feature, for ranking
  const range = f => { const [a, b] = rangeOf(f); return b - a; };
  const peak = {}; feats.forEach(f => { peak[f] = Math.max(...c.frames.map(fr => Math.abs((fr.f[f] ?? 0) - (c.rest[f] ?? 0)))) / range(f); });
  const order = [...feats].sort((a, b) => peak[b] - peak[a]);
  // default selected frame: where the top feature peaks
  const top = order[0];
  c.sel = c.frames.reduce((bi, fr, i, arr) => Math.abs((fr.f[top] ?? 0) - c.rest[top]) > Math.abs((arr[bi].f[top] ?? 0) - c.rest[top]) ? i : bi, 0);
  c.picked = new Set(order.slice(0, 2).filter(f => peak[f] > 0.08));
  c.ops = {}; c.thr = {};

  c.el.innerHTML = `
    <h3>Captured ${c.frames.length} frames for "${esc(p.name)}". Drag to the frame that best represents the pose.</h3>
    <input type="range" class="scrub" min="0" max="${c.frames.length - 1}" value="${c.sel}">
    <div class="small">frame <span class="fi">${c.sel}</span> / ${c.frames.length - 1} &nbsp;·&nbsp; ticked rows become this pose's conditions. Sorted by how much each feature moved.</div>
    <table class="trace"><thead><tr><th></th><th>feature</th><th>trace</th><th>rest</th><th>at frame</th><th>op</th><th>threshold</th></tr></thead><tbody></tbody></table>
    <div class="bar"><button class="primary apply">apply to pose</button><button class="cancel">discard</button></div>`;
  c.el.querySelector('.cancel').onclick = endCapture;
  c.el.querySelector('.apply').onclick = () => {
    p.conditions = [...c.picked].map(f => ({ feature: f, op: c.ops[f], value: c.thr[f] }));
    endCapture(); renderPoses(); scheduleSave();
  };
  c.el.querySelector('.scrub').oninput = e => { c.sel = +e.target.value; c.el.querySelector('.fi').textContent = c.sel; fillTrace(order, peak, true); };
  fillTrace(order, peak, false);
}

function suggest(f) {
  const c = capture, rest = c.rest[f] ?? 0, v = c.frames[c.sel].f[f] ?? 0;
  const op = v >= rest ? '>' : '<';
  const step = rangeOf(f)[2];
  const thr = rest + (v - rest) * 0.7;
  return { op, thr: Math.round(thr / step) * step };
}

function fillTrace(order, peak, keepEdits) {
  const c = capture, tb = c.el.querySelector('tbody');
  const fr = c.frames[c.sel];
  tb.innerHTML = '';
  order.forEach(f => {
    if (!keepEdits || !(f in c.ops)) { const s = suggest(f); c.ops[f] = s.op; c.thr[f] = s.thr; }
    const tr = document.createElement('tr');
    tr.className = c.picked.has(f) ? 'picked' : '';
    tr.innerHTML = `<td><input type="checkbox" ${c.picked.has(f) ? 'checked' : ''}></td>
      <td title="${info[f].desc}">${f}</td><td><canvas width="160" height="28"></canvas></td>
      <td class="n">${fmtU(f, c.rest[f])}</td><td class="n"><b>${fmtU(f, fr.f[f])}</b></td>
      <td><select><option ${c.ops[f] === '>' ? 'selected' : ''}>&gt;</option><option ${c.ops[f] === '<' ? 'selected' : ''}>&lt;</option></select></td>
      <td><input class="thr" type="number" step="any" value="${c.thr[f]}"></td>`;
    tr.querySelector('input[type=checkbox]').onchange = e => { e.target.checked ? c.picked.add(f) : c.picked.delete(f); tr.className = e.target.checked ? 'picked' : ''; };
    tr.querySelector('select').onchange = e => { c.ops[f] = e.target.value; };
    tr.querySelector('.thr').oninput = e => { c.thr[f] = parseFloat(e.target.value) || 0; };
    drawTrace(tr.querySelector('canvas'), c.frames.map(x => x.f[f] ?? 0), c.sel, c.thr[f]);
    tb.appendChild(tr);
  });
}

function drawTrace(cv, ys, sel, thr) {
  const ctx = cv.getContext('2d'), W = cv.width, H = cv.height;
  const lo = Math.min(...ys, thr), hi = Math.max(...ys, thr), span = (hi - lo) || 1;
  const X = i => i / (ys.length - 1) * (W - 2) + 1, Y = v => H - 2 - (v - lo) / span * (H - 4);
  ctx.clearRect(0, 0, W, H);
  ctx.strokeStyle = '#4a4f55'; ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(0, Y(thr)); ctx.lineTo(W, Y(thr)); ctx.stroke(); ctx.setLineDash([]);
  ctx.strokeStyle = '#4f8ef7'; ctx.lineWidth = 1.5; ctx.beginPath(); ys.forEach((v, i) => i ? ctx.lineTo(X(i), Y(v)) : ctx.moveTo(X(i), Y(v))); ctx.stroke();
  ctx.strokeStyle = '#f0b840'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(X(sel), 0); ctx.lineTo(X(sel), H); ctx.stroke();
}
