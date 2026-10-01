/* characters.js harness: executes the REAL web/js/api.js and
   web/js/rooms/characters.js inside a node vm with a stubbed DOM and
   fetch, then drives the Folks room's Keep -> preview -> Put in the
   game flow.

   It pins the contract T2 built:
     1. Keep sends POST /api/builder/character/place with preview:true
        (and never writes)
     2. the preview card shows the name, the role and the first seed
     3. Put in the game sends the same request with preview:false
     4. a 422 surfaces the server's own plain sentence on the page
     5. a 409 offers the replace step in plain words, real buttons
     6. the vault keep still works as its own explicit step

   Prints "ALL PASS" and exits 0 on success; throws/exits 1 otherwise.
   Deliberately a node-vm harness (like board_harness.mjs), NOT jsdom -
   jsdom is not installed in this environment and no network is
   available to fetch it. See tests/test_web_characters_place.py.
*/
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
  if (sel === '*') return true;
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

/* Only needs to read the one innerHTML string characters.js writes:
   a single empty <div class="..." id="folks-content"></div>. */
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
    if (!m[0].endsWith('/>') && m[1] !== '/') stack.push(child);
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
let mode = 'ok';
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
    if (mode === '422') return fail(422, 'the tile [4, 1] is not walkable');
    if (mode === '409') return fail(409, 'a character with that id already exists \u2014 send force to replace it');
    const at = body.at || [4, 1];
    const preview = {
      id: body.id,
      region: body.region,
      speaker: {
        name: body.display_name,
        at: at,
        near: body.near || 'nearby',
        voice_file: 'voices/' + body.id + '.md',
        seeds: body.seeds,
      },
      voice_file: 'voices/' + body.id + '.md',
      voice_text: body.voice,
      at: at,
    };
    return ok({
      ok: true,
      written: body.preview !== true,
      files: [],
      backup: null,
      preview: preview,
    });
  }
  throw new Error('harness: unexpected fetch ' + method + ' ' + url);
};

/* ---------- the studio kit characters.js expects ---------- */
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
  firstWalk: { attempt: () => {} },
  openFolio: () => {},
  studioAudio: { clank: () => {} },
  ferryNote: () => {},
};

/* ---------- run the real scripts in page order ---------- */
const ctxVm = vm.createContext(sandbox);
// api.js first so characters.js's IIFE captures the live API object.
vm.runInContext('"use strict";\n' + read('web/js/api.js'), ctxVm, { filename: 'api.js' });
sandbox.VEFR_STUDIO.API = sandbox.window.VEFR_API;
vm.runInContext('"use strict";\n' + read('web/js/rooms/characters.js'), ctxVm, { filename: 'characters.js' });

const characters = sandbox.VEFR_STUDIO.screens.characters;
const tick = () => new Promise((r) => setTimeout(r, 0));

const fails = [];
const check = (name, cond, extra = '') => {
  if (!cond) fails.push(name + (extra ? ' -- ' + extra : ''));
  console.log((cond ? 'ok   ' : 'FAIL ') + name + (extra && !cond ? ' -- ' + extra : ''));
};

const allButtons = () => descendants(root).filter((e) => e.tagName === 'BUTTON');
const button = (text) => allButtons().find((b) => b.textContent === text) || null;
const pageText = () => root.textContent;
const placeCalls = () => calls.filter((c) => c.url === '/api/builder/character/place');

async function enterRoom() {
  characters.enter();
  await tick();
  await tick();
}

async function roll() {
  const b = button('Suggest a character');
  if (!b) throw new Error('no Suggest a character button');
  b.click();
  await tick();
  await tick();
}

