/* Skin apply harness: plays the REAL woven player in jsdom. argv[2] = a skinned woven file,
   argv[3] = a plain one, argv[4] = a dressed one (backdrop + fonts), argv[5] = that same
   dressed file with prefers-contrast: more. Prints what the skin did to the page. */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const noop = () => {};
function boot(path, contrastMore) {
  return new JSDOM(fs.readFileSync(path, 'utf8'), {
    runScripts: 'dangerously', pretendToBeVisual: true, url: 'http://localhost/',
    beforeParse: (window) => {
      // The canvas is a stub, but it counts what the player asked it to paint.
      window.__painted = { drawImage: 0, fillRect: 0 };
      window.HTMLCanvasElement.prototype.getContext = function () {
        const real = { canvas: this };
        return new Proxy(real, {
          get: (t, k) => (k in t ? t[k] : (...a) => {
            if (k === 'drawImage') window.__painted.drawImage += 1;
            if (k === 'fillRect') window.__painted.fillRect += 1;
            void a;
          }),
        });
      };
      window.matchMedia = (q) => ({
        matches: /prefers-contrast: more/.test(q) ? !!contrastMore : false,
        addListener: noop, removeListener: noop, addEventListener: noop, removeEventListener: noop,
      });
    },
  }).window;
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function report(path, contrastMore) {
  const w = boot(path, contrastMore);
  for (let i = 0; i < 60 && !w.document.getElementById('ts-enter'); i++) await wait(50);
  // Press Begin, the way a person does: the map (and the stage rectangle the
  // camera publishes) only exist once the game is up.
  w.document.getElementById('ts-enter').click();
  for (let i = 0; i < 60 && !w.VEFR_STAGE; i++) await wait(50);
  await wait(200);
  const el = w.document.getElementById('vefr-skin-css');
  // The backdrop's picture never decodes under jsdom, so the harness stands in
  // for it: one decoded 64 px picture, then none. A resize redraws the map.
  const paintedWith = (img) => {
    w.VEFR_BACKDROP = img;
    w.__painted = { drawImage: 0, fillRect: 0 };
    w.dispatchEvent(new w.Event('resize'));
    return w.VEFR_BACKDROP_STATE ? w.VEFR_BACKDROP_STATE() : null;
  };
  const withPicture = paintedWith({ complete: true, naturalWidth: 64, naturalHeight: 64 });
  const withoutPicture = paintedWith(null);
  const r = {
    hasStyle: !!el,
    css: el ? el.textContent : '',
    bodyClass: w.document.body.className,
    htmlClass: w.document.documentElement.className,
    imgsWithText: [...w.document.querySelectorAll('img')].filter((i) => (i.alt || '').length > 0).length,
    backdropUrl: w.VEFR_BACKDROP_URL === undefined ? null : w.VEFR_BACKDROP_URL,
    hasRedraw: typeof w.VEFR_REDRAW === 'function',
    withPicture, withoutPicture,
    // The same maths three ways: no picture, a 300x240 map centred in an
    // 800x600 window (ground on all four sides), and a map that fills it.
    bands: w.VEFR_BACKDROP_BANDS ? {
      noPicture: w.VEFR_BACKDROP_BANDS(false, 800, 600, -250, -180, 300, 240),
      smallMap: w.VEFR_BACKDROP_BANDS(true, 800, 600, -250, -180, 300, 240),
      fullWindow: w.VEFR_BACKDROP_BANDS(true, 800, 600, 0, 0, 800, 600),
    } : null,
  };
  w.close();
  return r;
}
console.log(JSON.stringify({
  skinned: await report(process.argv[2]),
  plain: await report(process.argv[3]),
  dressed: await report(process.argv[4]),
  contrast: await report(process.argv[5], true),
}));
process.exit(0);
