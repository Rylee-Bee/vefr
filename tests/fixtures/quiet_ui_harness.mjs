/* Quiet UI harness: plays the REAL woven player in jsdom. Two files:
   argv[2] = the events fixture (a rat next to the hero, a named place one step
   right, a shopkeeper), argv[3] = the plain sample world (no enemies).
   Pins: WASD, E/F close Trade, the quiet bottom text, the verb row only near a
   monster, the collapsible corner panel. usage: node quiet_ui_harness.mjs <events.html> <sample.html> */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const noop = () => {};
function boot(path) {
  const dom = new JSDOM(fs.readFileSync(path, 'utf8'), {
    runScripts: 'dangerously', pretendToBeVisual: true, url: 'http://localhost/',
    beforeParse: (window) => {
      window.HTMLCanvasElement.prototype.getContext = function () {
        return new Proxy({ canvas: this }, { get: (t, k) => (k in t ? t[k] : noop) });
      };
      window.matchMedia = () => ({ matches: false, addListener: noop, removeListener: noop });
    },
  });
  return dom.window;
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const steps = [];
const note = (ok, what) => steps.push({ ok: !!ok, what });

async function begin(w) {
  for (let i = 0; i < 60 && !w.document.getElementById('ts-enter'); i++) await wait(50);
  w.document.getElementById('ts-enter').click();
  await wait(300);
}
const key = (w, k, extra) => w.document.dispatchEvent(new w.KeyboardEvent(
  'keydown', Object.assign({ key: k, bubbles: true, cancelable: true }, extra || {})));
const hero = (w) => w.VEFR_COMBAT.hero.at.slice();
const $ = (w, id) => w.document.getElementById(id);
const has = (w, id, cls) => $(w, id).classList.contains(cls);

try {
  // ---------- the events fixture: a rat next to the hero ----------
  const w = boot(process.argv[2]);
  await begin(w);
  note($(w, 'status').textContent.length > 0 && !has(w, 'status', 'quiet'),
       'the how-to-move line shows at the start');
  note(/WASD/.test($(w, 'status').textContent), 'the how-to-move line names WASD');
  note(has(w, 'use-hint', 'sr-only') && $(w, 'use-hint').textContent.length > 0,
       'the use-hint is screen-reader-only but still has its words');
  note(!$(w, 'verb-row').hidden, 'the fight buttons show with a monster next to the hero');

  const [x0, y0] = hero(w);
  key(w, 'd');
  const [x1, y1] = hero(w);
  note(x1 === x0 + 1 && y1 === y0, 'D walked right');
  note($(w, 'status').textContent === '', 'the how-to-move line is gone after the first step');
  note($(w, 'poi').textContent.length > 0 && !has(w, 'poi', 'quiet'),
       'the place name shows when you arrive on it');
  await wait(4400);                                   // the place name goes quiet by itself...
  note(has(w, 'poi', 'quiet'), 'the place name goes quiet after a few seconds');
  note($(w, 'poi').textContent.length > 0, '...and its text is kept, not cleared');
  // ---------- the corner panel ----------
  const tg = $(w, 'toasts-toggle');
  note(!!tg && tg.getAttribute('aria-expanded') === 'true', 'the corner panel has a toggle, open by default');
  tg.click();
  note(has(w, 'toasts', 'is-collapsed') && tg.getAttribute('aria-expanded') === 'false',
       'the toggle collapses the panel');
  tg.click();
  note(!has(w, 'toasts', 'is-collapsed') && tg.getAttribute('aria-expanded') === 'true',
       'and opens it again');

  // ---------- Trade closes with E and F ----------
  w.openTrade('keeper', 'The Keeper', w.document.body);
  note(!$(w, 'trade').hidden, 'Trade opened');
  key(w, 'e', { repeat: true });
  note(!$(w, 'trade').hidden, 'a held E does not close it');
  key(w, 'Enter');
  note(!$(w, 'trade').hidden, 'Enter with no button focused does not close it');
  key(w, 'e');
  note($(w, 'trade').hidden, 'E closes Trade');
  w.openTrade('keeper', 'The Keeper', w.document.body);
  key(w, 'F');
  note($(w, 'trade').hidden, 'F closes Trade');

  // ---------- WASD in a note: A/D turn pages ----------
  w.openReader({ id: 'a-test-note', title: 'A test note', pages: ['one', 'two', 'three'] });
  key(w, 'd');
  note($(w, 'reader-text').textContent === 'two', 'D turns to the next page');
  key(w, 'a');
  note($(w, 'reader-text').textContent === 'one', 'A turns back');
  key(w, 'Escape');

  w.close();

  // ---------- the plain sample: no monsters, no fight buttons ----------
  const s = boot(process.argv[3]);
  await begin(s);
  note($(s, 'verb-row').hidden, 'no fight buttons when there is no monster near');
  // WASD in open ground (nothing in the way): each key moves one tile its own way
  const walk = (k) => { const b = hero(s); key(s, k); const a = hero(s); return [a[0] - b[0], a[1] - b[1]]; };
  const moves = { d: walk('d'), a: walk('a'), s: walk('s'), w: walk('w') };
  note(moves.d[0] === 1 && moves.d[1] === 0, 'D walks one tile right');
  note(moves.a[0] === -1 && moves.a[1] === 0, 'A walks one tile left');
  note(moves.s[0] === 0 && moves.s[1] === 1, 'S walks one tile down');
  note(moves.w[0] === 0 && moves.w[1] === -1, 'W walks one tile up');
  const cap = walk('D');
  note(cap[0] === 1, 'a capital D works too');
  s.close();
} catch (err) { note(false, 'threw: ' + err.message); }
console.log(JSON.stringify({ allOk: steps.every((x) => x.ok), steps }));
process.exit(0);
