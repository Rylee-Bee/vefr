/* complete-act harness: plays the REAL woven file in jsdom for ONE session of a pack whose
   Begin-time rule fires `complete-act`. Reports the end card, then (optionally) presses Interact to
   close it, and dumps localStorage so a second session can be started from it (a reload).

   usage: node act_end_harness.mjs <woven.html> '<spec json>'
   spec:  { store: {key: value}, press: "e" | null }
   prints: { complete, card: {present, visible, role, modal, labelled, buttons, focusLabel, text},
             after: {present, visible}, store, errors } */
import fs from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';

const html = fs.readFileSync(process.argv[2], 'utf8');
const spec = JSON.parse(process.argv[3] || '{}');
const noop = () => {};
const errors = [];
function stubCanvas(window) {
  window.HTMLCanvasElement.prototype.getContext = function () {
    return { canvas: this, save: noop, restore: noop, translate: noop, setTransform: noop,
             fillRect: noop, clearRect: noop, drawImage: noop, beginPath: noop, arc: noop,
             fill: noop, stroke: noop, closePath: noop, moveTo: noop, lineTo: noop, fillText: noop };
  };
}
const virtualConsole = new VirtualConsole();
virtualConsole.on('jsdomError', (e) => errors.push(String((e && e.message) || e)));
const dom = new JSDOM(html, {
  runScripts: 'dangerously', pretendToBeVisual: true, url: 'http://localhost/', virtualConsole,
  beforeParse: (window) => {
    stubCanvas(window);
    window.matchMedia = () => ({ matches: false, addListener: noop, removeListener: noop });
    window.addEventListener('error', (e) => errors.push(String(e.message || e)));
    window.localStorage.setItem('vefr-save-seed', '42');
    for (const [k, v] of Object.entries(spec.store || {})) window.localStorage.setItem(k, v);
  },
});
const { window } = dom;
const document = window.document;
const wait = (ms) => new Promise((r) => window.setTimeout(r, ms));
const visible = (el) => !!el && !el.hidden && el.style.display !== 'none'
  && el.getAttribute('aria-hidden') !== 'true';
const cardInfo = () => {
  const el = document.getElementById('act-end');
  if (!el) return { present: false, visible: false };
  const buttons = [...el.querySelectorAll('button')].map((b) => b.textContent.trim());
  const labelled = el.getAttribute('aria-labelledby');
  return {
    present: true, visible: visible(el), role: el.getAttribute('role'),
    modal: el.getAttribute('aria-modal'),
    labelled: !!(labelled && document.getElementById(labelled)),
    buttons, focusLabel: (document.activeElement && document.activeElement.textContent || '').trim(),
    text: el.textContent,
  };
};

try {
  for (let i = 0; i < 60 && !document.getElementById('ts-enter'); i++) await wait(50);
  document.getElementById('ts-enter').click();
  for (let i = 0; i < 60 && !window.VEFR_COMBAT; i++) await wait(50);
  if (!window.VEFR_COMBAT) throw new Error('boot never produced VEFR_COMBAT');
  await wait(500);                                  // the starts rule has run
  const complete = window.VEFR_ACT_COMPLETE ? JSON.parse(JSON.stringify(window.VEFR_ACT_COMPLETE)) : null;
  const card = cardInfo();
  let after = null;
  if (spec.press) {
    document.dispatchEvent(new window.KeyboardEvent('keydown', { key: spec.press, bubbles: true }));
    await wait(200);
    const a = cardInfo();
    after = { present: a.present, visible: a.visible };
  }
  const store = {};
  for (let i = 0; i < window.localStorage.length; i++) {
    const k = window.localStorage.key(i); store[k] = window.localStorage.getItem(k);
  }
  console.log(JSON.stringify({ complete, card, after, store, errors }));
  window.close();
} catch (err) {
  console.error(String((err && err.stack) || err));
  process.exit(1);
}
