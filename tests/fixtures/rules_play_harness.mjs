/* Rules play harness: EXECUTES the woven single-file player in a real
   DOM (jsdom, dev-only) and drives the two events the fixture pack's
   rules listen for. Press Begin (the `starts` rule fires), take one
   step right onto the named place (the `comes-near` rule fires), and
   hand the player's rule log back as JSON: one { id, why } per fired
   rule, each `why` a plain sentence naming its rule id - plus the
   engine state's flags and belief sources, and the narrator's live
   line. Deterministic: the fixture is fixed.

   usage: node rules_play_harness.mjs <woven.html> */
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
const press = (dir) => {
  const b = [...document.querySelectorAll('#dpad button')]
    .find((x) => x.dataset.dir === dir);
  if (!b) throw new Error('no dpad button ' + dir);
  b.click();
};
const whyLog = () => (window.VEFR_WHY || []).slice();

try {
  // 1. Start the game: Begin presses, setup runs, the `starts` rule
  //    fires (the fixture pack guarantees one, so the log is the
  //    readiness signal).
  for (let i = 0; i < 60 && !document.getElementById('ts-enter'); i++) await wait(50);
  document.getElementById('ts-enter').click();
  for (let i = 0; i < 60 && whyLog().length < 1; i++) await wait(50);
  const afterStart = whyLog();
  const narratorAfterStart =
    (document.getElementById('combat-live') || {}).textContent || '';

  // 2. Walk one step right, onto the named place beside the start:
  //    the `comes-near` rule fires with distance 0.
  press('right');
  for (let i = 0; i < 60 && whyLog().length < 2; i++) await wait(50);
  const afterWalk = whyLog();

  const state = window.VEFR_RULES_STATE || null;
  console.log(JSON.stringify({
    afterStart: afterStart,
    afterWalk: afterWalk,
    narratorAfterStart: narratorAfterStart,
    poi: (document.getElementById('poi') || {}).textContent || '',
    narrator: (document.getElementById('combat-live') || {}).textContent || '',
    flags: state ? state.flags : null,
    beliefs: state ? state.beliefs : null,
    stored: window.localStorage.getItem(
      'vefr-rules-' + ((window.VEFR_WORLD && window.VEFR_WORLD.name) || 'world')),
  }));
} catch (err) {
  console.error(String((err && err.stack) || err));
  process.exit(1);
}
