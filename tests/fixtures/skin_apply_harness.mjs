/* Skin apply harness: plays the REAL woven player in jsdom. argv is a list of
   key/path pairs:
       node skin_apply_harness.mjs skinned skinned.html plain plain.html ...
   The key `contrast` boots that page with prefers-contrast: more. Prints what
   the skin did to each page as one JSON object keyed by the names.
   jsdom does not evaluate media queries and does not load fonts, so the python
   side asserts on the generated CSS text, not on computed layout.

   The report also carries interface slice 5: the five HUD icons (each of which
   must sit BESIDE the words, never inside them) and the speech box's portrait
   (which appears for a speaker the pack gave a picture, and not at all for one
   it did not). It also reports which real control every rule in the skin sheet
   reaches, so a rule about a switch can be read against the switch's own state
   rather than off its selector text. */
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

/* The five icons, each with the HUD line it belongs beside. */
const ICONS = {
  heart: '#hud-hp', star: '#hud-level', coin: '#hud-gold',
  bag: '#bag-strip', door: '#menu-open',
};
/* A real 8x8 PNG, so a portrait that came out broken would be a broken picture
   rather than an empty string. The python side only compares the string. */
const PORTRAIT = 'data:image/png;base64,'
  + 'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEUlEQVR4nGPYUhGFFTEMLQkAL4JhgQjp6wsAAAAASUVORK5CYII=';
/* A speaker whose id and display name are the same word, so the picture is
   found however the player chooses to look a speaker up. */
const SPEAKER_WITH = 'marta';
const SPEAKER_WITHOUT = 'nobody';

const text = (node) => (node ? (node.textContent || '') : null);

/* Which real control each rule in the skin sheet actually reaches. The two
   switches the toggle part paints are the probes: a resting phase button, a
   pressed phase button, and the fog switch put into each of its two states in
   turn. A rule that carries one of the two pictures has to reach exactly the
   controls in the state that picture belongs to, so the python side can read
   the state off the real DOM rather than off the selector text. */
const GUARD = '@media (prefers-contrast: no-preference) and (not (forced-colors: active))';

function stateReport(w, css) {
  let text = css;
  const at = css.indexOf(GUARD);
  if (at !== -1) text = css.slice(css.indexOf('{', at) + 1, css.lastIndexOf('}'));
  const sels = [...text.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => m[1].trim());
  const hitsFor = (el) => sels.map((sel) => {
    if (!el) return false;
    try { return el.matches(sel); } catch (e) { return false; }
  });
  const rail = [...w.document.querySelectorAll('.phase-rail button')];
  const resting = rail.find((b) => b.getAttribute('aria-pressed') === 'false') || rail[0];
  const pressed = rail.find((b) => b.getAttribute('aria-pressed') === 'true') || rail[1];
  if (resting) resting.setAttribute('aria-pressed', 'false');
  if (pressed) pressed.setAttribute('aria-pressed', 'true');
  const fog = w.document.getElementById('fog-toggle');
  let fogResting = null;
  let fogPressed = null;
  if (fog) {
    fog.setAttribute('aria-pressed', 'false');
    fogResting = hitsFor(fog);
    fog.setAttribute('aria-pressed', 'true');
    fogPressed = hitsFor(fog);
  }
  return {
    rules: sels,
    probes: [
      { name: 'phase-resting', hits: hitsFor(resting) },
      { name: 'phase-pressed', hits: hitsFor(pressed) },
      { name: 'fog-resting', hits: fogResting },
      { name: 'fog-pressed', hits: fogPressed },
    ],
  };
}

function iconReport(w) {
  const out = {};
  for (const [name, sel] of Object.entries(ICONS)) {
    const found = [...w.document.querySelectorAll(`svg[data-icon="${name}"]`)];
    const el = found[0] || null;
    const target = w.document.querySelector(sel);
    const hud = (n) => (n ? n.closest('.hud') : null);
    out[name] = {
      count: found.length,
      ariaHidden: el ? el.getAttribute('aria-hidden') : null,
      alt: el ? el.getAttribute('alt') : null,
      text: el ? el.textContent : null,
      viewBox: el ? el.getAttribute('viewBox') : null,
      // currentColor has to be in the MARKUP: the skin sheet sits behind a
      // media guard, and an icon painted from a stylesheet is the word's
      // colour, not the skin's.
      currentColor: el ? /currentColor/.test(el.outerHTML) : false,
      shapes: el ? el.querySelectorAll('path, circle, rect, line, polyline, polygon, ellipse').length : 0,
      // beside: the same HUD block as its line, and never inside that line.
      beside: !!(el && target) && hud(el) !== null && hud(el) === hud(target),
      inside: !!(el && target) && target.contains(el),
    };
  }
  return out;
}

