/* Descent document harness: the pure parts of the save-deltas rule, run
   in the REAL woven player so the numbers are the shipped ones.

   argv[2] = woven html, argv[3] = JSON cases made by pytest:
   {"descent": <block>, "docs": [<a document to trim and measure>...]}.
   Prints {"hasApi": bool, "results": [{floors, bytes, trimmed, bytesAfter}]}. */
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
w.VEFR_DESCENT_DEF = cases.descent;
await new Promise((r) => w.setTimeout(r, 300));
const D = w.VEFR_DESCENT;
const out = { hasApi: !!(D && D.trimDoc && D.docBytes && D.floorBytes), results: [] };
const size = (doc) => JSON.stringify(doc).length;
for (const doc of cases.docs) {
  const trimmed = D.trimDoc(JSON.parse(JSON.stringify(doc)));
  out.results.push({
    floors: Object.keys(trimmed.floors || {}).length,
    bytes: size(doc),
    bytesAfter: size(trimmed),
    order: trimmed.order || [],
    // In the document's own order, which is the order they were visited:
    // "cellar-0-1-10" sorts before "cellar-0-1-5" and means nothing by it.
    fogs: (trimmed.order || []).filter((k) => trimmed.floors[k] && trimmed.floors[k].fog),
  });
}
fs.writeSync(1, JSON.stringify(out) + '\n');
w.close();
process.exit(0);