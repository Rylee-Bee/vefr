/* Desk harness: EXECUTES the woven single-file player in jsdom and
   plays one desk morning: draw a whisper from the woven pool, judge
   it correctly, print a headline, read back what the world knows.
   The pleasant-loop protocol's mechanical half for Act 2.

   usage: node desk_harness.mjs <woven.html> */
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

const log = [];
let clicks = 0;
const click = (el) => { clicks += 1; el.click(); };

try {
  for (let i = 0; i < 60 && !document.getElementById('ts-enter'); i++) await wait(50);
  click(document.getElementById('ts-enter'));
  await wait(700);
  if (!document.getElementById('config').hidden) {
    click(document.getElementById('cfg-save'));
    await wait(100);
  }
  log.push(['open', document.getElementById('d-open').textContent]);
  log.push(['headlines', document.querySelectorAll('#d-headlines button').length]);

  click(document.getElementById('d-whisper'));
  await wait(150);
  const card = window.VEFR_DESK_LAST;
  log.push(['card', card ? { speaker: card.speaker, is_true: card.is_true } : null]);
  const cards = document.querySelectorAll('#d-feed .card');
  log.push(['feed-cards', cards.length]);
  const row = cards[cards.length - 1].querySelectorAll('.verb-row button');
  // judge it the way it actually is: the correct verdict
  const verdictIdx = card.is_true ? 0 : 1;
  click(row[verdictIdx]);
  await wait(50);
  log.push(['verdict-line', cards[cards.length - 1].querySelector('.verdict').textContent]);
  log.push(['facts', [...document.querySelectorAll('#d-facts li')].map((li) => li.textContent)]);

  click(document.querySelectorAll('#d-headlines button')[0]);
  await wait(50);
  log.push(['printed', [...document.querySelectorAll('#d-printed li')].map((li) => li.textContent)]);
  const journal = JSON.parse(window.localStorage.getItem('vefr-packaged-desk') || '[]');
  log.push(['journal', journal.map((e) => e.kind)]);
  log.push(['buttons-disabled-after-verdict',
    [...cards[cards.length - 1].querySelectorAll('.verb-row button')]
      .every((b) => b.disabled)]);
} catch (e) {
  log.push(['HARNESS-ERROR', String((e && e.message) || e)]);
}

process.stdout.write(JSON.stringify({ log, clicks }, null, 1));
window.close();
