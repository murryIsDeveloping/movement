// Loaded before the main script in index.html. Uses its globals (poses, info, live, state, rangeOf, esc) at call time.
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

function figCost(q, conds) {
  const f = figFeatures(q, figBody(q));
  let cost = 0;
  for (const c of conds) {
    const v = f[c.feature]; if (v === undefined) continue;
    const [lo, hi] = rangeOf(c.feature), m = FIG_MARGIN[(info[c.feature] || {}).unit] ?? 0.08;
    cost += Math.max(0, c.op === '>' ? c.value + m - v : v - (c.value - m)) / (hi - lo);
  }
  for (const [k, [lo, hi]] of Object.entries(FIG_BOUNDS)) cost += 0.02 * ((q[k] - FIG_REST[k]) / (hi - lo)) ** 2;
  return cost;
}

// Pattern search from the resting pose, once per elbow-bend direction; keep the cheapest.
function solveFigure(conds) {
  let best = null, bestCost = Infinity;
  for (const bendL of [1, -1]) for (const bendR of [1, -1]) {
    const q = { ...FIG_REST, bendL, bendR }, step = {};
    for (const [k, [lo, hi]] of Object.entries(FIG_BOUNDS)) step[k] = (hi - lo) / 4;
    let cur = figCost(q, conds);
    for (let halvings = 0; halvings < 9;) {
      let improved = false;
      for (const [k, [lo, hi]] of Object.entries(FIG_BOUNDS)) for (const d of [1, -1]) {
        const old = q[k];
        q[k] = Math.max(lo, Math.min(hi, old + d * step[k]));
        const c = figCost(q, conds);
        if (c < cur - 1e-9) { cur = c; improved = true; } else q[k] = old;
      }
      if (!improved) { for (const k in step) step[k] /= 2; halvings++; }
    }
    if (cur < bestCost) { bestCost = cur; best = q; }
  }
  return best;
}

function figUnmet(conds, q) {
  const f = figFeatures(q, figBody(q));
  return conds.filter(c => f[c.feature] !== undefined && !(c.op === '>' ? f[c.feature] > c.value : f[c.feature] < c.value));
}

function figureSVG(conds, caption = true) {
  if (!conds.length || !Object.keys(info).length) return '';
  const q = solveFigure(conds), unmet = figUnmet(conds, q);
  const hl = new Set(conds.flatMap(c => figParts(c.feature)));
  const ln = (a, b, part) => `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" class="${hl.has(part) ? 'hl' : ''}"/>`;
  const legs = P => ln(P.hL, P.kL, 'legL') + ln(P.kL, P.aL, 'legL') + ln(P.hR, P.kR, 'legR') + ln(P.kR, P.aR, 'legR')
    + [P.kL, P.aL, P.kR, P.aR].map(j => `<circle cx="${j.x}" cy="${j.y}" r=".05"/>`).join('');
  const P = figBody(q);
  const sc = { x: (P.sL.x + P.sR.x) / 2, y: P.sL.y }, hc = { x: 0, y: P.hL.y };
  const upper = ln(P.sL, P.sR, 'torso') + ln(P.hL, P.hR, 'torso') + ln(sc, hc, 'torso')
    + ln(P.sL, P.eL, 'armL') + ln(P.eL, P.wL, 'armL') + ln(P.sR, P.eR, 'armR') + ln(P.eR, P.wR, 'armR')
    + [P.sL, P.sR, P.eL, P.eR, P.wL, P.wR, P.hL, P.hR].map(j => `<circle cx="${j.x}" cy="${j.y}" r=".05"/>`).join('')
    + `<circle class="head ${hl.has('head') ? 'hl' : ''}" cx="${P.nose.x}" cy="${P.nose.y - 0.05}" r=".17"/>`;
  let lower = legs(P);
  if (q.cadence > 0.2) {   // jog: alternate a lifted knee at the required step rate
    const dur = `--dur:${(2 / q.cadence).toFixed(2)}s`;
    lower = `<g class="jogA" style="${dur}">${legs(figBody({ ...q, kneeL: Math.max(q.kneeL, 0.35) }))}</g>`
          + `<g class="jogB" style="${dur}">${legs(figBody({ ...q, kneeR: Math.max(q.kneeR, 0.35) }))}</g>`;
  }
  let body = upper + lower + motionArrows(conds, P);
  if (q.rise > 0.05) body = `<g class="hop" style="--h:${-q.rise}px">${body}</g>`;
  const svg = `<svg viewBox="-1.4 -2 2.8 4.2"><line class="ground" x1="-1.3" y1="2.05" x2="1.3" y2="2.05"/>${body}</svg>`;
  if (!caption) return svg;
  const tip = unmet.length ? `<div class="unmet">can't all hold at once: ${unmet.map(c => `${c.feature} ${c.op} ${c.value}`).join(', ')}</div>` : '';
  return `${svg}<div class="small">as seen in preview</div>${tip}`;
}

// Speed conditions (swipe, punch, clap) aren't positions: draw them as an arrow from the wrist.
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
  let out = '';
  for (const [s, [dx, dy]] of Object.entries(dir)) {
    const n = Math.hypot(dx, dy); if (!n) continue;
    const w = P['w' + s], ux = dx / n, uy = dy / n, e = { x: w.x + ux * 0.55, y: w.y + uy * 0.55 };
    const head = a => ({ x: e.x - 0.18 * (ux * Math.cos(a) - uy * Math.sin(a)), y: e.y - 0.18 * (ux * Math.sin(a) + uy * Math.cos(a)) });
    out += [[w, e], [e, head(0.5)], [e, head(-0.5)]].map(([a, b]) => `<line class="mv" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"/>`).join('');
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
