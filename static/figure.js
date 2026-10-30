// Loaded before the main script in index.html. Uses its globals (poses, info, live, state, rangeOf, fmtU, esc) at call time.
// ---------- preview figure: a stick figure posed so every condition holds ----------
// Built in image coords like the camera overlay (mirrored, y down, torso = 1), so it matches the preview.
// Static features are measured off the figure with the same formulas as src/features.py; motion and
// baseline features (jump, jog, squat, knee lift) are set directly and shown by geometry or animation.
const FIG_REST = { lean: 0, tilt: 0, raiseL: 12, raiseR: 12, angleL: 170, angleR: 170, kneeL: 0, kneeR: 0, drop: 0, rise: 0, cadence: 0 };
const FIG_BOUNDS = { lean: [-0.8, 0.8], tilt: [-0.5, 0.5], raiseL: [0, 180], raiseR: [0, 180], angleL: [20, 180], angleR: [20, 180],
                     kneeL: [0, 0.7], kneeR: [0, 0.7], drop: [0, 0.7], rise: [0, 0.8], cadence: [0, 4] };
const FIG_DIRECT = { hip_drop: 'drop', left_knee_lift: 'kneeL', right_knee_lift: 'kneeR', hip_rise: 'rise', step_cadence: 'cadence' };
const FIG_MARGIN = { deg: 8, torso: 0.08, 'steps/s': 0.4, 'torso/s': 0.5, 'deg/s': 50 };   // aim this far past each threshold
const FIG_PARTS = { left_knee_lift: ['legL'], right_knee_lift: ['legR'], wrists_distance: ['armL', 'armR'], wrist_low: ['armL', 'armR'],
                    lean: ['torso'], head_tilt: ['head'], hip_drop: ['torso', 'legL', 'legR'], hip_rise: ['torso', 'legL', 'legR'],
                    step_cadence: ['legL', 'legR'], clap: ['armL', 'armR'] };
const figParts = f => FIG_PARTS[f] || (f.startsWith('left_') ? ['armL'] : f.startsWith('right_') ? ['armR'] : []);

function figBody(q) {
  const hy = 1 + q.drop, sy = hy - Math.sqrt(1 - q.lean * q.lean), P = {};
  P.nose = { x: q.lean + q.tilt, y: sy - 0.35 };
  for (const [s, sign] of [['L', -1], ['R', 1]]) {   // mirrored: the user's left is on the image left
    const sh = { x: q.lean + sign * 0.25, y: sy };
    const t = q['raise' + s] * Math.PI / 180, u = [sign * Math.sin(t), Math.cos(t)];
    const el = { x: sh.x + u[0] * 0.45, y: sh.y + u[1] * 0.45 };
    const r = q['bend' + s] * sign * (180 - q['angle' + s]) * Math.PI / 180;
    const wr = { x: el.x + (u[0] * Math.cos(r) - u[1] * Math.sin(r)) * 0.4, y: el.y + (u[0] * Math.sin(r) + u[1] * Math.cos(r)) * 0.4 };
    const hip = { x: sign * 0.15, y: hy }, lift = q['knee' + s];
    let knee, ankle;
    if (lift > 0.02) { knee = { x: hip.x, y: hy + 0.5 - lift }; ankle = { x: hip.x, y: knee.y + 0.5 }; }
    else {   // feet stay on the ground; a squat pushes the knees out
      const half = (2 - hy) / 2, out = Math.sqrt(Math.max(0, 0.25 - half * half));
      knee = { x: hip.x + sign * out, y: hy + half }; ankle = { x: hip.x, y: 2 };
    }
    Object.assign(P, { ['s' + s]: sh, ['e' + s]: el, ['w' + s]: wr, ['h' + s]: hip, ['k' + s]: knee, ['a' + s]: ankle });
  }
  return P;
}

function figAngle(a, b, c) {
  const v1 = [a.x - b.x, a.y - b.y], v2 = [c.x - b.x, c.y - b.y];
  const cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (Math.hypot(...v1) * Math.hypot(...v2) + 1e-9);
  return Math.acos(Math.max(-1, Math.min(1, cos))) * 180 / Math.PI;
}

