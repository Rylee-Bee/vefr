/* Descent review harness: the two halves of the vefr#308 review that need
   the running player and a storage of their own - the byte budget the
   save is refused rather than written over, and Start over refusing to
   say a save is gone when it is not. Both run against the REAL woven
   player, so the save, the trim and the start-over are the shipped code.

   argv[2] = woven html, argv[3] = JSON cases made by pytest:
   {"mode": "budget" | "startover",
    "store": {<key>: <value>, ...},     # planted before the page runs
    "seedDoc": <a document already in storage>,
    "docs": [<a document to hand to saveDoc>, ...],
    "blockKey": "<the key a fake storage refuses to remove>",
    "failWrite": true}   # a browser that refuses to store a save at all

   budget:   for each document, put `seedDoc` in storage, call saveDoc,
             and report what storage holds afterwards.
   startover: enter the game so the card is offered, hand `store.raw()` a
             fake storage that refuses to remove `blockKey`, press Start
             over, and report what the card says and what is left.
             `failWrite` makes every save throw, the way a full or
             private-mode browser does.

   Every mode reports `bytes`: what the player's own `docBytes` and
   `floorBytes` make of a string of 100 U+2620, which is 100 UTF-16
   units and 300 UTF-8 bytes before the JSON quotes around it.

   Prints one line of JSON. */
import fs from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';

const noop = () => {};
const cases = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const errors = [];
const virtualConsole = new VirtualConsole();
virtualConsole.on('jsdomError', (e) => errors.push(String((e && e.message) || e)));

const dom = new JSDOM(fs.readFileSync(process.argv[2], 'utf8'), {
  runScripts: 'dangerously', pretendToBeVisual: true, url: 'http://localhost/',
  virtualConsole,
  beforeParse: (window) => {
    window.HTMLCanvasElement.prototype.getContext = function () {
      return new Proxy({ canvas: this }, { get: (t, k) => (k in t ? t[k] : noop) });
    };
    window.matchMedia = () => ({ matches: false, addListener: noop, removeListener: noop });
    for (const [k, v] of Object.entries(cases.store || {})) window.localStorage.setItem(k, v);
  },
});
const w = dom.window;
const wait = (ms) => new Promise((r) => w.setTimeout(r, ms));
const D = w.VEFR_DESCENT;
const out = { hasApi: !!(D && D.docKey), mode: cases.mode, errors };

/* What the player's own byte counter makes of a hundred U+2620: one
   hundred UTF-16 code units, three hundred UTF-8 bytes. A budget that
   counts the first is not counting bytes. */
if (D && D.docBytes && D.floorBytes) {
  const wide = String.fromCharCode(0x2620).repeat(100);
  out.bytes = { doc: D.docBytes(wide), floor: D.floorBytes({ s: wide }) };
}

/* The click into the game, the same one play.mjs's "begin" makes: the
   title screen's Enter, then the wait for the town to be up. */
async function enter() {
  for (let i = 0; i < 60 && !w.document.getElementById('ts-enter'); i++) await wait(50);
  const go = w.document.getElementById('ts-enter');
  if (go) go.click();
  for (let i = 0; i < 60 && !w.VEFR_COMBAT; i++) await wait(50);
  await wait(400);
}

function parsed(text) {
  try { return JSON.parse(text); } catch (e) { return {}; }
}

if (out.mode === 'budget' && out.hasApi) {
  const key = D.docKey();
  out.results = [];
  for (const doc of (cases.docs || [])) {
    const given = JSON.stringify(doc);
    // What was saved before this write, so "nothing was written" and
    // "the old save is still whole" are two different answers.
    w.localStorage.setItem(key, JSON.stringify(cases.seedDoc));
    const returned = D.saveDoc(JSON.parse(given));
    const stored = w.localStorage.getItem(key);
    const after = parsed(stored === null ? '' : stored);
    // Every floor record as it was written, and the biggest one: PLAN §3's
    // per-floor budget is about the record, not the whole save.
    const floorSizes = Object.keys(after.floors || {})
      .map((k) => JSON.stringify(after.floors[k]).length);
    out.results.push({
      given: given.length,
      storedBytes: stored === null ? -1 : stored.length,
      storedFloors: Object.keys(after.floors || {}).length,
      // What every floor record in the stored save weighs, by the same
      // count `floorBytes` makes, so the per-floor budget of PLAN §3 can
      // be asserted on what actually landed and not recomputed in Python.
      storedFloorBytes: Object.keys(after.floors || {})
        .map((n) => JSON.stringify(after.floors[n]).length),
      storedFlags: after.flags || {},
      order: after.order || [],
      floors: after.floors || {},
      floorSizes: floorSizes,
      maxFloorBytes: floorSizes.length ? Math.max(...floorSizes) : 0,
      returnedBytes: returned ? JSON.stringify(returned).length : -1,
      refusal: typeof D.saveRefusal === 'function' ? D.saveRefusal() : null,
    });
  }
}

if (out.mode === 'startover' && out.hasApi) {
  await enter();
  const card = w.document.getElementById('gen-card');
  const line = w.document.getElementById('gen-card-line');
  out.offered = { cardHidden: card ? card.hidden : null, line: line ? line.textContent : null };

  // What the player's own descent save holds, before anything is pressed:
  // the save that has to survive a Start over that cannot write one.
  out.before = { doc: w.localStorage.getItem(D.docKey()) };

  // A browser that refuses to store anything at all: full, private mode,
  // storage blocked. The shipped `store` gives up quietly on a write like
  // this, which is the whole finding - a Start over that clears anyway
  // leaves the player with no old save and no new one.
  if (cases.failWrite) {
    w.store.setJSON = function (key) {
      throw new Error('QuotaExceededError: this browser would not store ' + key);
    };
  }

  // The storage the player has: every key the page really holds, and a
  // remove that refuses for one of them the way a full or private-mode
  // browser does. `store.raw()` is the only door into storage, so this is
  // the storage the shipped start-over clears.
  const backing = {};
  for (let i = 0; i < w.localStorage.length; i++) backing[w.localStorage.key(i)] = true;
  const names = () => Object.keys(backing);
  const blocked = cases.blockKey;
  w.store.raw = () => ({
    get length() { return names().length; },
    key(i) { return names()[i] === undefined ? null : names()[i]; },
    removeItem(k) {
      if (k === blocked) throw new Error('the browser refused to remove ' + k);
      delete backing[k];
    },
  });

  let returned;
  try { returned = D.startOver(); }
  catch (e) { returned = 'threw: ' + String((e && e.message) || e); }
  out.returned = returned;
  await wait(300);
  out.after = {
    cardHidden: card ? card.hidden : null,
    line: line ? line.textContent : null,
    left: names(),
    // What the page's own storage holds now, so "the save survived" can
    // be asked of the save and not only of the key.
    doc: w.localStorage.getItem(D.docKey()),
    // Recorded, not asserted: jsdom does not navigate, so a reload shows
    // up only as its own "not implemented" on the console.
    reload: errors.some((m) => /not implemented/i.test(m) &&
                              /(location|navigation|reload)/i.test(m)),
  };
}

fs.writeSync(1, JSON.stringify(out) + '\n');
w.close();
process.exit(0);