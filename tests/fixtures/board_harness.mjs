/* board.js harness: executes the REAL web/board.js inside a node vm
   sandbox with a stubbed DOM, localStorage, and fetch, then drives
   the contract:

     1. generateStore is deterministic for a given world + seed
     2. the voices column is drawn from the pack's speakers (name +
        the speaker's first seed line), one card per speaker
     3. a world without speakers falls back to the seeded neutral
        pool (two filler cards, title-named)
     4. init() renders the columns and persists the store to
        localStorage under vefr-board-cards
     5. move() re-homes a card across columns, stamps it as edited,
        and persists - and a FRESH sandbox loading the same store
        keeps the moved card instead of regenerating
     6. move() returns false for an unknown id or column
     7. selecting a card fills the right rail and unhides it
     8. "try it" with no engine answers honestly (preview only);
        with a live stub it shows the response JSON

   Throws on any failed check; prints ALL PASS on success.
*/
import fs from 'node:fs';
import vm from 'node:vm';

const path = process.argv[2];
const code = fs.readFileSync(path, 'utf8');

const FAKE_WORLD = {
  title: 'Testfield',
  gold_rule: 'gold only when kind.',
  phases: ['dusk', 'dawn'],
  speakers: [
    {
      key: 'keeper',
      name: 'The Keeper',
      near: 'the stone',
      seeds: { dusk: 'sit a while.', dawn: 'morning already.' }
    }
  ]
};

function makeEl(id) {
  const el = {
    id,
    children: [],
    listeners: {},
    dataset: {},
    className: '',
    draggable: false,
    hidden: false,
    textContent: '',
    appendChild(child) { this.children.push(child); return child; },
    addEventListener(type, fn) {
      (this.listeners[type] = this.listeners[type] || []).push(fn);
    },
    click() {
      (this.listeners.click || []).forEach((fn) => fn({}));
    },
    fire(type, event) {
      (this.listeners[type] || []).forEach((fn) => fn(event));
    },
  };
  Object.defineProperty(el, 'innerHTML', {
    get() { return ''; },
    set(v) { if (v === '') this.children.length = 0; },
  });
  return el;
}

/* A sandbox document whose getElementById auto-creates holders for
   the board's known ids; createElement always makes fresh nodes. */
function makeDocument() {
  const registry = {};
  return {
    _registry: registry,
    addEventListener() { /* DOMContentLoaded never fires in-harness */ },
    getElementById(id) {
      if (!registry[id]) registry[id] = makeEl(id);
      return registry[id];
    },
    createElement() { return makeEl(''); },
  };
}

function makeSandbox(store, fetchImpl) {
  const document = makeDocument();
  const winListeners = {};
  const sandbox = {
    JSON, Math, Date, Promise, Object, Array, String, Number, isNaN,
    parseInt, setTimeout, setImmediate,
    console: { log: () => {}, error: () => {} },
    localStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
    },
    document,
    fetch: fetchImpl || ((url) => (url === '/api/world'
      ? Promise.resolve({ ok: true, json: async () => FAKE_WORLD })
      : Promise.reject(new Error('stub: no route')))),
  };
  sandbox.window = sandbox;
  sandbox.window.addEventListener = (t, fn) => {
    (winListeners[t] = winListeners[t] || []).push(fn);
  };
  sandbox.window.dispatchEvent = (ev) => {
    for (const fn of winListeners[ev.type] || []) fn(ev);
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  sandbox._winListeners = winListeners;
  return sandbox;
}

function run(sandbox) {
  vm.runInContext(code, sandbox, { filename: 'board.js' });
  return sandbox.window.VEFR_BOARD;
}

async function tick() {
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
}

function assert(cond, msg) {
  if (!cond) throw new Error(`FAIL: ${msg}`);
}

/* ---- 1. determinism ------------------------------------------------ */
{
  const s = makeSandbox({}, undefined);
  const B = run(s);
  const a = B.generateStore(FAKE_WORLD, 42);
  const b = B.generateStore(FAKE_WORLD, 42);
  assert(JSON.stringify(a) === JSON.stringify(b), 'same seed must reproduce the same store');
  const c = B.generateStore(FAKE_WORLD, 43);
  assert(JSON.stringify(a) !== JSON.stringify(c), 'different seed should differ');
}

/* ---- 2. voices come from the pack's speakers ----------------------- */
{
  const s = makeSandbox({}, undefined);
  const B = run(s);
  const store = B.generateStore(FAKE_WORLD, 42);
  assert(store.voices.length === 1, `one card per speaker (got ${store.voices.length})`);
  assert(store.voices[0].name === 'The Keeper', 'voice card name is the speaker');
  assert(store.voices[0].content === 'sit a while.', 'voice card content is the speaker seed');
  assert(store.whispers.length === 5, 'five whisper cards');
  assert(store.forge.length === 5, 'five forge cards');
  assert(store.bell.length === 5, 'five bell cards');
}

