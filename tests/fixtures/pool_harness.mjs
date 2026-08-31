/* Packaged-file pool harness: executes the REAL pool code extracted
   from a built dist/<world>.html - not a copy - inside a vm sandbox
   with a stubbed localStorage, then drives the pool-draw semantics:

   1. draws come from the asked-for combo first
   2. no entry repeats until its combo is exhausted
   3. a spent combo falls through to another combo's unused lines
   4. a fully spent pool draws null (the honest silence)
   5. usage persists across a "reload" via the localStorage store

   The spec file (argv[2]) is JSON: {code: <extracted JS>, pool: {...}}.
   The python test extracts the code block from the real built HTML, so
   what runs here is exactly what ships. Throws on any failed check;
   prints PASS lines on success. */
import fs from 'node:fs';
import vm from 'node:vm';

const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const { code, pool } = spec;

function makeSandbox(store) {
  const ctx = {
    JSON,
    Math,
    localStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
    },
    window: {},
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(code, ctx, { timeout: 5000 });
  if (typeof ctx.poolDraw !== 'function') {
    throw new Error('pool code did not define poolDraw on the sandbox');
  }
  return ctx;
}

const used = () => JSON.parse(store['vefr-pool-used'] || '{}');

/* ---------- scenario 1: draw, drain, fall through, silence ---------- */
const store = {};
const s1 = makeSandbox(store);
s1.window.VEFR_POOL = pool;

function whispersIncludes(list, w) { return list.indexOf(w) !== -1; }

const total = Object.values(pool).reduce((n, l) => n + l.length, 0);
const seen = [];
for (let i = 0; i < total + 5; i++) {
  const e = s1.poolDraw('rumor:dusk');
  if (e === null) break;
  seen.push(e);
}

// asked-for combo first: the first two draws are dusk entries
const duskWhispers = pool['rumor:dusk'].map((e) => e.whisper);
if (seen.length < 2 || !seen.slice(0, 2).every((e) => whispersIncludes(duskWhispers, e.whisper))) {
  throw new Error('first draws were not from the asked-for combo');
}

// full drain, zero repeats: every entry drawn exactly once
const sig = (e) => JSON.stringify(e);
const counts = {};
for (const e of seen) counts[sig(e)] = (counts[sig(e)] || 0) + 1;
for (const k of Object.keys(counts)) {
  if (counts[k] !== 1) throw new Error('pool drew an entry twice: ' + k);
}
if (seen.length !== total) throw new Error(`drained ${seen.length} of ${total} entries`);
if (s1.poolDraw('rumor:dusk') !== null) throw new Error('a spent pool must draw null, not repeat');

const u = used();
if (!u['rumor:dusk'] || u['rumor:dusk'].length !== pool['rumor:dusk'].length) {
  throw new Error('used-tracking did not record the dusk draws');
}
console.log('PASS drain/exhaust/fallthrough/silence (' + total + ' entries, no repeats)');

/* ---------- scenario 2: persistence across a reload ---------- */
const s2 = makeSandbox(store); // same store: simulates a page reload
s2.window.VEFR_POOL = pool;
if (s2.poolDraw('rumor:dusk') !== null) throw new Error('usage did not persist across a reload');
console.log('PASS persistence across reload');

console.log('pool harness passed');
