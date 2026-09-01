/* Packaged-file pool harness: executes the REAL pool code extracted
   from a built dist/<world>.html - not a copy - inside a vm sandbox
   with a stubbed localStorage, then drives the pool-draw semantics:

   1. draws come from the asked-for combo first
   2. no entry repeats until its combo is exhausted
   3. a spent combo falls through to another combo's unused lines
   4. a fully spent pool draws null (the honest silence)
   5. usage persists across a "reload" via the localStorage store
   6. a spent pool re-weaves its own cloth: the composer's words are
      pool words only, deterministic under a fixed seed
   7. an npc line never borrows another speaker's words
   8. with no pool at all, the composer keeps the honest silence

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

/* ---------- scenario 3: the composer re-weaves spent cloth ---------- */
const s3 = makeSandbox(store); // the pool is fully spent by now
s3.window.VEFR_POOL = pool;
const woven = s3.composeWhisper('rumor:dusk');
if (!woven) throw new Error('composer returned silence with a spent-but-nonempty pool');
const words = (s) => String(s).toLowerCase().replace(/[^a-z' ]/g, ' ').split(/\s+/).filter(Boolean);
const cloth = new Set();
for (const list of Object.values(pool)) {
  for (const e of list) if (e.whisper) for (const w of words(e.whisper)) cloth.add(w);
}
for (const w of words(woven.whisper)) {
  if (!cloth.has(w)) throw new Error('composer invented a word outside the pool: ' + w);
}
const again = s3.composeWhisper('rumor:dusk', 42);
const repeat = s3.composeWhisper('rumor:dusk', 42);
if (JSON.stringify(again) !== JSON.stringify(repeat)) {
  throw new Error('composer is not deterministic under a fixed seed');
}
console.log('PASS composer re-weaves spent cloth (pool words only, deterministic under seed)');

/* ---------- scenario 4: an npc line never borrows another voice ---------- */
const npcPool = {
  'npc:dusk:smith': [
    { speaker: 'The Smith', line: 'the forge keeps its own heat.' },
    { speaker: 'The Smith', line: 'iron remembers the hand that held it.' },
  ],
};
const s4 = makeSandbox({});
s4.window.VEFR_POOL = npcPool;
const wovenLine = s4.composeLine('npc:dusk:smith', 9);
if (!wovenLine || wovenLine.speaker !== 'The Smith') {
  throw new Error('composer failed on a two-entry npc combo');
}
const smithWords = new Set();
npcPool['npc:dusk:smith'].forEach((e) => words(e.line).forEach((w) => smithWords.add(w)));
for (const w of words(wovenLine.line)) {
  if (!smithWords.has(w)) throw new Error('npc composer borrowed outside the speaker: ' + w);
}
const loneVoice = makeSandbox({});
loneVoice.window.VEFR_POOL = { 'npc:dusk:smith': [npcPool['npc:dusk:smith'][0]] };
if (loneVoice.composeLine('npc:dusk:smith', 9) !== null) {
  throw new Error('a one-line npc combo must stay honestly silent, not borrow a voice');
}
console.log('PASS npc composer stays inside the speaker (honest silence with one line)');

/* ---------- scenario 5: whispers cross combos; no pool = silence ---------- */
const s5 = makeSandbox({});
s5.window.VEFR_POOL = {
  'rumor:dusk': [{ speaker: 'Ember', whisper: 'one alone.', is_true: true }],
  'rumor:dawn': [{ speaker: 'Ember', whisper: 'two together.', is_true: false }],
};
if (!s5.composeWhisper('rumor:dusk', 3)) {
  throw new Error('whisper composer refused a cross-combo weave');
}
const s6 = makeSandbox({});
s6.window.VEFR_POOL = {};
if (s6.composeWhisper('rumor:dusk', 1) !== null) {
  throw new Error('silence must stay honest when there is no pool at all');
}
console.log('PASS cross-combo whispers weave; no pool keeps the honest silence');

console.log('pool harness passed');