function figFeatures(q, P) {
  const f = {}, sx = (P.sL.x + P.sR.x) / 2, hipY = (P.hL.y + P.hR.y) / 2;
  for (const [side, s, sign] of [['left', 'L', -1], ['right', 'R', 1]]) {
    const sh = P['s' + s], el = P['e' + s], wr = P['w' + s];
    f[side + '_arm_raise'] = figAngle({ x: sh.x, y: sh.y + 1 }, sh, el);
    f[side + '_arm_angle'] = figAngle(sh, el, wr);
    f[side + '_wrist_out'] = sign * (wr.x - sh.x);
    f[side + '_wrist_up'] = sh.y - wr.y;
  }
  f.wrists_distance = Math.hypot(P.wL.x - P.wR.x, P.wL.y - P.wR.y);
  f.wrist_low = Math.max(P.wL.y, P.wR.y) - hipY;
  f.lean = sx - (P.hL.x + P.hR.x) / 2;
  f.head_tilt = P.nose.x - sx;
  for (const [feat, k] of Object.entries(FIG_DIRECT)) f[feat] = q[k];
  return f;
}

// How far the figure misses the conditions (each aimed a margin past its threshold), in fractions of each feature's range.
function figMiss(f, conds) {
  let cost = 0;
  for (const c of conds) {
    const v = f[c.feature]; if (v === undefined) continue;
    const [lo, hi] = rangeOf(c.feature), m = FIG_MARGIN[(info[c.feature] || {}).unit] ?? 0.08;
    cost += Math.max(0, c.op === '>' ? c.value + m - v : v - (c.value - m)) / (hi - lo);
  }
  return cost;
}

// misses, plus a little pull towards the resting pose so unconstrained parts stay relaxed
function figCost(q, conds) {
  let cost = figMiss(figFeatures(q, figBody(q)), conds);
  for (const [k, [lo, hi]] of Object.entries(FIG_BOUNDS)) cost += 0.02 * ((q[k] - FIG_REST[k]) / (hi - lo)) ** 2;
  return cost;
}

// Pattern search over the given parameters: nudge each up and down, halve the steps when nothing helps.
function figSearch(q, keys, cost) {
  const step = Object.fromEntries(keys.map(k => [k, (FIG_BOUNDS[k][1] - FIG_BOUNDS[k][0]) / 4]));
  let cur = cost(q);
  for (let halvings = 0; halvings < 9;) {
    let improved = false;
    for (const k of keys) for (const d of [1, -1]) {
      const old = q[k], [lo, hi] = FIG_BOUNDS[k];
      q[k] = Math.max(lo, Math.min(hi, old + d * step[k]));
      const c = cost(q);
      if (c < cur - 1e-9) { cur = c; improved = true; } else q[k] = old;
    }
    if (!improved) { for (const k in step) step[k] /= 2; halvings++; }
  }
  return cur;
}

// From the resting pose, once per elbow-bend direction; keep the cheapest.
function solveFigure(conds) {
  let best = null, bestCost = Infinity;
  for (const bendL of [1, -1]) for (const bendR of [1, -1]) {
    const q = { ...FIG_REST, bendL, bendR };
    const cur = figSearch(q, Object.keys(FIG_BOUNDS), q => figCost(q, conds));
    if (cur < bestCost) { bestCost = cur; best = q; }
  }
  return best;
}

// ---------- sweep: move the highlighted parts through the whole range the conditions allow ----------
// For each conditioned feature, push the figure to its lowest then highest value that still meets every
// condition, moving only the highlighted parts, and tween base -> low -> high -> base.
const FIG_KEYS = { armL: ['raiseL', 'angleL'], armR: ['raiseR', 'angleR'], torso: ['lean', 'drop'], head: ['tilt'],
                   legL: ['kneeL', 'drop'], legR: ['kneeR', 'drop'] };
const FIG_STILL = ['step_cadence', 'hip_rise'];   // already animated by the jog and the hop
const FIG_TWEEN = 8, FIG_HOLD = 4, FIG_FRAME = 0.1;   // frames per move, frames paused at each end, seconds per frame

function figPush(q0, conds, feature, sign, keys) {
  const [lo, hi] = rangeOf(feature), q = { ...q0 };
  // no pull to rest here, and misses weigh far more than the push, so it stops at the threshold (plus margin)
  figSearch(q, keys, q => { const f = figFeatures(q, figBody(q)); return 20 * figMiss(f, conds) - sign * f[feature] / (hi - lo); });
  return figUnmet(conds, q).length ? q0 : q;
}

