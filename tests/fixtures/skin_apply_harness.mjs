/* Skin apply harness: plays the REAL woven player in jsdom. argv[2] = a skinned woven file,
   argv[3] = a plain one. Prints what the skin did to the page. */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const noop = () => {};
function boot(path) {
  return new JSDOM(fs.readFileSync(path, 'utf8'), {
    runScripts: 'dangerously', pretendToBeVisual: true, url: 'http://localhost/',
    beforeParse: (window) => {
      window.HTMLCanvasElement.prototype.getContext = function () {
        return new Proxy({ canvas: this }, { get: (t, k) => (k in t ? t[k] : noop) });
      };
      window.matchMedia = () => ({ matches: false, addListener: noop, removeListener: noop });
    },
  }).window;
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function report(path) {
  const w = boot(path);
  for (let i = 0; i < 60 && !w.document.getElementById('ts-enter'); i++) await wait(50);
  await wait(200);
  const el = w.document.getElementById('vefr-skin-css');
  const r = {
    hasStyle: !!el,
    css: el ? el.textContent : '',
    bodyClass: w.document.body.className,
    htmlClass: w.document.documentElement.className,
    imgsWithText: [...w.document.querySelectorAll('img')].filter((i) => (i.alt || '').length > 0).length,
  };
  w.close();
  return r;
}
console.log(JSON.stringify({ skinned: await report(process.argv[2]), plain: await report(process.argv[3]) }));
process.exit(0);
