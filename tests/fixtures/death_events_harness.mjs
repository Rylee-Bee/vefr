/* Death events harness: EXECUTES the woven single-file player in a
   real DOM (jsdom, dev-only) and plays one death end to end. The hero
   begins in the town beside a rat whose single blow empties a 2-hp
   health bar; the pack has one rule on `falls` and one on `wakes`.

   It records every line the narrator says, in order, by wrapping the
   player's own `combatSay` - the two rules speak at two different
   moments (the fall, then the waking) and each replaces the last line
   on screen, so reading only the final text would prove one of them
   and lose the other.

   usage: node death_events_harness.mjs <woven.html> */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const html = fs.readFileSync(process.argv[2], 'utf8');
const noop = () => {};

/* jsdom has no canvas; the player only needs a 2D context to exist so
   setupTown runs. Every drawing call is a no-op. */
function stubCanvas(window) {
  window.HTMLCanvasElement.prototype.getContext = function () {
    return {
      canvas: this, save: noop, restore: noop, translate: noop,
      setTransform: noop, fillRect: noop, clearRect: noop, drawImage: noop,
      beginPath: noop, arc: noop, fill: noop, stroke: noop,
      closePath: noop, moveTo: noop, lineTo: noop, fillText: noop,
      rotate: noop,
    };
  };
}

const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  url: 'http://localhost/',
  beforeParse: (window) => {
    stubCanvas(window);
    window.matchMedia = () => ({
      matches: false, addListener: noop, removeListener: noop,
    });
  },
});
const { window } = dom;
const document = window.document;
const wait = (ms) => new Promise((r) => window.setTimeout(r, ms));
const snap = () => window.VEFR_COMBAT;
const flags = () => ((window.VEFR_RULES_STATE || {}).flags) || {};
const why = () => (window.VEFR_WHY || []).slice();
const sayLine = () => {
  const el = document.getElementById('combat-live');
  return el ? el.textContent : '';
};
const press = (dir) => {
  const b = [...document.querySelectorAll('#dpad button')]
    .find((x) => x.dataset.dir === dir);
  if (!b) throw new Error('no dpad button ' + dir);
  b.click();
};
const until = async (cond, label) => {
  for (let i = 0; i < 80 && !cond(); i++) await wait(25);
  if (!cond()) throw new Error('timed out waiting for ' + label);
};

const log = [];
const note = (what, value) => log.push([what, value]);

try {
  // ---- Begin: the hero stands in the town, nothing has happened yet ----
  for (let i = 0; i < 60 && !document.getElementById('ts-enter'); i++) await wait(50);
  document.getElementById('ts-enter').click();
  for (let i = 0; i < 60 && !window.VEFR_COMBAT; i++) await wait(50);

  const start = snap();
  note('start-region', start.region);
  note('start-hero', start.hero);

  // Every narrator line, in the order the player said it. `combatSay`
  // is the one surface a rule's `say` reaches, and it is a top-level
  // function, so the global binding is what the death path calls.
  const said = [];
  const realSay = window.combatSay;
  window.combatSay = function (msg) {
    said.push(msg);
    return realSay(msg);
  };

  note('flags-before', flags());
  note('why-before', why().map((e) => e.id));

  // ---- One step west: the bump that empties the health bar ----
  press('left');
  await until(() => flags()['fell'] === true, 'the falls rule');
  await until(() => flags()['awoke'] === true, 'the wakes rule');

  const end = snap();
  note('flags-after', flags());
  note('said', said);
  note('said-line', sayLine());
  note('end-region', end.region);
  note('end-hero', end.hero);
  note('why', why().map((e) => [e.id, e.why]));
} catch (e) {
  log.push(['HARNESS-ERROR', String((e && e.message) || e)]);
}

process.stdout.write(JSON.stringify({ log }, null, 1));
window.close();