function figSweep(q, conds) {
  const keys = [...new Set(conds.flatMap(c => figParts(c.feature)).flatMap(p => FIG_KEYS[p] || []))];
  const lerp = (a, b, t) => ({ ...a, ...Object.fromEntries(Object.keys(FIG_BOUNDS).map(k => [k, a[k] + (b[k] - a[k]) * t])) });
  const tween = (a, b) => Array.from({ length: FIG_TWEEN }, (_, i) => lerp(a, b, (i + 1) / FIG_TWEEN));
  const frames = [q], sweeps = [];
  if (!keys.length) return { frames, sweeps };
  for (const f of new Set(conds.map(c => c.feature))) {
    if (FIG_STILL.includes(f) || figFeatures(q, figBody(q))[f] === undefined) continue;
    const qlo = figPush(q, conds, f, -1, keys), qhi = figPush(q, conds, f, 1, keys);
    const vlo = figFeatures(qlo, figBody(qlo))[f], vhi = figFeatures(qhi, figBody(qhi))[f], [lo, hi] = rangeOf(f);
    if (vhi - vlo < 0.02 * (hi - lo)) continue;   // pinned: nothing worth showing
    sweeps.push({ feature: f, lo: vlo, hi: vhi });
    frames.push(...tween(q, qlo), ...Array(FIG_HOLD).fill(qlo), ...tween(qlo, qhi), ...Array(FIG_HOLD).fill(qhi), ...tween(qhi, q));
  }
  return { frames, sweeps };
}

function figUnmet(conds, q) {
  const f = figFeatures(q, figBody(q));
  return conds.filter(c => f[c.feature] !== undefined && !(c.op === '>' ? f[c.feature] > c.value : f[c.feature] < c.value));
}

function figureSVG(conds, caption = true) {
  if (!conds.length || !Object.keys(info).length) return '';
  const q = solveFigure(conds), unmet = figUnmet(conds, q);
  const { frames, sweeps } = unmet.length ? { frames: [q], sweeps: [] } : figSweep(q, conds);
  const dur = (frames.length * FIG_FRAME).toFixed(1);
  const joints = q => { const P = figBody(q); return { ...P, sc: { x: (P.sL.x + P.sR.x) / 2, y: P.sL.y }, hc: { x: 0, y: P.hL.y } }; };
  const Ps = frames.map(joints);
  const hl = new Set(conds.flatMap(c => figParts(c.feature)));
  const cls = part => hl.has(part) ? 'hl' : '';
  // one value per frame; a constant one stays a plain attribute
  const anim = (attr, vs) => vs.every(v => Math.abs(v - vs[0]) < 1e-4) ? ''
    : `<animate attributeName="${attr}" values="${vs.map(v => v.toFixed(3)).join(';')}" dur="${dur}s" repeatCount="indefinite"/>`;
  const line = (A, B, c) => `<line x1="${A[0].x}" y1="${A[0].y}" x2="${B[0].x}" y2="${B[0].y}" class="${c}">`
    + anim('x1', A.map(p => p.x)) + anim('y1', A.map(p => p.y)) + anim('x2', B.map(p => p.x)) + anim('y2', B.map(p => p.y)) + '</line>';
  const dot = (A, extra, dy = 0) => `<circle cx="${A[0].x}" cy="${A[0].y + dy}" ${extra}>`
    + anim('cx', A.map(p => p.x)) + anim('cy', A.map(p => p.y + dy)) + '</circle>';
  const ln = (Qs, a, b, part) => line(Qs.map(P => P[a]), Qs.map(P => P[b]), cls(part));
  const dots = (Qs, ks) => ks.map(k => dot(Qs.map(P => P[k]), 'r=".05"')).join('');
  const legs = Qs => ln(Qs, 'hL', 'kL', 'legL') + ln(Qs, 'kL', 'aL', 'legL') + ln(Qs, 'hR', 'kR', 'legR') + ln(Qs, 'kR', 'aR', 'legR')
    + dots(Qs, ['kL', 'aL', 'kR', 'aR']);
  const upper = ln(Ps, 'sL', 'sR', 'torso') + ln(Ps, 'hL', 'hR', 'torso') + ln(Ps, 'sc', 'hc', 'torso')
    + ln(Ps, 'sL', 'eL', 'armL') + ln(Ps, 'eL', 'wL', 'armL') + ln(Ps, 'sR', 'eR', 'armR') + ln(Ps, 'eR', 'wR', 'armR')
    + dots(Ps, ['sL', 'sR', 'eL', 'eR', 'wL', 'wR', 'hL', 'hR'])
    + dot(Ps.map(P => P.nose), `r=".17" class="head ${cls('head')}"`, -0.05);
  let lower = legs(Ps);
  if (q.cadence > 0.2) {   // jog: alternate a lifted knee at the required step rate
    const step = `--dur:${(2 / q.cadence).toFixed(2)}s`;
    lower = `<g class="jogA" style="${step}">${legs(frames.map(f => joints({ ...f, kneeL: Math.max(f.kneeL, 0.35) })))}</g>`
          + `<g class="jogB" style="${step}">${legs(frames.map(f => joints({ ...f, kneeR: Math.max(f.kneeR, 0.35) })))}</g>`;
  }
  let arrows = Ps.map(P => motionArrows(conds, P));
  if (arrows.some(a => a.length !== arrows[0].length)) arrows = arrows.map(() => arrows[0]);   // keep the line count fixed
  let body = upper + lower + arrows[0].map((_, i) => line(arrows.map(a => a[i][0]), arrows.map(a => a[i][1]), 'mv')).join('');
  if (q.rise > 0.05) body = `<g class="hop" style="--h:${-q.rise}px">${body}</g>`;
  const svg = `<svg viewBox="-1.4 -2 2.8 4.2"><line class="ground" x1="-1.3" y1="2.05" x2="1.3" y2="2.05"/>${body}</svg>`;
  if (!caption) return svg;
  const range = sweeps.length ? `<div class="small">moves through ${sweeps.map(s =>
    `${s.feature.replace(/_/g, ' ')} ${fmtU(s.feature, s.lo)}–${fmtU(s.feature, s.hi)}`).join(', ')}</div>` : '';
  const tip = unmet.length ? `<div class="unmet">can't all hold at once: ${unmet.map(c => `${c.feature} ${c.op} ${c.value}`).join(', ')}</div>` : '';
  return `${svg}<div class="small">as seen in preview</div>${range}${tip}`;
}

