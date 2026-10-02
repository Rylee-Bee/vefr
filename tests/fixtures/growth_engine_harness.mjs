/* Growth engine harness (T2): calls the PURE window.VEFR_GROWTH_ENGINE in
   the real woven player with literal configs and prints every result as
   JSON. usage: node growth_engine_harness.mjs <woven.html> */
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
const E = w.VEFR_GROWTH_ENGINE;
const J = (x) => JSON.parse(JSON.stringify(x));
const L = { mode: 'levels', levels: { xp: [0, 10, 25, 50], gain: { hp: 2, atk: 1 } } };
const P = { mode: 'practice', practice: {
  atk: { by: 'strikes', every: 3, gain: 1, cap: 2 },
  hp: { by: 'hits-taken', every: 2, gain: 1, cap: 5 } } };
const out = {};
out.hasEngine = !!E;
out.levelFor = [0, 9, 10, 24, 25, 999].map((x) => E.levelFor(L, x));
out.statsLevels = [0, 25].map((x) => J(E.statsFor(L, { xp: x, counts: {} })));
out.awardOne = J(E.award(L, { xp: 8, counts: {} }, 5));
out.awardTwo = J(E.award(L, { xp: 8, counts: {} }, 20));
out.awardZero = J(E.award(L, { xp: 8, counts: {} }, 0));
out.awardNeg = J(E.award(L, { xp: 8, counts: {} }, -4));
out.statsPractice = J(E.statsFor(P, { xp: 0, counts: { strikes: 8, 'hits-taken': 3 } }));
out.statsCapped = J(E.statsFor(P, { xp: 0, counts: { strikes: 100 } }));
let st = { xp: 0, counts: {} };
out.bumps = [];
for (let i = 0; i < 3; i++) {
  const r = E.bump(P, st, 'strikes');
  st = J(r.state);
  out.bumps.push(J(r.grown));
}
out.bumpState = st;
out.bumpLevelsMode = J(E.bump(L, { xp: 0, counts: {} }, 'strikes'));
out.bumpUnknown = J(E.bump(P, { xp: 0, counts: {} }, 'sneezes'));
out.nullStats = J(E.statsFor(null, { xp: 5, counts: {} }));
out.nullAward = J(E.award(null, { xp: 5, counts: {} }, 4));
out.badState = J(E.statsFor(L, { xp: 'bad', counts: 7 }));
out.nullState = J(E.statsFor(L, null));
out.shortTable = J(E.statsFor({ mode: 'levels', levels: { xp: [0, 5], gain: { hp: 1, atk: 0 } } },
                               { xp: 999, counts: {} }));
console.log(JSON.stringify(out));
w.close();
process.exit(0);
