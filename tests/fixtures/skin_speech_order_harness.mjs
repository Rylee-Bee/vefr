/* Load-order harness: the speech box (100-speech-box.js) and the skin
   (540-the-skin.js) in ONE script tag each, so the two really do load one
   after the other, in both orders - the order the parts ship in and the
   reverse. Each page carries a skin that opts into the themed interface and
   one speaker with a picture, and the report is what the speech box drew.

   Prints one JSON object keyed by "shipped" and "reversed" (and "nope" for a
   page with no skin at all).

     node skin_speech_order_harness.mjs */
import fs from 'node:fs';
import path from 'node:path';
import { JSDOM } from 'jsdom';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const parts = path.join(here, '..', '..', 'web', 'player', 'parts');
const SPEECH = fs.readFileSync(path.join(parts, '100-speech-box.js'), 'utf8');
const SKIN = fs.readFileSync(path.join(parts, '540-the-skin.js'), 'utf8');

/* A speaker the pack gave a picture, and the skin's one themed part (a gold
   plate), which is all it takes to opt into the themed interface. */
const PORTRAIT = 'data:image/png;base64,'
  + 'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEUlEQVR4nGPYUhGFFTEMLQkAL4JhgQjp6wsAAAAASUVORK5CYII=';
const SKIN_JSON = { name: 'order-test', parts: { 'gold-plate': { file: 'gold.png' } } };

const SHELL = `<!doctype html><html><head><title>order</title></head><body>
<div id="npc-box" hidden><p id="npc-name"></p><p id="npc-line"></p>
<p id="npc-note" hidden></p><button id="npc-close">close</button></div>
<div class="hud"><span id="hud-hp">Health</span><span id="hud-level">Level</span>
<span id="hud-gold">0 gold</span><span id="bag-strip"></span><a id="menu-open">Menu</a></div>
`;

const noop = () => {};

function page(order, skin) {
  const scripts = (order === 'shipped' ? [SPEECH, SKIN] : [SKIN, SPEECH])
    .map((src) => `<script>${src}</script>`).join('\n');
  const dom = new JSDOM(`${SHELL}${scripts}</body></html>`, {
    runScripts: 'dangerously', url: 'http://localhost/',
    beforeParse: (window) => {
      // The woven player bakes the skin in before the parts that read it, so
      // the harness does the same.
      window.VEFR_SKIN = skin;
      window.VEFR_SPRITES = { marta: PORTRAIT };
      window.matchMedia = (q) => ({
        matches: false, addListener: noop, removeListener: noop,
        addEventListener: noop, removeEventListener: noop,
      });
    },
  });
  return dom.window;
}

function report(order, skin) {
  const w = page(order, skin);
  const box = w.document.getElementById('npc-box');
  const out = { order, error: null, children: [], images: [], srcs: [], speaker: null,
    expectedSrc: PORTRAIT };
  try {
    if (typeof w.showSpeech !== 'function') throw new Error('window.showSpeech is missing');
    w.showSpeech('marta', 'A line from a speaker with a picture.', '');
    const imgs = [...box.querySelectorAll('img')];
    out.children = [...box.children].map((c) => c.tagName.toLowerCase());
    out.images = imgs.length;
    out.srcs = imgs.map((i) => i.getAttribute('src'));
    out.speaker = w.document.getElementById('npc-name').textContent;
    out.icons = w.document.querySelectorAll('svg[data-icon]').length;
  } catch (e) {
    out.error = String(e);
  }
  w.close();
  return out;
}

const report_all = {
  shipped: report('shipped', SKIN_JSON),
  reversed: report('reversed', SKIN_JSON),
  nope: report('shipped', null),
};
fs.writeSync(1, JSON.stringify(report_all) + '\n');
process.exit(0);