// Speed conditions (swipe, punch, clap) aren't positions: draw them as an arrow from the wrist. Returns [from, to] segments.
function motionArrows(conds, P) {
  const dir = { L: [0, 0], R: [0, 0] };
  const unit = (a, b) => { const n = Math.hypot(b.x - a.x, b.y - a.y) || 1; return [(b.x - a.x) / n, (b.y - a.y) / n]; };
  const add = (s, [x, y]) => { dir[s][0] += x; dir[s][1] += y; };
  for (const c of conds) {
    const s = c.op === '>' && c.value >= 0 ? 1 : c.op === '<' && c.value <= 0 ? -1 : 0;
    if (!s) continue;
    let m = c.feature.match(/^(left|right)_wrist_v([xy])$/);
    if (m) {
      const side = m[1] === 'left' ? 'L' : 'R';
      if (m[2] === 'x') dir[side][0] = s; else dir[side][1] = -s;   // + is up, image y points down
    } else if ((m = c.feature.match(/^(left|right)_punch$/)) && s > 0) {
      const side = m[1] === 'left' ? 'L' : 'R';
      add(side, unit(P['e' + side], P['w' + side]));   // forearm shooting out along its own line
    } else if (c.feature === 'clap' && s > 0) {
      add('L', unit(P.wL, P.wR)); add('R', unit(P.wR, P.wL));
    }
  }
  const out = [];
  for (const [s, [dx, dy]] of Object.entries(dir)) {
    const n = Math.hypot(dx, dy); if (!n) continue;
    const w = P['w' + s], ux = dx / n, uy = dy / n, e = { x: w.x + ux * 0.55, y: w.y + uy * 0.55 };
    const head = a => ({ x: e.x - 0.18 * (ux * Math.cos(a) - uy * Math.sin(a)), y: e.y - 0.18 * (ux * Math.sin(a) + uy * Math.cos(a)) });
    out.push([w, e], [e, head(0.5)], [e, head(-0.5)]);
  }
  return out;
}

// ---------- clashes: positions that fire two poses (different keys) at once ----------
// Each pose is a box in feature space (a lo..hi range per feature). Boxes that intersect clash if a body
// can actually hold the intersection, which the figure solver checks. Ignores release slack (margin).
function poseBox(p) {
  const box = {};
  for (const c of p.conditions) {
    const r = box[c.feature] || (box[c.feature] = [-Infinity, Infinity]);
    if (c.op === '>') r[0] = Math.max(r[0], c.value); else r[1] = Math.min(r[1], c.value);
  }
  return box;
}

