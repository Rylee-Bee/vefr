/* Equipment UI harness (A3): drives the REAL woven player in jsdom, opens
   the Bag panel, clicks through the DOM, and prints a JSON object pinning
   the slots, the live line, the stats, and the post-action storage.

   usage: node equip_ui_harness.mjs <woven.html> '[<spec json>]'
   spec is optional and defaults to []. It is an array of step objects:
     { "do": "openBag" }                      // opens the Bag panel
     { "do": "equip", "id": "<item id>" }     // clicks the Equip button
     { "do": "takeoff", "slot": "<slot>" }    // clicks Take off
     { "do": "setHp", "value": <n> }          // sets HERO_HP (for clamp tests)
     { "do": "reload" }                       // re-runs loadEquipped + re-render
     { "do": "snap", "tag": "label" }         // captures a named snapshot here

   The harness prints a JSON object with:
     final:    <snapshot>                 // state after the last step
     snaps:    {tag: snapshot, ...}       // every {do:"snap",tag} result
     errors:   [string]                   // any jsdom errors caught

   A snapshot:
     slotSentences:  [string]             // each slot row's visible text, in DOM order
     slotOrder:      [string]             // the data-slot values, in DOM order
     slotButtons:    {slot: string[]}     // the labels of buttons in each row
     bagNames:       [string]             // visible bag-row names, in DOM order
     bagButtons:     [{name, buttons}]    // per bag row, the buttons it carries
     live:           string               // the bag-live line after the last action
     heroMax:        number
     heroAtk:        number
     heroHp:         number
     storage:        {equip, bag}         // localStorage contents */
import fs from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';

const html = fs.readFileSync(process.argv[2], 'utf8');
const spec = JSON.parse(process.argv[3] || '[]');
const noop = () => {};
const errors = [];
const virtualConsole = new VirtualConsole();
virtualConsole.on('jsdomError', (e) => errors.push(String((e && e.message) || e)));

const dom = new JSDOM(html, {
  runScripts: 'dangerously', pretendToBeVisual: true, url: 'http://localhost/', virtualConsole,
  beforeParse: (window) => {
    window.HTMLCanvasElement.prototype.getContext = function () {
      return new Proxy({ canvas: this }, { get: (t, k) => (k in t ? t[k] : noop) });
    };
    window.matchMedia = () => ({ matches: false, addListener: noop, removeListener: noop });
    window.addEventListener('error', (e) => errors.push(String(e.message || e)));
    const store = (Array.isArray(spec) ? {} : (spec.store || {}));
    for (const [k, v] of Object.entries(store)) {
      if (typeof v === 'string') window.localStorage.setItem(k, v);
    }
  },
});
const w = dom.window;
const d = w.document;
const wait = (ms) => new Promise((r) => w.setTimeout(r, ms));

for (let i = 0; i < 60 && !d.getElementById('ts-enter'); i++) await wait(50);
d.getElementById('ts-enter').click();
for (let i = 0; i < 60 && !w.VEFR_COMBAT; i++) await wait(50);
await wait(300);

const steps = Array.isArray(spec) ? spec : (spec.steps || []);

const snap = () => {
  const rows = [...d.querySelectorAll('#equip-slots .equip-row')];
  const slotSentences = rows.map((r) => (r.querySelector('.equip-row-name') || {}).textContent || '');
  const slotOrder = rows.map((r) => r.dataset.slot || '');
  const slotButtons = {};
  const slotArt = {};
  rows.forEach((r) => {
    slotButtons[r.dataset.slot || ''] = [...r.querySelectorAll('button')].map((b) =>
      b.textContent.trim() || b.getAttribute('aria-label') || '');
    // What the slot draws: an inline SVG outline when empty, an <img>
    // when something with a sprite is worn, nothing otherwise. Reported
    // so a test can prove the outline is really drawn rather than
    // assuming it because no image was found.
    const art = r.querySelector('.equip-row-art');
    slotArt[r.dataset.slot || ''] = art
      ? (art.querySelector('img') ? 'img'
        : art.querySelector('svg') ? 'svg'
        : art.firstElementChild ? 'dot' : 'none')
      : 'no-art';
  });
  const bagRows = [...d.querySelectorAll('#bag-list .bag-row')];
  const bagNames = bagRows.map((r) => (r.querySelector('.bag-row-name') || {}).textContent || '');
  const bagButtons = bagRows.map((r) => ({
    name: (r.querySelector('.bag-row-name') || {}).textContent || '',
    buttons: [...r.querySelectorAll('button')].map((b) => b.textContent.trim()),
  }));
  const live = (d.getElementById('bag-live') || {}).textContent || '';
  const heroMax = typeof w.heroMax === 'function' ? w.heroMax() : null;
  const heroAtk = typeof w.heroAtk === 'function' ? w.heroAtk() : null;
  const heroHp = typeof w.HERO_HP !== 'undefined' ? w.HERO_HP : null;
  const worldName = (w.VEFR_WORLD && w.VEFR_WORLD.name) || 'world';
  let equip = null;
  let bag = null;
  try { equip = JSON.parse(w.localStorage.getItem('vefr-equipped-' + worldName) || 'null'); } catch (e) { /* ignore */ }
  try { bag = JSON.parse(w.localStorage.getItem('vefr-bag-' + worldName) || 'null'); } catch (e) { /* ignore */ }
  return { slotSentences, slotOrder, slotButtons, slotArt, bagNames, bagButtons, live,
           heroMax, heroAtk, heroHp, storage: { equip, bag } };
};

const openBag = () => {
  const btn = d.getElementById('bagbtn');
  if (btn) btn.click();
  const tab = d.querySelector('[data-panel="bag"]');
  if (tab) tab.click();
};

const doEquip = (id, opts) => {
  // `direct` bypasses the button lookup and calls window.equipItem
  // directly - used to test refusal lines for items with no button.
  if (opts && opts.direct) {
    if (typeof w.equipItem !== 'function') throw new Error('no equipItem');
    w.equipItem(id);
    return;
  }
  const btns = [...d.querySelectorAll('#bag-list .bag-row button[data-action="equip"]')];
  const b = btns.find((x) => x.dataset.item === id);
  if (!b) throw new Error('no Equip button for ' + id);
  b.click();
};

const doTakeoff = (slot) => {
  const b = d.querySelector('#equip-slots .equip-row[data-slot="' + slot + '"] button[data-action="takeoff"]');
  if (!b) throw new Error('no Take off button for slot ' + slot);
  b.click();
};

const doReload = () => {
  if (typeof w.loadEquipped === 'function') w.loadEquipped();
  if (typeof w.renderBagPanel === 'function') w.renderBagPanel();
  if (typeof w.renderBagStrip === 'function') w.renderBagStrip();
  if (typeof w.renderHp === 'function') w.renderHp();
};

const snaps = {};
let last = snap();
for (const step of steps) {
  if (!step || !step.do) continue;
  if (step.do === 'openBag') openBag();
  else if (step.do === 'equip') doEquip(step.id, { direct: !!step.direct });
  else if (step.do === 'takeoff') doTakeoff(step.slot);
  else if (step.do === 'setHp') w.HERO_HP = Number(step.value);
  else if (step.do === 'reload') doReload();
  else if (step.do === 'snap') {
    snaps[step.tag || String(Object.keys(snaps).length)] = snap();
    continue;
  }
  else throw new Error('unknown step: ' + step.do);
  last = snap();
}

console.log(JSON.stringify({ steps: steps.length, final: last, snaps, errors }));
w.close();
process.exit(0);
