/* Locked-door harness: plays the REAL woven file in jsdom for ONE session, walks the hero to
   the pinned door spot [9, 4] of make_interact_pack.py, presses Interact, and prints what happened.

   usage: node lock_play_harness.mjs <woven.html> '<spec json>'
   spec:  { store: {key: value}, key: "e" }
   prints: { regionBefore, regionAfter, heroBefore, heroAfter, hint, label, narrator, bag, errors } */
import fs from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';

const html = fs.readFileSync(process.argv[2], 'utf8');
const spec = JSON.parse(process.argv[3] || '{}');
const noop = () => {};
const errors = [];
const TO_DOOR = ['down', 'down', 'right', 'right', 'up', 'right', 'right', 'right', 'right',
                 'down', 'down', 'right', 'right'];                       // [9, 4], clear of the rat

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
const txt = (id) => (document.getElementById(id) || {}).textContent || '';
const snap = () => JSON.parse(JSON.stringify(window.VEFR_COMBAT));
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
  await wait(400);                                  // the starts rule, if any, has run
  TO_DOOR.forEach(press);
  const before = snap();
  const hint = txt('use-hint'), label = txt('interact-label');
  document.dispatchEvent(new window.KeyboardEvent('keydown', { key: spec.key || 'e', bubbles: true }));
  await wait(150);
  const after = snap();
  let bag = [];
  try { bag = JSON.parse(window.localStorage.getItem('vefr-bag-' + (window.VEFR_WORLD.name)) || '[]'); } catch (e) { /* none */ }
  console.log(JSON.stringify({
    regionBefore: before.region, regionAfter: after.region,
    heroBefore: before.hero.at, heroAfter: after.hero.at,
    hint, label, narrator: txt('combat-live'), near: txt('near'), bag, errors,
  }));
} catch (err) {
  console.error(String((err && err.stack) || err));
  process.exit(1);
}
