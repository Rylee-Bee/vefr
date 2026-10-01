/* walk_events_harness.mjs: executes the REAL web/js/api.js,
   web/js/rooms/workshop.js and web/js/rooms/characters.js inside a node vm
   with a stubbed DOM, fetch, achievements reporter and first walk, then
   drives the play/place loop.

   It pins the T5 contract:
     1. a successful Play it here fires `play_here` AND ticks the
        `play_here` walk step - and nothing else
     2. a real Put in the game fires `character_placed` AND ticks the
        `character_placed` walk step - and nothing else
     3. the Keep preview (previewPlacement) fires neither event and
        ticks neither step

   Deliberately a node-vm harness (like characters_harness.mjs), NOT jsdom -
   jsdom is not installed and there is no network to fetch it.

   Prints one `REPORT <json>` line and exits 0 on success; throws/exits 1
   otherwise. See tests/test_walk_and_events.py. */
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
    this.style = { _props: {} };
    this.children = [];
    this.parent = null;
    this.listeners = {};
    this.hidden = false;
    this.disabled = false;
    this._text = '';
    this._html = '';
    this._value = '';
    this._seq = nodeSeq++;
  }
  get textContent() {
    let s = this._text || '';
    for (const c of this.children) s += c.textContent;
    return s;
  }
  set textContent(v) { this._text = String(v); this.children = []; }
  set innerHTML(v) {
    this._html = String(v);
    this.children = [];
    if (this._html !== '') parseInto(this, this._html);
  }
  get innerHTML() { return this._html === undefined ? '' : this._html; }
  setAttribute(k, v) {
    this.attrs[k] = String(v);
    if (k === 'id') this.id = String(v);
    if (k === 'class' || k === 'className') this.className = String(v);
    if (k === 'value') this._value = String(v);
    if (k === 'hidden') this.hidden = v === true || v === 'true';
    if (k === 'disabled') this.disabled = v === true || v === 'true';
    const m = String(k).match(/^data-([\w-]+)$/);
    if (m) this.dataset[camel(m[1])] = String(v);
  }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  get value() { return this._value === undefined ? '' : this._value; }
  set value(v) { this._value = String(v); if (v !== '') this.attrs.value = String(v); }
  appendChild(c) {
    if (c.parent && c.parent !== this) {
      const i = c.parent.children.indexOf(c);
      if (i >= 0) c.parent.children.splice(i, 1);
    }
    c.parent = this;
    this.children.push(c);
    return c;
  }
  get parentNode() { return this.parent; }
  remove() {
    if (this.parent) this.parent.children = this.parent.children.filter((c) => c !== this);
    this.parent = null;
  }
  focus() { this.focused = true; }
  addEventListener(t, fn) { (this.listeners[t] ||= []).push(fn); }
  click() { this.dispatch('click'); }
  dispatch(type, extra = {}) {
    const ev = { type, target: this, preventDefault() {}, ...extra };
    for (const fn of this.listeners[type] || []) fn(ev);
  }
  querySelectorAll(sel) { return descendants(this).filter((e) => matchOne(e, sel)); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
}

