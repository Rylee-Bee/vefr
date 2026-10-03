/* Equipment engine harness (A2): calls the PURE window.VEFR_EQUIP_ENGINE in
   the real woven player with literal states and prints every result as JSON.
   usage: node equip_engine_harness.mjs <woven.html> */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const html = fs.readFileSync(process.argv[2], 'utf8');
const noop = () => {};
const dom = new JSDOM(html, {
  runScripts: 'dangerously', pretendToBeVisual: true, url: 'http://localhost/',
  beforeParse: (window) => {
    window.HTMLCanvasElement.prototype.getContext = function () {
      return new Proxy({ canvas: this }, { get: (t, k) => (k in t ? t[k] : noop) });
    };
    window.matchMedia = () => ({ matches: false, addListener: noop, removeListener: noop });
  },
});
const w = dom.window;
await new Promise((r) => w.setTimeout(r, 300));
const E = w.VEFR_EQUIP_ENGINE;
const J = (x) => JSON.parse(JSON.stringify(x));

// The catalog the equip fixture bakes: cloak-1 body +2hp, coat-1 body +1hp
// (a second body thing, so a swap into an occupied slot is testable), bow-1
// hand +1atk, ring-1 charm no mods, potion-1 no slot, plus the sample's
// unslotted torch and chalked map. Literal here, no dependency on a weave.
const ITEMS = {
  'cloak-1': { name: 'a hooded cloak', sprite: 'cloak', slot: 'body', mods: { hp: 2 } },
  'coat-1': { name: 'a patched coat', sprite: 'cloak', slot: 'body', mods: { hp: 1 } },
  'bow-1': { name: 'a short bow', sprite: 'bow', slot: 'hand', mods: { atk: 1 } },
  'ring-1': { name: 'a plain ring', sprite: 'ring', slot: 'charm', value: 3 },
  'potion-1': { name: 'a cloudy potion', sprite: 'potion', heal: 3, use: 'drink' },
  torch: { name: 'a pitch torch', light: { radius: 2, turns: 6 } },
};
const BASE = { hp: 6, atk: 2 };
const NOTHING = {};

const out = {};
out.hasEngine = !!E;
if (E) {
  // --- stat sums: base plus every worn mod -----------------------------------
  out.statsNone = J(E.statsFor(BASE, ITEMS, NOTHING));
  out.statsCloak = J(E.statsFor(BASE, ITEMS, { body: 'cloak-1' }));
  out.statsAll = J(E.statsFor(BASE, ITEMS, {
    body: 'cloak-1', hand: 'bow-1', charm: 'ring-1' }));
  out.statsRingOnly = J(E.statsFor(BASE, ITEMS, { charm: 'ring-1' }));
  // A worn id the catalog no longer has contributes nothing.
  out.statsGhost = J(E.statsFor(BASE, ITEMS, { head: 'gone-1' }));
  // Malformed bases and catalogs read as no gear, never a crash.
  out.statsNoBase = J(E.statsFor(null, ITEMS, { body: 'cloak-1' }));
  out.statsNoItems = J(E.statsFor(BASE, null, { body: 'cloak-1' }));
  out.statsBadState = J(E.statsFor(BASE, ITEMS, { body: 7, hand: ['x'] }));
  out.statsNoHp = J(E.statsFor({ atk: 2 }, ITEMS, { body: 'cloak-1' }));

  // --- equip -----------------------------------------------------------------
  out.equipEmpty = J(E.equip(NOTHING, ITEMS, 'body', 'cloak-1'));
  // Into a full slot, with an item that genuinely fits it: the old
  // wearer comes back for the bag.
  out.equipSwap = J(E.equip({ body: 'cloak-1' }, ITEMS, 'body', 'coat-1'));
  // A full slot is still refused when the item does not fit it: a charm
  // thing never becomes body gear just because body is taken.
  out.equipSwapMismatch = J(E.equip({ body: 'cloak-1' }, ITEMS, 'body', 'ring-1'));
  // The slot must be the item's own slot.
  out.equipWrongSlot = J(E.equip(NOTHING, ITEMS, 'hand', 'cloak-1'));
  out.equipBadSlot = J(E.equip(NOTHING, ITEMS, 'belt', 'cloak-1'));
  // An item with no slot cannot be worn at all.
  out.equipPotion = J(E.equip(NOTHING, ITEMS, 'body', 'potion-1'));
  out.equipGhost = J(E.equip(NOTHING, ITEMS, 'body', 'gone-1'));
  // The same id twice is impossible: it is already worn.
  out.equipTwice = J(E.equip({ body: 'cloak-1' }, ITEMS, 'body', 'cloak-1'));
  out.equipElsewhere = J(E.equip({ body: 'cloak-1' }, ITEMS, 'charm', 'cloak-1'));
  out.equipNoArgs = J(E.equip(NOTHING, ITEMS, 'body', null));
  out.equipNoCatalog = J(E.equip(NOTHING, null, 'body', 'cloak-1'));
  // Equipping is pure: the caller's state object is never written to.
  const frozen = Object.freeze({ body: 'cloak-1' });
  out.equipPure = J(E.equip(frozen, ITEMS, 'charm', 'ring-1'));
  out.equipPureInput = J(frozen);

  // --- unequip ---------------------------------------------------------------
  out.unequipWorn = J(E.unequip({ body: 'cloak-1', charm: 'ring-1' }, 'body'));
  out.unequipEmpty = J(E.unequip({ body: 'cloak-1' }, 'hand'));
  out.unequipBadSlot = J(E.unequip({ body: 'cloak-1' }, 'belt'));
  out.unequipNothing = J(E.unequip(null, 'body'));

  // --- a saved state that no longer matches the catalog ----------------------
  out.cleanOk = J(E.clean({ body: 'cloak-1', charm: 'ring-1' }, ITEMS));
  out.cleanGhost = J(E.clean({ body: 'gone-1', charm: 'ring-1' }, ITEMS));
  out.cleanWrongSlot = J(E.clean({ hand: 'cloak-1' }, ITEMS));
  out.cleanUnslotted = J(E.clean({ body: 'potion-1' }, ITEMS));
  out.cleanBadShape = J(E.clean({ body: 7, hat: 'cloak-1' }, ITEMS));
  out.cleanNoArgs = J(E.clean(null, null));

  // --- the health clamp ------------------------------------------------------
  out.clampLower = E.clampHealth(10, 5);
  out.clampSame = E.clampHealth(5, 5);
  out.clampHigher = E.clampHealth(5, 12);   // a bigger max never heals
  out.clampFloor = E.clampHealth(2, 0);     // never below 1
  out.clampDead = E.clampHealth(0, 5);      // never below 1
  out.clampJunk = [E.clampHealth('x', 5), E.clampHealth(5, 'x'), E.clampHealth(null, null)];
}
console.log(JSON.stringify(out));
w.close();
process.exit(0);
