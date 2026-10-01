/* undo_harness.mjs: executes the REAL web/js/api.js and
   web/js/rooms/workshop.js inside a node vm with a stubbed DOM and
   fetch, then presses the Desk's **Undo last edit** button.

   It pins the client contract:
     1. the button exists, is a real <button type="button">, and its
        message region is role="status" aria-live="polite"
     2. pressing it POSTs /api/builder/edits/undo with a JSON body
        ({"name": null} - the route falls back to the active world,
        what characters.js already sends for a placement)
     3. on 200 the route's own sentence appears verbatim in the region,
        the Desk reloads, and the button is re-enabled
     4. on 404 the message is friendly (the route's words), not an
        error, no status code, and NOTHING else is refetched
     5. on any other failure the sentence is plain - never "409
        Conflict" - and the button is re-enabled
     6. the button is disabled while a request is in flight

   Deliberately a node-vm harness (like characters_harness.mjs), NOT
   jsdom - jsdom is not installed and there is no network to fetch it.

   Prints "ALL PASS" and exits 0 on success; exits 1 otherwise.
   See tests/test_web_undo_button.py. */
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
    this._text = '';
    if (this._html !== '') parseInto(this, this._html);
  }
  get innerHTML() { return this._html === undefined ? '' : this._html; }
  setAttribute(k, v) {
    this.attrs[k] = String(v);
    if (k === 'id') this.id = String(v);
    if (k === 'class' || k === 'className') this.className = String(v);
    if (k === 'value') this._value = String(v);
    if (k === 'type') this.type = String(v);
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

/* The room HTML uses void tags (img, input, br...). Text between tags is
   kept too, so a button's label reads back from textContent exactly as
   an accessible name would. */
const VOID = new Set(['img', 'input', 'br', 'hr', 'meta', 'link', 'source']);
function parseInto(parent, html) {
  const tagRe = /<(\/?)([a-zA-Z][\w-]*)((?:\s+[^\s=>]+(?:="[^"]*")?)*)\s*\/?>/g;
  const stack = [parent];
  let last = 0;
  let m;
  while ((m = tagRe.exec(html)) !== null) {
    const text = html.slice(last, m.index);
    if (text) stack[stack.length - 1]._text += text;
    last = tagRe.lastIndex;
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
  navigator: {},
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
  calls.push({ url, method, body, headers: (opts && opts.headers) || {} });
  const ok = (data) => Promise.resolve({
    ok: true, status: 200, statusText: 'OK',
    json: () => Promise.resolve(data),
  });
  const fail = (status, detail) => Promise.resolve({
    ok: false, status, statusText: 'ERR',
    json: () => Promise.resolve({ detail }),
  });
  if (url === '/api/world') {
    return ok({ title: 'Testfield', act: 'The brief', surface: 'a field', phases: ['dusk', 'dawn'] });
  }
  if (url === '/api/journal') return ok({ entries: [] });
  if (url === '/api/builder/edits/undo') {
    if (mode === '404') return fail(404, 'there is nothing to undo in this world');
    if (mode === '409') return fail(409, 'that edit has no backup to put back');
    return ok({
      ok: true,
      undone: 'put Stern at the gate',
      message: 'Undid the last edit: put Stern at the gate.',
    });
  }
  throw new Error('harness: unexpected fetch ' + method + ' ' + url);
};

/* ---------- the studio kit the room expects ---------- */
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
  AMBIENCE: { workshop: 'The lamp is warm.' },
  actionsLine: () => ({ kind: '', text: '' }),
  chronicleLine: () => ({ kind: '', text: '' }),
  emptyState: (text) => h('div', { className: 'empty', textContent: text }),
  esc: (s) => String(s == null ? '' : s),
  firstWalk: { attempt: () => {} },
  foldChronicle: () => [],
  formatTime: (t) => String(t == null ? '' : t),
  inhabitWorld: () => {},
  loadingState: (text) => h('div', { className: 'loading', textContent: text }),
  navigate: () => {},
  openFolio: () => {},
  setLantern: () => {},
  truncate: (s, n) => (!s ? '' : (s.length > n ? s.slice(0, n) + '\u2026' : s)),
};

/* ---------- run the real scripts in page order ---------- */
const ctxVm = vm.createContext(sandbox);
vm.runInContext('"use strict";\n' + read('web/js/api.js'), ctxVm, { filename: 'api.js' });
sandbox.VEFR_STUDIO.API = sandbox.window.VEFR_API;
vm.runInContext('"use strict";\n' + read('web/js/rooms/workshop.js'), ctxVm, { filename: 'workshop.js' });

const workshop = sandbox.VEFR_STUDIO.screens.workshop;
const tick = () => new Promise((r) => setTimeout(r, 0));
const flush = async () => { for (let i = 0; i < 8; i++) await tick(); };
const byId = (id) => root.querySelector('#' + id) || descendants(root).find((e) => e.id === id) || null;
const undoCalls = () => calls.filter((c) => c.url === '/api/builder/edits/undo');

const fails = [];
const check = (name, cond, extra = '') => {
  if (!cond) fails.push(name + (extra ? ' -- ' + extra : ''));
  console.log((cond ? 'ok   ' : 'FAIL ') + name + (extra && !cond ? ' -- ' + extra : ''));
};

try {
  workshop.init();

  /* ---------------- 1. the button and its live region ---------------- */
  const btn = byId('ws-undo-edit');
  check('the Desk offers an Undo last edit button',
    !!btn && btn.tagName === 'BUTTON', btn && btn.tagName);
  check('it is a real button with type=button', !!btn && btn.type === 'button',
    btn && String(btn.type));
  check('its accessible name is exactly "Undo last edit"',
    !!btn && btn.textContent === 'Undo last edit', btn && JSON.stringify(btn.textContent));
  const region = byId('ws-undo-status');
  check('the message region is a polite status',
    !!region && region.getAttribute('role') === 'status'
      && region.getAttribute('aria-live') === 'polite');

  /* ---------------- 2. on 200: the route's sentence, verbatim ------- */
  calls.length = 0;
  mode = 'ok';
  btn.click();
  check('the button is disabled while the request is in flight', btn.disabled === true);
  await flush();

  const post = undoCalls()[0];
  check('a POST to /api/builder/edits/undo was made', !!post && post.method === 'POST',
    JSON.stringify(post && { url: post.url, method: post.method }));
  check('it carried a JSON body', !!post && typeof post.body === 'object'
    && post.body !== null && post.headers['Content-Type'] === 'application/json',
    JSON.stringify(post && post.headers));
  check('it asked for the active world by name: null',
    !!post && 'name' in post.body && post.body.name === null,
    JSON.stringify(post && post.body));
  check("the route's sentence appears verbatim in the status region",
    region.textContent === 'Undid the last edit: put Stern at the gate.',
    JSON.stringify(region.textContent));
  check('the Desk reloaded its content after the undo',
    calls.some((c) => c.url === '/api/world'),
    JSON.stringify(calls.map((c) => c.url)));
  check('the button is re-enabled after the success', btn.disabled === false);

  /* ---------------- 3. on 404: friendly, and nothing else ---------- */
  calls.length = 0;
  mode = '404';
  btn.click();
  check('the button is disabled while the 404 is in flight', btn.disabled === true);
  await flush();

  const empty = region.textContent;
  check('a 404 keeps the route’s own words', empty.includes('nothing to undo'),
    JSON.stringify(empty));
  check('a 404 is friendly, not an error',
    !empty.includes('404') && !empty.includes('ERR') && !empty.includes('Error'),
    JSON.stringify(empty));
  check('a 404 changes nothing else (no Desk reload)',
    !calls.some((c) => c.url === '/api/world'),
    JSON.stringify(calls.map((c) => c.url)));
  check('the button is re-enabled after the 404', btn.disabled === false);

  /* ---------------- 4. any other failure: a plain sentence --------- */
  calls.length = 0;
  mode = '409';
  btn.click();
  check('the button is disabled while the 409 is in flight', btn.disabled === true);
  await flush();

  const refused = region.textContent;
  check('a 409 never shows a raw status or conflict',
    !refused.includes('409') && !refused.includes('Conflict') && !refused.includes('Error')
      && !refused.includes('ERR'),
    JSON.stringify(refused));
  check('a 409 is a plain, friendly sentence', refused.length > 0
    && refused.includes('nothing changed'), JSON.stringify(refused));
  check('a 409 changes nothing else (no Desk reload)',
    !calls.some((c) => c.url === '/api/world'),
    JSON.stringify(calls.map((c) => c.url)));
  check('the button is re-enabled after the 409', btn.disabled === false);
} catch (err) {
  fails.push('HARNESS ERROR: ' + ((err && err.message) || String(err)));
  console.log('FAIL HARNESS ERROR: ' + ((err && err.stack) || String(err)));
}

if (fails.length) {
  console.log('\n' + fails.length + ' FAILED');
  process.exit(1);
}
console.log('\nALL PASS');