// every position in box b is also inside box a
const boxWithin = (b, a) => Object.entries(a).every(([f, [lo, hi]]) => { const r = b[f] || [-Infinity, Infinity]; return r[0] >= lo && r[1] <= hi; });

function rangeText(f, [lo, hi]) {
  if (lo > -Infinity && hi < Infinity) return `${lo} < ${f} < ${hi}`;
  return lo > -Infinity ? `${f} > ${lo}` : `${f} < ${hi}`;
}

// Features on the same arm move together (raise an arm and the wrist rises), so they count as one group.
const clashGroups = f => f.includes('knee') ? [f] : f.startsWith('left_') ? ['armL'] : f.startsWith('right_') ? ['armR']
  : f.startsWith('wrist') || f === 'clap' ? ['armL', 'armR'] : [f];
const poseGroups = p => new Set(p.conditions.flatMap(c => clashGroups(c.feature)));

// Poses on unrelated body parts (jog + raise arm) firing together is a combo, not a clash: only pairs
// sharing a feature group are checked. Returns { clashes, combos } where combos counts the skipped pairs.
function findClashes() {
  const live = poses.filter(p => p.enabled !== false && p.conditions.length);
  const out = [];
  let combos = 0;
  live.forEach((a, i) => live.slice(i + 1).forEach(b => {
    if (a.key === b.key) return;
    const ga = poseGroups(a);
    if (![...poseGroups(b)].some(g => ga.has(g))) { combos++; return; }
    const A = poseBox(a), B = poseBox(b), both = {};
    for (const f of new Set([...Object.keys(A), ...Object.keys(B)])) {
      const ra = A[f] || [-Infinity, Infinity], rb = B[f] || [-Infinity, Infinity];
      both[f] = [Math.max(ra[0], rb[0]), Math.min(ra[1], rb[1])];
      if (both[f][0] >= both[f][1]) return;
    }
    const conds = [...a.conditions, ...b.conditions];
    if (figUnmet(conds, solveFigure(conds)).length) return;   // ranges overlap but no body can hold it
    const kind = boxWithin(A, B) && boxWithin(B, A) ? 'same' : boxWithin(B, A) ? 'b-in-a' : boxWithin(A, B) ? 'a-in-b' : 'overlap';
    out.push({ a, b, kind, both, conds });
  }));
  return { clashes: out, combos };
}

const poseLabel = p => `<b>${esc(p.name)}</b> <span class="small">(${esc(p.key)})</span>`;

function renderClashes() {
  const root = document.getElementById('clashes');
  if (!Object.keys(info).length) { root.innerHTML = ''; return; }
  const { clashes: list, combos } = findClashes();
  const btn = document.getElementById('clashBtn');
  btn.textContent = `clashes (${list.length})`;
  btn.classList.toggle('warn', list.length > 0);
  const note = combos ? ` ${combos} pair${combos > 1 ? 's' : ''} on separate body parts can combine (e.g. jog + arm raise); not shown.` : '';
  if (!list.length) { root.innerHTML = `<p class="small">No clashes: no two poses on the same body part fire together.${note}</p>`; return; }
  root.innerHTML = `<p class="small">Poses on the same body part that can fire at once.${note}</p>` + list.map(({ a, b, kind, both, conds }) => {
    const where = Object.entries(both).map(([f, r]) => `<code>${rangeText(f, r)}</code>`).join(', ');
    const text = kind === 'same' ? `${poseLabel(a)} and ${poseLabel(b)} have the same conditions: they always fire together.`
      : kind === 'b-in-a' ? `Every ${poseLabel(b)} also fires ${poseLabel(a)}.`
      : kind === 'a-in-b' ? `Every ${poseLabel(a)} also fires ${poseLabel(b)}.`
      : `${poseLabel(a)} and ${poseLabel(b)} both fire when ${where}.`;
    return `<div class="clash"><div class="fig">${figureSVG(conds, false)}</div><div>${text}</div></div>`;
  }).join('');
}

let clashFrame = null;
function scheduleClashes() {
  if (clashFrame) return;
  clashFrame = requestAnimationFrame(() => { clashFrame = null; renderClashes(); });
}
