// Loaded before the main script in index.html. Uses its globals (poses, info, esc, renderPoses, scheduleSave) and
// figure.js's figureSVG at call time.
// ---------- preset library: tested/untested presets, and groups of them to load as the active poses ----------
// The library is edited here and sent whole to the server (PUT /library), which validates and saves it.
// Built-in presets and groups (builtin: true) ship with the app and are read-only: use, clone, or put them in your
// own groups. Running from source (lib.edit_builtins) they're editable, to tune them before shipping.
// Active poses remember the preset they came from (pose.preset), so tuning one live can be saved back to it.
// A group is a setup for one game or class: its presets, plus keys overriding their default keys (g.keys).
// Keys are bindings, not tuning: they aren't compared or saved back to the preset from a pose card.
let lib = { presets: [], groups: [], edit_builtins: false };
const editable = x => !x.builtin || lib.edit_builtins;
const libView = { status: 'all', group: '', search: '' };
const picked = new Set();   // preset names ticked in the panel, for "group selected"
const TUNE_FIELDS = ['conditions', 'margin', 'enabled', 'hold', 'delay'];
const copy = o => JSON.parse(JSON.stringify(o));
const poseFields = p => Object.fromEntries(TUNE_FIELDS.map(k => [k, copy(p[k])]));
const presetOf = name => name ? lib.presets.find(p => p.name === name) : undefined;
const figCache = new Map();   // conditions JSON -> svg: solving 40-odd figures on every filter keystroke is slow
function presetFigure(conds) {
  const k = JSON.stringify(conds);
  if (!figCache.has(k)) {
    const svg = figureSVG(conds, false);
    if (!svg) return '';   // feature info not in yet
    figCache.set(k, svg);
  }
  return figCache.get(k);
}

function uniqueName(base, taken) {
  if (!taken.includes(base)) return base;
  for (let n = 2; ; n++) if (!taken.includes(`${base} ${n}`)) return `${base} ${n}`;
}

async function loadLibrary() {
  const r = await fetch('/library');
  if (r.ok) lib = await r.json();
  renderLibrary(); renderPoses();
}

let libSaving = Promise.resolve();
function saveLibrary() {
  renderLibrary(); updatePresetBadges();
  const body = JSON.stringify(lib);
  libSaving = libSaving.then(() => fetch('/library', { method: 'PUT', body })).then(r => r.json()).then(j => {
    if (!j.ok) { alert('library not saved: ' + j.error); loadLibrary(); }
  });
}

// ---------- actions ----------
const poseFromPreset = (pr, key) => ({ name: pr.name, key: key || pr.key, ...poseFields(pr), preset: pr.name });

// keys: a group's bindings, preset name -> key, over each preset's default key
function usePresets(names, replace, keys = {}) {
  const add = names.map(presetOf).filter(Boolean).map(pr => poseFromPreset(pr, keys[pr.name]));
  if (replace) {
    if (poses.length && !confirm(`Replace your ${poses.length} active poses with these ${add.length}?`)) return;
    if (capture) endCapture();
    showUndo(null);   // undoing a delete from the old set would mix it into the new one
    poses.length = 0;
  }
  poses.push(...add);
  renderPoses(); scheduleSave(); renderLibrary();
}

function newPreset() {
  const name = uniqueName('new preset', lib.presets.map(p => p.name));
  const pr = { name, status: 'untested', notes: '', builtin: false, key: '1', conditions: [{ feature: 'right_arm_raise', op: '>', value: 90 }],
               margin: 0.1, enabled: true, hold: 0, delay: 0 };
  lib.presets.push(pr);
  saveLibrary(); usePresets([name], false);   // straight into the active poses: conditions get tuned live
}

function clonePreset(pr) {
  const c = { ...copy(pr), name: uniqueName(`${pr.name} copy`, lib.presets.map(p => p.name)), status: 'untested', builtin: false };
  lib.presets.splice(lib.presets.indexOf(pr) + 1, 0, c);
  saveLibrary();
}

function renamePreset(pr, name) {
  name = name.trim();
  if (!name || name === pr.name) return renderLibrary();
  if (presetOf(name)) { alert(`there is already a preset named "${name}"`); return renderLibrary(); }
  for (const g of lib.groups) {
    g.presets = g.presets.map(n => n === pr.name ? name : n);
    if (pr.name in g.keys) { g.keys[name] = g.keys[pr.name]; delete g.keys[pr.name]; }
  }
  poses.forEach(p => { if (p.preset === pr.name) p.preset = name; });
  pr.name = name;
  saveLibrary(); scheduleSave();
}