function npcBoxReport(w) {
  const box = w.document.getElementById('npc-box');
  const imgs = [...box.querySelectorAll('img')];
  return {
    hidden: box.hidden,
    speaker: text(w.document.getElementById('npc-name')),
    line: text(w.document.getElementById('npc-line')),
    noteHidden: w.document.getElementById('npc-note').hidden,
    images: imgs.length,
    srcs: imgs.map((i) => i.getAttribute('src')),
    alts: imgs.map((i) => i.getAttribute('alt')),
    ariaHidden: imgs.map((i) => i.getAttribute('aria-hidden')),
    // any node the player marked as the portrait slot, however it named it
    portraitSlots: box.querySelectorAll('[data-portrait], [class*="portrait"]').length,
    children: [...box.children].map((c) => c.tagName.toLowerCase()
      + (c.id ? '#' + c.id : '.' + c.className)),
  };
}

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

  // ---- the words the icons sit beside, driven through the player's own code ----
  // The purse: five gold. A world that does not trade keeps the line hidden,
  // but the WORDS are written either way, and the words are what the icon must
  // not replace.
  try {
    if (typeof w.saveGold === 'function' && typeof w.renderGold === 'function') {
      w.saveGold(5);
      w.renderGold();
    }
  } catch (e) { r.goldError = String(e); }
  // One thing carried, so the bag strip has exactly one pip.
  try {
    if (typeof w.bagAdd === 'function') w.bagAdd('torch');
  } catch (e) { r.bagError = String(e); }
  const strip = w.document.getElementById('bag-strip');
  const tl = w.document.querySelector('.hud--tl');
  r.icons = iconReport(w);
  r.hud = {
    gold: text(w.document.getElementById('hud-gold')),
    hp: text(w.document.getElementById('hud-hp')),
    level: text(w.document.getElementById('hud-level')),
    menuOpen: text(w.document.getElementById('menu-open')),
    bagChildren: strip ? strip.children.length : -1,
    bagChildTags: strip ? [...strip.children].map((c) => c.tagName.toLowerCase()) : [],
    // the HUD row as the shell builds it, so a plain page can be pinned to it
    hudTlChildren: tl ? [...tl.children].map((c) => c.id || c.className) : [],
  };

  // ---- the speech box's portrait ----
  const npc = { error: null, expectedSrc: PORTRAIT, withPortrait: null, withoutPortrait: null };
  try {
    if (typeof w.showSpeech !== 'function') throw new Error('window.showSpeech is missing');
    w.VEFR_SPRITES = Object.assign({}, w.VEFR_SPRITES, {
      [SPEAKER_WITH]: PORTRAIT,
    });
    w.showSpeech(SPEAKER_WITH, 'A line from a speaker with a picture.', '');
    npc.withPortrait = npcBoxReport(w);
    // The three-argument call every player path makes, with a speaker the pack
    // gave no picture: no portrait element at all, and none left over.
    w.showSpeech(SPEAKER_WITHOUT, 'A line from a speaker with no picture.', '');
    npc.withoutPortrait = npcBoxReport(w);
  } catch (e) {
    npc.error = String(e);
  }
  r.npcBox = npc;
  r.stateRules = stateReport(w, r.css);

  w.close();
  return r;
}
const out = {};
for (let i = 2; i + 1 < process.argv.length; i += 2) {
  out[process.argv[i]] = await report(process.argv[i + 1], process.argv[i] === 'contrast');
}
// Synchronous write: console.log is async on a pipe and process.exit can truncate it.
fs.writeSync(1, JSON.stringify(out) + '\n');
process.exit(0);
