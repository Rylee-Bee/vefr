/* Kitchen harness: EXECUTES the woven single-file player's inline
   script against a stub DOM and PLAYS one cooking morning end to end.
   The pleasant-loop protocol's mechanical half: it counts clicks,
   reads every feedback line, and returns the morning's journal and
   the printed page so pytest can assert the loop actually looped.

   usage: node kitchen_harness.mjs <woven.html> */
import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(process.argv[2], 'utf8');
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];

/* ---------- minimal DOM ---------- */
let seq = 0;
const byId = new Map();

class El {
  constructor(tag) {
    this.tagName = String(tag || 'div').toUpperCase();
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
    this._html = '';
    this._seq = seq++;
    this.classList = { add: () => {}, remove: () => {}, contains: () => false };
  }
  set textContent(v) { this._text = String(v); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(''); }
  set innerHTML(v) { this._html = String(v); this.children = []; }
  get innerHTML() { return this._html; }
  appendChild(c) { c.parent = this; this.children.push(c); return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k] ?? null; }
  addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  focus() {}
  click() {
    CLICKS.total += 1;
    /* real clicks bubble: delegated listeners live on containers */
    let el = this;
    while (el) {
      (el.listeners.click || []).forEach((fn) => fn({ target: this }));
      el = el.parent;
    }
  }
  closest(sel) {
    /* supports button[data-x] */
    const mAttr = sel.match(/^button\[data-([\w-]+)\]$/);
    let el = this;
    while (el) {
      if (el.tagName === 'BUTTON') {
        if (!mAttr || el.dataset[mAttr[1]] !== undefined) return el;
      }
      el = el.parent;
    }
    return null;
  }
  querySelectorAll(sel) { return queryAll(this, sel); }
}

function matchSeg(el, seg) {
  const m = seg.match(/^([a-z]*)?(\.[\w-]+)?$/);
  if (!m) return false;
  const [, tag, cls] = m;
  if (tag && el.tagName !== tag.toUpperCase()) return false;
  if (cls && !(' ' + el.className + ' ').includes(' ' + cls.slice(1) + ' ')) return false;
  return Boolean(tag || cls);
}

function descend(el, segs, out) {
  if (!segs.length) return;
  for (const child of el.children) {
    if (matchSeg(child, segs[0])) {
      if (segs.length === 1) out.push(child);
      else descend(child, segs.slice(1), out);
    }
    descend(child, segs, out);
  }
}

function queryAll(root, sel) {
  const out = [];
  for (const part of sel.split(',')) {
    const segs = part.trim().split(/\s*>\s*|\s+/).filter(Boolean)
      .map((s) => (s.startsWith('#') ? s : s));
    if (!segs.length) continue;
    if (segs[0].startsWith('#')) {
      const start = byId.get(segs[0].slice(1));
      if (!start) continue;
      if (segs.length === 1) { out.push(start); continue; }
      descend(start, segs.slice(1), out);
    } else {
      descend(root, segs, out);
    }
  }
  return out;
}

const CLICKS = { total: 0 };
const store = new Map();
const localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
};

const documentEl = new El('body');
const document = {
  body: documentEl,
  getElementById: (id) => {
    if (!byId.has(id)) {
      const el = new El('div');
      el.id = id;
      byId.set(id, el);
    }
    return byId.get(id);
  },
  createElement: (tag) => new El(tag),
  querySelectorAll: (sel) => queryAll(documentEl, sel),
  addEventListener: () => {},
};

const context = {
  document,
  window: null,
  localStorage,
  console,
  alert: () => {},
  setTimeout: (fn) => { fn(); return 0; },
  requestAnimationFrame: (fn) => { fn(); },
  location: { search: '', pathname: '/' },
  fetch: () => Promise.reject(new Error('offline harness')),
  VEFR_WORLD: {}, VEFR_LOGBOK: '', VEFR_LEDGER: '', VEFR_VOICES: {},
  VEFR_POOL: {}, VEFR_FRAGMENTS: {},
};
context.window = context;
context.globalThis = context;
vm.createContext(context);
vm.runInContext(script, context, { filename: 'woven.html' });

/* ---------- play the morning ---------- */
const log = [];
const line = () => document.getElementById('k-line')._text;
const pantryClick = (label) => {
  const b = queryAll(document.getElementById('k-pantry'), 'button')
    .find((x) => x._text === label);
  if (!b) throw new Error('no pantry button ' + label);
  b.click();
};

let clicksT1 = -1;
let clicksT2 = -1;
/* the stub DOM doesn't parse markup: seed the hidden states the
   template ships with, so initKitchen's reveals mean something */
['kitchen', 'k-headlines', 'k-page', 'k-again'].forEach((id) => {
  document.getElementById(id).hidden = true;
});
context.initKitchen();
try {
log.push(['open', document.getElementById('k-open')._text]);
log.push(['line0', line()]);
log.push(['tickets', queryAll(document.getElementById('k-tickets'), '.card').length]);

const clicksBefore = CLICKS.total;
pantryClick('fried egg'); pantryClick('red salsa');
log.push(['wrap1', document.getElementById('k-wrap')._text]);
document.getElementById('k-serve').click();
log.push(['serve1', line()]);
clicksT1 = CLICKS.total - clicksBefore;

const c2 = CLICKS.total;
pantryClick('melted cheese');
document.getElementById('k-serve').click();
log.push(['serve2-wrong', line()]);
clicksT2 = CLICKS.total - c2;

document.getElementById('k-aside').click();
log.push(['aside3', line()]);
log.push(['headlines-visible', !document.getElementById('k-headlines').hidden]);
const heads = queryAll(document.getElementById('k-headline-list'), 'button');
log.push(['headline-count', heads.length]);
heads[1].click();
const page = document.getElementById('k-page');
log.push(['page-visible', !page.hidden]);
log.push(['page-text', page.textContent.replace(/\s+/g, ' ').trim()]);
const journal = JSON.parse(localStorage.getItem('vefr-packaged-kitchen') || '[]');
log.push(['journal', journal.map((e) => e.kind)]);
document.getElementById('k-sleep').click();
log.push(['after-sleep', line()]);
log.push(['done-after-sleep', queryAll(document.getElementById('k-tickets'), '.card.done').length]);
} catch (e) {
  log.push(['HARNESS-ERROR', String(e && e.message || e)]);
}

process.stdout.write(JSON.stringify({
  log,
  clicks: { total: CLICKS.total, t1: clicksT1, t2: clicksT2 },
  setIntervalInTemplate: html.includes('setInterval'),
}, null, 1));
