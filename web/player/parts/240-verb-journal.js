
// Verbs record to the packaged player's own journal - the same
// no-failure contract as the server route they mirror
// (/api/combat/action): the action only lives in the log.
const COMBAT_KEY = 'vefr-packaged-combat';
function recordVerb(verb) {
  var log = store.getJSON(COMBAT_KEY, []);
  log.push({ verb: verb, phase: STATE.get().phase, at: new Date().toISOString() });
  store.setJSON(COMBAT_KEY, log);
  renderCombatLog(log);
}

// Arrivals journal - the packaged twin of /api/journal/move: one
// entry per change of named place under the hero, browser storage
// only, same no-failure contract as the verbs above.
const MOVES_KEY = 'vefr-packaged-moves';
var lastPlace = null;
function journalVisit(poi, x, y) {
  if (poi === lastPlace) return;
  lastPlace = poi;
  var log = store.getJSON(MOVES_KEY, []);
  log.push({ kind: 'move', poi: poi, x: x, y: y, phase: STATE.get().phase, at: new Date().toISOString() });
  store.setJSON(MOVES_KEY, log);
}

function renderCombatLog(log) {
  var el = document.getElementById('combat-log');
  if (!el) return;
  if (!log || !log.length) { el.textContent = ''; return; }
  var last = log[log.length - 1];
  el.textContent = 'last action: ' + last.verb + ' (' + last.phase + ')';
}

// The combat line: one plain sentence for the eye and the screen
// reader. A hit is said, never shown by colour alone. It rides the
// same aria-live idiom as #library-live.
function combatSay(msg) {
  var el = document.getElementById('combat-live');
  if (el) el.textContent = msg || '';
}

