/* Combat harness: EXECUTES the woven single-file player in a real DOM
   (jsdom, dev-only) and plays the first fight end to end. Bump the
   adjacent enemy, watch it hit back, kill it and see it stay dead;
   watch a distant enemy inside its sight step toward the hero; then
   take a fatal blow and wake up whole at the baked wake point. It then
   plays the loot loop (a drop, a bag, a chest) and the reward loop
   (trade at a shopkeeper's fixed prices, then drink a potion that
   heals up to the max and says so when already whole). Deterministic:
   the fixture is fixed, so every number here is pinned.

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
  log.push(['gold-line0', document.getElementById('hud-gold').textContent]);
  log.push(['gold-line0-hidden', document.getElementById('hud-gold').hidden]);
  log.push(['rat-start', byId(start)['cellar-rat']]);
  log.push(['pale-start', byId(start)['pale-thing']]);

  // 1. Bump the adjacent rat: it loses hero.atk (2) hp, then hits back
  //    for 1. The pale thing, six tiles away and in sight, steps closer.
  press('right');
  let s = snap();
  log.push(['after-bump1', s]);
  log.push(['said-bump1', sayLine()]);
  log.push(['hp-line1', hpLine()]);

  // 2. Bump again: the rat falls; its id is remembered as slain, and
  //    its drop is left on the tile it died on.
  press('right');
  s = snap();
  log.push(['after-bump2', s]);
  log.push(['said-bump2', sayLine()]);
  log.push(['slain-after-kill',
    window.localStorage.getItem('vefr-slain-combat-test-town')]);
  log.push(['floor-after-kill', s.floor]);
  log.push(['bag-after-kill', s.bag]);

  // 3. Step onto the drop: it is taken, leaves the floor, and the bag
  //    holds it. The pale thing keeps walking in.
  press('right');
  s = snap();
  log.push(['after-take', s]);
  log.push(['said-take', sayLine()]);
  log.push(['bag-after-take', s.bag]);
  log.push(['floor-after-take', s.floor]);
  log.push(['strip-hidden-after-take',
    document.getElementById('bag-strip').hidden]);
  log.push(['strip-count-after-take',
    document.getElementById('bag-strip').children.length]);

  // 4. Walk into the pale thing. It is adjacent now and one blow of 2
  //    empties a 2-hp hero: Cozy death, restored and woken whole.
  press('right');
  s = snap();
  log.push(['after-death', s]);
  log.push(['said-death', sayLine()]);
  log.push(['hp-line-death', hpLine()]);

  // 5. A chest at [1, 2] holds a note and two items. Step onto it and
  //    use it: the note opens and the items join the bag (the potion a
  //    second time - two potions are two potions).
  press('down');
  document.getElementById('interact').click();
  s = snap();
  log.push(['after-chest', s]);
  log.push(['said-chest', sayLine()]);
  log.push(['bag-after-chest', s.bag]);
  log.push(['floor-after-chest', s.floor]);
  log.push(['reader-title', document.getElementById('reader-title').textContent]);
  // The Bag panel (pause menu) lists one row per carried thing.
  document.getElementById('menu-open').click();
  document.querySelector('[data-panel="bag"]').click();
  log.push(['bag-panel-rows',
    document.getElementById('bag-list').querySelectorAll('.bag-row').length]);
  log.push(['bag-panel-count', document.getElementById('bag-count').textContent]);

  // 6. Trade: a merchant stands beside the chest tile. Close the menu,
  //    interact to open the Trade panel, sell a potion for its 8 gold,
  //    then buy one back for 8. The purse and the bag move exactly.
  document.getElementById('menu-close').click();
  document.getElementById('interact').click();
  log.push(['trade-open', !document.getElementById('trade').hidden]);
  log.push(['trade-title', document.getElementById('trade-title').textContent]);
  log.push(['trade-gold-open',
    document.getElementById('trade-gold').textContent]);
  const sellButton = document.querySelector(
    '#trade-sell button[data-item="cloudy-potion"]');
  sellButton.click();
  s = snap();
  log.push(['after-sell', s]);
  log.push(['said-sell', document.getElementById('trade-live').textContent]);
  log.push(['gold-after-sell', s.gold]);
  const buyButton = document.querySelector(
    '#trade-buy button[data-item="cloudy-potion"]');
  buyButton.click();
  s = snap();
  log.push(['after-buy', s]);
  log.push(['said-buy', document.getElementById('trade-live').textContent]);
  log.push(['gold-after-buy', s.gold]);
  log.push(['bag-after-buy', s.bag]);
  document.getElementById('trade-close').click();
  log.push(['trade-closed', document.getElementById('trade').hidden]);

  // 7. Use: walk to the pale thing and take one blow (hp 3 -> 1), then
  //    drink a 3-heal potion. The drink clamps at the 3-hp max (heals
  //    only 2) and one copy leaves the bag; a second drink at full
  //    health says so and costs nothing.
  press('up');
  press('right');
  press('right');
  press('right');
  s = snap();
  log.push(['after-blow', s]);
  document.getElementById('menu-open').click();
  document.querySelector('[data-panel="bag"]').click();
  log.push(['bag-gold-line', document.getElementById('bag-gold').textContent]);
  const useA = document.querySelector(
    '#bag-list button[data-item="cloudy-potion"]');
  useA.click();
  s = snap();
  log.push(['after-use', s]);
  log.push(['said-use', document.getElementById('bag-live').textContent]);
  log.push(['hp-after-use', s.hero.hp]);
  const useB = document.querySelector(
    '#bag-list button[data-item="cloudy-potion"]');
  useB.click();
  s = snap();
  log.push(['after-use-full', s]);
  log.push(['said-use-full', document.getElementById('bag-live').textContent]);
  log.push(['bag-after-use-full', s.bag]);
} catch (e) {
  log.push(['HARNESS-ERROR', String((e && e.message) || e)]);
}

process.stdout.write(JSON.stringify({
  log,
  setIntervalInTemplate: html.includes('setInterval'),
}, null, 1));
window.close();