function descendants(el) {
  const out = [];
  for (const c of el.children) { out.push(c); out.push(...descendants(c)); }
  return out;
}
function camel(s) { return s.replace(/-([a-z])/g, (_, c) => c.toUpperCase()); }
function matchOne(el, sel) {
  sel = sel.trim();
  const tagOnly = sel.match(/^([a-zA-Z][\w-]*)$/);
  if (tagOnly) return el.tagName === tagOnly[1].toUpperCase();
  const cls = sel.match(/^\.([\w-]+)$/);
  if (cls) return String(el.className).split(/\s+/).includes(cls[1]);
  const id = sel.match(/^#([\w-]+)$/);
  if (id) return el.id === id[1];
  const tagCls = sel.match(/^([a-zA-Z][\w-]*)\.([\w-]+)$/);
  if (tagCls) {
    return el.tagName === tagCls[1].toUpperCase()
      && String(el.className).split(/\s+/).includes(tagCls[2]);
  }
  throw new Error('harness: unsupported selector ' + sel);
}

/* The room HTML uses void tags (img, input, br...). The characters harness
   parser only ever saw a single div, so it pushed every open tag; here a
   void tag must NOT go on the stack or the tree skews. */
const VOID = new Set(['img', 'input', 'br', 'hr', 'meta', 'link', 'source']);
function parseInto(parent, html) {
  const tagRe = /<(\/?)([a-zA-Z][\w-]*)((?:\s+[^\s=>]+(?:="[^"]*")?)*)\s*\/?>/g;
  const stack = [parent];
  let m;
  while ((m = tagRe.exec(html)) !== null) {
    if (m[1] === '/') { if (stack.length > 1) stack.pop(); continue; }
    const child = new El(m[2]);
    const attrRe = /([^\s=]+)(?:="([^"]*)")?/g;
    let a;
    while ((a = attrRe.exec(m[3] || '')) !== null) {
      if (!a[1]) continue;
      if (a[1] === 'class') child.className = a[2] || '';
      else if (a[1] === 'id') child.id = a[2] || '';
      else child.setAttribute(a[1], a[2] || '');
    }
    stack[stack.length - 1].appendChild(child);
    const selfClosing = m[0].endsWith('/>') || VOID.has(m[2].toLowerCase());
    if (!selfClosing && m[1] !== '/') stack.push(child);
  }
}

const root = new El('body');
const store = {};
const sandbox = {
  console, setTimeout, clearTimeout, Promise, Math, JSON, Date, Array, Object,
  String, Number, Boolean, Error, URLSearchParams,
  history: { replaceState: () => {} },
  localStorage: {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; },
  },
  location: { origin: 'http://localhost', pathname: '/', href: 'http://localhost/', search: '', hash: '' },
  document: {
    documentElement: root,
    body: root,
    createElement: (t) => new El(t),
    getElementById: () => null,
    querySelector: (s) => root.querySelector(s),
    querySelectorAll: (s) => root.querySelectorAll(s),
    addEventListener: () => {},
  },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

/* ---------- fetch stub ---------- */
const calls = [];
sandbox.fetch = function (url, opts) {
  const method = (opts && opts.method) || 'GET';
  const body = opts && opts.body ? JSON.parse(opts.body) : null;
  calls.push({ url, method, body });
  const ok = (data) => Promise.resolve({
    ok: true, status: 200, statusText: 'OK',
    json: () => Promise.resolve(data),
  });
  const fail = (status, detail) => Promise.resolve({
    ok: false, status, statusText: 'ERR',
    json: () => Promise.resolve({ detail }),
  });
  if (url === '/api/wiki') return ok({ characters: [] });
  if (url === '/api/world') return ok({ title: 'Testfield', speakers: [], phases: ['dusk', 'dawn'] });
  if (url === '/api/vault' && method === 'GET') return ok({ items: [] });
  if (url === '/api/vault' && method === 'POST') return ok({ bond: body && body.bond });
  if (url === '/api/builder/face/roll') {
    return ok({ ok: true, face: { name: 'Stern', role: 'guard', seed: 'Halt. ...oh, it is you.', at: [4, 1] } });
  }
  if (url === '/api/builder/character/place') {
    const at = body.at || [4, 1];
    const preview = {
      id: body.id, region: body.region,
      speaker: { name: body.display_name, at: at, near: body.near || 'nearby',
        voice_file: 'voices/' + body.id + '.md', seeds: body.seeds },
      voice_file: 'voices/' + body.id + '.md', voice_text: body.voice, at: at,
    };
    return ok({ ok: true, written: body.preview !== true, files: [], backup: null, preview: preview });
  }
  throw new Error('harness: unexpected fetch ' + method + ' ' + url);
};

/* ---------- the studio kit the rooms expect ---------- */
function h(tag, attrs, children) {
  const e = new El(tag);
  if (attrs) Object.keys(attrs).forEach((k) => {
    if (k === 'className') e.className = attrs[k];
    else if (k === 'textContent') e.textContent = attrs[k];
    else if (k === 'innerHTML') e.innerHTML = attrs[k];
    else if (k === 'hidden') e.hidden = attrs[k] === true;
    else if (k === 'value') e.value = attrs[k];
    else e.setAttribute(k, attrs[k]);
  });
  if (children) {
    if (typeof children === 'string') e.innerHTML = children;
    else if (Array.isArray(children)) children.forEach((c) => { if (c) e.appendChild(c); });
    else e.appendChild(children);
  }
  return e;
}

const main = new El('main');
root.appendChild(main);

/* What T5 watches: the reported events and the walk ticks, in order. */
const events = [];
const attempts = [];
sandbox.VEFR_ACHIEVE = (event) => { events.push(event); return Promise.resolve(); };

sandbox.VEFR_STUDIO = {
  screens: {},
  API: null,
  h: h,
  main: main,
  truncate: (s, n) => (!s ? '' : (s.length > n ? s.slice(0, n) + '\u2026' : s)),
  residentLine: () => null,
  emptyState: (text) => h('div', { className: 'empty', textContent: text }),
  loadingState: (text) => h('div', { className: 'loading', textContent: text }),
  spot: () => h('div', {}),
  firstWalk: { attempt: (id) => { attempts.push(id); }, start: () => {}, reset: () => {}, openSheet: () => {} },
  openFolio: () => {},
  navigate: () => {},
  ferryNote: () => {},
  studioAudio: { clank: () => {} },
};

/* ---------- run the real scripts in page order ---------- */
const ctxVm = vm.createContext(sandbox);
vm.runInContext('"use strict";\n' + read('web/js/api.js'), ctxVm, { filename: 'api.js' });
sandbox.VEFR_STUDIO.API = sandbox.window.VEFR_API;
vm.runInContext('"use strict";\n' + read('web/js/rooms/workshop.js'), ctxVm, { filename: 'workshop.js' });
vm.runInContext('"use strict";\n' + read('web/js/rooms/characters.js'), ctxVm, { filename: 'characters.js' });

/* Play it here must weave first; the fetch route is not the point, the
   success path is. Resolve it directly so the pane opens. */
sandbox.VEFR_API.weaveBuild = () => Promise.resolve({
  name: 'testfield.html', size_bytes: 4096, download_url: '/api/builder/weave/download/testfield.html',
});

const workshop = sandbox.VEFR_STUDIO.screens.workshop;
const characters = sandbox.VEFR_STUDIO.screens.characters;
const tick = () => new Promise((r) => setTimeout(r, 0));
const flush = async () => { for (let i = 0; i < 8; i++) await tick(); };
const byId = (id) => root.querySelector('#' + id) || descendants(root).find((e) => e.id === id) || null;
const allButtons = () => descendants(root).filter((e) => e.tagName === 'BUTTON');
const button = (text) => allButtons().find((b) => b.textContent === text) || null;
const snapshot = () => ({ events: events.slice(), attempts: attempts.slice() });

try {
  /* ---------------- 1. Play it here: event + tick ---------------- */
  workshop.init();
  const play = byId('ws-weave-play');
  if (!play) throw new Error('no #ws-weave-play button after workshop.init()');
  play.click();
  await flush();
  const afterPlay = snapshot();

  /* ---------------- 2. Keep (preview): neither ---------------- */
  events.length = 0; attempts.length = 0;
  characters.init();
  characters.enter();
  await flush();
  const roll = button('Suggest a character');
  if (!roll) throw new Error('no Suggest a character button');
  roll.click();
  await flush();
  const keep = button('Keep this character');
  if (!keep) throw new Error('no Keep this character button');
  keep.click();
  await flush();
  const afterPreview = snapshot();

  /* ---------------- 3. Put in the game: event + tick ---------------- */
  events.length = 0; attempts.length = 0;
  const put = button('Put in the game');
  if (!put) throw new Error('no Put in the game button after preview');
  put.click();
  await flush();
  const afterPut = snapshot();

  console.log('REPORT ' + JSON.stringify({ afterPlay, afterPreview, afterPut }));
} catch (err) {
  console.log('HARNESS ERROR: ' + ((err && err.stack) || String(err)));
  process.exit(1);
}
