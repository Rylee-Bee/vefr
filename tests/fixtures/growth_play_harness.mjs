/* Growth play harness (derived from the events harness): EXECUTES the woven single-file player in a
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
const text = () => document.body.textContent;
const foe = () => window.refreshCombatSnapshot().enemies.filter((e) => e.alive)[0];
// bump the first living enemy once; resolves when its hp changes or it falls
const strikeOnce = async () => {
  const f = foe(); if (!f) return false;
  const hp0 = f.hp; const id = f.id;
  for (let i = 0; i < 30; i++) {
    const cur = window.refreshCombatSnapshot().enemies.find((e) => e.id === id);
    if (!cur || !cur.alive || cur.hp !== hp0) return true;
    const [hx, hy] = window.VEFR_COMBAT.hero.at; const [fx, fy] = cur.at;
    if (fx !== hx) press(fx < hx ? 'left' : 'right'); else press(fy < hy ? 'up' : 'down');
    await wait(15);
  }
  return false;
};
const growthState = (name) => JSON.parse(window.localStorage.getItem('vefr-growth-' + name) || 'null');
const mode = process.argv[3];
try {
  for (let i = 0; i < 60 && !document.getElementById('ts-enter'); i++) await wait(50);
  document.getElementById('ts-enter').click();
  await wait(300);
  if (mode === 'levels') {
    note(window.heroMax() === 8 && window.heroAtk() === 2, 'level 1 numbers are the base 8 / 2');
    for (let i = 0; i < 6 && foe(); i++) await strikeOnce();
    note(!foe(), 'the rat fell');
    note(/3 experience/.test(text()), 'the award line says 3 experience');
    note(/Level 2/.test(text()), 'the level-up line says Level 2');
    note(window.heroMax() === 10 && window.heroAtk() === 3, 'level 2 numbers are 10 / 3');
    const s = growthState('growth-test');
    note(s && s.xp === 3, 'the xp is saved under vefr-growth-<world>');
    note(window.HERO_HP > 0 && window.HERO_HP <= 10, 'health stays inside the new max');
  } else {
    note(window.heroAtk() === 2, 'practice starts at the base attack');
    await strikeOnce();
    note(window.heroAtk() === 3, 'one strike taught attack +1');
    note(/Attack up by 1/.test(text()), 'the growth line says Attack up by 1');
    note(!/experience/.test(text()), 'practice mode shows no experience');
    for (let i = 0; i < 8 && foe(); i++) await strikeOnce();
    note(window.heroAtk() === 3, 'the cap holds: attack stays 3');
  }
} catch (err) { note(false, 'threw: ' + err.message); }
console.log(JSON.stringify({ allOk: steps.every((s) => s.ok), steps }));
window.close();
process.exit(0);
