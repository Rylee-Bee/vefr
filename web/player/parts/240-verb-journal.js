
// Verbs record to the packaged player's own journal - the same
// no-failure contract as the server route they mirror
// (/api/combat/action): the action only lives in the log.
const COMBAT_KEY = 'vefr-packaged-combat';
function recordVerb(verb) {
  var log = [];
  try { log = JSON.parse(localStorage.getItem(COMBAT_KEY) || '[]'); } catch (e) {}
  log.push({ verb: verb, phase: STATE.get().phase, at: new Date().toISOString() });
  try { localStorage.setItem(COMBAT_KEY, JSON.stringify(log)); } catch (e) {}
  renderCombatLog(log);
}

// Arrivals journal - the packaged twin of /api/journal/move: one
// entry per change of named place under the hero, localStorage
// only, same no-failure contract as the verbs above.
const MOVES_KEY = 'vefr-packaged-moves';
var lastPlace = null;
function journalVisit(poi, x, y) {
  if (poi === lastPlace) return;
  lastPlace = poi;
  var log = [];
  try { log = JSON.parse(localStorage.getItem(MOVES_KEY) || '[]'); } catch (e) {}
  log.push({ kind: 'move', poi: poi, x: x, y: y, phase: STATE.get().phase, at: new Date().toISOString() });
  try { localStorage.setItem(MOVES_KEY, JSON.stringify(log)); } catch (e) {}
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

