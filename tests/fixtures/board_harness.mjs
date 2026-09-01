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
    tabIndex: 0,
    textContent: '',
    focus() { this.focused = true; },
    setAttribute(k, v) { this.attrs = this.attrs || {}; this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs ? (this.attrs[k] ?? null) : null; },
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
  assert(doc['board-rail'].focused === true, 'focus moves into the opened rail');
  assert(card.getAttribute('aria-pressed') === 'true', 'selected card is pressed');
  /* keyboard re-homing: the rail carries one button per column */
  assert(doc['board-move-whispers'].disabled === true,
    'current column re-home button disabled');
  assert(doc['board-move-forge'].disabled === false,
    'other column re-home buttons enabled');
  /* keyboard path: Enter selects, same as click */
  const card2 = doc['board-whispers'].children[1];
  assert(card2.getAttribute('role') === 'button' && card2.tabIndex === 0,
    'cards are keyboard-reachable buttons');
  card2.fire('keydown', { key: 'Enter', preventDefault() {} });
  assert(B.state.selected.id === card2.dataset.id,
    'keyboard select moved selection to the second card');
  /* rail re-home button moves the card and announces it */
  const cardId = B.state.selected.id;
  doc['board-move-forge'].click();
  assert(B.state.selected.id === cardId, 'selection survives a rail move');
  assert(doc['board-forge'].children.length === 6, 'rail move landed the card (5 seeded + 1)');
  assert(doc['board-forge'].children[5].dataset.id === cardId,
    'the moved card is the one that arrived');
  assert(doc['board-whispers'].children.length === 4, 'rail move emptied the source');
  assert(doc['board-status'].textContent.includes('forge'),
    'move announced via aria-live status');
  assert(JSON.parse(s.localStorage.getItem('vefr-board-cards')).forge.length === 6,
    'rail move persisted');
}