function deletePreset(pr) {
  if (!confirm(`Delete preset "${pr.name}"? Active poses made from it stay.`)) return;
  lib.presets.splice(lib.presets.indexOf(pr), 1);
  for (const g of lib.groups) removeFromGroup(g, pr.name);
  poses.forEach(p => { if (p.preset === pr.name) p.preset = ''; });
  saveLibrary(); scheduleSave();
}

// An active pose's conditions and timings into its preset. A pose with no preset, or tuned from a locked built-in,
// becomes a new untested preset of yours (keeping the built-in's notes, and the pose's key as its default key).
function savePoseToLibrary(p) {
  let pr = presetOf(p.preset);
  if (pr && editable(pr)) Object.assign(pr, poseFields(p));
  else {
    const name = uniqueName(pr ? `${pr.name} tuned` : p.name, lib.presets.map(x => x.name));
    pr = { name, status: 'untested', notes: pr ? pr.notes : '', builtin: false, key: p.key, ...poseFields(p) };
    lib.presets.push(pr);
    p.preset = pr.name; scheduleSave();
  }
  saveLibrary();
}

function addGroup(base, members, keys = {}) {
  lib.groups.push({ name: uniqueName(base, lib.groups.map(g => g.name)), notes: '', presets: members, keys, builtin: false });
  saveLibrary();
}

// The active poses' presets, with the keys they're bound to now: save a setup tuned for a game as a group.
function groupFromActive() {
  const linked = poses.filter(p => presetOf(p.preset)), keys = {};
  if (linked.length < poses.length) alert(`${poses.length - linked.length} active poses aren't in the library and were left out: use "→ library" on them first.`);
  for (const p of linked) if (p.key !== presetOf(p.preset).key) keys[p.preset] = p.key;
  addGroup('my setup', [...new Set(linked.map(p => p.preset))], keys);
}

function cloneGroup(g) {
  lib.groups.splice(lib.groups.indexOf(g) + 1, 0, { ...copy(g), name: uniqueName(`${g.name} copy`, lib.groups.map(x => x.name)), builtin: false });
  saveLibrary();
}

function removeFromGroup(g, name) {
  g.presets = g.presets.filter(n => n !== name);
  delete g.keys[name];
}

function renameGroup(g, name) {
  name = name.trim();
  if (!name || name === g.name) return renderLibrary();
  if (lib.groups.some(x => x.name === name)) { alert(`there is already a group named "${name}"`); return renderLibrary(); }
  if (libView.group === g.name) libView.group = name;
  g.name = name; saveLibrary();
}

// ---------- active pose cards: library status badge and save-back button ----------
// tested / untested / changed (tuned since last saved to its preset) / not in library
function presetBadge(p) {
  const pr = presetOf(p.preset);
  if (!pr) return { cls: 'none', text: 'not in library', tip: '→ library saves it as a new untested preset' };
  if (JSON.stringify(poseFields(p)) !== JSON.stringify(poseFields(pr)))
    return { cls: 'changed', text: `${pr.status}, changed`, tip: editable(pr) ? `differs from preset "${pr.name}": → library saves the changes into it`
                                                                             : `differs from built-in "${pr.name}": → library saves it as your own preset` };
  if (!editable(pr)) return { cls: pr.status, text: `${pr.status}, built-in`, tip: `built-in preset "${pr.name}": tune it and → library saves your own copy` };
  return { cls: pr.status, text: pr.status, tip: `preset "${pr.name}": click to mark ${pr.status === 'tested' ? 'untested' : 'tested'}` };
}

function updatePresetBadges() {
  document.querySelectorAll('.pose').forEach(div => {
    const p = poses[div.dataset.i], el = div.querySelector('.badge'); if (!p || !el) return;
    const b = presetBadge(p);
    el.className = 'badge ' + b.cls; el.textContent = b.text; el.title = b.tip;
  });
}

function wirePresetControls(div, p) {
  div.querySelector('.badge').onclick = () => {
    const pr = presetOf(p.preset);
    if (!pr || !editable(pr) || presetBadge(p).cls === 'changed') return;
    pr.status = pr.status === 'tested' ? 'untested' : 'tested'; saveLibrary();
  };
  div.querySelector('.tolib').onclick = () => savePoseToLibrary(p);
}

