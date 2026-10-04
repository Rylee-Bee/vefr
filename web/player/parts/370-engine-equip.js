// -- equip start --
// The equipment engine: what is worn (a {slot: itemId} map) and the
// pack's item catalog in, the hero's numbers and a moved state out.
// Pure logic only - no DOM, no clock, no randomness, no storage - so
// tests/fixtures/equip_engine_harness.mjs can run this exact text in
// the real woven player. Nothing is ever written into a caller's
// state: the caller's object is the one that gets saved, so every
// change returns a fresh copy. Malformed input reads as no gear or no
// change, never a crash.
window.VEFR_EQUIP_ENGINE = (function () {
  // The five slots Rylee fixed; anything else cannot be worn.
  var SLOTS = ['hand', 'body', 'head', 'feet', 'charm'];

  function isObj(v) {
    return typeof v === 'object' && v !== null && !Array.isArray(v);
  }

  function isWhole(v) {
    return typeof v === 'number' && isFinite(v) && v % 1 === 0;
  }

  // Any finite number is a health figure; junk counts as zero.
  function isNum(v) {
    return typeof v === 'number' && isFinite(v);
  }

  function isSlot(slot) {
    return SLOTS.indexOf(slot) >= 0;
  }

  // The state as a plain map, or an empty one when it is missing or
  // malformed, so every reader below starts from the same shape.
  function stateOrEmpty(state) {
    return isObj(state) ? state : {};
  }

  // A fresh shallow copy of a state map; the caller's object is never
  // touched, because the caller's object is the one that gets saved.
  function copyState(state) {
    var out = {};
    Object.keys(stateOrEmpty(state)).forEach(function (key) {
      out[key] = state[key];
    });
    return out;
  }

  // statsFor(base, items, equipped): the hero's {hp, atk} with every
  // worn item's mods added. A base, catalog or worn entry that is
  // malformed adds nothing; a stat the base does not carry starts at
  // 0. Both keys always come back.
  function statsFor(base, items, equipped) {
    // A base that is not an object is no hero at all: read it as no
    // gear, never as a bare pair of mods.
    if (!isObj(base)) return { hp: 0, atk: 0 };
    var hp = isWhole(base.hp) ? base.hp : 0;
    var atk = isWhole(base.atk) ? base.atk : 0;
    if (isObj(items) && isObj(equipped)) {
      Object.keys(equipped).forEach(function (slot) {
        var entry = items[equipped[slot]];
        if (typeof equipped[slot] !== 'string' || !isObj(entry) || !isObj(entry.mods)) {
          return;
        }
        if (isWhole(entry.mods.hp) && entry.mods.hp >= 0) hp += entry.mods.hp;
        if (isWhole(entry.mods.atk) && entry.mods.atk >= 0) atk += entry.mods.atk;
      });
    }
    return { hp: hp, atk: atk };
  }

  // equip(state, items, slot, itemId): wear an item, or swap out the
  // one already there. Refusals name why in a fixed order: an id the
  // catalog cannot reason about, then a slot that is not one of the
  // five, then an item with no slot, then a fit or duplicate problem.
  // Refusals hand back the very state they were given; success hands
  // back a copy, with the old wearer in `swapped`.
  function equip(state, items, slot, itemId) {
    var from = stateOrEmpty(state);
    var entry = isObj(items) ? items[itemId] : null;
    if (typeof itemId !== 'string' || !isObj(entry)) {
      return { state: from, swapped: null, reason: 'not-an-item' };
    }
    if (!isSlot(slot)) {
      return { state: from, swapped: null, reason: 'bad-slot' };
    }
    if (typeof entry.slot !== 'string') {
      return { state: from, swapped: null, reason: 'no-slot' };
    }
    // The item must fit the slot asked for; an id already worn in its
    // own slot is the same refusal, so a duplicate is impossible.
    if (entry.slot !== slot || from[slot] === itemId) {
      return { state: from, swapped: null, reason: 'wrong-slot' };
    }
    var next = copyState(from);
    var swapped = typeof from[slot] === 'string' ? from[slot] : null;
    next[slot] = itemId;
    return { state: next, swapped: swapped, reason: 'ok' };
  }

  // unequip(state, slot): take a slot off. A fresh state without that
  // slot, and the id that was there; an empty slot, a slot that is not
  // one of the five, or a missing state removes nothing.
  function unequip(state, slot) {
    var from = stateOrEmpty(state);
    var next = copyState(from);
    var removed = null;
    if (isSlot(slot)) {
      if (typeof from[slot] === 'string') removed = from[slot];
      delete next[slot];
    }
    return { state: next, removed: removed };
  }

  // clean(state, items): a fresh saved state holding only what still
  // fits the catalog - a real slot key, a string id, an item that
  // still exists and still names that same slot. Everything else is
  // dropped rather than crashed. A missing state or catalog is empty.
  function clean(state, items) {
    var out = {};
    if (!isObj(state) || !isObj(items)) return out;
    Object.keys(state).forEach(function (key) {
      var id = state[key];
      var entry = typeof id === 'string' ? items[id] : null;
      if (!isSlot(key) || typeof id !== 'string' || !isObj(entry)) return;
      if (typeof entry.slot === 'string' && entry.slot === key) out[key] = id;
    });
    return out;
  }

  // clampHealth(hp, maxHp): the smaller of the two, never below 1, so
  // taking off a thing that lowered max health can hurt but not kill.
  // Junk reads as 0; a bigger max never heals.
  function clampHealth(hp, maxHp) {
    var cur = isNum(hp) ? hp : 0;
    var max = isNum(maxHp) ? maxHp : 0;
    var out = cur < max ? cur : max;
    return out < 1 ? 1 : out;
  }

  return {
    statsFor: statsFor,
    equip: equip,
    unequip: unequip,
    clean: clean,
    clampHealth: clampHealth
  };
})();
// -- equip end --
