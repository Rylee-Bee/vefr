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
  get textContent() { return this._text; }
  set textContent(v) { this._text = String(v); this.children = []; }
  set innerHTML(v) { this._html = String(v); if (v === '') this.children = []; }
  get innerHTML() { return this._html === undefined ? '' : this._html; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  appendChild(c) { c.parent = this; this.children.push(c); return c; }
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

/* the elements both scripts reach for, matching index.html */
const tabsBox = mk('div', '', 'tabs');
const TABVIEWS = ['rumors', 'vault', 'bell', 'town', 'journal'];
const tabBtns = {};
for (const v of TABVIEWS) {
  tabBtns[v] = mk('button', 'tab-' + v, '', tabsBox, { view: v });
  mk('section', 'view-' + v, 'view');
}
mk('div', 'rumor-phase', 'phase-rail');
mk('button', 'whisper-btn');
mk('span', 'status', 'note');
const feed = mk('section', 'feed');
mk('p', '', 'empty', feed);
mk('button', 'forge-btn');
mk('span', 'forge-status', 'note');
const forgeOut = mk('section', 'forge-out');
mk('section', 'vault-list');
mk('button', 'ring-btn');
mk('span', 'bell-status', 'note');
mk('section', 'letter-out');
mk('div', 'town-phase', 'phase-rail');
mk('p', 'near-note', 'note');
mk('p', 'carrying', 'note');
mk('div', 'dpad');
const npcBox = mk('div', 'npc-box', 'npc-box');
mk('p', 'npc-name', 'npc-name', npcBox);
mk('p', 'npc-line', 'npc-line', npcBox);
mk('button', 'npc-close', '', npcBox);
mk('p', 'poi', 'note');
mk('p', 'watched', 'note');
mk('button', 'export-btn');
mk('button', 'journal-clear-btn');
mk('p', 'journal-status', 'note');
mk('section', 'journal-list');

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
  URL: { createObjectURL: () => 'blob:x', revokeObjectURL: () => {} },
  Blob: class { constructor(p) { this.parts = p; } },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.document = {
  getElementById: (id) => byId.get(id) || null,
  querySelector: (s) => root.querySelector(s),
  querySelectorAll: (s) => root.querySelectorAll(s),
  createElement: (t) => new El(t),
  addEventListener: (t, fn) => { (winListeners[t] ||= []).push(fn); },
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
  willow_start: [1, 0],
  willow_color: '#fff',
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
sandbox.fetch = (url, opts) => {
  const method = (opts && opts.method) || 'GET';
  const body = opts && opts.body ? JSON.parse(opts.body) : null;
  calls.push({ url, method, body });
  const ok = (data) => Promise.resolve({
    ok: true,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(typeof data === 'string' ? data : JSON.stringify(data)),
  });
  if (url === '/api/world') return ok(WORLD);
  if (url === '/api/vault' && method === 'GET') return ok(vault.slice());
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
  if (url === '/api/bell') return ok({ letter: 'For you.' });
  if (url === '/api/journal') return ok([{ at: '2026-08-31T00:00:00Z', kind: 'rumor', speaker: 'a voice', whisper: 'hm', is_true: true }]);
  if (url === '/api/journal/clear') return ok({ cleared: true });
  if (url === '/api/export') return ok('# story');
  throw new Error('harness: unexpected fetch ' + method + ' ' + url);
};

/* ---------- run the real scripts, in page order ---------- */
const ctxVm = vm.createContext(sandbox);
const html = read('web/index.html');
const inline = html.split('<script>')[1].split('</script>')[0];

for (const [label, code] of [
  ['state.js', read('web/state.js')],
  ['town.js', read('web/town.js')],
  ['index.html inline', inline],
]) {
  vm.runInContext('"use strict";' + code, ctxVm, { filename: label });
}

/* ---------- drive the flows ---------- */
const tick = () => new Promise((r) => setTimeout(r, 5));
const S = () => sandbox.window.OLD-STATE-GLOBAL.get();
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

/* the journal tab from the previous task must still work */
check('journal rendered on its tab', byId.get('journal-list').innerHTML.includes('a voice'), byId.get('journal-list').innerHTML);
check('journal status counted', byId.get('journal-status').textContent.includes('1 thing happened'), byId.get('journal-status').textContent);

/* the export button from the previous task must still work */
byId.get('export-btn').click();
await tick();
check('export fetched', calls.some((c) => c.url === '/api/export'));
check('export status set', byId.get('journal-status').textContent.includes('yours to keep'), byId.get('journal-status').textContent);

/* journal clear */
byId.get('journal-clear-btn').click();
await tick();
check('journal clear posted', calls.some((c) => c.url === '/api/journal/clear'));

/* the bell */
byId.get('ring-btn').click();
await tick();
check('bell letter rendered', byId.get('letter-out').innerHTML.includes('For you.'));

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
sandbox.window.OLD-STATE-GLOBAL.setPhase('whispers');
check('unknown phase refused', S().phase === 'dusk', S().phase);

/* dpad still moves */
const dpadBtn = new El('button');
dpadBtn.dataset.dir = 'up';
byId.get('dpad').appendChild(dpadBtn);
dpadBtn.click();
check('dpad move did not throw', true);

console.log('\n' + (fail.length ? 'FAILURES:\n  ' + fail.join('\n  ') : 'all harness checks passed'));
process.exit(fail.length ? 1 : 0);