try {
  characters.init();
  await tick();

  /* ---------------- 1. Keep previews, writes nothing ---------------- */
  calls.length = 0;
  mode = 'ok';
  await enterRoom();
  await roll();

  const keep = button('Keep this character');
  check('the draft panel offers Keep', !!keep);
  const vault = button('Keep in the vault');
  check('the draft panel still offers the vault keep', !!vault);

  keep.click();
  await tick();
  await tick();

  const previewCall = placeCalls().pop();
  check('Keep calls the place route', !!previewCall);
  check('Keep asks for a preview', previewCall && previewCall.body.preview === true,
    JSON.stringify(previewCall && previewCall.body));
  check('Keep sends no force', previewCall && previewCall.body.force === false,
    JSON.stringify(previewCall && previewCall.body));
  check('Keep never wrote', !calls.some((c) => c.url === '/api/vault' && c.method === 'POST'));
  check('the slug is derived from the name', previewCall && previewCall.body.id === 'stern',
    previewCall && previewCall.body.id);
  check('the display name is sent whole', previewCall && previewCall.body.display_name === 'Stern',
    previewCall && previewCall.body.display_name);

  /* ---------------- 2. The preview card ---------------- */
  check('the preview card shows the name', pageText().includes('Stern'), pageText());
  check('the preview card shows the role', pageText().includes('guard'), pageText());
  check('the preview card shows the first line', pageText().includes('Halt. ...oh, it is you.'),
    pageText());

  /* ---------------- 3. Put in the game writes ---------------- */
  const put = button('Put in the game');
  check('the preview card offers Put in the game', !!put);
  check('the preview card offers Cancel', !!button('Cancel'));
  put.click();
  await tick();
  await tick();
  await tick();

  const writeCall = placeCalls().pop();
  check('Put calls the place route again', !!writeCall);
  check('Put asks for a real write', writeCall && writeCall.body.preview === false,
    JSON.stringify(writeCall && writeCall.body));
  check('Put is the same character', writeCall && writeCall.body.id === 'stern');
  check('a confirmation in words is shown', pageText().includes('Stern is in the game'),
    pageText());

  /* ---------------- 4. A 422 shows the server's sentence ---------------- */
  calls.length = 0;
  mode = '422';
  await enterRoom();
  await roll();
  button('Keep this character').click();
  await tick();
  await tick();
  check('a 422 shows the server\u2019s plain sentence',
    pageText().includes('the tile [4, 1] is not walkable'), pageText());
  check('a 422 writes nothing',
    !calls.some((c) => c.url === '/api/builder/character/place' && c.body && c.body.preview === false));

  /* ---------------- 5. A 409 offers replace ---------------- */
  calls.length = 0;
  mode = '409';
  await enterRoom();
  await roll();
  button('Keep this character').click();
  await tick();
  await tick();
  check('a 409 is surfaced as a plain question',
    pageText().includes('Stern is already in the game. Replace them?'), pageText());
  const replace = button('Replace');
  check('a 409 offers a real Replace button', !!replace);
  if (replace) {
    replace.click();
    await tick();
    await tick();
    const forcedCall = placeCalls().pop();
    check('Replace previews with force', forcedCall && forcedCall.body.preview === true
      && forcedCall.body.force === true, JSON.stringify(forcedCall && forcedCall.body));
  }

  /* ---------------- 6. The vault keep still works ---------------- */
  calls.length = 0;
  mode = 'ok';
  await enterRoom();
  await roll();
  const vault2 = button('Keep in the vault');
  check('the vault keep survives a fresh room', !!vault2);
  vault2.click();
  await tick();
  await tick();
  const vaultCall = calls.filter((c) => c.url === '/api/vault' && c.method === 'POST').pop();
  check('the vault keep still posts to the vault', !!vaultCall);
  check('the vault card is still a face',
    vaultCall && vaultCall.body.kind === 'face', JSON.stringify(vaultCall && vaultCall.body));
} catch (err) {
  fails.push('HARNESS ERROR: ' + ((err && err.message) || String(err)));
  console.log('FAIL HARNESS ERROR: ' + ((err && err.stack) || String(err)));
}

if (fails.length) {
  console.log('\n' + fails.length + ' FAILED');
  process.exit(1);
}
console.log('\nALL PASS');
