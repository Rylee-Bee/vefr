/* Walk-sheet harness: plays the REAL woven file in jsdom and reports window.VEFR_HERO_FRAME after the
   hero stands, steps once in a direction, and settles.
   usage: node walk_harness.mjs <woven.html> '<spec json>'   spec: { steps: ["right", ...] }
   prints: { sheets: window.VEFR_SPRITE_SHEETS keys, start, during: [...frame after each step], settled, errors } */
import fs from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';

const html = fs.readFileSync(process.argv[2], 'utf8');
const spec = JSON.parse(process.argv[3] || '{}');
const noop = () => {};
const errors = [];
function stubCanvas(window) {
  window.HTMLCanvasElement.prototype.getContext = function () {
    return { canvas: this, save: noop, restore: noop, translate: noop, setTransform: noop, scale: noop,
             fillRect: noop, clearRect: noop, drawImage: noop, beginPath: noop, arc: noop,
             fill: noop, stroke: noop, closePath: noop, moveTo: noop, lineTo: noop, fillText: noop, rotate: noop };
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
  },
});
const { window } = dom;
const document = window.document;
const wait = (ms) => new Promise((r) => window.setTimeout(r, ms));
const frame = () => (window.VEFR_HERO_FRAME ? JSON.parse(JSON.stringify(window.VEFR_HERO_FRAME)) : null);
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
  await wait(400);
  const start = frame();
  const during = [];
  for (const d of spec.steps || []) { press(d); during.push(frame()); await wait(60); }
  await wait(900);
  const settled = frame();
  console.log(JSON.stringify({ sheets: Object.keys(window.VEFR_SPRITE_SHEETS || {}), start, during, settled, errors }));
  window.close();
} catch (err) {
  console.error(String((err && err.stack) || err));
  process.exit(1);
}
