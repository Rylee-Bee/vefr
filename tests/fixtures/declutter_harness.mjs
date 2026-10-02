/* Declutter harness: the REAL woven player in jsdom. argv[2] = a woven file with two phases.
   Prints what the action bar, the top bar and the Display panel contain. */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const noop = () => {};
const w = new JSDOM(fs.readFileSync(process.argv[2], 'utf8'), {
  runScripts: 'dangerously', pretendToBeVisual: true, url: 'http://localhost/',
  beforeParse: (win) => {
    win.HTMLCanvasElement.prototype.getContext = function () {
      return new Proxy({ canvas: this }, { get: (t, k) => (k in t ? t[k] : noop) });
    };
    win.matchMedia = () => ({ matches: false, addListener: noop, removeListener: noop });
  },
}).window;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
for (let i = 0; i < 60 && !w.document.getElementById('ts-enter'); i++) await wait(50);
w.document.getElementById('ts-enter').click();
await wait(300);
const d = w.document, q = (s) => d.querySelector(s), all = (s) => [...d.querySelectorAll(s)];
const tool = (id) => {
  const b = d.getElementById(id);
  return b && {
    isTool: b.classList.contains('gbtn--tool'), gold: b.classList.contains('gbtn--gold'),
    svgHidden: !!b.querySelector('svg[aria-hidden="true"]'),
    word: (b.querySelector('.sr-only') || {}).textContent, title: b.title,
    key: (b.querySelector('kbd') || {}).textContent,
  };
};
const rail = d.getElementById('phase');
const phases = Object.keys(w.VEFR_WORLD.phases);
const first = rail && rail.querySelector('button');
const second = rail && rail.querySelectorAll('button')[1];
if (second) second.click();
const out = {
  railInDisplayPanel: !!q('[data-panel-body="display"] #phase'),
  railInTopBar: !!q('.hud--tr #phase'),
  topBarChildren: [...q('.hud--tr').children].map((e) => e.id),
  railButtons: rail ? rail.querySelectorAll('button').length : -1,
  phaseCount: phases.length,
  pressedAfterClick: second ? second.getAttribute('aria-pressed') : null,
  firstUnpressed: first ? first.getAttribute('aria-pressed') : null,
  mainButtons: all('.acts .gbtn--main').map((e) => e.id),
  tools: { talk: tool('talk'), whisper: tool('whisper'), bagbtn: tool('bagbtn'), explore: tool('explore') },
  explorePressedAttr: d.getElementById('explore').getAttribute('aria-pressed'),
};
fs.writeSync(1, JSON.stringify(out) + '\n');
w.close();
process.exit(0);
