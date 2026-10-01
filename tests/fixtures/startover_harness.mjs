/* Start-over harness: executes the REAL window.startoverKeys helper
   extracted from web/packaged.html between its own marker comments,
   inside a node vm sandbox with no npm packages (jsdom is not needed
   and not installed). It hands the helper a fake storage and prints,
   as JSON: the keys it removed (in order), a second run over the same
   storage, the keys that survived, and the result for a storage that
   refuses every remove.

   What runs here is exactly what ships, not a copy. Throws on a missing
   block or a function that never lands on the sandbox.

   Usage: node startover_harness.mjs <path/to/packaged.html> */
import fs from 'node:fs';
import vm from 'node:vm';

const htmlPath = process.argv[2];
if (!htmlPath) throw new Error('usage: startover_harness.mjs <packaged.html>');
const html = fs.readFileSync(htmlPath, 'utf8');

const start = html.indexOf('// -- startover start --');
const end = html.indexOf('// -- startover end --');
if (start === -1 || end === -1 || end < start) {
  throw new Error('startover markers not found in ' + htmlPath);
}
const code = html.slice(start, end);

const ctx = { Math };
ctx.globalThis = ctx;
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(code, ctx, { timeout: 5000 });
if (typeof ctx.startoverKeys !== 'function') {
  throw new Error('the extracted block did not define startoverKeys');
}

/* A storage object with the same shape as localStorage: length, key(i)
   and removeItem(k), backed by a plain object whose insertion order is
   stable. */
function fakeStorage(seed) {
  const store = Object.assign({}, seed);
  return {
    get store() { return store; },
    get length() { return Object.keys(store).length; },
    key(i) { return Object.keys(store)[i]; },
    removeItem(k) { delete store[k]; },
  };
}

const s = fakeStorage({
  'vefr-hp-town': '3',
  'vefr-slain-town': '[]',
  'vefr-floor-town': '[]',
  'vefr-packaged-combat': '[]',
  'keep-me': 'x',
  'some-other-app': 'y',
  'notvefr-thing': 'z',
  'myPrefs': 'p',
});
const removed = ctx.startoverKeys(s);
const removedAgain = ctx.startoverKeys(s);

/* A storage that refuses every remove: the helper must skip and carry
   on, never throw. */
const refuses = {
  length: 2,
  key(i) { return ['vefr-a', 'vefr-b'][i]; },
  removeItem() { throw new Error('storage says no'); },
};
let refusedResult;
let refusedThrew = false;
try { refusedResult = ctx.startoverKeys(refuses); }
catch (e) { refusedThrew = true; }

process.stdout.write(JSON.stringify({
  removed,
  removedAgain,
  survivors: Object.keys(s.store).sort(),
  refusedResult,
  refusedThrew,
}, null, 1));