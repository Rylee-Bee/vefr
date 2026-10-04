/* Album harness: plays the REAL woven file in jsdom for ONE session, then opens Menu > Album.
   usage: node album_harness.mjs <woven.html> '<spec json>'   spec: { store: {key: value} }
   prints: { album: window.VEFR_ALBUM, live, button: {present, visible}, panel: text, store, errors } */
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
try {
  for (let i = 0; i < 60 && !document.getElementById('ts-enter'); i++) await wait(50);
  document.getElementById('ts-enter').click();
  for (let i = 0; i < 60 && !window.VEFR_COMBAT; i++) await wait(50);
  if (!window.VEFR_COMBAT) throw new Error('boot never produced VEFR_COMBAT');
  await wait(500);
  const live = (document.getElementById('combat-live') || {}).textContent || '';
  document.getElementById('menu-open').click();
  await wait(100);
  const btn = document.querySelector('#menu [data-panel="album"]');
  const button = { present: !!btn, visible: !!btn && !btn.hidden && !(btn.parentElement && btn.parentElement.hidden) };
  let panel = '';
  if (btn) {
    btn.click();
    await wait(100);
    panel = (document.getElementById('album-panel') || {}).textContent || '';
  }
  const album = window.VEFR_ALBUM ? JSON.parse(JSON.stringify(window.VEFR_ALBUM)) : null;
  const store = {};
  for (let i = 0; i < window.localStorage.length; i++) {
    const k = window.localStorage.key(i); store[k] = window.localStorage.getItem(k);
  }
  console.log(JSON.stringify({ album, live, button, panel, store, errors }));
  window.close();
} catch (err) {
  console.error(String((err && err.stack) || err));
  process.exit(1);
}
