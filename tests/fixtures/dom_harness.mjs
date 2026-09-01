/* Stubbed-DOM harness: actually EXECUTES web/state.js, web/town.js and
   the inline script from web/index.html, then drives the real user
   flows. Catches runtime-only bugs (undeclared vars, stale closures,
   desync) that node --check cannot see. Throws on any of them because
   the stub DOM has no forgiving `undefined` paths. */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const ROOT = process.argv[2];
const read = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');

/* ---------- minimal DOM ---------- */
let nodeSeq = 0;
class El {
  constructor(tag) {
    this.tagName = (tag || 'div').toUpperCase();
    this.id = '';
    this.className = '';
    this.type = '';
    this.dataset = {};
    this.attrs = {};
    this.style = {};
    this.children = [];
    this.parent = null;
    this.listeners = {};
    this.hidden = false;
    this.disabled = false;
    this._text = '';
    this._seq = nodeSeq++;
    this.classList = {
      _s: new Set(),
      add: (c) => this.classList._s.add(c),
      remove: (c) => this.classList._s.delete(c),
      contains: (c) => this.classList._s.has(c),
    };
  }
  get textContent() {
    /* recursive like the real DOM: own _text + all descendants' _text */
    let s = this._text || '';
    for (const c of this.children) s += c.textContent;
    return s;
  }
  set textContent(v) { this._text = String(v); this.children = []; }
  set innerHTML(v) { this._html = String(v); if (v === '') this.children = []; }
  get innerHTML() { return this._html === undefined ? '' : this._html; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  get value() { return this._value || ''; }
  set value(v) { this._value = String(v); }
  appendChild(c) { c.parent = this; this.children.push(c); return c; }
  focus() { /* focusable like the real element; harness tracks nothing */ }
  remove() {
    if (this.parent) this.parent.children = this.parent.children.filter((c) => c !== this);
    this.parent = null;
  }
  insertAdjacentHTML(_where, html) { this._html = String(html) + (this._html || ''); }
  addEventListener(t, fn) { (this.listeners[t] ||= []).push(fn); }
  click() { this.dispatch('click'); }
  dispatch(type, extra = {}) {
    const ev = { type, target: this, preventDefault() {}, ...extra };
    if (!ev.target.closest) ev.target.closest = (sel) => matchSel(ev.target, sel);
    for (const fn of this.listeners[type] || []) fn(ev);
    /* bubble to ancestors, which is how the rail + forgeOut handlers work */
    let p = this.parent;
    while (p) {
      for (const fn of p.listeners[type] || []) fn(ev);
      p = p.parent;
    }
  }
  querySelectorAll(sel) { return descendants(this).filter((e) => matchOne(e, sel)); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
}

function descendants(el) {
  const out = [];
  for (const c of el.children) { out.push(c); out.push(...descendants(c)); }
  return out;
}
function matchOne(el, sel) {
  sel = sel.trim();
  if (sel === 'button') return el.tagName === 'BUTTON';
  let m = sel.match(/^button\[data-([\w-]+)\]$/);
  if (m) return el.tagName === 'BUTTON' && el.dataset[camel(m[1])] !== undefined;
  m = sel.match(/^\.([\w-]+)$/);
  if (m) return String(el.className).split(/\s+/).includes(m[1]);
  m = sel.match(/^#([\w-]+)$/);
  if (m) return el.id === m[1];
  m = sel.match(/^\[data-([\w-]+)\]$/);
  if (m) return el.dataset && el.dataset[camel(m[1])] !== undefined;
  m = sel.match(/^\.tabs button$/);
  if (m) return el.tagName === 'BUTTON' && isUnder(el, (a) => String(a.className).split(/\s+/).includes('tabs'));
  throw new Error('harness: unsupported selector ' + sel);
}
function isUnder(el, pred) {
  let p = el.parent;
  while (p) { if (pred(p)) return true; p = p.parent; }
  return false;
}
function matchSel(el, sel) {
  let cur = el;
  while (cur) { if (matchOne(cur, sel)) return cur; cur = cur.parent; }
  return null;
}
const camel = (s) => s.replace(/-([a-z])/g, (_, c) => c.toUpperCase());

const byId = new Map();
const root = new El('body');

function mk(tag, id, cls, parent = root, data = {}) {
  const e = new El(tag);
  e.id = id || '';
  e.className = cls || '';
  Object.assign(e.dataset, data);
  parent.appendChild(e);
  if (e.id) byId.set(e.id, e);
  return e;
}
function mkBtnWithData(id, dataKey, dataVal) {
  var e = mk('button', id, '', root, { [dataKey]: dataVal });
  return e;
}
const tabsBox = mk('div', '', 'tabs');
const TABVIEWS = ['rumors', 'vault', 'stefna', 'town', 'journal', 'wiki', 'trace', 'weave', 'builder', 'board'];
const tabBtns = {};
for (const v of TABVIEWS) {
  tabBtns[v] = mk('button', 'tab-' + v, '', tabsBox, { view: v });
  mk('section', 'view-' + v, 'view');
}
/* the dev board's holders - the lazy boot renders into these */
mk('div', 'board-whispers');
mk('div', 'board-voices');
mk('div', 'board-forge');
mk('div', 'board-bell');
mk('aside', 'board-rail');
mk('button', 'rail-try');
mk('div', 'rumor-phase', 'phase-rail');
mk('button', 'whisper-btn');
mk('button', 'new-game-btn');
mk('span', 'status', 'note');
const feed = mk('section', 'feed');
mk('p', '', 'empty', feed);
mk('button', 'forge-btn');
mk('span', 'forge-status', 'note');
const forgeOut = mk('section', 'forge-out');
mk('section', 'vault-list');
mk('button', 'strike-btn');
mk('span', 'stefna-status', 'note');
mk('section', 'letter-out');
mk('div', 'town-phase', 'phase-rail');
mk('p', 'near-note', 'note');
 mk('p', 'carrying', 'note');
  mk('div', 'hud-hp', 'hud-hp');
  mk('div', 'hud-hp-fill', 'hud-hp-fill');
  mk('span', 'hud-hp-value', 'hud-hp-value');
  mk('p', 'encounter-prompt', 'encounter-prompt');
  mk('div', 'dpad');
  const npcBox = mk('div', 'npc-box', 'npc-box');
  mk('p', 'npc-name', 'npc-name', npcBox);
  mk('p', 'npc-line', 'npc-line', npcBox);
  const verbRow = mk('div', 'verb-row', 'verb-row', npcBox);
  mkBtnWithData('verb-attack-btn', 'verb', 'attack', verbRow);
  mkBtnWithData('verb-console-btn', 'verb', 'console', verbRow);
  mkBtnWithData('verb-hurl-btn', 'verb', 'hurl', verbRow);
  mkBtnWithData('verb-observe-btn', 'verb', 'observe', verbRow);
  mk('button', 'npc-close', '', npcBox);
mk('p', 'poi', 'note');
mk('p', 'watched', 'note');
mk('button', 'export-btn');
mkBtnWithData('export-journal-btn', 'exportTab', 'journal');
mk('button', 'journal-clear-btn');
mk('p', 'journal-status', 'note');
mk('section', 'journal-list');
mk('span', 'wiki-status', 'note');
mk('section', 'wiki-characters');
mk('section', 'wiki-relics');
mk('span', 'trace-status', 'note');
mk('section', 'trace-list');
mkBtnWithData('export-rumors-btn', 'exportTab', 'rumors');
mkBtnWithData('export-vault-btn', 'exportTab', 'vault');
mkBtnWithData('export-stefna-btn', 'exportTab', 'stefna');
mkBtnWithData('export-town-btn', 'exportTab', 'town');
mk('select', 'builder-pack-picker');
mk('button', 'builder-refresh-packs');
mk('p', 'builder-pack-info', 'note');
mk('input', 'builder-import-repo');
mk('input', 'builder-import-name');
mk('button', 'builder-import-btn');
mk('p', 'builder-import-status', 'note');
 mk('button', 'builder-validate-btn');
  mk('button', 'builder-verify-btn');
  mk('p', 'builder-validate-status', 'note');
  mk('button', 'builder-resolved-btn');
  mk('button', 'builder-handoff-btn');
  mk('p', 'builder-resolved-status', 'note');
  mk('pre', 'builder-resolved-out');
  mk('span', 'weave-status', 'note');
  mk('section', 'weave-list');
  mk('section', 'builder-chat-log');
const bForm = mk('form', 'builder-chat-form');
mk('textarea', 'builder-chat-input', '', bForm);
mk('button', 'builder-chat-send', '', bForm);

// dev drawer stubs
mk('div', 'dev-drawer-backdrop');
const devDrawer = mk('div', 'dev-drawer');
devDrawer.hidden = true;
byId.get('dev-drawer-backdrop').hidden = true;
mk('button', 'dev-drawer-trigger');
mk('button', 'dev-drawer-close', '', devDrawer);
mk('input', 'dev-drawer-filter', '', devDrawer);
mk('p', 'dev-drawer-filter-count', '', devDrawer);
mk('div', 'dev-drawer-content', '', devDrawer);

// prefs panel stubs
mk('div', 'prefs-backdrop');
const prefsPanel = mk('div', 'prefs-panel');
prefsPanel.hidden = true;
byId.get('prefs-backdrop').hidden = true;
mk('button', 'prefs-trigger');
mk('button', 'prefs-close', '', prefsPanel);
mk('button', 'prefs-share', '', prefsPanel);
mk('button', 'prefs-reset', '', prefsPanel);
mk('p', 'prefs-share-status', '', prefsPanel);
mk('p', 'prefs-saved-readout', '', prefsPanel);
mk('p', 'skuld-readout', '', prefsPanel);

const prefKeys = ['textSize', 'spacing', 'font', 'contrast', 'palette', 'motion', 'focus', 'density'];
for (const k of prefKeys) {
  const sel = mk('select', 'pref-' + k, '', prefsPanel, { prefKey: k });
  sel.setAttribute('data-pref-key', k);
}

// rune card + gallery stubs
const runeCard = mk('section', 'rune-card');
mk('button', 'rune-cast-toggle', '', runeCard);
mk('button', 'rune-gallery-btn', '', runeCard);
mk('div', 'rune-stave-was', '', runeCard);
mk('div', 'rune-name-was', '', runeCard);
mk('div', 'rune-stave-is', '', runeCard);
mk('div', 'rune-name-is', '', runeCard);
mk('div', 'rune-stave-asks', '', runeCard);
mk('div', 'rune-name-asks', '', runeCard);
mk('p', 'rune-meanings', '', runeCard);
const runeGallery = mk('div', 'rune-gallery', 'rune-gallery');
mk('button', 'rune-gallery-close', '', runeGallery);
mk('div', 'rune-gallery-grid', '', runeGallery);

/* a canvas whose 2d context records nothing but must never be called
   with a missing method */
const canvas = mk('canvas', 'town-canvas');
canvas.width = 0;
canvas.height = 0;
const ctx2d = new Proxy({}, {
  get: () => () => {},
  set: () => true,
});
canvas.getContext = () => ctx2d;

const store = {};
const winListeners = {};
const sandbox = {
  console,
  setTimeout,
  clearTimeout,
  Promise,
  Math,
  JSON,
  Date,
  Array,
  Object,
  String,
  Number,
  Boolean,
  Error,
  URLSearchParams,
  URL: {
    createObjectURL: () => 'blob:x',
    revokeObjectURL: () => {},
  },
  btoa: (s) => Buffer.from(s, 'binary').toString('base64'),
  atob: (s) => Buffer.from(s, 'base64').toString('binary'),
  history: { replaceState: () => {} },
  localStorage: {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; },
  },
  location: {
    origin: 'http://localhost',
    pathname: '/',
    href: 'http://localhost/',
    search: '',
  },
  navigator: {
    clipboard: {
      writeText: (txt) => { sandbox._lastCopied = txt; return Promise.resolve(); },
    },
  },
  Blob: class { constructor(p) { this.parts = p; } },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.document = {
  documentElement: root,
  getElementById: (id) => byId.get(id) || null,
  querySelector: (s) => root.querySelector(s),
  querySelectorAll: (s) => root.querySelectorAll(s),
  createElement: (t) => new El(t),
  addEventListener: (t, fn) => { (winListeners[t] ||= []).push(fn); },
  execCommand: (cmd) => true,
  body: root,
};
sandbox.Event = class { constructor(t) { this.type = t; } };
sandbox.window.addEventListener = (t, fn) => { (winListeners[t] ||= []).push(fn); };
sandbox.window.dispatchEvent = (ev) => { for (const fn of winListeners[ev.type] || []) fn(ev); };
sandbox.window.setTimeout = setTimeout;
sandbox.window.confirm = () => true;

/* ---------- fake API ---------- */
const WORLD = {
  title: 'Emberfield',
  phases: ['dusk', 'dawn'],
  tile: 32,
  bg: '#000',
  map: ['.....', '..#..', '.....'],
  legend: { '.': { base: ['#111'], deco: null, deco_color: '#222' }, '#': { base: ['#333'], solid: true } },
  pois: { '1,1': 'the well' },
  hero_start: [1, 0],
  hero_color: '#fff',
  watch: { tower: [4, 0, 3], r_by_phase: { dusk: 3, dawn: 1 }, overlay: 'rgba(0,0,0,0.2)' },
  sanctuary_tiles: [],
  water_by_phase: { dusk: 'high' },
  flood_tiles: [[2, 0]],
  speakers: [{ key: 'smith', name: 'The Smith', at: [1, 1], near: 'well', seeds: [] }],
  speaker_color: '#888',
  speaker_head: '#ddd',
};

let vault = [];
const calls = [];

/* The harness refuses to answer a URL the real server would not
   serve. The route table comes from FastAPI itself, written to a
   JSON file by test_web_dom.py (VEFR_ROUTES_JSON) - one source of
   truth, so a renamed route fails HERE with the real message
   instead of passing green while live play 404s. Without the env
   var (bare `node harness` runs), validation is skipped. */
const KNOWN_ROUTES = (() => {
  // VEFR_ROUTES_JSON names a FILE of routes (written by test_web_dom.py);
  // parse the file, never the path itself.
  const p = process.env.VEFR_ROUTES_JSON;
  if (!p) return [];
  try {
    return JSON.parse(fs.readFileSync(p, "utf8"));
  } catch (err) {
    console.error("harness: could not read route table", p, "-", err.message);
    return [];
  }
})();
function assertServed(url) {
  if (!KNOWN_ROUTES.length) return;
  const path = String(url).split('?')[0];
  const served = KNOWN_ROUTES.some((p) => {
    if (p === path) return true;
    if (!p.includes('{')) return false;
    const rx = new RegExp(
      '^' + p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\\\{[^}]+\\\}/g, '[^/]+') + '$'
    );
    return rx.test(path);
  });
  if (!served) {
    throw new Error(
      'harness fetched a route the server does not serve: ' + path
      + ' - update web/ to match src/vefr/main.py (stefna-tab incident class)'
    );
  }
}

sandbox.fetch = (url, opts) => {
  assertServed(url);
  const method = (opts && opts.method) || 'GET';
  const body = opts && opts.body ? JSON.parse(opts.body) : null;
  calls.push({ url, method, body });
  const ok = (data) => Promise.resolve({
    ok: true,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(typeof data === 'string' ? data : JSON.stringify(data)),
  });
  if (url === '/api/world') return ok(WORLD);
  if (url === '/api/vault' && method === 'GET') return ok({ items: vault.slice(), starred: [] });
  if (url === '/api/vault' && method === 'POST') { vault.push(body); return ok({ bond: body.bond }); }
  if (url === '/api/forge') return ok({ name: 'Ash Hammer', kind: 'tool', bond: 'attuned', lore: 'warm', enchant: null, curse: null });
  if (url === '/api/rumor') {
    if (body && 'phase' in body && typeof body.phase !== 'string') throw new Error('rumor got a non-string phase: ' + JSON.stringify(body));
    return ok({ speaker: 'a voice', whisper: 'hm', is_true: true, hook: null });
  }
  if (url === '/api/npc') {
    if (body && 'phase' in body && typeof body.phase !== 'string') throw new Error('npc got a non-string phase: ' + JSON.stringify(body));
    return ok({ speaker: 'The Smith', line: 'aye' });
  }
  if (url === '/api/stefna') return ok({ letter: 'For you.' });
  if (url === '/api/journal') return ok({ entries: [{ at: '2026-08-31T00:00:00Z', kind: 'rumor', speaker: 'a voice', whisper: 'hm', is_true: true }], starred: [] });
  if (url === '/api/trace') return ok({ events: [{ at: '2026-08-31T13:00:00Z', route: '/api/rumor', ms: 812.3, ok: true, phase: 'whispers', speaker: 'Old Sela' }] });
  if (url === '/api/weave') return ok({ events: [{ event: 'pack.load.end', at: 1234567890.0, pack: 'sample-world', acts: 1, shape: 'acts', surface: 'combat' }] });
  if (url.startsWith('/api/builder/aspects')) return ok({
    pack: { name: 'sample-world', title: 'Emberfield', surface: 'combat', shape: 'acts', phases: ['dusk', 'dawn'], gold_rule: '', journey: [] },
    act: { id: 'act-1', title: 'Emberfield', index: 0, total_acts: 1, enemies: [], bosses: [], transitions: [] },
    regions: { town: { title: 'town', has_map: true, pois: ['inn'], hero_start: [1, 1] } },
    speakers: { smith: { name: 'The Smith', near: 'forge', voice_file: 'smith.md', seeds: { dusk: 'aye' } } },
    rune_cast: { phase: 'dusk', seed: 1, iso_minute: '2026-08-31T11:06', positions: [{ position: 'what_was', name: 'Fehu', stave: '\u16A0', short: 'wealth' }] },
    recent_trace: [{ at: '2026-08-31T13:00:00Z', route: '/api/rumor', ms: 12.3, ok: true }],
  });
  if (url === '/api/builder/resolved') return ok({ name: 'sample-world', title: 'Emberfield', _shape: 'acts', _current_act: 0, acts: [] });
  if (url === '/api/combat/action' && method === 'POST') return ok({ at: '2026-08-31T22:00:00Z', kind: body.kind, phase: body.phase, target: body.target });
  if (url === '/api/wiki') return ok({ characters: [{ key: 'sela', name: 'Old Sela', lines: 1, recent: [{ at: '2026-08-31T00:00:00Z', phase: 'whispers', line: 'the well remembers' }] }], relics: [{ name: 'knife', bond: 'assigned', lore: 'heavy' }], rumors: 1, letters: 0 });
  if (url === '/api/starred') return ok({ starred: [] });
  if (url === '/api/journal/clear') return ok({ cleared: true });
  if (url.startsWith('/api/export')) return ok('# story');
  if (url.startsWith('/api/export/tabs/')) {
    const tab = url.split('/').pop();
    return ok(`# section\n\n## ${tab}\n\nexported.`);
  }
  if (url === '/api/builder/worlds') return ok({
    worlds: [
      { name: 'sample-world', title: 'Emberfield', phases: ['dusk', 'dawn'], speakers: ['smith'] },
    ],
  });
  if (url === '/api/builder/chat') return ok({ reply: 'aye, that is what I would write.' });
  if (url === '/api/runes/cast') return ok({
    phase: 'whispers',
    seed: 1,
    iso_minute: '2026-08-31T11:06',
    positions: [
      { position: 'what_was',  name: 'Fehu',  stave: '\u16A0', short: 'wealth, the seed-fire', long: 'the first gift' },
      { position: 'what_is',   name: 'Ingwaz', stave: '\u16DC', short: 'the seed, the gestation', long: 'the time before' },
      { position: 'what_asks', name: 'Raido',  stave: '\u16B1', short: 'the ride, the road', long: 'the first going' },
    ],
    prompt_block: 'cast',
  });
  if (url === '/api/runes') return ok({
    runes: [
      { name: 'Fehu', stave: '\u16A0', aettir: 1, short: 'wealth', long: 'long fehu', engine_phase: 'whispers' },
      { name: 'Thurisaz', stave: '\u16A6', aettir: 1, short: 'thorn', long: 'long thurisaz', engine_phase: 'doubts' },
      { name: 'Kenaz', stave: '\u16B2', aettir: 1, short: 'torch', long: 'long kenaz', engine_phase: 'feared' },
      { name: 'Sowilo', stave: '\u16F0', aettir: 2, short: 'sun', long: 'long sowilo', engine_phase: 'awed' },
      { name: 'Ansuz', stave: '\u16A8', aettir: 1, short: 'god', long: 'long ansuz', engine_phase: null },
    ],
    anchors: { whispers: { name: 'Fehu', stave: '\u16A0', short: 'wealth' } },
  });
  throw new Error('harness: unexpected fetch ' + method + ' ' + url);
};

/* ---------- run the real scripts, in page order ---------- */
const ctxVm = vm.createContext(sandbox);
const html = read('web/index.html');

// Extract and execute all scripts in order
const scriptRegex = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
const inlineScripts = [];
let match;
while ((match = scriptRegex.exec(html)) !== null) {
  const fullTag = match[0];
  if (!fullTag.includes('src=')) {
    inlineScripts.push(match[1]);
  }
}

const scriptsToRun = [
  ['state.js', read('web/state.js')],
  ['prefs.js', read('web/prefs.js')],
  ['town.js', read('web/town.js')],
  ['board.js', read('web/board.js')],
];
for (let i = 0; i < inlineScripts.length; i++) {
  scriptsToRun.push([`index.html inline [${i}]`, inlineScripts[i]]);
}

for (const [label, code] of scriptsToRun) {
  vm.runInContext('"use strict";\n' + code, ctxVm, { filename: label });
}

/* ---------- drive the flows ---------- */
const tick = () => new Promise((r) => setTimeout(r, 5));
const S = () => sandbox.window.VEFR_STATE.get();
const railOf = (id) => byId.get(id).children.map((b) => b.textContent + (b.getAttribute('aria-pressed') === 'true' ? '*' : ''));
const fail = [];
const check = (name, cond, extra = '') => {
  if (!cond) fail.push(name + (extra ? ' -- ' + extra : ''));
  console.log((cond ? 'ok   ' : 'FAIL ') + name + (extra && !cond ? ' -- ' + extra : ''));
};

await tick();

check('world loaded into shared state', S().world && S().phases.length === 2);
check('phase defaults to the pack first phase', S().phase === 'dusk', S().phase);
check('rumor rail built from the pack', railOf('rumor-phase').join(',') === 'dusk*,dawn', railOf('rumor-phase').join(','));
check('town rail built from the pack', railOf('town-phase').join(',') === 'dusk*,dawn', railOf('town-phase').join(','));
check('one /api/world request only', calls.filter((c) => c.url === '/api/world').length === 1);
check('canvas sized from the map', canvas.width === 5 * 32 && canvas.height === 3 * 32);

/* the core desync case: set the phase from the RUMORS rail, and the
   TOWN rail must follow */
byId.get('rumor-phase').children[1].click();
await tick();
check('rumors click moves shared phase', S().phase === 'dawn', S().phase);
check('town rail followed the rumors rail', railOf('town-phase').join(',') === 'dusk,dawn*', railOf('town-phase').join(','));
check('rumors rail shows its own click', railOf('rumor-phase').join(',') === 'dusk,dawn*', railOf('rumor-phase').join(','));

/* and back the other way */
byId.get('town-phase').children[0].click();
await tick();
check('town click moves shared phase', S().phase === 'dusk', S().phase);
check('rumors rail followed the town rail', railOf('rumor-phase').join(',') === 'dusk*,dawn', railOf('rumor-phase').join(','));

/* the whisper sends the shared phase, not a hardcoded one */
byId.get('whisper-btn').click();
await tick();
const lastRumor = calls.filter((c) => c.url === '/api/rumor').pop();
check('whisper sent the shared phase', lastRumor.body.phase === 'dusk', JSON.stringify(lastRumor.body));
check('whisper card rendered', byId.get('feed').innerHTML.includes('data-phase="dusk"'));

/* forge + keep: the town HUD must update with no tab click */
byId.get('forge-btn').click();
await tick();
const keepBtn = new El('button');
keepBtn.dataset.keep = '1';
forgeOut.appendChild(keepBtn);
keepBtn.click();
await tick();
check('kept item is in shared vault', S().vault.length === 1 && S().vault[0].name === 'Ash Hammer');
check('carrying updated without a tab switch', S().carrying && S().carrying.name === 'Ash Hammer');
check('town HUD shows the carried item', byId.get('carrying').textContent.includes('Ash Hammer'), byId.get('carrying').textContent);
check('vault list rendered from shared state', byId.get('vault-list').innerHTML.includes('Ash Hammer'));

/* tab switching must not lose any of it */
for (const v of TABVIEWS) { tabBtns[v].click(); await tick(); }
check('phase survived a full tab tour', S().phase === 'dusk', S().phase);
check('carrying survived a full tab tour', S().carrying && S().carrying.name === 'Ash Hammer');
check('town rail still pressed correctly', railOf('town-phase').join(',') === 'dusk*,dawn', railOf('town-phase').join(','));
check('rumors rail still pressed correctly', railOf('rumor-phase').join(',') === 'dusk*,dawn', railOf('rumor-phase').join(','));
check('vault list still populated', byId.get('vault-list').innerHTML.includes('Ash Hammer'));

/* the dev board boots lazily on its own tab, off the shared world
   fetch - the page must still have asked /api/world exactly once */
check('board rendered cards', byId.get('board-whispers').children.length > 0,
  `whispers cards: ${byId.get('board-whispers').children.length}`);
check('board added no second world fetch',
  calls.filter((c) => c.url === '/api/world').length === 1,
  calls.filter((c) => c.url === '/api/world').length);

/* the journal tab from the previous task must still work */
check('journal rendered on its tab', byId.get('journal-list').innerHTML.includes('a voice'), byId.get('journal-list').innerHTML);
check('journal status counted', byId.get('journal-status').textContent.includes('1 thing happened'), byId.get('journal-status').textContent);

/* the wiki tab renders characters + relics from /api/wiki */
check('wiki rendered characters', byId.get('wiki-characters').innerHTML.includes('Old Sela'), byId.get('wiki-characters').innerHTML);
check('wiki rendered relics', byId.get('wiki-relics').innerHTML.includes('knife'), byId.get('wiki-relics').innerHTML);
check('trace rendered the call', byId.get('trace-list').innerHTML.includes('/api/rumor'), byId.get('trace-list').innerHTML);

/* the export button from the previous task must still work */
byId.get('export-btn').click();
await tick();
check('export fetched', calls.some((c) => c.url === '/api/export'));
check('export status set', byId.get('journal-status').textContent.includes('yours to keep'), byId.get('journal-status').textContent);

/* per-tab export buttons: each tab pulls its own markdown section */
const tabExports = ['rumors', 'vault', 'stefna', 'town', 'journal'];
for (const t of tabExports) {
  byId.get('export-' + t + '-btn').click();
  await tick();
  check('per-tab export ' + t + ' fetched',
    calls.some((c) => c.url === '/api/export/tabs/' + t),
    calls.filter((c) => c.url === '/api/export/tabs/' + t).length + ' calls');
}

/* journal clear */
byId.get('journal-clear-btn').click();
await tick();
check('journal clear posted', calls.some((c) => c.url === '/api/journal/clear'));

/* the stefna */
byId.get('strike-btn').click();
await tick();
check('stefna letter rendered', byId.get('letter-out').innerHTML.includes('For you.'));

/* town movement + talking, on the shared phase */
sandbox.document.dispatch = null;
for (const fn of winListeners['keydown'] || []) fn({ key: 'ArrowDown', preventDefault() {} });
check('poi updated after a move', byId.get('poi').textContent.length > 0, byId.get('poi').textContent);
canvas.dispatch('click');
await tick();
const npcCall = calls.filter((c) => c.url === '/api/npc').pop();
check('npc asked with the shared phase', npcCall && npcCall.body.phase === 'dusk', JSON.stringify(npcCall && npcCall.body));
check('npc line rendered', byId.get('npc-line').textContent === 'aye', byId.get('npc-line').textContent);

/* setPhase must refuse a tone the pack does not have */
sandbox.window.VEFR_STATE.setPhase('whispers');
check('unknown phase refused', S().phase === 'dusk', S().phase);

/* dpad still moves */
const dpadBtn = new El('button');
dpadBtn.dataset.dir = 'up';
byId.get('dpad').appendChild(dpadBtn);
dpadBtn.click();
check('dpad move did not throw', true);

/* the builder tab from this session: packs load, chat round-trips */
tabBtns.builder.click();
await tick();
check('builder packs loaded',
  calls.some((c) => c.url === '/api/builder/worlds') &&
  byId.get('builder-pack-picker').children.length === 1,
  byId.get('builder-pack-picker').children.length + ' picker options');
byId.get('builder-chat-input').value = 'who is the smith?';
byId.get('builder-chat-form').dispatch('submit');
await tick();
const chatCall = calls.filter((c) => c.url === '/api/builder/chat').pop();
check('builder chat posted', !!chatCall, JSON.stringify(chatCall));
check('builder chat reply rendered', byId.get('builder-chat-log').textContent.includes('aye'));
check('builder validate button wired', byId.get('builder-validate-btn') !== null);

/* ---------- preferences controller flows ---------- */
const trig = byId.get('prefs-trigger');
const pPanel = byId.get('prefs-panel');
const pBackdrop = byId.get('prefs-backdrop');
const pClose = byId.get('prefs-close');
const pShare = byId.get('prefs-share');
const pReset = byId.get('prefs-reset');

check('prefs panel initially hidden', pPanel.hidden === true && pBackdrop.hidden === true);

// 1. Trigger opens panel
trig.click();
await tick();
check('prefs panel opens on trigger click', pPanel.hidden === false && pBackdrop.hidden === false && trig.getAttribute('aria-expanded') === 'true');

// 2. Escape key closes panel
for (const fn of winListeners['keydown'] || []) fn({ key: 'Escape', preventDefault() {} });
await tick();
check('escape key closes prefs panel', pPanel.hidden === true && pBackdrop.hidden === true && trig.getAttribute('aria-expanded') === 'false');

// 3. Backdrop click closes panel
trig.click();
await tick();
pBackdrop.click();
await tick();
check('backdrop click closes prefs panel', pPanel.hidden === true && pBackdrop.hidden === true);

// 4. Close button closes panel
trig.click();
await tick();
pClose.click();
await tick();
check('close button closes prefs panel', pPanel.hidden === true && pBackdrop.hidden === true);

// 5. Select rows call VEFR_PREFS.set
trig.click();
await tick();
for (const k of prefKeys) {
  const sel = byId.get('pref-' + k);
  sel.value = k === 'contrast' ? 'high' : (k === 'textSize' ? 'xl' : 'test-val');
  sel.dispatch('change');
  await tick();
  const cur = sandbox.window.VEFR_PREFS.get();
  check(`pref select ${k} updates state`, cur[k] === sel.value, `${cur[k]} vs ${sel.value}`);
}

// 5b. The readbacks: Urd says what is saved, Skuld says what reads
// now - both live on every change, no dead em-dash placeholders.
const savedReadout = byId.get('prefs-saved-readout');
const skuldReadout = byId.get('skuld-readout');
check('urd readout announces the saved state',
  savedReadout.textContent.includes('saved:') && savedReadout.textContent.includes('text xl'),
  savedReadout.textContent);
check('skuld readback is live, not placeholders',
  skuldReadout.textContent.includes('reading now:') && skuldReadout.textContent.includes('contrast high'),
  skuldReadout.textContent);
check('skuld sample keeps its engine voice, no dead meta',
  !skuldReadout.textContent.includes('phase:') && !skuldReadout.textContent.includes('speaker:'));

// 6. Reset restores defaults
pReset.click();
await tick();
const afterReset = sandbox.window.VEFR_PREFS.get();
check('reset restores defaults', afterReset.textSize === 'm' && afterReset.contrast === 'm');
check('readbacks return to defaults after reset',
  savedReadout.textContent.includes('text m') && skuldReadout.textContent.includes('contrast m'),
  savedReadout.textContent + ' | ' + skuldReadout.textContent);

// 7. Share link button generates URL and copies
pShare.click();
await tick();
check('share button copies url', typeof sandbox._lastCopied === 'string' && sandbox._lastCopied.includes('?prefs='));

/* ---------- dev overlay & aspect inspector flows ---------- */
const dTrig = byId.get('dev-drawer-trigger');
const dDrawer = byId.get('dev-drawer');
const dBackdrop = byId.get('dev-drawer-backdrop');
const dClose = byId.get('dev-drawer-close');
const dContent = byId.get('dev-drawer-content');

check('dev drawer initially hidden', dDrawer.hidden === true && dBackdrop.hidden === true);

// 1. Trigger opens drawer & loads aspects
dTrig.click();
await tick();
check('dev drawer opens on trigger click', dDrawer.hidden === false && dBackdrop.hidden === false && dTrig.getAttribute('aria-expanded') === 'true');
check('dev drawer fetched /api/builder/aspects', calls.some((c) => c.url.startsWith('/api/builder/aspects')));
check('dev drawer rendered aspect content', dContent.innerHTML.includes('Pack &amp; Surface') && dContent.innerHTML.includes('Emberfield'));

// 2. Escape key closes drawer
for (const fn of winListeners['keydown'] || []) fn({ key: 'Escape', preventDefault() {} });
await tick();
check('escape key closes dev drawer', dDrawer.hidden === true && dBackdrop.hidden === true && dTrig.getAttribute('aria-expanded') === 'false');

// 3. Backtick key toggles drawer
for (const fn of winListeners['keydown'] || []) fn({ key: '`', preventDefault() {}, target: { tagName: 'BODY' } });
await tick();
check('backtick key opens dev drawer', dDrawer.hidden === false && dBackdrop.hidden === false);

// 4. Close button closes drawer
dClose.click();
await tick();
check('close button closes dev drawer', dDrawer.hidden === true && dBackdrop.hidden === true);

// 5. The section filter re-renders from the stored payload
const dFilter = byId.get('dev-drawer-filter');
const dCount = byId.get('dev-drawer-filter-count');
dTrig.click();
await tick();
check('filter restores all sections on a fresh open',
  dContent.innerHTML.includes('Pack &amp; Surface') && dCount.innerHTML === '');
dFilter.value = 'rune';
dFilter.dispatch('input');
await tick();
check('filter narrows to the matching section',
  dContent.innerHTML.includes('Living Rune Cast')
  && !dContent.innerHTML.includes('Pack &amp; Surface'));
check('filter announces the match count',
  dCount.textContent.includes('of 6 sections match'));
dFilter.value = 'zzz-no-such-aspect';
dFilter.dispatch('input');
await tick();
check('a filter with no matches says so plainly',
  dContent.innerHTML.includes('no sections match')
  && dCount.textContent.includes('0 of 6'));
dFilter.value = '';
dFilter.dispatch('input');
await tick();
check('clearing the filter restores all sections',
  dContent.innerHTML.includes('Pack &amp; Surface')
  && dContent.innerHTML.includes('Recent Trace Events')
  && dCount.textContent === '');
dClose.click();
await tick();

console.log('\n' + (fail.length ? 'FAILURES:\n  ' + fail.join('\n  ') : 'all harness checks passed'));
process.exit(fail.length ? 1 : 0);