// ---------- panel ----------
function renderLibrary() {
  const root = document.getElementById('library');
  if (!root || !document.getElementById('libPanel').classList.contains('open')) return;
  const counts = { tested: 0, untested: 0 };
  lib.presets.forEach(p => counts[p.status]++);
  const inUse = new Set(poses.map(p => p.preset));
  const grp = lib.groups.find(g => g.name === libView.group);
  const q = libView.search.toLowerCase();
  const VIEWS = { all: () => true, tested: p => p.status === 'tested', untested: p => p.status === 'untested', 'built-in': p => p.builtin, mine: p => !p.builtin };
  const shown = lib.presets.filter(p => VIEWS[libView.status](p)
    && (!grp || grp.presets.includes(p.name)) && (!q || (p.name + ' ' + p.notes).toLowerCase().includes(q)));

  root.innerHTML = `
    <h2>Groups</h2>
    <p class="small">A group is a setup for a game or class: its poses and the key each one presses there (blank = the preset's own key).
      <b>load</b> replaces the active poses with the group; <b>add</b> appends it. ${lib.edit_builtins
      ? 'Running from source: built-ins are editable here, and changes go into the shipped <code>presets.yaml</code>.'
      : 'Built-ins are locked: <b>clone</b> one to make your own.'}</p>
    <div class="groups"></div>
    <div class="bar"><button class="ng">+ empty group</button><button class="na" title="A group of the presets behind the active poses, with the keys they're bound to now">+ group from active poses</button></div>
    <h2>Presets <span class="small">${counts.tested} tested, ${counts.untested} untested</span></h2>
    <div class="bar">
      <select class="fs">${['all', 'tested', 'untested', 'built-in', 'mine'].map(s => `<option ${s === libView.status ? 'selected' : ''}>${s}</option>`).join('')}</select>
      <select class="fg"><option value="">any group</option>${lib.groups.map(g => `<option ${g.name === libView.group ? 'selected' : ''}>${esc(g.name)}</option>`).join('')}</select>
      <input class="fq" placeholder="search" value="${esc(libView.search)}">
      <button class="primary np" title="New untested preset, also added to the active poses for tuning">+ new preset</button>
    </div>
    ${picked.size ? `<div class="bar"><span class="small">${picked.size} ticked</span><button class="primary gp">+ group from ticked</button><button class="pc">clear</button></div>` : ''}
    <p class="small"><b>use</b> adds a preset to the active poses. Tune it there with the live values, then <b>→ library</b> on the pose saves it back.</p>
    <div class="presets"></div>`;
  root.querySelector('.ng').onclick = () => addGroup('new group', []);
  root.querySelector('.na').onclick = groupFromActive;
  if (picked.size) {
    root.querySelector('.gp').onclick = () => { addGroup('new group', lib.presets.map(p => p.name).filter(n => picked.has(n))); picked.clear(); renderLibrary(); };
    root.querySelector('.pc').onclick = () => { picked.clear(); renderLibrary(); };
  }
  root.querySelector('.np').onclick = newPreset;
  root.querySelector('.fs').onchange = e => { libView.status = e.target.value; renderLibrary(); };
  root.querySelector('.fg').onchange = e => { libView.group = e.target.value; renderLibrary(); };
  const fq = root.querySelector('.fq');
  fq.oninput = e => { libView.search = e.target.value; renderLibrary(); const f = document.querySelector('#library .fq'); f.focus(); f.setSelectionRange(f.value.length, f.value.length); };

  const gs = root.querySelector('.groups');
  for (const g of lib.groups) {
    const el = document.createElement('div');
    el.className = 'group';
    const untested = g.presets.filter(n => presetOf(n).status === 'untested').length;
    const ed = editable(g);
    el.innerHTML = `
      <div class="pose-head">
        ${ed ? `<input class="name" value="${esc(g.name)}" title="group name">` : `<b class="name">${esc(g.name)}</b>`}
        ${g.builtin ? '<span class="tag">built-in</span>' : ''}
        <span class="small">${g.presets.length} poses${untested ? `, ${untested} untested` : ''}</span>
        <button class="load primary">load</button><button class="add">add</button><button class="cl">clone</button>${ed ? '<button class="danger del">delete</button>' : ''}
      </div>
      ${ed ? `<textarea class="notes" rows="1" placeholder="notes: game, class, what each key does">${esc(g.notes)}</textarea>` : g.notes ? `<p class="small">${esc(g.notes)}</p>` : ''}
      <div class="chips">${g.presets.map(n => {
        const k = g.keys[n] || '', def = presetOf(n).key;
        return `<span class="chip ${presetOf(n).status}">${esc(n)}${ed
          ? `<input class="gk" data-n="${esc(n)}" value="${esc(k)}" placeholder="${esc(def)}" title="key in this group: click, then press it. Backspace clears it (blank = preset's ${esc(def)})."><button data-n="${esc(n)}" title="remove from group">×</button>`
          : ` <code>${esc(k || def)}</code>`}</span>`;
      }).join('')}</div>`;
    el.querySelector('.load').onclick = () => usePresets(g.presets, true, g.keys);
    el.querySelector('.add').onclick = () => usePresets(g.presets, false, g.keys);
    el.querySelector('.cl').onclick = () => cloneGroup(g);
    gs.appendChild(el);
    if (!ed) continue;
    el.querySelector('.name').onchange = e => renameGroup(g, e.target.value);
    el.querySelector('.del').onclick = () => {
      if (!confirm(`Delete group "${g.name}"? Its presets stay.`)) return;
      lib.groups.splice(lib.groups.indexOf(g), 1);
      if (libView.group === g.name) libView.group = '';
      saveLibrary();
    };
    el.querySelector('.notes').onchange = e => { g.notes = e.target.value; saveLibrary(); };
    el.querySelectorAll('.chip button').forEach(b => b.onclick = () => { removeFromGroup(g, b.dataset.n); saveLibrary(); });
    el.querySelectorAll('.chip .gk').forEach(i => keyField(i, k => {
      if (k && k !== presetOf(i.dataset.n).key) g.keys[i.dataset.n] = k; else delete g.keys[i.dataset.n];
      saveLibrary();
    }, true));
  }

  const ps = root.querySelector('.presets');
  for (const pr of shown) {
    const el = document.createElement('div');
    el.className = 'preset ' + pr.status;
    const ed = editable(pr);
    const member = lib.groups.filter(g => g.presets.includes(pr.name)), others = lib.groups.filter(g => editable(g) && !member.includes(g));
    el.innerHTML = `
      <div class="fig">${presetFigure(pr.conditions)}</div>
      <div>
        <div class="pose-head">
          <input type="checkbox" class="pick" title="tick presets, then + group from ticked" ${picked.has(pr.name) ? 'checked' : ''}>${ed ? `
          <input class="name" value="${esc(pr.name)}" title="preset name">
          <select class="st" title="flip to tested once it works in a drill">${['tested', 'untested'].map(s => `<option ${s === pr.status ? 'selected' : ''}>${s}</option>`).join('')}</select>
          <span class="small">default key</span><input class="key" value="${esc(pr.key)}" title="click, then press the key: space, f1, left shift... Letters, digits and names the browser can't capture (tab, num_lock): type, then Enter. Esc while typing cancels. Groups can bind it to another key.">` : `
          <b class="name">${esc(pr.name)}</b><span class="badge ${pr.status}">${pr.status}</span>
          <span class="small">default key <code>${esc(pr.key)}</code></span>`}
          ${pr.builtin ? '<span class="tag">built-in</span>' : ''}
        </div>
        ${ed ? `<textarea class="notes" rows="2" placeholder="how to do it">${esc(pr.notes)}</textarea>` : `<p class="small notes">${esc(pr.notes)}</p>`}
        <div class="chips">${member.map(g => `<span class="chip">${esc(g.name)}${editable(g) ? `<button data-g="${esc(g.name)}" title="remove from group">×</button>` : ''}</span>`).join('')}
          ${others.length ? `<select class="tog"><option value="">+ group…</option>${others.map(g => `<option>${esc(g.name)}</option>`).join('')}</select>` : ''}</div>
        <div class="bar">
          <button class="use primary">use</button>${inUse.has(pr.name) ? '<span class="small">in active poses</span>' : ''}
          <button class="cl">clone</button>${ed ? '<button class="danger del">delete</button>' : ''}
          <span class="small">${pr.conditions.length} conditions${pr.delay ? `, delay ${pr.delay}s` : ''}${pr.hold ? `, hold ${pr.hold}s` : ''}</span>
        </div>
      </div>`;
    el.querySelector('.pick').onchange = e => { if (e.target.checked) picked.add(pr.name); else picked.delete(pr.name); renderLibrary(); };
    el.querySelectorAll('.chips button').forEach(b => b.onclick = () => { removeFromGroup(lib.groups.find(x => x.name === b.dataset.g), pr.name); saveLibrary(); });
    const tog = el.querySelector('.tog');
    if (tog) tog.onchange = e => { lib.groups.find(g => g.name === e.target.value).presets.push(pr.name); saveLibrary(); };
    el.querySelector('.use').onclick = () => usePresets([pr.name], false);
    el.querySelector('.cl').onclick = () => clonePreset(pr);
    ps.appendChild(el);
    if (!ed) continue;
    el.querySelector('.name').onchange = e => renamePreset(pr, e.target.value);
    el.querySelector('.st').onchange = e => { pr.status = e.target.value; saveLibrary(); };
    keyField(el.querySelector('.key'), k => { pr.key = k; saveLibrary(); });
    el.querySelector('.notes').onchange = e => { pr.notes = e.target.value; saveLibrary(); };
    el.querySelector('.del').onclick = () => deletePreset(pr);
  }
  if (!shown.length) ps.innerHTML = '<p class="small">No presets match.</p>';
}