/* ---- 7b. syncColumns: pointer drops keep their dropped position ----- */
{
  const s = makeSandbox({}, undefined);
  const B = run(s);
  B.init();
  await tick();
  const doc = s.document._registry;
  /* simulate a within-column drag: reverse the whispers order in the DOM */
  const ids = doc['board-whispers'].children.map((el) => el.dataset.id);
  doc['board-whispers'].children.reverse();
  B.syncColumns('whispers', 'whispers', ids[0]);
  assert(doc['board-status'].textContent.includes('reordered in whispers'),
    'within-column reorder announced, not silent');
  const saved = JSON.parse(s.localStorage.getItem('vefr-board-cards'));
  assert(JSON.stringify(saved.whispers.map((c) => c.id))
    === JSON.stringify(doc['board-whispers'].children.map((el) => el.dataset.id)),
    'store order synced to the dropped DOM order');
  /* simulate a cross-column drop: move the last whispers card to forge */
  const moved = doc['board-whispers'].children[4];
  const movedId = moved.dataset.id;
  doc['board-forge'].children.push(moved);
  doc['board-whispers'].children.pop();
  B.syncColumns('whispers', 'forge', movedId);
  const saved2 = JSON.parse(s.localStorage.getItem('vefr-board-cards'));
  const movedCard = saved2.forge.find((c) => c.id === movedId);
  assert(!!movedCard, 'cross-column drop synced the store');
  assert(movedCard.edited !== null, 're-homed card stamped as edited');
  assert(s.document._registry['board-status'].textContent.includes('forge'),
    'cross-column drop announced');
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

/* ---- 9. the lazy boot registered for vefr:board --------------------- */
{
  let worldCalls = 0;
  const countingFetch = (url) => {
    if (url === '/api/world') worldCalls++;
    return Promise.resolve({ ok: true, json: async () => FAKE_WORLD });
  };
  const s = makeSandbox({}, countingFetch);
  run(s);
  const fns = s._winListeners['vefr:board'] || [];
  assert(fns.length === 1, `boot must listen for vefr:board (got ${fns.length})`);
  fns[0]({});
  await tick();
  const doc = s.document._registry;
  assert(doc['board-whispers'].children.length === 5, 'lazy boot rendered whispers');
  assert(worldCalls === 1, `lazy boot asks for the world exactly once (got ${worldCalls})`);
}

/* ---- 10. the draft to the smith: context, thread, honest offline ---- */
{
  /* online: the smith answers. board.js reads the global fetch at
     call time, so re-stubbing the sandbox property after init works. */
  const chatBodies = [];
  const sOn = makeSandbox({}, undefined);
  const B = run(sOn);
  B.init();
  await tick();
  sOn.fetch = (url, opts) => {
    if (url.indexOf('/api/builder/chat') > -1) {
      chatBodies.push(JSON.parse(opts.body));
      return Promise.resolve({ ok: true, json: async () => ({ reply: 'keep it short.' }) });
    }
    return Promise.resolve({ ok: true, json: async () => FAKE_WORLD });
  };
  const doc = sOn.document._registry;
  const draftBox = sOn.document.getElementById('rail-draft');
  const card = doc['board-whispers'].children[0];
  card.click();
  draftBox.value = 'make it about the harvest';
  doc['rail-chat-send'].click();
  await tick();
  /* the thread renders as labeled paragraphs - one per turn */
  const turnText = () => doc['rail-chat-log'].children.map((p) => p.textContent).join('\n');
  assert(doc['rail-chat-log'].children.length === 2, 'one paragraph per turn');
  assert(turnText().includes('you: make it about the harvest'),
    'draft logged as the author turn');
  assert(turnText().includes('smith: keep it short.'),
    'smith reply logged');
  assert(doc['rail-chat-log'].children[0].className.indexOf('board-chat-user') > -1,
    'author turn is classed for the luminance roles');
  assert(doc['rail-chat-log'].children[1].className.indexOf('board-chat-smith') > -1,
    'smith reply is classed too');
  assert(draftBox.value === '', 'textarea cleared on success');
  assert(B.state.threads[card.dataset.id].length === 2, 'thread holds both turns');
  assert(chatBodies.length === 1, 'exactly one chat call');
  assert(chatBodies[0].message.includes('[card]')
    && chatBodies[0].message.includes(card.textContent.split(' \u2014 ')[0]),
    'composed message carries the card context');
  assert(chatBodies[0].message.includes('make it about the harvest'),
    'composed message carries the draft');
  assert(chatBodies[0].history.length === 1,
    'the first call replays the one turn so far');

  /* the 6-turn cap: keep talking; the engine must never see more
     than the last six turns of the thread */
  for (let n = 2; n <= 7; n++) {
    draftBox.value = 'turn ' + n;
    doc['rail-chat-send'].click();
    await tick();
  }
  assert(chatBodies.length === 7, 'seven turns sent');
  assert(chatBodies[6].history.length === 6,
    'the engine sees at most the last 6 turns');
  assert(chatBodies[6].history.some((t) => t.content.includes('turn 7')),
    'the newest turn is inside the replayed window');

  /* offline: the turn comes back out of the thread, told honestly */
  const sOff = makeSandbox({}, (url) => (url.indexOf('/api/builder/chat') > -1
    ? Promise.reject(new Error('no engine'))
    : Promise.resolve({ ok: true, json: async () => FAKE_WORLD })));
  const BOff = run(sOff);
  BOff.init();
  await tick();
  const dOff = sOff.document._registry;
  dOff['board-whispers'].children[0].click();
  sOff.document.getElementById('rail-draft').value = 'a question for later';
  dOff['rail-chat-send'].click();
  await tick();
  assert(dOff['rail-chat-log'].children.some((p) => p.textContent.includes('the draft stays yours')),
    'offline draft says so plainly');
  assert((BOff.state.threads[dOff['board-whispers'].children[0].dataset.id] || []).length === 0,
    'failed turn leaves the thread empty');
}

/* ---- 10b. clearing the thread: same store, honest announcement ------- */
{
  const s = makeSandbox({}, undefined);
  const B = run(s);
  B.init();
  await tick();
  s.fetch = (url) => Promise.resolve({ ok: true, json: async () => ({ reply: 'aye.' }) });
  const doc = s.document._registry;
  const card = doc['board-whispers'].children[0];
  card.click();
  s.document.getElementById('rail-draft').value = 'a first take';
  doc['rail-chat-send'].click();
  await tick();
  assert(doc['rail-chat-log'].children.length === 2, 'precondition: thread rendered');
  doc['rail-chat-clear'].click();
  assert((B.state.threads[card.dataset.id] || []).length === 0, 'clear wiped the thread');
  assert(doc['rail-chat-log'].children.length === 0, 'clear emptied the log');
  assert(doc['board-status'].textContent.includes('cleared'), 'clear announced');
}

/* ---- 11. reseed: the seeded board is disposable ---------------------- */
{
  const s = makeSandbox({}, undefined);
  const B = run(s);
  B.init();
  await tick();
  const doc = s.document._registry;
  /* move a card around first - reseed must wipe the moves too */
  B.move(doc['board-whispers'].children[0].dataset.id, 'forge');
  assert(doc['board-forge'].children.length === 6, 'precondition: card moved');
  B.reseed();
  assert(doc['board-whispers'].children.length === 5, 'reseed restored whispers');
  assert(doc['board-forge'].children.length === 5, 'reseed restored forge');
  assert(doc['board-voices'].children.length === 1, 'reseed restored voices');
  const saved = JSON.parse(s.localStorage.getItem('vefr-board-cards'));
  assert(saved.forge.length === 5, 'reseeded store persisted');
  assert(doc['board-status'].textContent.includes('reseeded'),
    'reseed announced');
}

console.log('ALL PASS');
