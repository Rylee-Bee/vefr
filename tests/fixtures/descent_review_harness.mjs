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
    "blockKey": "<the key a fake storage refuses to remove>"}

   budget:   for each document, put `seedDoc` in storage, call saveDoc,
             and report what storage holds afterwards.
   startover: enter the game so the card is offered, hand `store.raw()` a
             fake storage that refuses to remove `blockKey`, press Start
             over, and report what the card says and what is left.

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
    out.results.push({
      given: given.length,
      storedBytes: stored === null ? -1 : stored.length,
      storedFloors: Object.keys(after.floors || {}).length,
      storedFlags: after.flags || {},
      order: after.order || [],
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

  out.returned = D.startOver();
  await wait(300);
  out.after = {
    cardHidden: card ? card.hidden : null,
    line: line ? line.textContent : null,
    left: names(),
    // Recorded, not asserted: jsdom does not navigate, so a reload shows
    // up only as its own "not implemented" on the console.
    reload: errors.some((m) => /not implemented/i.test(m) &&
                              /(location|navigation|reload)/i.test(m)),
  };
}

fs.writeSync(1, JSON.stringify(out) + '\n');
w.close();
process.exit(0);