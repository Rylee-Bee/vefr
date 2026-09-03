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
    /* style: an object whose keys are CSS property names in
       camelCase (left, top, width, height). Setting `style.left =
       '0px'` writes to this map; getBoundingClientRect() reads from
       it so the dock controller can verify geometry. cssText exposes
       the joined string for `el.style.cssText` style writes. */
    this.style = {
      _props: {},
      _listeners: {},
      set cssText(v) { this._props = {}; String(v).split(';').forEach((decl) => { const [k, val] = decl.split(':'); if (k && val) this[k.trim()] = val.trim(); }); },
      get cssText() { return Object.entries(this._props).map(([k, v]) => k + ':' + v).join(';'); },
    };
    /* Make every style assignment route through a Proxy so
       `el.style.left = '0px'` lands in the map. We re-create the
       proxy on each property set to keep things simple. */
    this.style = new Proxy(this.style, {
      get(t, k) {
        if (k === '_props' || k === '_listeners' || k === 'cssText') return t[k];
        return t._props[k];
      },
      set(t, k, v) {
        if (k === 'cssText') { t.cssText = v; return true; }
        t._props[k] = String(v);
        return true;
      },
    });
    this.children = [];
    this.parent = null;
    this.listeners = {};
    this.hidden = false;
    this.disabled = false;
    this._text = '';
    this._seq = nodeSeq++;
    this._rect = { left: 0, top: 0, width: 0, height: 0, right: 0, bottom: 0 };
    this.classList = {
      _s: new Set(),
      add: (c) => this.classList._s.add(c),
      remove: (c) => this.classList._s.delete(c),
      contains: (c) => this.classList._s.has(c),
      toggle: function (c, force) {
        const has = this._s.has(c);
        const next = (typeof force === 'boolean') ? force : !has;
        if (next) this._s.add(c); else this._s.delete(c);
        return next;
      },
    };
  }
  getBoundingClientRect() {
    /* The dock controller reads the workspace rect once per layout;
       it expects width/height to drive absolute pixel math. Tests
       set this rect on the workspace explicitly via the helper. */
    return this._rect;
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
  setAttribute(k, v) {
    this.attrs[k] = String(v);
    /* Mirror data-* attributes into dataset so the controller can
       read them back either way. A real DOM does this via a Proxy
       on dataset; the harness just keeps them in sync. */
    const m = String(k).match(/^data-([\w-]+)$/);
    if (m) this.dataset[camel(m[1])] = String(v);
  }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  get value() { return this._value || ''; }
  set value(v) { this._value = String(v); }
  appendChild(c) {
    /* Move semantics: detach from old parent first, then attach to
       the new one. Real DOM `appendChild` moves a node; without
       this, the dock controller's wrap-everything-after-the-title
       loop re-appends the same resize handle forever. */
    if (c.parent && c.parent !== this) {
      const i = c.parent.children.indexOf(c);
      if (i >= 0) c.parent.children.splice(i, 1);
    }
    c.parent = this;
    this.children.push(c);
    return c;
  }
  /* Minimal parentNode + insertBefore for the few spots in the page
     that need them (e.g. the dock controller inserting its live
     region just after the workspace). Behavior matches the real DOM
     well enough for the harness: insertBefore(newChild, refChild)
     places newChild directly before refChild in this.children. */
  get parentNode() { return this.parent; }
  insertBefore(newChild, refChild) {
    newChild.parent = this;
    if (!refChild) { this.children.push(newChild); return newChild; }
    const i = this.children.indexOf(refChild);
    if (i < 0) { this.children.push(newChild); return newChild; }
    this.children.splice(i, 0, newChild);
    return newChild;
  }
  /* nextSibling/previousSibling/nextElementSibling are used by the
     dock controller when it wraps the existing panel content into
     a .panel-body div. */
  get nextSibling() {
    if (!this.parent) return null;
    const i = this.parent.children.indexOf(this);
    return i >= 0 && i + 1 < this.parent.children.length ? this.parent.children[i + 1] : null;
  }
  get previousSibling() {
    if (!this.parent) return null;
    const i = this.parent.children.indexOf(this);
    return i > 0 ? this.parent.children[i - 1] : null;
  }
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
  /* Pointer events are dispatched the same way as the regular ones;
     the dock controller uses pointerId/clientX/clientY to track
     drags, so we pass those through verbatim. */
  pointer(type, extra = {}) { this.dispatch(type, extra); }
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
  m = sel.match(/^\[data-([\w-]+)="([^"]*)"\]$/);
  if (m) return el.dataset && el.dataset[camel(m[1])] === m[2];
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
const TABVIEWS = ['rumors', 'vault', 'stefna', 'town', 'journal', 'wiki', 'trace', 'weave', 'builder', 'board'];
const PLAYVIEWS = ['rumors', 'vault', 'stefna', 'town', 'journal'];
const VIEWZONE = {
  rumors: 'play', vault: 'play', stefna: 'play', town: 'play', journal: 'play',
  wiki: 'build', builder: 'build', board: 'build', trace: 'weave', weave: 'weave',
};
const zonesBox = mk('div', '', 'zones');
const zoneBtns = {};
for (const zone of ['play', 'build', 'weave']) {
  zoneBtns[zone] = mk('button', 'zone-' + zone, 'zone-btn', zonesBox, { zone });
}
const zoneNavs = {};
for (const zone of ['play', 'build', 'weave']) {
  zoneNavs[zone] = mk('nav', 'zone-nav-' + zone, 'tabs zone-nav', root, { zoneNav: zone });
}
const playWorkspace = mk('div', 'play-workspace', 'play-workspace');
/* The dock controller reads getBoundingClientRect() to position the
   panels; give the workspace a generous virtual size so absolute
   pixel math produces visible coords. */
playWorkspace._rect = { left: 0, top: 0, width: 1280, height: 800, right: 1280, bottom: 800 };
const tabBtns = {};
for (const v of TABVIEWS) {
  tabBtns[v] = mk('button', 'tab-' + v, '', zoneNavs[VIEWZONE[v]], { view: v });
  const view = mk('section', 'view-' + v, PLAYVIEWS.includes(v) ? 'view play-panel' : 'view',
    PLAYVIEWS.includes(v) ? playWorkspace : root);
  /* The dock controller injects window controls around the existing
     <h2 class="panel-title"> on each play panel. The real page has
     one; the harness needs at least an empty one per panel so the
     controller's querySelector finds it. The Norwegian subtitles
     live in <span class="sub"> children in the real page but the
     dock controller only reads textContent, so we keep them empty
     here. */
  if (PLAYVIEWS.includes(v)) {
    const title = mk('h2', '', 'panel-title', view, { panel: v });
    /* The dock controller reads title.textContent.trim() to build
       aria-labels like "Drag Whispers panel". The harness titles
       are empty by default; this map gives each one a readable
       name without needing real <span class="sub"> markup. */
    const NAMES = { town: 'Town', rumors: 'Whispers', vault: 'Vault', stefna: 'Bell', journal: 'Journal' };
    title._text = NAMES[v] || v;
    title.setAttribute('aria-label', title._text);
  }
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
/* Dock layout reset lives in the dev drawer filter bar; the dock
   controller's reset hook lives on window.VEFR_DOCK. */
mk('button', 'dev-dock-reset');

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
/* Window size is set by the dock tests via setWinSize(). 1200 keeps
   the dock controller in free-dock mode for the existing tests. */
let winWidth = 1200;
let winHeight = 900;
const sandbox = {
  console,
  setTimeout,
  clearTimeout,
  requestAnimationFrame: (cb) => { cb(0); return 0; },
  cancelAnimationFrame: () => {},
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
  get innerWidth() { return winWidth; },
  get innerHeight() { return winHeight; },
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
  /* Document-level pointer events fire here from the dock controller's
     drag listeners. The pointermove/up/cancel handlers are registered
     via addEventListener; firing through dispatchEvent walks the same
     listener table. */
  dispatchEvent: (ev) => { for (const fn of winListeners[ev.type] || []) fn(ev); return true; },
  execCommand: (cmd) => true,
  body: root,
  /* getComputedStyle: the dock controller reads the breakpoint CSS
     variable here. The stub returns the property the test stored, or
     '' for unknown keys. */
  defaultView: sandbox,
};
sandbox.window.getComputedStyle = (el, pseudoEl) => ({
  getPropertyValue: (name) => {
    /* The dock controller only reads --free-dock-breakpoint. Tests
       override it via setWinBreakpoint() when they need a different
       value; default is '1180px' (matches the CSS variable
       :root --free-dock-breakpoint). */
    if (name === '--free-dock-breakpoint') return sandbox._breakpoint || '1180px';
    return '';
  },
});
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
  if (url === '/api/journal/move' && method === 'POST') {
    if (!body || typeof body.poi !== 'string' || typeof body.x !== 'number' || typeof body.y !== 'number') {
      throw new Error('move got a bad body: ' + JSON.stringify(body));
    }
    return ok({ logged: true, entry: body });
  }
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
check('play workspace is the initial mode', root.dataset.zone === 'play' && playWorkspace.hidden === false);
check('desktop play context stays mounted', PLAYVIEWS.every((v) => byId.get('view-' + v).hidden === false));
check('non-play views stay out of the play workspace', ['wiki', 'builder', 'board', 'trace', 'weave'].every((v) => byId.get('view-' + v).hidden === true));

/* Mode switches collapse back to one view, then restore the composed
   play workspace without losing state or handlers. */
zoneBtns.build.click();
await tick();
check('build mode opens its default view', root.dataset.zone === 'build' && byId.get('view-wiki').hidden === false && playWorkspace.hidden === true);
zoneBtns.play.click();
await tick();
check('returning to play restores every live panel', playWorkspace.hidden === false && PLAYVIEWS.every((v) => byId.get('view-' + v).hidden === false));

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

/* the road walked: one /api/journal/move per change of place,
   nothing per tile (the throttle is place-equality) */
const moveCalls = () => calls.filter((c) => c.url === '/api/journal/move');
const movesBefore = moveCalls().length;
for (const fn of winListeners['keydown'] || []) fn({ key: 'ArrowDown', preventDefault() {} }); // (1,2) - still 'the well'
await tick();
check('same-place step posted no move', moveCalls().length === movesBefore, String(moveCalls().length));
for (let i = 0; i < 3; i++) {
  for (const fn of winListeners['keydown'] || []) fn({ key: 'ArrowRight', preventDefault() {} });
  await tick();
}
check('place change posted one move', moveCalls().length === movesBefore + 1,
  JSON.stringify(moveCalls().slice(-1)));
const moveCall = moveCalls().pop();
check('move carries poi, phase, tile', moveCall && moveCall.body.poi === 'Emberfield'
  && moveCall.body.phase === 'dusk' && moveCall.body.x === 4 && moveCall.body.y === 2,
  JSON.stringify(moveCall && moveCall.body));

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

/* ---------- free-dock Play workspace ---------- */
/* The dock controller injects window controls into every play panel
   at boot; on a wide viewport, all five panels are positioned
   absolutely inside the workspace. On a narrow viewport, the
   composed grid takes over and the controls stay hidden via CSS. */

const dockPlayViews = ['town', 'rumors', 'vault', 'stefna', 'journal'];

check('dock controller exposed on window.VEFR_DOCK', typeof sandbox.window.VEFR_DOCK === 'object'
  && typeof sandbox.window.VEFR_DOCK.reset === 'function'
  && typeof sandbox.window.VEFR_DOCK.layout === 'function');
check('window is wide enough for free-dock mode', sandbox.window.VEFR_DOCK.isFree() === true,
  'innerWidth=' + sandbox.window.innerWidth);
check('body dock attribute is free on a wide viewport', root.dataset.dock === 'free',
  'data-dock=' + root.dataset.dock);

for (const key of dockPlayViews) {
  const view = byId.get('view-' + key);
  /* The dock controller injects drag-handle + controls into the
     title row, and the resize-handle into the panel root. */
  const title = view.querySelector('.panel-title');
  check(`panel ${key} rendered with a drag handle`,
    !!title.querySelector('.panel-drag-handle'), key);
  check(`panel ${key} rendered with a resize handle`,
    !!view.querySelector('.panel-resize-handle'), key);
  check(`panel ${key} rendered with a snap-to-default control`,
    !!title.querySelector('[data-panel-control="dock"]'), key);
  check(`panel ${key} rendered with a minimize control`,
    !!title.querySelector('[data-panel-control="minimize"]'), key);
  /* In free-dock mode every panel is positioned absolutely; the inline
     style.left/top/width/height are set by the controller. */
  check(`panel ${key} positioned absolutely`,
    view.style._props.left
    && view.style._props.top
    && view.style._props.width
    && view.style._props.height,
    JSON.stringify(view.style._props));
  check(`panel ${key} body wrapped for minimize`,
    !!view.querySelector('.panel-body'), key);
}

/* Drag the Whispers panel: pointerdown on its drag handle, two
   pointermoves, then a pointerup. The inline left coord must
   increase by the second move's delta. */
const whispersView = byId.get('view-rumors');
const whispersHandle = whispersView.querySelector('.panel-title').querySelector('.panel-drag-handle');
const startLeft = parseInt(whispersView.style._props.left, 10);
const startTop = parseInt(whispersView.style._props.top, 10);
const startWidth = parseInt(whispersView.style._props.width, 10);

whispersHandle.pointer('pointerdown', { pointerId: 7, clientX: 100, clientY: 100 });
sandbox.document.dispatchEvent({ type: 'pointermove', pointerId: 7, clientX: 200, clientY: 150 });
sandbox.document.dispatchEvent({ type: 'pointermove', pointerId: 7, clientX: 250, clientY: 175 });
sandbox.document.dispatchEvent({ type: 'pointerup',   pointerId: 7, clientX: 250, clientY: 175 });
await tick();

const afterLeft = parseInt(whispersView.style._props.left, 10);
const afterTop = parseInt(whispersView.style._props.top, 10);
check('drag moved the whispers panel right and down',
  afterLeft > startLeft && afterTop > startTop,
  `start=(${startLeft},${startTop}) after=(${afterLeft},${afterTop})`);
check('drag persisted to localStorage',
  typeof store['vefr:dock:v1'] === 'string'
  && store['vefr:dock:v1'].includes('"rumors"'),
  store['vefr:dock:v1'] || '(empty)');
check('drag did not change the panel width',
  parseInt(whispersView.style._props.width, 10) === startWidth,
  'width ' + whispersView.style._props.width);

/* Resize the Vault panel via its resize handle: drag the bottom-right
   grip diagonally and verify the panel grew. */
const vaultView = byId.get('view-vault');
const vaultResize = vaultView.querySelector('.panel-resize-handle');
const vStartW = parseInt(vaultView.style._props.width, 10);
const vStartH = parseInt(vaultView.style._props.height, 10);
vaultResize.pointer('pointerdown', { pointerId: 8, clientX: 300, clientY: 400 });
sandbox.document.dispatchEvent({ type: 'pointermove', pointerId: 8, clientX: 360, clientY: 460 });
sandbox.document.dispatchEvent({ type: 'pointerup',   pointerId: 8, clientX: 360, clientY: 460 });
await tick();
check('resize grew the vault panel',
  parseInt(vaultView.style._props.width, 10) > vStartW
  && parseInt(vaultView.style._props.height, 10) > vStartH,
  `before=(${vStartW},${vStartH}) after=(${vaultView.style._props.width},${vaultView.style._props.height})`);

/* Escape cancels an in-flight drag and reverts the panel geometry. */
const bellView = byId.get('view-stefna');
const bellResize = bellView.querySelector('.panel-resize-handle');
const bellStart = { w: bellView.style._props.width, h: bellView.style._props.height };
bellResize.pointer('pointerdown', { pointerId: 9, clientX: 200, clientY: 200 });
sandbox.document.dispatchEvent({ type: 'pointermove', pointerId: 9, clientX: 260, clientY: 260 });
for (const fn of winListeners['keydown'] || []) fn({ key: 'Escape', preventDefault() {}, target: { tagName: 'BUTTON' } });
sandbox.document.dispatchEvent({ type: 'pointercancel', pointerId: 9, clientX: 260, clientY: 260 });
await tick();
check('escape cancels an in-flight resize',
  bellView.style._props.width === bellStart.w
  && bellView.style._props.height === bellStart.h,
  `start=${JSON.stringify(bellStart)} after=${bellView.style._props.width}x${bellView.style._props.height}`);

/* Snap-to-default control: clicking the dock button restores the
   panel to the default coords (left=0.02 of 1280 = ~25px, etc.). */
const beforeSnap = { l: whispersView.style._props.left, t: whispersView.style._props.top };
const dockBtn = whispersView.querySelector('[data-panel-control="dock"]');
dockBtn.click();
await tick();
const afterSnap = { l: whispersView.style._props.left, t: whispersView.style._props.top };
check('snap-to-default moves the panel back to its default coords',
  beforeSnap.l !== afterSnap.l || beforeSnap.t !== afterSnap.t,
  `before=${JSON.stringify(beforeSnap)} after=${JSON.stringify(afterSnap)}`);

/* Minimize control: clicking it toggles the is-minimised class. */
const minBtn = byId.get('view-journal').querySelector('[data-panel-control="minimize"]');
const journalView = byId.get('view-journal');
check('journal panel starts unminimized', !journalView.classList.contains('is-minimised'));
minBtn.click();
await tick();
check('minimize button toggles the is-minimised class',
  journalView.classList.contains('is-minimised'));
minBtn.click();
await tick();
check('second minimize click restores the panel',
  !journalView.classList.contains('is-minimised'));

/* Keyboard drag: Enter on the drag handle starts, ArrowRight moves,
   Escape cancels, Enter commits. */
const kbdView = byId.get('view-journal');
const kbdHandle = kbdView.querySelector('.panel-title').querySelector('.panel-drag-handle');
const kbdStartLeft = kbdView.style._props.left;
for (const fn of winListeners['keydown'] || []) fn({ key: 'Enter', preventDefault() {}, target: { tagName: 'BUTTON' } });
for (const fn of winListeners['keydown'] || []) fn({ key: 'ArrowLeft', preventDefault() {}, target: { tagName: 'BUTTON' } });
for (const fn of winListeners['keydown'] || []) fn({ key: 'Escape', preventDefault() {}, target: { tagName: 'BUTTON' } });
await tick();
check('keyboard drag is no-op after Escape',
  kbdView.style._props.left === kbdStartLeft,
  `start=${kbdStartLeft} after=${kbdView.style._props.left}`);

/* Reset hook: window.VEFR_DOCK.reset() clears the layout. */
sandbox.window.VEFR_DOCK.reset();
await tick();
check('reset hook clears the dock layout', store['vefr:dock:v1'] === undefined,
  'storage: ' + JSON.stringify(store['vefr:dock:v1']));

/* Narrow viewport: dock disables and inline geometry is cleared. */
winWidth = 900;
sandbox.window.dispatchEvent({ type: 'resize' });
await tick();
check('narrow viewport disables free-dock mode',
  root.dataset.dock === 'composed',
  'data-dock=' + root.dataset.dock);
check('narrow viewport clears inline geometry',
  !whispersView.style._props.left
  && !whispersView.style._props.top
  && !whispersView.style._props.width,
  JSON.stringify(whispersView.style._props));
/* Restore wide viewport for any later checks. */
winWidth = 1200;
sandbox.window.dispatchEvent({ type: 'resize' });
await tick();

console.log('\n' + (fail.length ? 'FAILURES:\n  ' + fail.join('\n  ') : 'all harness checks passed'));
process.exit(fail.length ? 1 : 0);
