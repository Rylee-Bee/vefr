// ---- the desk (desk ruleset v0) ----
// Rumors arrive carrying a hidden truth: baked in the pool offline,
// in the model's schema live, true-by-construction in the composer.
// The Desk judges them; correct verdicts and printed headlines become
// what the world knows. Fully client-side here - the packaged file
// has no engine server; the live app's /api/desk/* routes carry the
// same rules with the engine owning truth.
var DESK_KEY = 'vefr-packaged-desk';
function deskJournal() {
  try { return JSON.parse(localStorage.getItem(DESK_KEY) || '[]'); }
  catch (e) { return []; }
}
function deskLog(entry) {
  var j = deskJournal();
  entry.at = new Date().toISOString();
  j.push(entry);
  try { localStorage.setItem(DESK_KEY, JSON.stringify(j)); } catch (e) {}
  return entry;
}
function deskLive() {
  var c = loadConfig();
  return Boolean(c.llmUrl && c.llmModel);
}
function initDesk() {
  var act = (VEFR_WORLD.acts && VEFR_WORLD.acts[0]) || {};
  var D = act.desk || {};
  document.querySelectorAll(
    '#phase, #play > section.controls, #feed, #hud-hp, #encounter-prompt,'
    + ' #town-canvas, #near, #poi, #dpad, #npc-box, #verb-row, #combat-log,'
    + ' #combat-live, #play > h2, #play > p.status'
  ).forEach(function (el) { el.hidden = true; });
  document.getElementById('desk').hidden = false;
  document.getElementById('d-open').textContent =
    D.opening || 'the desk opens. what is true is what can be proven.';
  (D.headlines || []).forEach(function (h) {
    var b = document.createElement('button');
    b.type = 'button';
    b.textContent = h;
    b.addEventListener('click', function () { printHeadline(h); });
    document.getElementById('d-headlines').appendChild(b);
  });
  renderPrinted(); renderFacts();
  document.getElementById('d-whisper').addEventListener('click', function () {
    drawRumor();
  });
}
async function drawRumor() {
  var status = document.getElementById('d-status');
  var ph = STATE.get().phase || Object.keys(VEFR_WORLD.phases || {})[0] || '';
  var card = null;
  var how = '';
  if (deskLive()) {
    try {
      var tone = window.VEFR_WORLD.phases[ph] || '';
      var system = 'You are the whisper that flies out every day and comes home.\n'
        + 'Write ONE tavern rumor from the world described below, in-world,\n'
        + 'spoken by a named minor character. Follow the Contract strictly:\n'
        + 'never explain, never label, never use modern words. Show only.\n\n'
        + 'CURRENT PHASE: ' + tone + '\n\n'
        + (window.VEFR_LOGBOK || '').slice(0, 4000) + '\n\n'
        + 'Whispers already collected - match their cadence, do not repeat them:\n\n'
        + (window.VEFR_LEDGER || '');
      var schema = { type: 'object', properties: {
        speaker: { type: 'string' },
        whisper: { type: 'string' },
        is_true: { type: 'boolean' },
      }, required: ['speaker', 'whisper', 'is_true'], additionalProperties: false };
      var r = await llmPost({
        model: llmModel,
        messages: [
          { role: 'system', content: system },
          { role: 'user', content: 'Whisper one tavern rumor. Reply with only the JSON object.' },
        ],
        response_format: { type: 'json_schema', json_schema: { schema: schema, strict: true } },
        max_tokens: 200, temperature: 0.95, stream: false,
        chat_template_kwargs: { reasoning_effort: 'low' },
      });
      if (r.ok) {
        var j = await r.json();
        card = JSON.parse(j.choices[0].message.content);
        how = 'heard live.';
      }
    } catch (e) { card = null; }
  }
  if (!card) { card = poolDraw('rumor:' + ph); if (card) how = 'from the woven pool.'; }
  if (!card) { card = composeWhisper('rumor:' + ph); if (card) how = "woven anew from the pool's cloth."; }
  if (!card && typeof whisperFromFragments === 'function') {
    card = whisperFromFragments();
    if (card) how = "from the pack's own fragments.";
  }
  if (!card) { status.textContent = 'the well is dry; nothing came back.'; return; }
  if (card.is_true === undefined) card.is_true = true;
  window.VEFR_DESK_LAST = card;
  showDeskCard(card);
  status.textContent = how;
}
function showDeskCard(card) {
  var feed = document.getElementById('d-feed');
  var cardEl = document.createElement('article');
  cardEl.className = 'card';
  var who = document.createElement('p');
  who.className = 'speaker';
  who.textContent = card.speaker;
  var wh = document.createElement('p');
  wh.className = 'whisper';
  wh.textContent = '\u201c' + card.whisper + '\u201d';
  var row = document.createElement('div');
  row.className = 'verb-row';
  ['true', 'false'].forEach(function (v) {
    var b = document.createElement('button');
    b.type = 'button';
    b.textContent = v === 'true' ? 'trust it' : 'doubt it';
    b.dataset.verdict = v;
    b.addEventListener('click', function () {
      verifyRumor(card, v, cardEl, row);
    });
    row.appendChild(b);
  });
  cardEl.appendChild(who); cardEl.appendChild(wh); cardEl.appendChild(row);
  feed.appendChild(cardEl);
}
function verifyRumor(card, verdict, cardEl, row) {
  var correct = card.is_true === (verdict === 'true');
  deskLog({ kind: 'desk_verdict', whisper: card.whisper, verdict: verdict,
            correct: correct, truth: card.is_true });
  row.querySelectorAll('button').forEach(function (b) { b.disabled = true; });
  var v = document.createElement('p');
  v.className = 'verdict';
  v.textContent = (correct ? 'rightly judged. ' : 'wrongly judged. ')
    + (card.is_true ? 'confirmed: ' : 'debunked: ') + card.whisper;
  cardEl.appendChild(v);
  addFact(correct ? (card.is_true ? 'confirmed' : 'debunked') : 'missed',
          card.whisper);
}
function addFact(kind, text) {
  var ul = document.getElementById('d-facts');
  var li = document.createElement('li');
  li.className = kind;
  li.textContent = kind + ': ' + text;
  ul.appendChild(li);
}
function printHeadline(h) {
  deskLog({ kind: 'printed', headline: h });
  var ul = document.getElementById('d-printed');
  var li = document.createElement('li');
  li.textContent = h;
  ul.appendChild(li);
}
function renderPrinted() {
  var ul = document.getElementById('d-printed');
  ul.innerHTML = '';
  deskJournal().filter(function (e) { return e.kind === 'printed'; })
    .forEach(function (e) {
      var li = document.createElement('li');
      li.textContent = e.headline;
      ul.appendChild(li);
    });
}
function renderFacts() {
  var ul = document.getElementById('d-facts');
  ul.innerHTML = '';
  deskJournal().filter(function (e) {
    return e.kind === 'desk_verdict' && e.correct;
  }).forEach(function (e) {
    addFact(e.truth ? 'confirmed' : 'debunked', e.whisper);
  });
}

