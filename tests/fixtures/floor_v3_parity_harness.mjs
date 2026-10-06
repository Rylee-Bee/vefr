/* Parity harness: the woven player's JavaScript twin of the v3 generator must draw
   exactly the floor Python draws, stage for stage.

     node floor_v3_parity_harness.mjs <woven html> <cases.json> <out base>

   <cases.json> (written by pytest, from tests/floor_v3_parity_cases.py):
     {"packs": {"<key>": <section pack>}, "stamps": [<stamp record>...],
      "depth": 3, "cycle": 0, "cases": [{i, seed, w, h, kind, size, stamped, pack}]}

   The canonical form is `tests/fixtures/floor_plan_canon.mjs`, imported here
   and injected into the Chromium test, so both paths compare the same bytes.

   Writes three files next to <out base>, and prints one JSON line:
     <out base>.stages.jsonl  one line per case: {"i", "plan", "layout", "graph",
                              "pop", "floor", "failed"} - each a canonical string,
                              or "" where the stage was not reached
     <out base>.e2e.jsonl     one line per case: {"i", "gen", "floor"}
     <out base>.meta.json     {"hasApi", "constants", "streams", "perf"}

*/
import fs from 'node:fs';
import { performance } from 'node:perf_hooks';
import { JSDOM } from 'jsdom';
import { canon } from './floor_plan_canon.mjs';

const htmlPath = process.argv[2];
const casesPath = process.argv[3];
const outBase = process.argv[4];

const noop = () => {};
const dom = new JSDOM(fs.readFileSync(htmlPath, 'utf8'), {
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

const cases = JSON.parse(fs.readFileSync(casesPath, 'utf8'));
const D = w.VEFR_DELVE;

// The determinism check needs the stream names of a REAL floor key, because
// that is what the check compares: `run_seed / section.id / cycle / k`, the
// same four parts `tests/floor_v3_parity_cases.py:floor_key` builds. Asking
// the twin for the streams of the literal 'seed/section/0/1' could only ever
// return that literal back, so the check could never be satisfied by a twin
// that got the names right. The first case of the sweep carries the four
// parts already: its seed, its kind, its Section pack's id, and the sweep's
// own cycle and k.
const firstCase = cases.cases[0];
const firstKey = firstCase
  ? firstCase.seed + '/' + cases.packs[firstCase.pack].id + '/'
    + cases.cycle + '/' + cases.depth
  : 'seed/section/0/1';
const meta = {
  hasApi: !!(D && typeof D.v3Attempt === 'function'
    && typeof D.generateFloorV3 === 'function'),
  constants: D ? D.v3Constants : {},
  streams: D ? D.v3Streams(firstKey) : {},
  perf: {},
};

function finish(code) {
  fs.writeFileSync(outBase + '.meta.json', JSON.stringify(meta) + '\n');
  process.stdout.write(JSON.stringify({ hasApi: meta.hasApi, cases: cases.cases.length }) + '\n');
  w.close();
  process.exit(code);
}

if (!meta.hasApi) {
  fs.writeFileSync(outBase + '.stages.jsonl', '');
  fs.writeFileSync(outBase + '.e2e.jsonl', '');
  finish(2);
}

const stages = fs.openSync(outBase + '.stages.jsonl', 'w');
const e2e = fs.openSync(outBase + '.e2e.jsonl', 'w');

// Generate + validate is the budget PLAN.md section 3 measures, so the timing
// wraps the whole public call - the retry ladder and the v2 fallback included -
// and the warm-up pass is discarded rather than counted as a slow first sample.
function percentile(values, p) {
  const ordered = values.slice().sort(function (a, b) { return a - b; });
  return ordered[Math.min(ordered.length - 1, Math.floor(p * (ordered.length - 1)))];
}

const samples = {};
function measure(label, run) {
  run();                      // warm-up, discarded: not a slow first sample
  const t0 = performance.now();
  const result = run();
  const ms = performance.now() - t0;
  (samples[label] || (samples[label] = [])).push(ms);
  return result;
}

for (let c = 0; c < cases.cases.length; c++) {
  const kase = cases.cases[c];
  const pack = cases.packs[kase.pack];
  if (!pack) throw new Error('no Section pack named ' + kase.pack);
  const records = kase.stamped ? cases.stamps : [];
  const key = kase.seed + '/' + pack.id + '/' + cases.cycle + '/' + cases.depth;

  // A twin that throws on one case is a mismatch, not a dead harness: the
  // case is written out as it went wrong and the run carries on, so the test
  // names the seed rather than a stack trace.
  let got;
  try {
    got = D.v3Attempt(key, kase.w, kase.h, pack, kase.kind,
      records, cases.depth, false);
  } catch (err) {
    fs.writeSync(stages, JSON.stringify({
      i: kase.i, plan: '', layout: '', graph: '', pop: '', floor: '',
      failed: 'threw: ' + (err && err.message ? err.message : String(err)),
    }) + '\n');
    continue;
  }
  fs.writeSync(stages, JSON.stringify({
    i: kase.i,
    plan: canon(got.plan),
    layout: canon(got.layout),
    graph: got.graph === null ? '' : canon(got.graph),
    pop: got.pop === null ? '' : canon(got.pop),
    floor: got.floor === null ? '' : canon(got.floor),
    failed: got.failed,
  }) + '\n');

  const label = kase.size + (kase.stamped ? '-stamped' : '');
  const floor = measure(label, function () {
    return D.generateFloorV3(kase.seed, [kase.w, kase.h], pack, kase.kind,
      records, cases.depth, cases.cycle);
  });
  // The whole floor comes back only when the stage comparison could not
  // already have covered it: a v2 fallback, or a floor the first attempt
  // failed and the retry ladder then drew. Everything else was compared
  // stage by stage, and the ladder is proved by the `gen` and by these two.
  const settled = floor.gen === 3 && got.failed === '';
  fs.writeSync(e2e, JSON.stringify({
    i: kase.i,
    gen: floor.gen,
    floor: settled ? '' : canon(floor),
  }) + '\n');
}

for (const label of Object.keys(samples)) {
  const values = samples[label];
  meta.perf[label] = {
    seeds: values.length,
    ms_p50: Math.round(percentile(values, 0.50) * 1000) / 1000,
    ms_p95: Math.round(percentile(values, 0.95) * 1000) / 1000,
  };
}

fs.closeSync(stages);
fs.closeSync(e2e);
finish(0);