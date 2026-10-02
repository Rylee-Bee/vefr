/* Rules-save harness: plays the REAL woven file in jsdom for ONE session and
   prints what the rules engine holds. A reload is simulated by the caller:
   feed the previous run's printed `store` back in as `spec.store`.

   usage: node rules_save_harness.mjs <woven.html> '<spec json>'
   spec:  { store: {key: value}, begin: true, walk: ["right"], peek: false, storage: "ok"|"get-throws"|"set-throws" }
       peek: call the player's rulesStateNow() at the end, so a state loaded from a save can be read with no event fired
   prints: { why, state: {flags, fired, beliefs, items} | null, store, world, errors, narrator }

   Deterministic: fixed settle times, no clock reads in the output. */
import fs from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';

const html = fs.readFileSync(process.argv[2], 'utf8');
const spec = JSON.parse(process.argv[3] || '{}');
const noop = () => {};
const errors = [];

function stubCanvas(window) {
  window.HTMLCanvasElement.prototype.getContext = function () {
    return {
      canvas: this, save: noop, restore: noop, translate: noop,
      setTransform: noop, fillRect: noop, clearRect: noop, drawImage: noop,
      beginPath: noop, arc: noop, fill: noop, stroke: noop,
      closePath: noop, moveTo: noop, lineTo: noop, fillText: noop,
    };
  };
}

const virtualConsole = new VirtualConsole();
virtualConsole.on('jsdomError', (e) => errors.push(String((e && e.message) || e)));

const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  url: 'http://localhost/',
  virtualConsole,
  beforeParse: (window) => {
    stubCanvas(window);
    window.matchMedia = () => ({ matches: false, addListener: noop, removeListener: noop });
    window.addEventListener('error', (e) => errors.push(String(e.message || e)));
    for (const [k, v] of Object.entries(spec.store || {})) window.localStorage.setItem(k, v);
    if (spec.storage === 'get-throws') {
      Object.defineProperty(window, 'localStorage', {
        get() { throw new Error('storage blocked'); }, configurable: true,
      });
    } else if (spec.storage === 'set-throws') {
      window.Storage.prototype.setItem = function () { throw new Error('quota'); };
    }
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
  if (spec.begin !== false) {
    document.getElementById('ts-enter').click();
    await wait(600);
  }
  for (const dir of spec.walk || []) {
    press(dir);
    await wait(400);
  }
  if (spec.peek && typeof window.rulesStateNow === 'function') window.rulesStateNow();
  const s = window.VEFR_RULES_STATE || null;
  let store = {};
  if (spec.storage !== 'get-throws') {
    for (let i = 0; i < window.localStorage.length; i++) {
      const k = window.localStorage.key(i);
      store[k] = window.localStorage.getItem(k);
    }
  }
  console.log(JSON.stringify({
    why: (window.VEFR_WHY || []).slice(),
    state: s ? { flags: s.flags, fired: s.fired, beliefs: s.beliefs, items: s.items } : null,
    store,
    world: window.VEFR_WORLD || null,
    errors,
    narrator: (document.getElementById('combat-live') || {}).textContent || '',
  }));
} catch (err) {
  console.error(String((err && err.stack) || err));
  process.exit(1);
}
