/* Sound harness: plays the REAL woven file in jsdom (no AudioContext exists there, so the player must
   cope), optionally walks to the pinned door spot [9, 4] and presses Interact, and reports the cue log.
   usage: node sound_harness.mjs <woven.html> '<spec json>'
   spec:  { store: {key: value}, door: true|false }
   prints: { sound: window.VEFR_SOUND, toggle: {present, checked}, store, errors } */
import fs from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';

const html = fs.readFileSync(process.argv[2], 'utf8');
const spec = JSON.parse(process.argv[3] || '{}');
const noop = () => {};
const errors = [];
const TO_DOOR = ['down', 'down', 'right', 'right', 'up', 'right', 'right', 'right', 'right',
                 'down', 'down', 'right', 'right'];
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
const press = (dir) => {
  const b = [...document.querySelectorAll('#dpad button')].find((x) => x.dataset.dir === dir);
  if (!b) throw new Error('no dpad button ' + dir);
  b.click();
};
try {
  for (let i = 0; i < 60 && !document.getElementById('ts-enter'); i++) await wait(50);
  document.getElementById('ts-enter').click();
  for (let i = 0; i < 60 && !window.VEFR_COMBAT; i++) await wait(50);
  if (!window.VEFR_COMBAT) throw new Error('boot never produced VEFR_COMBAT');
  await wait(500);
  if (spec.door) {
    TO_DOOR.forEach(press);
    document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'e', bubbles: true }));
    await wait(200);
  }
  document.getElementById('menu-open').click();
  await wait(100);
  const t = document.getElementById('sound-toggle');
  const toggle = { present: !!t, checked: !!(t && t.checked) };
  const sound = window.VEFR_SOUND ? JSON.parse(JSON.stringify(window.VEFR_SOUND)) : null;
  const store = {};
  for (let i = 0; i < window.localStorage.length; i++) {
    const k = window.localStorage.key(i); store[k] = window.localStorage.getItem(k);
  }
  console.log(JSON.stringify({ sound, toggle, store, errors }));
  window.close();
} catch (err) {
  console.error(String((err && err.stack) || err));
  process.exit(1);
}
