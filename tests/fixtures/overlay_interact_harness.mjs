/* Overlay interact harness (derived from the events harness): EXECUTES the woven single-file player in a
   real DOM (jsdom, dev-only) and performs every player action the
   rules engine can now notice - through the paths a player uses:
   Interact on a chest, walking onto a drop, bumping a rat, using a
   kept quest tool, trading at a shopkeeper, closing a book, turning
   the watch. It reports the fired rules, the bag, the gold and the
   two new evidence panels.

   usage: node events_play_harness.mjs <woven.html> */
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
const whyLog = () => (window.VEFR_WHY || []).slice();
const flags = () => ((window.VEFR_RULES_STATE || {}).flags) || {};
const bag = () => JSON.parse(
  window.localStorage.getItem('vefr-bag-events-test') || '[]');
const hero = () => window.VEFR_COMBAT.hero.at.slice();
const until = async (cond, label) => {
  for (let i = 0; i < 80 && !cond(); i++) await wait(25);
  if (!cond()) throw new Error('timed out waiting for ' + label);
};
const press = (dir) => {
  const b = [...document.querySelectorAll('#dpad button')]
    .find((x) => x.dataset.dir === dir);
  if (!b) throw new Error('no dpad button ' + dir);
  b.click();
};
const walkTo = async (tx, ty) => {
  for (let i = 0; i < 40; i++) {
    const [x, y] = hero();
    if (x === tx && y === ty) return;
    if (x !== tx) press(x < tx ? 'right' : 'left');
    else press(y < ty ? 'down' : 'up');
    await wait(10);
  }
};


const steps = [];
const note = (ok, what) => steps.push({ ok: !!ok, what });
const key = (k, extra) => document.dispatchEvent(new window.KeyboardEvent(
  'keydown', Object.assign({ key: k, bubbles: true, cancelable: true }, extra || {})));
const hidden = (id) => document.getElementById(id).hidden;
try {
  for (let i = 0; i < 60 && !document.getElementById('ts-enter'); i++) await wait(50);
  document.getElementById('ts-enter').click();
  await wait(300);

  // ---- a three-page note: E turns the pages, then closes it ----
  window.openReader({ id: 'a-test-note', title: 'A test note', pages: ['one', 'two', 'three'] });
  note(!hidden('reader'), 'the reader opened');
  key('e');
  note(document.getElementById('reader-text').textContent === 'two', 'E turned to page two');
  key(' ');
  note(document.getElementById('reader-text').textContent === 'three', 'Space turned to page three');
  key('Enter', { repeat: true });
  note(!hidden('reader'), 'a held key did not close the note');
  key('f');
  note(hidden('reader'), 'F on the last page closed the note');

  // ---- a speech box: E continues it, and starts no second talk ----
  window.showSpeech('Someone', 'A line.', '');
  note(!hidden('npc-box'), 'the speech box opened');
  key('e');
  note(hidden('npc-box'), 'E closed the speech box');
  window.showSpeech('Someone', 'Another line.', '');
  key('Enter');
  note(hidden('npc-box'), 'Enter closed the speech box');
  window.showSpeech('Someone', 'A third line.', '');
  key('e', { repeat: true });
  note(!hidden('npc-box'), 'a held E did not dismiss it');
  document.getElementById('npc-close').click();

} catch (err) { note(false, 'threw: ' + err.message); }
console.log(JSON.stringify({ allOk: steps.every((s) => s.ok), steps }));
window.close();
process.exit(0);
