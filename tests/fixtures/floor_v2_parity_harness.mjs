/* Parity harness: the woven player's JavaScript twin of the floor generator must draw the
   SAME rows as Python. argv[2] = woven html, argv[3] = JSON of cases made by pytest:
   {"prng": [{"seed", "count"}], "floors": [{"seed","width","height","rooms"}]}.
   Prints {"prng": [[floats]...], "floors": [[rows]...]}. */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const noop = () => {};
const dom = new JSDOM(fs.readFileSync(process.argv[2], 'utf8'), {
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
const cases = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const D = w.VEFR_DELVE;
const out = { hasApi: !!(D && D.prng && D.generateFloorV2), prng: [], floors: [] };
if (out.hasApi) {
  for (const c of cases.prng) { const r = D.prng(c.seed); out.prng.push(Array.from({ length: c.count }, () => r())); }
  for (const c of cases.floors) out.floors.push(D.generateFloorV2(c.seed, c.width, c.height, c.rooms));
}
console.log(JSON.stringify(out));
w.close();
process.exit(0);
