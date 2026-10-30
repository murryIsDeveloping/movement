// Loaded before the main script in index.html. Uses its globals (poses, info, live, state, rangeOf, fmt, fmtU, esc) at call time.
// ---------- preview figure: a stick figure posed so every condition holds ----------
// Built in image coords like the camera overlay (mirrored, y down, torso = 1), so it matches the preview.
// Static features are measured off the figure with the same formulas as src/features.py; motion and
// baseline features (jump, jog, squat, knee lift) are set directly and shown by geometry or animation.
// foot: a planted ankle's sideways offset from the hip (+ = away from the body), or how far a lifted one tucks in towards
// the other leg (as in tree); out: a lifted knee's swing away from the body
// fold: bending forward towards the camera, which shortens the torso on screen by that fraction
const FIG_REST = { lean: 0, tilt: 0, raiseL: 12, raiseR: 12, angleL: 170, angleR: 170, kneeL: 0, kneeR: 0, drop: 0, rise: 0, cadence: 0,
                   footL: 0, footR: 0, outL: 0, outR: 0, fold: 0 };
const FIG_BOUNDS = { lean: [-0.8, 0.8], tilt: [-0.5, 0.5], raiseL: [0, 180], raiseR: [0, 180], angleL: [20, 180], angleR: [20, 180],
                     kneeL: [0, 0.7], kneeR: [0, 0.7], drop: [0, 0.7], rise: [0, 0.8], cadence: [0, 4],
                     footL: [-0.2, 0.7], footR: [-0.2, 0.7], outL: [0, 0.5], outR: [0, 0.5], fold: [0, 0.7] };
const FIG_DIRECT = { hip_drop: 'drop', left_knee_lift: 'kneeL', right_knee_lift: 'kneeR', hip_rise: 'rise', step_cadence: 'cadence' };
const FIG_MARGIN = { deg: 8, torso: 0.08, 'steps/s': 0.4, 'torso/s': 0.5, 'deg/s': 50 };   // aim this far past each threshold
const FIG_PARTS = { left_knee_lift: ['legL'], right_knee_lift: ['legR'], left_knee_angle: ['legL'], right_knee_angle: ['legR'],
                    left_knee_out: ['legL'], right_knee_out: ['legR'], wrists_distance: ['armL', 'armR'], wrist_low: ['armL', 'armR', 'torso'],
                    lean: ['torso'], head_tilt: ['head'], hip_drop: ['torso', 'legL', 'legR'], hip_rise: ['torso', 'legL', 'legR'],
                    step_cadence: ['legL', 'legR'], clap: ['armL', 'armR'] };
const figParts = f => FIG_PARTS[f] || (f.startsWith('left_') ? ['armL'] : f.startsWith('right_') ? ['armR'] : []);

