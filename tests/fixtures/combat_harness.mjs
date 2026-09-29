/* Combat harness: EXECUTES the woven single-file player in a real DOM
   (jsdom, dev-only) and plays the first fight end to end. Bump the
   adjacent enemy, watch it hit back, kill it and see it stay dead;
   watch a distant enemy inside its sight step toward the hero; then
   take a fatal blow and wake up whole at the baked wake point.
   Deterministic: the fixture is fixed, so every number here is pinned.

   usage: node combat_harness.mjs <woven.html> */
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
      beginPath: noop, arc: noop, fill: noop, stroke: noop, closePath: noop,
      moveTo: noop, lineTo: noop, fillText: noop,
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

const log = [];
const snap = () => window.VEFR_COMBAT;
const byId = (s) => Object.fromEntries(s.enemies.map((e) => [e.id, e]));
const press = (dir) => {
  const b = [...document.querySelectorAll('#dpad button')]
    .find((x) => x.dataset.dir === dir);
  if (!b) throw new Error('no dpad button ' + dir);
  b.click();
};
const hpLine = () => document.getElementById('hud-hp-value').textContent;
const sayLine = () => document.getElementById('combat-live').textContent;

try {
  for (let i = 0; i < 60 && !document.getElementById('ts-enter'); i++) await wait(50);
  document.getElementById('ts-enter').click();
  for (let i = 0; i < 60 && !window.VEFR_COMBAT; i++) await wait(50);

  const start = snap();
  log.push(['start', start]);
  log.push(['hp-line0', hpLine()]);
  log.push(['rat-start', byId(start)['cellar-rat']]);
  log.push(['pale-start', byId(start)['pale-thing']]);

  // 1. Bump the adjacent rat: it loses hero.atk (2) hp, then hits back
  //    for 1. The pale thing, six tiles away and in sight, steps closer.
  press('right');
  let s = snap();
  log.push(['after-bump1', s]);
  log.push(['said-bump1', sayLine()]);
  log.push(['hp-line1', hpLine()]);

  // 2. Bump again: the rat falls; its id is remembered as slain.
  press('right');
  s = snap();
  log.push(['after-bump2', s]);
  log.push(['said-bump2', sayLine()]);
  log.push(['slain-after-kill',
    window.localStorage.getItem('vefr-slain-combat-test-town')]);

  // 3. Walk toward the pale thing while it walks in. It is adjacent at
  //    [4,1] by the time the hero reaches [3,1], and one blow of 2
  //    empties a 2-hp hero: Cozy death, restored and woken whole.
  press('right');
  press('right');
  s = snap();
  log.push(['after-death', s]);
  log.push(['said-death', sayLine()]);
  log.push(['hp-line-death', hpLine()]);
} catch (e) {
  log.push(['HARNESS-ERROR', String((e && e.message) || e)]);
}

process.stdout.write(JSON.stringify({
  log,
  setIntervalInTemplate: html.includes('setInterval'),
}, null, 1));
window.close();
