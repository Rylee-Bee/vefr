// -- growth start --
// The growth engine: XP or practice counts in, the extra hp/atk out.
// Pure logic only - no DOM, no clock, no randomness, no storage - so
// tests/fixtures/growth_engine_harness.mjs can run this exact text in
// the real woven player. The baked pack's `growth` block is the
// config; `null`, or any other mode, means the hero never grows, and
// every call still answers with the same shape.
//
// State is { xp, counts } and is never mutated: anything malformed
// counts as zero or empty, and every result comes back as a fresh
// object. `level` is derived from the table on every call, never
// stored, so a re-woven game cannot leave a stale level behind.
window.VEFR_GROWTH_ENGINE = (function () {
  function isObj(v) {
    return typeof v === 'object' && v !== null && !Array.isArray(v);
  }

  function isWhole(v) {
    return typeof v === 'number' && isFinite(v) && v % 1 === 0;
  }

  function xpOf(state) {
    return isObj(state) && isWhole(state.xp) ? state.xp : 0;
  }

  // A copy of the state holding only real whole-number counts, so a
  // malformed entry falls away instead of surviving into a save.
  function copyState(state) {
    var counts = {};
    if (isObj(state) && isObj(state.counts)) {
      Object.keys(state.counts).forEach(function (kind) {
        if (isWhole(state.counts[kind])) counts[kind] = state.counts[kind];
      });
    }
    return { xp: xpOf(state), counts: counts };
  }

  // The XP table: a strictly rising list of whole numbers starting
  // at 0. A missing or malformed table is empty (level 1 forever).
  function xpTable(config) {
    if (!isObj(config) || config.mode !== 'levels') return [];
    var levels = isObj(config.levels) ? config.levels : {};
    return Array.isArray(levels.xp) ? levels.xp : [];
  }

  // One stat's gain from a gain block: only hp and atk, whole
  // numbers, anything else reads as no gain.
  function gainOf(block, stat) {
    if (!isObj(block) || !isWhole(block[stat]) || block[stat] < 0) return 0;
    return block[stat];
  }

  function levelsGain(config, stat) {
    var levels = isObj(config.levels) ? config.levels : {};
    return gainOf(isObj(levels.gain) ? levels.gain : {}, stat);
  }

  function levelFor(config, xp) {
    var table = xpTable(config);
    if (!table.length) return 1;
    var x = isWhole(xp) ? xp : 0;
    var n = 0;
    for (var i = 0; i < table.length; i++) {
      if (isWhole(table[i]) && table[i] <= x) n++;
    }
    if (n < 1) n = 1;
    if (n > table.length) n = table.length;
    return n;
  }

  // One practice stat's total after the cap: every `every` counts
  // earns `gain`, capped for good. A malformed spec grows nothing.
  function practiceTotal(spec, counts) {
    if (!isObj(spec)) return 0;
    var every = spec.every, gain = spec.gain, cap = spec.cap;
    if (!isWhole(every) || every < 1) return 0;
    if (!isWhole(gain) || gain < 0) return 0;
    var by = spec.by;
    var n = typeof by === 'string' && isObj(counts) && isWhole(counts[by])
      ? counts[by] : 0;
    var total = Math.floor(n / every) * gain;
    if (isWhole(cap) && total > cap) total = cap;
    return total;
  }

  // The extra stats the level or practice has earned. The level is
  // only a levels-mode idea; practice has none.
  function statsFor(config, state) {
    if (!isObj(config) || (config.mode !== 'levels' && config.mode !== 'practice')) {
      return { level: null, hp: 0, atk: 0 };
    }
    if (config.mode === 'levels') {
      var level = levelFor(config, xpOf(state));
      return {
        level: level,
        hp: (level - 1) * levelsGain(config, 'hp'),
        atk: (level - 1) * levelsGain(config, 'atk')
      };
    }
    var counts = isObj(state) && isObj(state.counts) ? state.counts : {};
    var practice = isObj(config.practice) ? config.practice : {};
    return {
      level: null,
      hp: practiceTotal(practice.hp, counts),
      atk: practiceTotal(practice.atk, counts)
    };
  }

  // award(config, state, xp): levels mode only. A positive whole
  // number of XP moves the hero; anything else leaves the hero where
  // it was. `grew` is the extra hp/atk the crossed levels bought.
  function award(config, state, xp) {
    var before = copyState(state);
    if (!isObj(config) || config.mode !== 'levels') {
      return { state: before, level: null, levelsGained: 0, grew: { hp: 0, atk: 0 } };
    }
    var from = levelFor(config, before.xp);
    if (!isWhole(xp) || xp <= 0) {
      return { state: before, level: from, levelsGained: 0, grew: { hp: 0, atk: 0 } };
    }
    var after = { xp: before.xp + xp, counts: before.counts };
    var to = levelFor(config, after.xp);
    var crossed = to - from;
    return {
      state: after,
      level: to,
      levelsGained: crossed,
      grew: {
        hp: crossed * levelsGain(config, 'hp'),
        atk: crossed * levelsGain(config, 'atk')
      }
    };
  }

  // The stats a practice kind feeds, in a fixed order so `grown` is
  // stable; a kind no stat names feeds none.
  function statsBy(practice, kind) {
    var stats = [];
    ['hp', 'atk'].forEach(function (stat) {
      var spec = isObj(practice[stat]) ? practice[stat] : null;
      if (spec && spec.by === kind) stats.push(stat);
    });
    return stats;
  }

  // bump(config, state, kind): practice mode only. Count one more
  // time; report each stat whose total just crossed a step, with
  // the gain it got (never more than the cap allows).
  function bump(config, state, kind) {
    var before = copyState(state);
    var unchanged = { state: before, grown: [] };
    if (!isObj(config) || config.mode !== 'practice' || typeof kind !== 'string') {
      return unchanged;
    }
    var practice = isObj(config.practice) ? config.practice : {};
    var stats = statsBy(practice, kind);
    if (!stats.length) return unchanged;
    var old = before.counts;
    var was = {};
    stats.forEach(function (stat) {
      was[stat] = practiceTotal(practice[stat], old);
    });
    var counts = {};
    Object.keys(old).forEach(function (k) { counts[k] = old[k]; });
    counts[kind] = (isWhole(counts[kind]) ? counts[kind] : 0) + 1;
    var after = { xp: before.xp, counts: counts };
    var grown = [];
    stats.forEach(function (stat) {
      var now = practiceTotal(practice[stat], counts);
      if (now > was[stat]) grown.push({ stat: stat, gain: now - was[stat] });
    });
    return { state: after, grown: grown };
  }

  return { levelFor: levelFor, statsFor: statsFor, award: award, bump: bump };
})();
// -- growth end --