function figBody(q) {
  const hy = 1 + q.drop, sy = hy - Math.sqrt(1 - q.lean * q.lean) * (1 - q.fold), P = {};
  P.nose = { x: q.lean + q.tilt, y: sy - 0.35 * (1 - 2 * q.fold) };   // bowing: the head drops to the shoulders
  for (const [s, sign] of [['L', -1], ['R', 1]]) {   // mirrored: the user's left is on the image left
    const sh = { x: q.lean + sign * 0.25, y: sy };
    const t = q['raise' + s] * Math.PI / 180, u = [sign * Math.sin(t), Math.cos(t)];
    const el = { x: sh.x + u[0] * 0.45, y: sh.y + u[1] * 0.45 };
    const r = q['bend' + s] * sign * (180 - q['angle' + s]) * Math.PI / 180;
    const wr = { x: el.x + (u[0] * Math.cos(r) - u[1] * Math.sin(r)) * 0.4, y: el.y + (u[0] * Math.sin(r) + u[1] * Math.cos(r)) * 0.4 };
    const hip = { x: sign * 0.15, y: hy }, lift = q['knee' + s], footX = hip.x + sign * q['foot' + s];
    let knee, ankle;
    if (lift > 0.02) {   // the thigh swings out as far as its length allows; the shin hangs from the knee, tucked in by foot
      const down = 0.5 - lift, out = Math.min(q['out' + s], Math.sqrt(Math.max(0, 0.25 - down * down)));
      knee = { x: hip.x + sign * out, y: hy + down };
      const dx = -sign * Math.max(0, Math.min(0.5, q['foot' + s]));
      ankle = { x: knee.x + dx, y: knee.y + Math.sqrt(0.25 - dx * dx) };
    }
    // a lift too small to clear the floor with the hips dropped is a planted foot, not a leg through the ground:
    // else a straight back leg (warrior) is drawn hanging under the hip instead of reaching out to the side
    if (!ankle || ankle.y > 2) {   // foot on the ground; a squat or a wide stance bends the knee outwards to make up the length
      const dx = footX - hip.x;
      ankle = { x: footX, y: Math.hypot(dx, 2 - hy) > 1 ? hy + Math.sqrt(Math.max(0, 1 - dx * dx)) : 2 };   // too far: foot lifts a touch
      const ay = ankle.y - hy, d = Math.hypot(dx, ay) || 1e-9, h = Math.sqrt(Math.max(0, 0.25 - d * d / 4));
      let px = -ay / d, py = dx / d;   // perpendicular to hip -> ankle, turned to point away from the body
      if (px * sign < 0) { px = -px; py = -py; }
      knee = { x: (hip.x + footX) / 2 + px * h, y: (hy + ankle.y) / 2 + py * h };
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

// u: in torso lengths as seen, like u() in features.py, so a fold (a shorter torso on screen) scales them up
function figFeatures(q, P) {
  const f = {}, sx = (P.sL.x + P.sR.x) / 2, hipY = (P.hL.y + P.hR.y) / 2;
  const torso = Math.hypot(sx - (P.hL.x + P.hR.x) / 2, P.sL.y - hipY) || 1e-6, u = v => v / torso;
  for (const [side, s, sign] of [['left', 'L', -1], ['right', 'R', 1]]) {
    const sh = P['s' + s], el = P['e' + s], wr = P['w' + s];
    f[side + '_arm_raise'] = figAngle({ x: sh.x, y: sh.y + 1 }, sh, el);
    f[side + '_arm_angle'] = figAngle(sh, el, wr);
    f[side + '_wrist_out'] = u(sign * (wr.x - sh.x));
    f[side + '_wrist_up'] = u(sh.y - wr.y);
    f[side + '_knee_angle'] = figAngle(P['h' + s], P['k' + s], P['a' + s]);
    f[side + '_knee_out'] = u(sign * (P['k' + s].x - P['h' + s].x));
  }
  f.wrists_distance = u(Math.hypot(P.wL.x - P.wR.x, P.wL.y - P.wR.y));
  f.wrist_low = u(Math.max(P.wL.y, P.wR.y) - hipY);
  f.lean = u(sx - (P.hL.x + P.hR.x) / 2);
  f.head_tilt = u(P.nose.x - sx);
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
  // fold only when nothing else will do: a shorter torso scales up every torso-length feature, so a slight bow would
  // otherwise stand in for raising the arms higher
  return cost + 0.2 * q.fold;
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

// From the resting pose, once per elbow-bend direction; keep the cheapest. Hands together overhead (steeple, crescent)
// can't be reached from arms down, one step at a time, so a miss tries again from arms up. Likewise a straight leg
// reaching out to the side (warrior): spreading the foot alone bends the knee, so it needs the hips dropped with it.
const FIG_ARMS_UP = { raiseL: 170, raiseR: 170, angleL: 120, angleR: 120 };
const FIG_WIDE = { footL: 0.5, footR: 0.5, drop: 0.15 };
// anyFit: the first figure that meets every condition, not the most relaxed one; enough to know a body can hold them
function solveFigure(conds, anyFit = false) {
  let best = null, bestCost = Infinity;
  for (const start of [{}, FIG_ARMS_UP, FIG_WIDE]) {
    for (const bendL of [1, -1]) for (const bendR of [1, -1]) {
      const q = { ...FIG_REST, ...start, bendL, bendR };
      const cur = figSearch(q, Object.keys(FIG_BOUNDS), q => figCost(q, conds));
      if (cur < bestCost) { bestCost = cur; best = q; }
      if (anyFit && !figUnmet(conds, best).length) return best;
    }
    if (!figUnmet(conds, best).length) break;
  }
  return best;
}

// ---------- sweep: move the highlighted parts through the whole range the conditions allow ----------
// For each conditioned feature, push the figure to its lowest then highest value that still meets every
// condition, moving only the highlighted parts, and tween base -> low -> high -> base.
const FIG_KEYS = { armL: ['raiseL', 'angleL'], armR: ['raiseR', 'angleR'], torso: ['lean', 'drop', 'fold'], head: ['tilt'],
                   legL: ['kneeL', 'drop', 'footL', 'outL'], legR: ['kneeR', 'drop', 'footR', 'outR'] };
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
  // an arm with a motion arrow (swipe, punch, clap) holds still: sweeping its position range would read as the move
  // itself, a swipe out drawn as a raise overhead
  const moving = new Set(conds.filter(c => /_(wrist_v[xy]|punch)$/.test(c.feature) || c.feature === 'clap').flatMap(c => figParts(c.feature)));
  for (const f of new Set(conds.map(c => c.feature))) {
    if (FIG_STILL.includes(f) || figParts(f).some(p => moving.has(p)) || figFeatures(q, figBody(q))[f] === undefined) continue;
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

// conditions + caption -> svg. Loading a group redraws every pose card, and the library and clash panel draw the same
// presets again; solving each takes up to a few hundred ms. Cleared when it gets big (dragging a slider adds one a step).
const figSVGs = new Map();
function figureSVG(conds, caption = true) {
  if (!conds.length || !Object.keys(info).length) return '';
  const k = caption + JSON.stringify(conds);
  if (!figSVGs.has(k)) {
    if (figSVGs.size > 500) figSVGs.clear();
    figSVGs.set(k, drawFigure(conds, caption));
  }
  return figSVGs.get(k);
}

function drawFigure(conds, caption) {
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
    `${s.feature.replace(/_/g, ' ')} ${fmt(s.lo)}–${fmtU(s.feature, s.hi)}`).join(', ')}</div>` : '';
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

// a range in the pose cards' words: "hip rise > 0.20 t", "65° < right arm raise < 106°"
function rangeText(f, [lo, hi]) {
  const name = f.replace(/_/g, ' ');
  if (lo > -Infinity && hi < Infinity) return `${fmtU(f, lo)} < ${name} < ${fmtU(f, hi)}`;
  return lo > -Infinity ? `${name} > ${fmtU(f, lo)}` : `${name} < ${fmtU(f, hi)}`;
}

// Features on the same arm or leg move together (raise an arm and the wrist rises), so they count as one group.
const clashGroups = f => f.includes('knee') ? [f.startsWith('left_') ? 'legL' : 'legR'] : f.startsWith('left_') ? ['armL'] : f.startsWith('right_') ? ['armR']
  : f.startsWith('wrist') || f === 'clap' ? ['armL', 'armR'] : [f];
const poseGroups = p => new Set(p.conditions.flatMap(c => clashGroups(c.feature)));

// Each overlapping pair needs a figure solved to know a body can hold it: hundreds of pairs, tens of seconds, for a
// big group. So the search runs a slice at a time between frames, and the page stays usable; a newer run (after an
// edit) supersedes it. Whether a body can hold a set of conditions is remembered, so a rerun after an edit is quick.
let clashRun = 0;
const clashFits = new Map();   // conditions JSON -> a body can hold them
const pause = () => new Promise(r => setTimeout(r));

// Poses on unrelated body parts (jog + raise arm) firing together is a combo, not a clash: only pairs
// sharing a feature group are checked. Returns { clashes, combos } where combos counts the skipped pairs,
// or null if a newer run started meanwhile.
async function findClashes(run) {
  const live = poses.filter(p => p.enabled !== false && p.conditions.length);
  const out = [];
  let combos = 0, slice = performance.now();
  for (let i = 0; i < live.length; i++) for (const b of live.slice(i + 1)) {
    const a = live[i];
    if (a.key === b.key) continue;
    const ga = poseGroups(a);
    if (![...poseGroups(b)].some(g => ga.has(g))) { combos++; continue; }
    const A = poseBox(a), B = poseBox(b), both = {};
    let apart = false;
    for (const f of new Set([...Object.keys(A), ...Object.keys(B)])) {
      const ra = A[f] || [-Infinity, Infinity], rb = B[f] || [-Infinity, Infinity];
      both[f] = [Math.max(ra[0], rb[0]), Math.min(ra[1], rb[1])];
      if (both[f][0] >= both[f][1]) { apart = true; break; }
    }
    if (apart) continue;
    const conds = [...a.conditions, ...b.conditions], k = JSON.stringify(conds);
    if (!clashFits.has(k)) {
      if (performance.now() - slice > 30) { await pause(); slice = performance.now(); if (run !== clashRun) return null; }
      clashFits.set(k, !figUnmet(conds, solveFigure(conds, true)).length);
    }
    if (!clashFits.get(k)) continue;   // ranges overlap but no body can hold it
    const kind = boxWithin(A, B) && boxWithin(B, A) ? 'same' : boxWithin(B, A) ? 'b-in-a' : boxWithin(A, B) ? 'a-in-b' : 'overlap';
    out.push({ a, b, kind, both, conds });
  }
  out.sort((x, y) => KIND_RANK[x.kind] - KIND_RANK[y.kind]);   // stable: list order within a kind
  return { clashes: out, combos };
}

const poseLabel = p => `<b>${esc(p.name)}</b> <span class="small">(${esc(p.key)})</span>`;
// worst first: one pose always firing the other before a partial overlap
const KIND_RANK = { same: 0, 'b-in-a': 1, 'a-in-b': 1, overlap: 2 };

// Clashes marked fine (expected, or harmless in play), by pose-name pair, saved in the config as clashes_ok. They stay
// listed, dimmed, but don't count: the button only warns about clashes nobody has looked at.
let clashOk = new Set(), clashOkWant = null, clashOkAt = 0;
const pairKey = (a, b) => JSON.stringify([a.name, b.name].sort());
const isOk = c => clashOk.has(pairKey(c.a, c.b));
const okSig = keys => JSON.stringify([...keys].sort());
// from each broadcast; like send keys, our own change wins over the broadcasts still in flight from before it
function takeClashOk(list) {
  const incoming = (list || []).map(p => JSON.stringify([...p].sort()));
  if (clashOkWant !== null && okSig(incoming) !== clashOkWant && performance.now() - clashOkAt < 1000) return;
  clashOkWant = null;
  if (okSig(incoming) === okSig(clashOk)) return;
  clashOk = new Set(incoming); showClashCount(); drawClashList();
}
function setClashOk(c, ok) {
  if (ok) clashOk.add(pairKey(c.a, c.b)); else clashOk.delete(pairKey(c.a, c.b));
  clashOkWant = okSig(clashOk); clashOkAt = performance.now();
  send({ type: 'config', config: { clashes_ok: [...clashOk].map(k => JSON.parse(k)) } });
  showClashCount(); drawClashList();
}

let clashes = null;   // the latest search's result, drawn when the panel opens
async function renderClashes() {
  const btn = document.getElementById('clashBtn'), run = ++clashRun;
  if (!Object.keys(info).length) { clashes = null; document.getElementById('clashes').innerHTML = ''; return; }
  btn.textContent = 'clashes (…)';
  const found = await findClashes(run);
  if (!found) return;
  clashes = found;
  showClashCount();
  drawClashList();
}
// counts only the clashes not marked fine; none left reads as a plain button
function showClashCount() {
  if (!clashes) return;
  const btn = document.getElementById('clashBtn'), n = clashes.clashes.filter(c => !isOk(c)).length;
  btn.textContent = n ? `clashes (${n})` : 'clashes';
  btn.classList.toggle('warn', n > 0);
}

// Only while the panel is open, and the figures a few at a time after the text: a big group has 150-odd clashes.
let clashDraw = 0;
async function drawClashList() {
  const root = document.getElementById('clashes'), draw = ++clashDraw;
  if (!clashes || !document.getElementById('clashPanel').classList.contains('open')) return;
  const { combos } = clashes, list = [...clashes.clashes.filter(c => !isOk(c)), ...clashes.clashes.filter(isOk)];
  const note = combos ? ` ${combos} pair${combos > 1 ? 's' : ''} on separate body parts can combine (e.g. jog + arm raise); not shown.` : '';
  if (!list.length) { root.innerHTML = `<p class="small">No clashes: no two poses on the same body part fire together.${note}</p>`; return; }
  root.innerHTML = `<p class="small">Poses on the same body part that can fire at once, worst first. Mark one <b>fine</b> if it's
    expected or harmless in play: it stays here, dimmed, and stops counting.${note}</p>` + list.map(c => {
    const { a, b, kind, both } = c, ok = isOk(c);
    const where = `<ul>${Object.entries(both).map(([f, r]) => `<li>${rangeText(f, r)}</li>`).join('')}</ul>`;
    const text = kind === 'same' ? `${poseLabel(a)} and ${poseLabel(b)} have the same conditions: they always fire together.`
      : kind === 'b-in-a' ? `Every ${poseLabel(b)} also fires ${poseLabel(a)}.`
      : kind === 'a-in-b' ? `Every ${poseLabel(a)} also fires ${poseLabel(b)}.`
      : `${poseLabel(a)} and ${poseLabel(b)} both fire when:${where}`;
    return `<div class="clash ${ok ? 'ok' : ''}"><div class="fig"></div><div>${text}</div>
      <button class="mark" title="${ok ? 'count this clash again' : 'expected or harmless in play: dim it and stop counting it'}">${ok ? 'not fine' : 'fine'}</button></div>`;
  }).join('');
  root.querySelectorAll('.clash .mark').forEach((btn, i) => btn.onclick = () => setClashOk(list[i], !isOk(list[i])));
  const figs = root.querySelectorAll('.clash .fig');
  let slice = performance.now();
  for (let i = 0; i < list.length; i++) {
    if (performance.now() - slice > 30) { await pause(); slice = performance.now(); if (draw !== clashDraw) return; }
    figs[i].innerHTML = figureSVG(list[i].conds, false);
  }
}

let clashFrame = null;
function scheduleClashes() {
  if (clashFrame) return;
  clashFrame = requestAnimationFrame(() => { clashFrame = null; renderClashes(); });
}
