// ---- durable rule saves (docs/adr/0009-rule-saves.md) ----
// A pack that declares saves.rules = 'persist' keeps the four
// mutable engine parts (flags, fired, beliefs, items) under
// `vefr-rulestate-<world>`, so a reload remembers. Reset mode (the
// default) never reads or writes that key. Derived values (where,
// meanings, the rules themselves) are never stored, and every storage
// access is wrapped: a hostile storage can never stop the game.
function rulesPersist() {
  var s = window.VEFR_WORLD && window.VEFR_WORLD.saves;
  return !!(s && s.rules === 'persist');
}
function rulesSaveKey() {
  return 'vefr-rulestate-' + ((window.VEFR_WORLD && window.VEFR_WORLD.name) || 'world');
}
// Local copies of the engine's own checks; the engine block is pure and
// closed, so the wiring keeps its own.
function rulesIsObj(v) {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}
function rulesOwn(obj, key) {
  return !!obj && Object.prototype.hasOwnProperty.call(obj, key);
}
// A rule id the current bake still knows.
function rulesHasRule(id) {
  var rules = window.VEFR_RULES;
  if (!Array.isArray(rules)) return false;
  for (var i = 0; i < rules.length; i++) {
    if (rules[i] && rules[i].id === id) return true;
  }
  return false;
}
// A belief holder the current bake still knows: a declared person, or
// any speaker the act groups by region.
function rulesKnowsHolder(who) {
  if (typeof who !== 'string' || !who) return false;
  if (rulesOwn(window.VEFR_PEOPLE, who)) return true;
  var groups = window.VEFR_SPEAKERS;
  if (!rulesIsObj(groups)) return false;
  var regions = Object.keys(groups);
  for (var i = 0; i < regions.length; i++) {
    if (rulesIsObj(groups[regions[i]]) && rulesOwn(groups[regions[i]], who)) {
      return true;
    }
  }
  return false;
}
// Read the stored save: null when absent, unparseable, or not an
// object. The version and shape are checked by the caller.
function rulesSaveRead() {
  var raw = store.get(rulesSaveKey());
  if (typeof raw !== 'string' || !raw) return null;
  var saved = null;
  try { saved = JSON.parse(raw); } catch (e) { return null; }
  if (!rulesIsObj(saved)) return null;
  return saved;
}
// A save this bake understands: version 1 and the four parts present
// as objects. Anything else is coerced to a fresh state.
function rulesSaveShapeOk(saved) {
  return rulesIsObj(saved.flags) && rulesIsObj(saved.fired)
    && rulesIsObj(saved.beliefs) && rulesIsObj(saved.items);
}
// Overlay the save onto the fresh state, dropping every entry the
// current bake does not know: removed flags, rules, people, claims and
// items, and malformed beliefs.
function rulesStateOverlay(state, saved) {
  Object.keys(saved.flags).forEach(function (k) {
    if (rulesOwn(window.VEFR_FLAGS, k) && typeof saved.flags[k] === 'boolean') {
      state.flags[k] = saved.flags[k];
    }
  });
  Object.keys(saved.fired).forEach(function (id) {
    if (saved.fired[id] === true && rulesHasRule(id)) state.fired[id] = true;
  });
  Object.keys(saved.beliefs).forEach(function (who) {
    if (!rulesKnowsHolder(who) || !rulesIsObj(saved.beliefs[who])) return;
    var held = saved.beliefs[who];
    if (!rulesIsObj(state.beliefs[who])) state.beliefs[who] = {};
    Object.keys(held).forEach(function (claim) {
      var b = held[claim];
      if (!rulesOwn(window.VEFR_CLAIMS, claim)) return;
      if (!rulesIsObj(b) || typeof b.value !== 'boolean'
          || typeof b.source !== 'string') return;
      state.beliefs[who][claim] = { value: b.value, source: b.source };
    });
  });
  Object.keys(saved.items).forEach(function (id) {
    if (saved.items[id] === true && rulesOwn(window.VEFR_ITEMS, id)) {
      state.items[id] = true;
    }
  });
}
// persist + legacy "from-log": no save yet, so mark as fired exactly
// the rules the WHY log proves fired. Unknown ids (a rule the pack
// dropped) are ignored.
function rulesLegacyFromLog() {
  var s = window.VEFR_WORLD && window.VEFR_WORLD.saves;
  return !!(s && s.legacy === 'from-log');
}
function rulesStateSeedFromLog(state) {
  rulesWhyLoad();
  for (var i = 0; i < window.VEFR_WHY.length; i++) {
    var e = window.VEFR_WHY[i];
    if (e && typeof e.id === 'string' && rulesHasRule(e.id)) {
      state.fired[e.id] = true;
    }
  }
}
// Whether a v===1 save was read this session. `starts` is skipped when
// one was; `blocked` marks a newer (v>1) save that must not be
// overwritten. Module-level because both live for the whole session.
var RULES_SAVE_LOADED = false;
var RULES_SAVE_BLOCKED = false;
// Load on the first state build, persist mode only. Never throws: a
// v>1 save is left exactly as it is, anything unreadable gives the
// fresh state.
function rulesStateLoad(state) {
  if (!rulesPersist()) return;
  // Load the log too: the legacy path reads it, and the menu reads it
  // even when nothing fires this session.
  rulesWhyLoad();
  var saved = rulesSaveRead();
  if (saved && saved.v === 1 && rulesSaveShapeOk(saved)) {
    RULES_SAVE_LOADED = true;
    rulesStateOverlay(state, saved);
    return;
  }
  if (saved && typeof saved.v === 'number' && saved.v > 1) {
    RULES_SAVE_BLOCKED = true;   // a newer save must not be destroyed
    return;
  }
  if (rulesLegacyFromLog()) rulesStateSeedFromLog(state);
}
// Write the four mutable parts after every event. Wrapped and silent:
// a failed write keeps play going in memory.
function saveRulesState() {
  if (!rulesPersist() || RULES_SAVE_BLOCKED || !RULES_STATE) return;
  var payload = {
    v: 1,
    flags: RULES_STATE.flags,
    fired: RULES_STATE.fired,
    beliefs: RULES_STATE.beliefs,
    items: RULES_STATE.items
  };
  store.setJSON(rulesSaveKey(), payload);
}
// `starts` fires once per save: skipped only when a valid save loaded
// this session. A fresh (or cleared) start and reset mode fire it.
// Build first, so the load has set the flag before the decision.
function rulesStartsNow() {
  if (!rulesPersist()) return true;
  rulesStateNow();
  return !RULES_SAVE_LOADED;
}

