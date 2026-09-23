/* Kitchen harness: EXECUTES the woven single-file player in a real
   DOM (jsdom, MIT, dev-only) and PLAYS one cooking morning end to
   end. The pleasant-loop protocol's mechanical half: it counts
   clicks, reads every feedback line, and returns the morning's
   journal and the printed page so pytest can assert the loop
   actually looped. The felt half lives in the playtest notes
   pasted per increment (VEFR-ACT1-SPEC-2026-09-22.md section 9).

   usage: node kitchen_harness.mjs <woven.html> */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const html = fs.readFileSync(process.argv[2], 'utf8');
const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  url: 'http://localhost/',
});
const { window } = dom;
const document = window.document;
const wait = (ms) => new Promise((r) => window.setTimeout(r, ms));

/* ---------- play the morning ---------- */
const log = [];
const line = () => document.getElementById('k-line').textContent;
let clicks = 0;
const click = (el) => { clicks += 1; el.click(); };
const pantryClick = (label) => {
  const b = [...document.querySelectorAll('#k-pantry button')]
    .find((x) => x.textContent === label);
  if (!b) throw new Error('no pantry button ' + label);
  click(b);
};

let clicksT1 = -1;
let clicksT2 = -1;
try {
  for (let i = 0; i < 60 && !document.getElementById('ts-enter'); i++) await wait(50);
  click(document.getElementById('ts-enter'));
  await wait(700);
  if (!document.getElementById('config').hidden) {
    click(document.getElementById('cfg-save'));
    await wait(100);
  }
  log.push(['open', document.getElementById('k-open').textContent]);
  log.push(['line0', line()]);
  log.push(['tickets', document.querySelectorAll('#k-tickets .card').length]);

  const before = clicks;
  pantryClick('fried egg'); pantryClick('red salsa');
  log.push(['wrap1', document.getElementById('k-wrap').textContent]);
  click(document.getElementById('k-serve'));
  log.push(['serve1', line()]);
  clicksT1 = clicks - before;

  const c2 = clicks;
  pantryClick('melted cheese');
  click(document.getElementById('k-serve'));
  log.push(['serve2-wrong', line()]);
  clicksT2 = clicks - c2;

  click(document.getElementById('k-aside'));
  log.push(['aside3', line()]);
  log.push(['headlines-visible', !document.getElementById('k-headlines').hidden]);
  const heads = [...document.querySelectorAll('#k-headline-list button')];
  log.push(['headline-count', heads.length]);
  click(heads[1]);
  const page = document.getElementById('k-page');
  log.push(['page-visible', !page.hidden]);
  log.push(['page-text', page.textContent.replace(/\s+/g, ' ').trim()]);
  const journal = JSON.parse(window.localStorage.getItem('vefr-packaged-kitchen') || '[]');
  log.push(['journal', journal.map((e) => e.kind)]);
  click(document.getElementById('k-sleep'));
  log.push(['after-sleep', line()]);
  log.push(['done-after-sleep', document.querySelectorAll('#k-tickets .card.done').length]);
} catch (e) {
  log.push(['HARNESS-ERROR', String((e && e.message) || e)]);
}

process.stdout.write(JSON.stringify({
  log,
  clicks: { total: clicks, t1: clicksT1, t2: clicksT2 },
  setIntervalInTemplate: html.includes('setInterval'),
}, null, 1));
window.close();