/* ---- 3. no speakers -> neutral fallback ---------------------------- */
{
  const s = makeSandbox({}, undefined);
  const B = run(s);
  const bare = { title: 'Barefield', phases: ['dusk'], speakers: [] };
  const store = B.generateStore(bare, 7);
  assert(store.voices.length === 2, 'two filler voice cards');
  assert(store.voices.every((c) => c.name === 'Barefield'), 'fillers are title-named');
  assert(store.voices.every((c) => B.NEUTRAL.voices.includes(c.content)),
    'filler content comes from the neutral pool');
  /* the bone-strip invariant: no canon string anywhere in the store */
  const blob = JSON.stringify(store);
  ['the wanderer', 'the ferryman', 'the roll-keeper', 'the sea-figure', 'private-canon'].forEach((n) => {
    assert(!blob.includes(n), `neutral store must not contain "${n}"`);
  });
}

/* ---- 4+5. init renders + persists; move re-homes + persists -------- */
{
  const store = {};
  const s1 = makeSandbox(store, undefined);
  const B1 = run(s1);
  B1.init();
  await tick();
  const doc1 = s1.document._registry;
  assert(doc1['board-whispers'].children.length === 5, 'whispers rendered');
  assert(doc1['board-voices'].children.length === 1, 'voices rendered');
  assert(store['vefr-board-cards'], 'store persisted');
  const voiceId = JSON.parse(store['vefr-board-cards']).voices[0].id;

  const moved = B1.move(voiceId, 'forge');
  assert(moved === true, 'move returns true on a real move');
  assert(doc1['board-forge'].children.length === 6, 'card arrived in forge');
  assert(doc1['board-voices'].children.length === 0, 'voices column emptied');
  const saved = JSON.parse(store['vefr-board-cards']);
  assert(saved.voices.length === 0 && saved.forge.length === 6, 'move persisted');

  /* fresh sandbox, same localStorage: the moved card survives boot */
  const s2 = makeSandbox(store, undefined);
  const B2 = run(s2);
  B2.init();
  await tick();
  const doc2 = s2.document._registry;
  assert(doc2['board-forge'].children.length === 6, 'fresh boot keeps the moved card');
  assert(doc2['board-voices'].children.length === 0, 'fresh boot does not regenerate');
  const whenText = doc2['board-forge'].children[5].children[0].textContent;
  assert(whenText.indexOf('moved') === 0, `moved card stamped (got "${whenText}")`);
}

/* ---- 6. move rejects unknowns -------------------------------------- */
{
  const s = makeSandbox({}, undefined);
  const B = run(s);
  B.init();
  await tick();
  assert(B.move('nope', 'forge') === false, 'unknown id rejected');
  assert(B.move('whatever', 'not-a-column') === false, 'unknown column rejected');
}

/* ---- 7. selecting a card fills the rail ----------------------------- */
{
  const s = makeSandbox({}, undefined);
  const B = run(s);
  B.init();
  await tick();
  const doc = s.document._registry;
  const card = doc['board-whispers'].children[0];
  card.click();
  assert(doc['board-rail'].hidden === false, 'rail unhides on select');
  assert(doc['rail-request'].textContent.includes('/api/rumor'),
    'request panel names the endpoint');
  assert(doc['rail-name'].textContent.length > 0, 'rail shows the card name');
}

/* ---- 8. try it: honest offline, live online ------------------------- */
{
  /* offline: the world loads, but the generation route does not answer */
  const sOff = makeSandbox({}, (url) => (url === '/api/world'
    ? Promise.resolve({ ok: true, json: async () => FAKE_WORLD })
    : Promise.reject(new Error('no engine'))));
  const BOff = run(sOff);
  BOff.init();
  await tick();
  const dOff = sOff.document._registry;
  dOff['board-whispers'].children[0].click();
  dOff['rail-try'].click();
  await tick();
  assert(dOff['rail-try-out'].textContent.includes('preview only'),
    'offline try-it says preview only');

  /* online: stub answers */
  const sOn = makeSandbox({}, () => Promise.resolve({
    ok: true,
    json: async () => ({ speaker: 'x', whisper: 'y' }),
  }));
  const BOn = run(sOn);
  BOn.init();
  await tick();
  const dOn = sOn.document._registry;
  dOn['board-whispers'].children[0].click();
  dOn['rail-try'].click();
  await tick();
  assert(dOn['rail-try-out'].textContent.includes('speaker'),
    'online try-it shows the response JSON');
}

/* ---- 9. the lazy boot registered for old-name:board --------------------- */
{
  let worldCalls = 0;
  const countingFetch = (url) => {
    if (url === '/api/world') worldCalls++;
    return Promise.resolve({ ok: true, json: async () => FAKE_WORLD });
  };
  const s = makeSandbox({}, countingFetch);
  run(s);
  const fns = s._winListeners['old-name:board'] || [];
  assert(fns.length === 1, `boot must listen for old-name:board (got ${fns.length})`);
  fns[0]({});
  await tick();
  const doc = s.document._registry;
  assert(doc['board-whispers'].children.length === 5, 'lazy boot rendered whispers');
  assert(worldCalls === 1, `lazy boot asks for the world exactly once (got ${worldCalls})`);
}

console.log('ALL PASS');
