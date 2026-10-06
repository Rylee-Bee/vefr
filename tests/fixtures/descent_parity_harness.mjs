/* Descent parity harness: the woven player's JavaScript twin of `locate`
   and the play-time floor must answer exactly what Python answers.

   argv[2] = woven html, argv[3] = JSON cases made by pytest:
   {"descent": <the pack's descent block>, "depths": [1, 2, ...],
    "runs": [0, 1]}.
   Prints {"hasApi": bool, "located": [...], "plans": [...]}.

   A second descent may come with the cases as `blueprintDescent`, with
   `blueprintDepths`: the same block plus the pack's Blueprint, which is
   what a floor resolves its families through. It is planted exactly as
   the first one is - the player reads the block at call time - and its
   answers come back under `blueprint`. */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const noop = () => {};
const cases = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
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
// The block is planted after the file has run, exactly as the bake writes
// it and the player reads it at call time. Nothing else is planted: no
// storage, so nothing here can be a saved value.
w.VEFR_DESCENT_DEF = cases.descent;
await new Promise((r) => w.setTimeout(r, 300));
const D = w.VEFR_DESCENT;
const out = { hasApi: !!(D && D.locate && D.floorPlan), located: [], plans: [] };
if (out.hasApi) {
  for (const depth of cases.depths) {
    const at = D.locate(depth);
    out.located.push([at.cycle, at.section, at.k]);
    out.plans.push(D.floorPlan(depth));
  }
  for (const run of cases.runs) {
    out.plans.push(D.floorPlan(1, run));
  }
}
if (cases.blueprintDescent) {
  w.VEFR_DESCENT_DEF = cases.blueprintDescent;
  out.blueprint = { located: [], plans: [] };
  for (const depth of cases.blueprintDepths) {
    const at = D.locate(depth);
    out.blueprint.located.push([at.cycle, at.section, at.k]);
    out.blueprint.plans.push(D.floorPlan(depth));
  }
}
fs.writeSync(1, JSON.stringify(out) + '\n');
w.close();
process.exit(0);