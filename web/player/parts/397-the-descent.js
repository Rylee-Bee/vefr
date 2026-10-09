// ---- the descent: play-time floors (slice E1) ----
// The runtime half of `vefr.delve`'s descent, and the only place the
// player keeps a floor. A floor that was never baked at weave time is
// drawn here, at the stair, from the run seed - and what the save keeps
// about it is a handful of deltas (who was killed, what was dropped
// where, which secrets, and the explored bitset), never the grid.
//
// Four things live here, and they are the four questions a floor asks:
//   1. the pure twin: `locate`, the floor key, the five streams, the
//      plan, the layout, the mobs - all of it identical to Python's,
//      because the parity harness demands the same answers;
//   2. the virtual region: `ensureRegion` grows `window.VEFR_REGIONS`,
//      `window.VEFR_ENEMIES` and the transitions the moment a stair is
//      used, so a floor nobody baked loads and plays;
//   3. the save: one document per world through `store()`, with the
//      identity triple of every visited floor, the 40-floor cap and the
//      byte budgets of PLAN §3;
//   4. the two cards: the New-descent control, and the one-time
//      `gen_version` card a Release 1 save is offered.
//
// Nothing here names a game, reads a clock, or touches storage directly:
// the only randomness is `VEFR_DELVE.prng`, and every draw is
// `Math.floor(rng() * n)` off a stream named `v3|<floor key>|<stream>`.
window.VEFR_DESCENT = (function () {

  // The same numbers as `src/vefr/delve.py`; the parity harness is what
  // proves the two agree.
  var GEN_VERSION = 3;
  var STREAM_VERSION = 'v3';
  var MOB_SPACING = 7;
  var FLOOR_CAP = 40;
  var FLOOR_BYTES = 1500;
  var SAVE_BYTES = 250000;
  var DEFAULT_SIZE_W = [48, 64];
  var DEFAULT_SIZE_H = [32, 44];
  var DEFAULT_ROOMS = [12, 18];
  var DEFAULT_FOG_RADIUS = 5;
  var DEFAULT_FAMILY = 'a stranger in the dark';
  var DOC_VERSION = 1;
  var LEGEND_FALLBACK = {
    '#': { base: ['#20242b'], solid: true, tile: 'dungeon-wall' },
    '.': { base: ['#1a1d22'], tile: 'dungeon-floor' },
    u: { base: ['#2b2f38'], tile: 'dungeon-stairs-up' },
    d: { base: ['#2b2f38'], tile: 'dungeon-stairs-down' }
  };

  // ---- the pack's block ------------------------------------------------
  // Read at call time, never captured: a woven file bakes the block in
  // before the first step, and a harness may plant its own.
  function def() { return window.VEFR_DESCENT_DEF || null; }

  function on() {
    var d = def();
    return !!(d && typeof d.run_seed === 'string' && d.run_seed &&
              Array.isArray(d.sections) && d.sections.length &&
              d.sections.every(function (s) { return s && typeof s.id === 'string'; }));
  }

  function sections() {
    var d = def();
    return on() ? d.sections : [];
  }

  function worldName() {
    return (window.VEFR_WORLD && window.VEFR_WORLD.name) || 'world';
  }

  function baseSeed() {
    var d = def();
    return (d && d.run_seed) || '';
  }

  // ---- the streams, in Python's order ---------------------------------
  function floorName(sectionId, cycle, k) {
    return sectionId + '-' + cycle + '-' + k;
  }

  function floorKey(seed, sectionId, cycle, k) {
    return seed + '/' + sectionId + '/' + cycle + '/' + k;
  }

  function streamSeed(key, stream) { return STREAM_VERSION + '|' + key + '|' + stream; }
  function lootSeed(key, mobId) { return streamSeed(key, 'loot|' + mobId); }
  function chestSeed(key, chestId) { return streamSeed(key, 'chest|' + chestId); }
  function runSeed(base, run) {
    run = (typeof run === 'number' && run > 0) ? Math.floor(run) : 0;
    return run === 0 ? base : base + '/run-' + run;
  }

  function randRange(rng, lo, hi) { return lo + Math.floor(rng() * (hi - lo + 1)); }

  function isWhole(n) { return typeof n === 'number' && isFinite(n) && Math.floor(n) === n; }

  function rangeOf(holder, key, fallback) {
    var value = holder ? holder[key] : null;
    if (Array.isArray(value) && value.length === 2 &&
        isWhole(value[0]) && isWhole(value[1]) && value[0] <= value[1]) {
      return [value[0], value[1]];
    }
    return fallback;
  }

  function sizeRange(section, axis, fallback) {
    var size = section ? section.size : null;
    var value = (size && typeof size === 'object') ? size[axis] : null;
    if (Array.isArray(value) && value.length === 2 &&
        isWhole(value[0]) && isWhole(value[1]) &&
        value[0] <= value[1] && value[0] >= 5) {
      return [value[0], value[1]];
    }
    return fallback;
  }

  function floorsOf(section) {
    var value = section ? section.floors : null;
    if (isWhole(value) && value >= 1) return value;
    return null;
  }

  // ---- the families (the twin of `delve._families_of`) -----------------

  function has(object, key) {
    return Object.prototype.hasOwnProperty.call(object, key);
  }

  // One Blueprint family's base record by id, or null: the twin of
  // `vefr.blueprint.resolve_family`. The `extends` chain is walked to its
  // root, then each family's own `defaults` are merged over them, a later
  // value replacing an earlier one whole. A family the Blueprint does not
  // have, one whose parent is missing and one caught in a cycle all come
  // back with no base - the validator says those out loud (`vefr check`,
  // `/families/0/family`), and a floor lays itself rather than refusing
  // to be walked.
  function familyBase(id) {
    var source = def();
    var families = (source && source.blueprint &&
                    typeof source.blueprint.families === 'object' &&
                    source.blueprint.families)
      ? source.blueprint.families : null;
    if (!families || typeof id !== 'string' || !has(families, id)) return null;
    var chain = [], seen = {}, current = id;
    while (true) {
      if (has(seen, current)) return null;          // a cycle has no root
      seen[current] = true;
      chain.push(current);
      var record = families[current];
      var parent = (record && typeof record === 'object') ? record.extends : null;
      if (parent === undefined || parent === null) break;
      if (!has(families, parent)) return null;     // an unknown parent
      current = parent;
    }
    var base = null;
    for (var i = chain.length - 1; i >= 0; i--) {   // the root first
      var defaults = families[chain[i]] ? families[chain[i]].defaults : null;
      if (!defaults || typeof defaults !== 'object') continue;
      if (!base) base = {};
      for (var key in defaults) {
        if (has(defaults, key)) base[key] = defaults[key];
      }
    }
    return base;
  }

  // A family's health as a range, for the one draw that spends it: a
  // Blueprint base is one whole number - `hp: 4` is four hit points,
  // every floor - and a pair is a Section's or a test's own range.
  function hpRange(family) {
    var value = family ? family.hp : null;
    if (isWhole(value)) return [value, value];
    return rangeOf(family, 'hp', [1, 1]);
  }

  // ---- where a depth leads (the twin of `locate`) ----------------------
  function locate(depth) {
    var list = sections();
    var counts = list.map(floorsOf);
    var total = counts.reduce(function (a, b) { return a + (b || 0); }, 0);
    if (!isWhole(depth) || depth < 1 || !total) return null;
    var cycle = Math.floor((depth - 1) / total);
    var within = (depth - 1) % total;
    for (var i = 0; i < list.length; i++) {
      var count = counts[i] || 0;
      if (within < count) {
        return { cycle: cycle, section: list[i].id, sectionIndex: i,
                 k: within + 1, depth: depth };
      }
      within -= count;
    }
    return null;
  }

  // The name back into the depth it plays at, so a region that is only
  // known by its name still knows which floor it is.
  function depthOfName(name) {
    var at = parseName(name);
    if (!at) return 0;
    var list = sections();
    var total = 0;
    for (var i = 0; i < list.length; i++) total += floorsOf(list[i]) || 0;
    var before = 0;
    for (var j = 0; j < at.sectionIndex; j++) before += floorsOf(list[j]) || 0;
    return at.cycle * total + before + at.k;
  }

  // "<section id>-<cycle>-<k>": the id may itself carry dashes, so the
  // two numbers are read off the end and the id is the rest.
  function parseName(name) {
    if (!on()) return null;
    var m = /^(.*)-(\d+)-(\d+)$/.exec(String(name === undefined ? '' : name));
    if (!m) return null;
    var list = sections();
    for (var i = 0; i < list.length; i++) {
      if (list[i].id === m[1]) {
        return { section: list[i], sectionIndex: i,
                 cycle: Number(m[2]), k: Number(m[3]) };
      }
    }
    return null;
  }

  function isGenerated(name) { return parseName(name) !== null; }

  // ---- a floor, drawn (the twin of `floor_plan`) ----------------------
  function seedFor(run) { return runSeed(baseSeed(), run); }

  function planFloor(key, section, k) {
    var wr = sizeRange(section, 'w', DEFAULT_SIZE_W);
    var hr = sizeRange(section, 'h', DEFAULT_SIZE_H);
    var rr = rangeOf(section, 'rooms', DEFAULT_ROOMS);
    var rng = window.VEFR_DELVE.prng(streamSeed(key, 'plan'));
    var w = randRange(rng, wr[0], wr[1]);
    var h = randRange(rng, hr[0], hr[1]);
    var rooms = randRange(rng, Math.max(1, rr[0]), Math.max(1, rr[1]));
    var kind = 'n';
    var pattern = section ? section.pattern : null;
    if (Array.isArray(pattern) && k >= 1 && k <= pattern.length &&
        typeof pattern[k - 1] === 'string') {
      kind = pattern[k - 1];
    }
    return { kind: kind, w: w, h: h, rooms: rooms };
  }

  function sectionHash(section) { return hash12(canonical(section)); }

  // How many randoms this floor's area asks for. The budget is not a
  // draw: it is the same area budget the v3 pop stage clamps (PLAN.md
  // section 2, step 4 - "randoms by area budget"), read off the floor's
  // own walkable tiles. One tile TILES_PER_MOB times is one monster slot,
  // clamped to the same two numbers, so a descent Section carries no
  // `mobs` key at all - the count is generator policy, not pack data.
  // The three numbers are `VEFR_DELVE.v3Constants`, part 396's own.
  function mobBudget(rows) {
    var C = (window.VEFR_DELVE && window.VEFR_DELVE.v3Constants) || {};
    var per = C.TILES_PER_MOB, lo = C.MOBS_MIN, hi = C.MOBS_MAX;
    var walkable = 0;
    for (var y = 0; y < rows.length; y++) {
      var row = rows[y], at = row.indexOf('.');
      while (at !== -1) { walkable++; at = row.indexOf('.', at + 1); }
    }
    return Math.min(hi, Math.max(lo, Math.floor(walkable / per)));
  }

  // A Section names a Blueprint family by id and carries no record of
  // its own (ADR 0014), so the base - hp, atk, sight, drops, name - is
  // resolved out of the pack's Blueprint, which the bake writes into the
  // descent block beside the Sections, and the Section's own keys win
  // over it. That is `vefr.sections.families`, the merge the validator
  // and the generator already share, so a monster here cannot come out
  // with a family the check would not have accepted. An entry with no
  // base still draws; its stats come back at this function's own floor
  // of 1, which is the answer for a base that says nothing.
  function familiesOf(section) {
    var listed = (section && Array.isArray(section.families))
      ? section.families : [];
    var out = [];
    for (var i = 0; i < listed.length; i++) {
      var entry = listed[i];
      if (!entry || typeof entry !== 'object' || Array.isArray(entry)) continue;
      var name = entry.family;
      var base = (typeof name === 'string' && name) ? familyBase(name) : null;
      var merged = {};
      if (base) {
        for (var b in base) if (has(base, b)) merged[b] = base[b];
      }
      for (var e in entry) if (has(entry, e)) merged[e] = entry[e];
      out.push(merged);
    }
    return out.filter(function (f) {
      return typeof f.family === 'string' && f.family; })
      .sort(function (a, b) {
        return a.family < b.family ? -1 : (a.family > b.family ? 1 : 0); });
  }

  function mobsAt(key, section, rows, up, down) {
    var rng = window.VEFR_DELVE.prng(streamSeed(key, 'pop'));
    var count = mobBudget(rows);
    var families = familiesOf(section);
    var pool = [];
    for (var f = 0; f < families.length; f++) {
      var weight = families[f].weight;
      weight = (isWhole(weight) && weight > 0 && weight <= 99) ? weight : 1;
      for (var w = 0; w < weight; w++) pool.push(families[f]);
    }
    var candidates = [];
    for (var y = 0; y < rows.length; y++) {
      for (var x = 0; x < rows[y].length; x++) {
        if (rows[y][x] !== '.') continue;
        if (Math.abs(x - up[0]) + Math.abs(y - up[1]) < MOB_SPACING) continue;
        if (Math.abs(x - down[0]) + Math.abs(y - down[1]) < MOB_SPACING) continue;
        candidates.push([x, y]);
      }
    }
    var mobs = [];
    for (var i = 0; i < count; i++) {
      if (!candidates.length || !pool.length) break;
      var pick = Math.floor(rng() * candidates.length);
      var at = candidates.splice(pick, 1)[0];
      var family = pool[Math.floor(rng() * pool.length)];
      var hr = hpRange(family);
      var hp = randRange(rng, Math.max(1, hr[0]), Math.max(1, hr[1]));
      var atk = isWhole(family.atk) ? family.atk : 1;
      var sight = isWhole(family.sight) ? family.sight : 6;
      mobs.push({
        id: 'm' + i, family: family.family,
        name: (typeof family.name === 'string' && family.name) ? family.name : DEFAULT_FAMILY,
        at: [at[0], at[1]], hp: Math.max(1, hp), atk: Math.max(1, atk),
        sight: Math.max(1, sight), drops: mobDrops(key, 'm' + i, family.drops)
      });
    }
    return mobs;
  }

  // A monster's own loot stream: the order monsters are killed in cannot
  // change what they drop.
  function mobDrops(key, mobId, table) {
    var ids = Array.isArray(table)
      ? table.filter(function (i) { return typeof i === 'string' && i; }) : [];
    if (!ids.length) return [];
    var rng = window.VEFR_DELVE.prng(lootSeed(key, mobId));
    return [ids[Math.floor(rng() * ids.length)]];
  }

  function floorPlan(depth, run) {
    var at = locate(depth);
    if (!at) return null;
    var section = sections()[at.sectionIndex];
    var run0 = isWhole(run) ? run : currentRun();
    var key = floorKey(seedFor(run0), at.section, at.cycle, at.k);
    var plan = planFloor(key, section, at.k);
    var rows = window.VEFR_DELVE.generateFloorV2(streamSeed(key, 'layout'),
                                                  plan.w, plan.h, plan.rooms);
    var up = null, down = null;
    for (var y = 0; y < rows.length && (!up || !down); y++) {
      for (var x = 0; x < rows[y].length; x++) {
        if (rows[y][x] === 'u' && !up) up = [x, y];
        else if (rows[y][x] === 'd' && !down) down = [x, y];
      }
    }
    if (!up || !down) return null;
    var fog = (section && typeof section.fog === 'object') ? section.fog : null;
    var radius = (fog && isWhole(fog.radius)) ? fog.radius : DEFAULT_FOG_RADIUS;
    return {
      name: floorName(at.section, at.cycle, at.k), key: key,
      identity: { gen: GEN_VERSION, hash: sectionHash(section), key: key },
      depth: depth, cycle: at.cycle, section: at.section, k: at.k,
      kind: plan.kind, w: plan.w, h: plan.h, rooms: plan.rooms, rows: rows,
      anchors: { up: up, down: down },
      mobs: mobsAt(key, section, rows, up, down),
      fog: { radius: Math.max(1, radius) }
    };
  }

  // ---- canonical JSON and a short digest ------------------------------
  // The identity of a floor includes a hash of its Section, so the two
  // languages must agree on the bytes they hash: keys sorted, no spaces,
  // and numbers written the way both languages write a whole number.
  function canonical(value) {
    if (value === null || value === undefined) return 'null';
    if (typeof value === 'boolean') return value ? 'true' : 'false';
    if (typeof value === 'number') return isFinite(value) ? String(value) : 'null';
    if (typeof value === 'string') return JSON.stringify(value);
    if (Array.isArray(value)) {
      var parts = [];
      for (var i = 0; i < value.length; i++) parts.push(canonical(value[i]));
      return '[' + parts.join(',') + ']';
    }
    if (typeof value === 'object') {
      var keys = Object.keys(value).sort();
      var out = [];
      for (var k = 0; k < keys.length; k++) {
        if (value[keys[k]] === undefined) continue;
        out.push(JSON.stringify(keys[k]) + ':' + canonical(value[keys[k]]));
      }
      return '{' + out.join(',') + '}';
    }
    return 'null';
  }

  function utf8Bytes(text) {
    var out = [], i, c;
    for (i = 0; i < text.length; i++) {
      c = text.charCodeAt(i);
      if (c < 0x80) { out.push(c); continue; }
      if (c < 0x800) {
        out.push(0xc0 | (c >> 6), 0x80 | (c & 63));
        continue;
      }
      if (c >= 0xd800 && c <= 0xdbff && i + 1 < text.length) {
        var next = text.charCodeAt(i + 1);
        if (next >= 0xdc00 && next <= 0xdfff) {
          i++;
          var cp = 0x10000 + ((c - 0xd800) << 10) + (next - 0xdc00);
          out.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 63),
                   0x80 | ((cp >> 6) & 63), 0x80 | (cp & 63));
          continue;
        }
      }
      out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
    }
    return out;
  }

  function hash12(text) {
    var bytes = utf8Bytes(text);
    var h1 = 2166136261, h2 = 3335557771;
    for (var i = 0; i < bytes.length; i++) {
      h1 = Math.imul(h1 ^ bytes[i], 16777619) >>> 0;
      h2 = Math.imul(h2 ^ ((bytes[i] + i) & 255), 2246822519) >>> 0;
    }
    return hex8(h1) + hex8(h2).slice(0, 4);
  }

  function hex8(n) {
    var s = (n >>> 0).toString(16);
    while (s.length < 8) s = '0' + s;
    return s;
  }

  // ---- the save: one document, deltas only ----------------------------
  function docKey() { return 'vefr-descent-' + worldName(); }

  function freshDoc() {
    return { v: DOC_VERSION, gen: GEN_VERSION, run: 0, seed: baseSeed(),
             order: [], floors: {}, flags: {}, card: 0 };
  }

  function isObj(v) {
    return typeof v === 'object' && v !== null && !Array.isArray(v);
  }

  function loadDoc() {
    var saved = store.getJSON(docKey(), null);
    if (!isObj(saved) || saved.v !== DOC_VERSION) return freshDoc();
    if (!isObj(saved.floors)) saved.floors = {};
    if (!isObj(saved.flags)) saved.flags = {};
    if (!Array.isArray(saved.order)) saved.order = Object.keys(saved.floors);
    if (!isWhole(saved.run)) saved.run = 0;
    return saved;
  }

  function currentRun() {
    var run = loadDoc().run;
    return isWhole(run) && run >= 0 ? run : 0;
  }

  // PLAN §3's budgets are in BYTES, and the browser stores UTF-8, so
  // they are counted in UTF-8 bytes. `String.length` counts UTF-16 code
  // units, and one such unit is three bytes for most characters outside
  // ASCII - so a floor whose Section id, flags or deltas carry an accent,
  // an emoji or a skull weighed a third of what it weighs on disk and
  // sailed under a budget it did not fit.
  function bytesOf(value) { return utf8Length(JSON.stringify(value)); }

  function utf8Length(text) { return new TextEncoder().encode(text).length; }

  function floorBytes(record) { return bytesOf(record); }

  // PLAN §3's other half: a visited floor may not carry more than
  // FLOOR_BYTES, and nothing else in the save enforces that - forty floors
  // at 1.5 KB is 60 KB, comfortably inside SAVE_BYTES, so a save of
  // oversized records sails under the whole-save trim and the per-floor
  // number is a claim rather than a contract.
  //
  // What a floor gives up, in this order:
  //   1. the explored bitset. It is where the hero has walked, not what has
  //      been done, and on a big floor it is the whole weight of the record;
  //   2. the longest list of deltas, from its end, until it fits. Only a
  //      pack whose floors carry more deltas than the budget allows gets
  //      here, and it keeps as many as it can rather than being refused.
  // The identity triple is never given up: a floor that is over budget is
  // still the right floor, and its kills and chests stay true to it.
  var FLOOR_LISTS = ['kills', 'chests', 'drops', 'secrets'];

  function fitFloor(record) {
    var out = copyRecord(record);
    if (floorBytes(out) <= FLOOR_BYTES) return out;
    out.fog = '';
    while (floorBytes(out) > FLOOR_BYTES) {
      var longest = '';
      for (var i = 0; i < FLOOR_LISTS.length; i++) {
        if (!longest || out[FLOOR_LISTS[i]].length > out[longest].length) {
          longest = FLOOR_LISTS[i];
        }
      }
      if (!out[longest].length) break;
      out[longest].pop();
    }
    return out;
  }

  function fitFloors(doc) {
    var names = Object.keys(isObj(doc.floors) ? doc.floors : {});
    for (var i = 0; i < names.length; i++) {
      if (isObj(doc.floors[names[i]])) doc.floors[names[i]] = fitFloor(doc.floors[names[i]]);
    }
    return doc;
  }

  // The cap of PLAN §2: at most `FLOOR_CAP` floors, oldest first; and if
  // the save is still over its byte budget, the oldest bitsets go before
  // anything else, because a bitset is the whole weight of a floor.
  //
  // This is the whole-save half of the budget and nothing else: it is the
  // frozen order of sacrifice, and it deliberately does not shrink a
  // record to FLOOR_BYTES. The per-floor half is `fitFloors`, applied by
  // `saveDoc` to what is about to be written, so a document that arrives
  // oversized still reports exactly what the order of sacrifice leaves.
  function trimDoc(doc) {
    return fitDoc(doc).doc;
  }

  // The whole order a save gives things up in: the oldest bitsets first,
  // then the oldest floors whole, and nothing after that - the story
  // flags are the world's own memory and are never given up. So `fits`
  // says whether what is left is inside the budget or whether the save
  // can only be refused.
  function fitDoc(doc) {
    var names = Array.isArray(doc.order) ? doc.order.slice() : [];
    var known = Object.keys(isObj(doc.floors) ? doc.floors : {});
    for (var i = 0; i < known.length; i++) {
      if (names.indexOf(known[i]) === -1) names.push(known[i]);
    }
    while (names.length > FLOOR_CAP) names.shift();
    var out = { v: doc.v, gen: doc.gen, run: doc.run, seed: doc.seed,
                card: doc.card, flags: isObj(doc.flags) ? doc.flags : {},
                floors: {}, order: [] };
    for (var n = 0; n < names.length; n++) {
      var record = doc.floors[names[n]];
      if (!isObj(record)) continue;
      out.floors[names[n]] = copyRecord(record);
      out.order.push(names[n]);
    }
    var i2 = 0;
    while (bytesOf(out) > SAVE_BYTES && i2 < out.order.length) {
      var oldest = out.floors[out.order[i2]];
      if (oldest && oldest.fog) oldest.fog = '';
      i2++;
    }
    while (bytesOf(out) > SAVE_BYTES && out.order.length) {
      delete out.floors[out.order.shift()];
    }
    return { doc: out, fits: bytesOf(out) <= SAVE_BYTES };
  }

  function copyRecord(record) {
    return { g: record.g, h: record.h, k: record.k, n: record.n, s: record.s,
             kills: Array.isArray(record.kills) ? record.kills.slice() : [],
             chests: Array.isArray(record.chests) ? record.chests.slice() : [],
             drops: Array.isArray(record.drops) ? record.drops.slice() : [],
             secrets: Array.isArray(record.secrets) ? record.secrets.slice() : [],
             fog: typeof record.fog === 'string' ? record.fog : '' };
  }

  // A save that cannot be stored is never stored, and says so in words
  // the player can act on: the engine's own rule, not this part's
  // invention. The refusal is kept until a save goes through, and the
  // Descent panel shows it the next time it is opened.
  var lastRefusal = '';

  function saveRefusal() { return lastRefusal; }

  function refuse(text) {
    lastRefusal = text;
    var line = document.getElementById('descent-line');
    if (line) line.textContent = text;
  }

  function saveDoc(doc) {
    // The whole-save trim first (its order of sacrifice is the frozen
    // contract), then the per-floor budget on what survived it. Fitting a
    // floor only ever makes the save smaller, so `fits` still holds.
    var fit = fitDoc(doc);
    if (!fit.fits) {
      refuse('This descent has grown too large to save, so what happened on '
        + 'these floors is not being remembered. Start a new descent, or '
        + "clear this site's saved game in your browser, and try again.");
      return null;
    }
    lastRefusal = '';
    var out = fitFloors(fit.doc);
    store.setJSON(docKey(), out);
    return out;
  }

  // ---- the floors a descent remembers ---------------------------------
  // The identity triple is checked every time a floor is entered. A floor
  // that does not match is a floor the pack or the generator has moved
  // on from: it is drawn again and its deltas go, while the story flags
  // - which belong to the world, not to one floor - stay.
  var currentName = '';

  function recordFor(name, plan) {
    var doc = loadDoc();
    var record = doc.floors[name];
    if (isObj(record) && (record.h !== plan.identity.hash ||
                          record.g !== plan.identity.gen ||
                          record.k !== plan.identity.key)) {
      record = null;
    }
    if (!isObj(record)) {
      record = { g: plan.identity.gen, h: plan.identity.hash,
                 k: plan.identity.key, n: plan.depth, s: plan.section,
                 kills: [], chests: [], drops: [], secrets: [], fog: '' };
    }
    doc.floors[name] = record;
    if (doc.order.indexOf(name) === -1) doc.order.push(name);
    return { doc: doc, record: record, name: name };
  }

  function updateCurrent(mutator) {
    if (!currentName) return null;
    var doc = loadDoc();
    var record = doc.floors[currentName];
    if (!isObj(record)) return null;
    mutator(record);
    return saveDoc(doc);
  }

  function readCurrent(field, fallback) {
    var doc = loadDoc();
    var record = doc.floors[currentName];
    if (!isObj(record)) return fallback;
    var value = record[field];
    return value === undefined ? fallback : value;
  }

  // ---- the virtual region --------------------------------------------
  // The hook the plan calls the biggest structural unknown: the player's
  // region tables are plain objects and `enterRegion` only asks for
  // `regions[name]`, so a floor that was never baked is grown here, at
  // the moment the stair is used, before the player looks for it.
  var wired = {};

  function regionEntry(plan) {
    var legend = (def() && isObj(def().legend)) ? def().legend : LEGEND_FALLBACK;
    var upKey = plan.anchors.up[0] + ',' + plan.anchors.up[1];
    var downKey = plan.anchors.down[0] + ',' + plan.anchors.down[1];
    var pois = {}, poiText = {};
    pois[upKey] = 'the stair up';
    poiText[upKey] = 'Steps climb back toward the day.';
    pois[downKey] = 'the stair down';
    poiText[downKey] = 'Steps drop into the dark.';
    return {
      map: plan.rows.slice(), legend: legend, pois: pois, poi_text: poiText,
      hero_start: plan.anchors.up.slice(), sanctuary_tiles: [],
      watch: {}, water_by_phase: {}, flood_tiles: [], tile: 32,
      fog: plan.fog, bg: '#0d0f12', hero_color: '#e8e5df',
      speaker_color: '#8b939c', speaker_head: '#d8d5df'
    };
  }

  function enemyEntry(mob) {
    return { id: mob.id, name: mob.name, sprite: '', at: mob.at.slice(),
             hp: mob.hp, atk: mob.atk, sight: mob.sight,
             drops: mob.drops.slice() };
  }

  function pushTransition(list, t) {
    for (var i = 0; i < list.length; i++) {
      var one = list[i];
      if (one && one.from === t.from && String(one.at) === String(t.at) &&
          one.to === t.to) return;
    }
    list.push(t);
  }

  // The stairs of a generated floor: down to the next depth, up to the
  // floor above - and the first floor's stair up is the way home.
  function wireFloor(name, plan) {
    if (wired[name]) return;
    wired[name] = true;
    var list = window.VEFR_TRANSITIONS || [];
    var down = locate(plan.depth + 1);
    if (down) {
      var below = floorPlan(plan.depth + 1);
      if (below) {
        pushTransition(list, { from: name, at: plan.anchors.down.slice(),
                               to: below.name, to_at: below.anchors.up.slice() });
      }
    }
    var up = locate(plan.depth - 1);
    if (up) {
      var above = floorPlan(plan.depth - 1);
      if (above) {
        pushTransition(list, { from: name, at: plan.anchors.up.slice(),
                               to: above.name, to_at: above.anchors.down.slice() });
      }
    } else {
      var entry = entryHere();
      if (entry) {
        pushTransition(list, { from: name, at: plan.anchors.up.slice(),
                               to: entry.region, to_at: entry.at.slice() });
      }
    }
    window.VEFR_TRANSITIONS = list;
  }

  // The pack's own stair into the deep: the tile in a baked region the
  // descent starts from. It is a transition like any other, so the one
  // verb, the reach and the lock rules all work on it as they always did.
  function entryHere() {
    var d = def();
    if (!d || !isObj(d.entry)) return null;
    var region = d.entry.region;
    var at = d.entry.at;
    if (typeof region !== 'string' || !region ||
        !Array.isArray(at) || at.length !== 2 || !isWhole(at[0]) || !isWhole(at[1])) {
      return null;
    }
    return { region: region, at: at };
  }

  function wireEntry() {
    var entry = entryHere();
    if (!entry) return;
    var list = window.VEFR_TRANSITIONS || [];
    var first = locate(1);
    if (!first) return;
    var plan = floorPlan(1);
    if (!plan) return;
    pushTransition(list, { from: entry.region, at: entry.at.slice(),
                           to: plan.name, to_at: plan.anchors.up.slice() });
    window.VEFR_TRANSITIONS = list;
  }

  // ---- books pinned to a generated floor (the twin of `place_books`) --
  // A library book on a generated floor names where on it to lie, not a
  // tile: the floor is redrawn every run, so the tile is chosen from the
  // floor itself - reachable ground, off the stairs and the monsters, one
  // book per tile - from the floor's own `book|<id>` stream. The same run
  // always shows a book in the same place; a new run moves it.
  var BOOK_NEAR = [2, 6];

  function floorDistances(rows, start) {
    var dist = {};
    dist[start[0] + ',' + start[1]] = 0;
    var queue = [[start[0], start[1]]];
    for (var i = 0; i < queue.length; i++) {
      var x = queue[i][0], y = queue[i][1], d = dist[x + ',' + y];
      var steps = [[x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]];
      for (var s = 0; s < 4; s++) {
        var nx = steps[s][0], ny = steps[s][1];
        if (ny < 0 || ny >= rows.length || nx < 0 || nx >= rows[0].length) continue;
        if (rows[ny].charAt(nx) === '#' || has(dist, nx + ',' + ny)) continue;
        dist[nx + ',' + ny] = d + 1;
        queue.push([nx, ny]);
      }
    }
    return dist;
  }

  function placeBooks(plan, books) {
    var rows = plan.rows, up = plan.anchors.up, down = plan.anchors.down;
    var fromUp = floorDistances(rows, up), fromDown = floorDistances(rows, down);
    var taken = {};
    taken[up[0] + ',' + up[1]] = true;
    taken[down[0] + ',' + down[1]] = true;
    (plan.mobs || []).forEach(function (m) { taken[m.at[0] + ',' + m.at[1]] = true; });
    var out = {};
    function xy(k) { var p = k.split(','); return [Number(p[0]), Number(p[1])]; }
    function free(k) {
      var t = xy(k);
      return !taken[k] && has(fromUp, k) && rows[t[1]].charAt(t[0]) === '.';
    }
    function within(dist, lo, hi) {
      return Object.keys(dist).filter(function (k) {
        return dist[k] >= lo && (hi === null || dist[k] <= hi) && free(k);
      });
    }
    books.slice().sort(function (a, b) { return a.id < b.id ? -1 : (a.id > b.id ? 1 : 0); })
      .forEach(function (book) {
        var tiles = book.place === 'near-up' ? within(fromUp, BOOK_NEAR[0], BOOK_NEAR[1])
          : (book.place === 'near-down' ? within(fromDown, BOOK_NEAR[0], BOOK_NEAR[1]) : []);
        if (!tiles.length) tiles = within(fromUp, BOOK_NEAR[0], null);
        if (!tiles.length) tiles = within(fromUp, 0, null);
        if (!tiles.length) return;
        tiles.sort(function (a, b) {
          var p = xy(a), q = xy(b);
          return p[1] - q[1] || p[0] - q[0];
        });
        var rng = window.VEFR_DELVE.prng(streamSeed(plan.key, 'book|' + book.id));
        var pick = tiles[Math.floor(rng() * tiles.length)];
        taken[pick] = true;
        out[book.id] = xy(pick);
      });
    return out;
  }

  // The library's books pinned to this floor get their tile for this run,
  // so finding, drawing and chests read `at` exactly as for any map book.
  function pinBooks(name, plan) {
    var pinned = (window.VEFR_LIBRARY || []).filter(function (b) {
      return b && b.found === 'map' && b.region === name && typeof b.place === 'string';
    });
    if (!pinned.length) return;
    var at = placeBooks(plan, pinned.map(function (b) { return { id: b.id, place: b.place }; }));
    pinned.forEach(function (b) { if (at[b.id]) b.at = at[b.id]; });
  }

  function ensureRegion(name) {
    if (!on() || wired[name]) return false;
    var depth = depthOfName(name);
    if (!depth) return false;
    var plan = floorPlan(depth);
    if (!plan) return false;
    var regions = window.VEFR_REGIONS;
    if (!regions) return false;
    regions[name] = regionEntry(plan);
    pinBooks(name, plan);
    var enemies = window.VEFR_ENEMIES;
    if (!enemies) enemies = window.VEFR_ENEMIES = {};
    enemies[name] = plan.mobs.map(enemyEntry);
    currentName = name;
    // The record is made before the player arrives, so an identity
    // mismatch is settled by the floor the player is about to see.
    var held = recordFor(name, plan);
    saveDoc(held.doc);
    wireFloor(name, plan);
    return true;
  }

  // Arriving somewhere: the stairs of the floor left behind, and the
  // Stardew reset when the way back is the surface.
  function onEnter(name) {
    if (!on()) return;
    var leaving = currentName;
    var entering = String(name === undefined ? '' : name);
    if (leaving && !isGenerated(entering)) {
      returnToTown(leaving);
    }
    if (isGenerated(entering)) {
      ensureRegion(entering);
    } else {
      currentName = '';
    }
  }

  // Returning to town clears what the Section's floors produced - what was
  // killed, taken and dropped there, the mines reset all together - and
  // keeps the memory of where the hero has walked and what they found.
  function returnToTown(name) {
    var doc = loadDoc();
    var changed = false;
    var floors = isObj(doc.floors) ? doc.floors : {};
    for (var i = 0; i < doc.order.length; i++) {
      var record = floors[doc.order[i]];
      if (!isObj(record)) continue;
      var at = parseName(doc.order[i]);
      if (!at || at.section.id !== sectionIdOf(name)) continue;
      if (record.kills.length || record.chests.length || record.drops.length) {
        record.kills = [];
        record.chests = [];
        record.drops = [];
        changed = true;
      }
    }
    if (changed) saveDoc(doc);
  }

  function sectionIdOf(name) {
    var at = parseName(name);
    return at ? at.section.id : '';
  }

  // ---- the story flags, which outlive every floor ---------------------
  function flags() { return loadDoc().flags; }

  function setFlag(flag, value) {
    var doc = loadDoc();
    doc.flags[flag] = (value === undefined) ? true : !!value;
    saveDoc(doc);
  }

  function landings() {
    var value = flags()['landing'];
    return Array.isArray(value) ? value : [];
  }

  function recordLanding(depth) {
    var doc = loadDoc();
    var seen = Array.isArray(doc.flags['landing']) ? doc.flags['landing'] : [];
    if (seen.indexOf(depth) === -1) {
      seen.push(depth);
      seen.sort(function (a, b) { return a - b; });
      doc.flags['landing'] = seen;
      saveDoc(doc);
    }
  }

  // ---- the deltas, read and written by the parts that own them -------
  function loadKills() { return readCurrent('kills', []); }
  function saveKills(ids) { return updateCurrent(function (r) { r.kills = ids; }); }
  function loadChests() { return readCurrent('chests', []); }
  function saveChests(ids) { return updateCurrent(function (r) { r.chests = ids; }); }
  function loadDrops() { return readCurrent('drops', []); }
  function saveDrops(list) { return updateCurrent(function (r) { r.drops = list; }); }
  function loadSecrets() { return readCurrent('secrets', []); }
  function saveSecrets(list) { return updateCurrent(function (r) { r.secrets = list; }); }

  // The explored bitset rides in the same record as everything else, so
  // the cap that keeps the save small keeps the memory too.
  function loadFog() { return readCurrent('fog', ''); }
  function saveFog(text) { return updateCurrent(function (r) { r.fog = text || ''; }); }

  // ---- a new descent --------------------------------------------------
  function resetRegions() {
    var regions = window.VEFR_REGIONS;
    var enemies = window.VEFR_ENEMIES;
    var names = Object.keys(isObj(regions) ? regions : {});
    for (var i = 0; i < names.length; i++) {
      if (!isGenerated(names[i])) continue;
      delete regions[names[i]];
      if (enemies) delete enemies[names[i]];
    }
    var list = window.VEFR_TRANSITIONS || [];
    var kept = [];
    for (var j = 0; j < list.length; j++) {
      var t = list[j];
      if (t && isGenerated(t.from) && isGenerated(t.to)) continue;
      kept.push(t);
    }
    window.VEFR_TRANSITIONS = kept;
    wired = {};
  }

  // A new run is the same descent with a fresh seed: run one is the
  // pack's own, and every run after it is counted, so a player never
  // waits on a clock for a new world.
  function startRun(run) {
    var doc = loadDoc();
    var next = isWhole(run) && run >= 0 ? run : doc.run + 1;
    doc.run = next;
    doc.seed = runSeed(baseSeed(), next);
    doc.floors = {};
    doc.order = [];
    saveDoc(doc);
    resetRegions();
    currentName = '';
    wireEntry();
    return next;
  }

  // ---- the one-time gen_version card ----------------------------------
  // A Release 1 save cannot carry generated floors (PLAN §1, item 8), so
  // it is offered the choice once: keep this world as it was, or start
  // over with the floors the pack now carries.
  // The keys Release 1 wrote. `vefr-equipped-` and the fog bitset are
  // deliberately absent: the player writes both on a first run, and a
  // player who has never played is not an old save.
  var CARD_KEYS = ['vefr-bag-', 'vefr-gold-', 'vefr-hp-', 'vefr-library-',
                   'vefr-album-'];

  function oldSaveExists() {
    var name = worldName();
    for (var i = 0; i < CARD_KEYS.length; i++) {
      if (store.get(CARD_KEYS[i] + name) !== null) return true;
    }
    return false;
  }

  function needsCard() {
    if (!on()) return false;
    if (loadDoc().card === GEN_VERSION) return false;
    return oldSaveExists();
  }

  function cardShown() { return cardOpen; }

  var cardOpen = false;

  function showCard() {
    var box = document.getElementById('gen-card');
    if (!box) return false;
    var d = def();
    var line = document.getElementById('gen-card-line');
    if (line) {
      line.textContent = (d && d.card && d.card.note)
        ? d.card.note
        : 'The floors under this world are new. An old save cannot carry them: '
          + 'start over and play the new floors, or keep the world you have.';
    }
    box.hidden = false;
    cardOpen = true;
    var keep = document.getElementById('gen-card-keep');
    if (keep) keep.focus();
    return true;
  }

  function hideCard() {
    var box = document.getElementById('gen-card');
    if (box) box.hidden = true;
    cardOpen = false;
  }

  function keepOldSave() {
    var doc = loadDoc();
    doc.card = GEN_VERSION;
    saveDoc(doc);
    hideCard();
  }

  // Every save this site still holds, or null when the storage cannot be
  // asked at all. A storage that refused a remove leaves its key behind,
  // and a player told their save is gone when it is not is worse off
  // than one who is told the truth.
  function vefrKeysIn(storage) {
    if (!storage || typeof storage.length !== 'number' || typeof storage.key !== 'function') {
      return null;
    }
    var left = [];
    try {
      for (var i = 0; i < storage.length; i++) {
        var k = storage.key(i);
        if (typeof k === 'string' && k.indexOf('vefr-') === 0) left.push(k);
      }
    } catch (e) { return null; }
    return left;
  }

  function sayStartOverFailed(text) {
    var line = document.getElementById('gen-card-line');
    if (line) line.textContent = text;
    var box = document.getElementById('gen-card');
    if (box) box.hidden = false;
    cardOpen = true;
  }

  // A Start over clears every vefr- key on this site, and a clear cannot
  // be taken back - so the browser is asked to STORE a save first, and
  // the answer is read back rather than taken on trust. `store.setJSON`
  // gives up quietly when storage is full or blocked, so a write that
  // returned is not a write that happened; clearing on top of one of
  // those erases the only copy of the game and leaves nothing behind,
  // without a word to the player.
  //
  // The save written here is the new game's: this generation's mark, no
  // floors, the same seed. It is the save the reload would write anyway;
  // writing it first is what makes the clear safe.
  function freshSave() {
    var doc = freshDoc();
    doc.card = GEN_VERSION;
    return doc;
  }

  // Whether the new save is really in storage afterwards, not merely
  // handed over to a store that swallowed it.
  function storedSave(doc) {
    var written = null;
    try { written = saveDoc(doc); } catch (e) { return false; }
    if (!isObj(written)) return false;
    var back = store.getJSON(docKey(), null);
    if (!isObj(back)) return false;
    return JSON.stringify(back) === JSON.stringify(written);
  }

  function startOver() {
    var before = loadDoc();
    if (!storedSave(freshSave())) {
      sayStartOverFailed('Your saved game could not be cleared: this browser '
        + 'would not store a new save, so clearing the old one would leave '
        + 'you with nothing at all. Nothing has been cleared and nothing '
        + 'has been lost. Free some space, or allow this site to store '
        + 'data, then try Start over again.');
      return false;
    }
    var storage = store.raw();
    try { window.startoverKeys(storage); } catch (e) { /* read below says what is left */ }
    var left = vefrKeysIn(storage);
    if (left === null || left.length) {
      // The clear did not finish, so this was not a Start over: what was
      // about to be erased goes back where it was, and the refusal is
      // said. The message has always promised nothing was lost.
      putBack(before);
      if (left === null) {
        sayStartOverFailed('Your saved game could not be checked, so nothing has '
          + 'been cleared and nothing has been lost. Clear this site\'s saved '
          + 'game in your browser, then try Start over again.');
      } else {
        sayStartOverFailed('Your saved game could not be cleared: this browser '
          + 'would not let the game remove ' + left.length
          + (left.length === 1 ? ' save.' : ' saves.')
          + ' Nothing has been lost. Clear this site\'s saved game in your '
          + 'browser, then try Start over again.');
      }
      return false;
    }
    hideCard();
    window.location.reload();
    return true;
  }

  // The save that was there before a clear that did not finish. It goes
  // back through `saveDoc`, so the documented order of sacrifice still
  // decides what a too-large save keeps.
  function putBack(doc) {
    try { saveDoc(doc); } catch (e) { /* nothing left to say: the refusal above stands */ }
  }

  function offerCard() {
    if (!on()) return false;
    var doc = loadDoc();
    if (sweepIdentities(doc)) saveDoc(doc);
    if (needsCard()) return showCard();
    markGeneration();
    hideCard();
    return false;
  }

  // ---- the New-descent control ---------------------------------------
  function bindCard() {
    var keep = document.getElementById('gen-card-keep');
    var over = document.getElementById('gen-card-over');
    if (keep && !keep.dataset.bound) {
      keep.dataset.bound = '1';
      keep.addEventListener('click', keepOldSave);
    }
    if (over && !over.dataset.bound) {
      over.dataset.bound = '1';
      over.addEventListener('click', startOver);
    }
  }

  function bindDescent() {
    bindCard();
    var item = document.getElementById('menu-descent');
    var body = document.getElementById('descent-body');
    var line = document.getElementById('descent-line');
    var fresh = document.getElementById('descent-new');
    var row = document.getElementById('menu-descent-row');
    if (!on()) {
      // A pack that carries no descent has no descent to offer: the menu
      // item is not shown at all, rather than shown and refused.
      if (row) row.hidden = true;
      return false;
    }
    if (row) row.hidden = false;
    var render = function () {
      if (!line) return;
      var doc = loadDoc();
      var deepest = 0;
      for (var i = 0; i < doc.order.length; i++) {
        var record = doc.floors[doc.order[i]];
        if (isObj(record) && isWhole(record.n) && record.n > deepest) {
          deepest = record.n;
        }
      }
      line.textContent = 'Run ' + (doc.run + 1) + ' of the descent (' + doc.seed +
        '). Deepest floor reached: ' + deepest + '. A new descent starts the '
        + 'same Sections over with a fresh seed.';
      // A save that could not be stored is said first, while it is true.
      if (lastRefusal) line.textContent = lastRefusal;
    };
    render();
    if (item) {
      item.addEventListener('click', function () {
        render();
        if (fresh) fresh.focus();
      });
    }
    if (fresh) {
      fresh.addEventListener('click', function () {
        startRun();
        render();
        if (window.closeMenu) window.closeMenu();
        var first = locate(1);
        if (first) enterDescentFloor(1);
      });
    }
    return true;
  }

  // The one way into the deep that is not a stair on a floor: the
  // control itself, for a player who wants the next run now.
  function enterDescentFloor(depth) {
    var plan = floorPlan(depth);
    if (!plan) return false;
    ensureRegion(plan.name);
    if (typeof window.VEFR_ENTER_REGION === 'function') window.VEFR_ENTER_REGION(plan.name, null);
    return true;
  }

  function floor() {
    if (!currentName) return null;
    var depth = depthOfName(currentName);
    return depth ? floorPlan(depth) : null;
  }

  function markGeneration() {
    // The save declares which generation wrote it. A pack with no descent
    // never writes one, so a pack without a descent is exactly as it was.
    var doc = loadDoc();
    if (doc.card === GEN_VERSION) return false;
    doc.card = GEN_VERSION;
    saveDoc(doc);
    return true;
  }

  // Every remembered floor is checked against the floor this pack would
  // draw now, once, when the game starts. One that no longer matches is
  // dropped whole - it will be drawn again, and it is not the floor the
  // save was about. The story flags are never touched: a save that has
  // lost a floor has not lost the world.
  function sweepIdentities(doc) {
    var changed = false;
    var names = Array.isArray(doc.order) ? doc.order.slice() : [];
    for (var i = 0; i < names.length; i++) {
      var name = names[i];
      var at = parseName(name);
      var record = isObj(doc.floors) ? doc.floors[name] : null;
      if (!at || !isObj(record)) continue;
      var depth = depthOfName(name);
      if (!depth) continue;
      // `at.section` is the section OBJECT (see parseName); floorKey
      // concatenates its sectionId argument, so passing the object made
      // this key `run-a/[object Object]/0/1`, which never matched the
      // stored key and emptied every floor record on every load - the
      // kill list, the chests, the drops and the explored bitset with
      // it. The plan path takes `.id` (planFor, :251 area); so does
      // sectionIdOf, :704. Same accessor, same reason.
      var key = floorKey(seedFor(doc.run), at.section.id, at.cycle, at.k);
      if (record.h === sectionHash(at.section) && record.g === GEN_VERSION &&
          record.k === key) {
        continue;
      }
      // Not the floor the save was about: it is drawn again, so its
      // deltas are meaningless and go. What it *was* - how deep it was,
      // which Section - is kept, so the journal still reads true.
      doc.floors[name] = {
        g: GEN_VERSION, h: sectionHash(at.section), k: key,
        n: isWhole(record.n) ? record.n : depth, s: at.section,
        kills: [], chests: [], drops: [], secrets: [], fog: ''
      };
      changed = true;
    }
    return changed;
  }

  var api = {
    on: on, GEN_VERSION: GEN_VERSION, FLOOR_CAP: FLOOR_CAP,
    FLOOR_BYTES: FLOOR_BYTES, SAVE_BYTES: SAVE_BYTES,
    locate: locate, floorName: floorName, floorKey: floorKey,
    streamSeed: streamSeed, lootSeed: lootSeed, chestSeed: chestSeed,
    runSeed: runSeed, sectionHash: sectionHash, parseName: parseName,
    isGenerated: isGenerated, depthOfName: depthOfName, floorPlan: floorPlan,
    planFloor: planFloor, mobsAt: mobsAt, mobDrops: mobDrops, placeBooks: placeBooks,
    ensureRegion: ensureRegion, onEnter: onEnter, entryHere: entryHere,
    wireEntry: wireEntry, docKey: docKey,
    loadDoc: loadDoc, saveDoc: saveDoc, trimDoc: trimDoc, fitDoc: fitDoc,
    saveRefusal: saveRefusal,
    docBytes: bytesOf, floorBytes: floorBytes,
    loadKills: loadKills, saveKills: saveKills,
    loadChests: loadChests, saveChests: saveChests,
    loadDrops: loadDrops, saveDrops: saveDrops,
    loadSecrets: loadSecrets, saveSecrets: saveSecrets,
    loadFog: loadFog, saveFog: saveFog,
    flags: flags, setFlag: setFlag, landings: landings,
    recordLanding: recordLanding,
    needsCard: needsCard, cardShown: cardShown, offerCard: offerCard,
    keepOldSave: keepOldSave, startOver: startOver,
    bindDescent: bindDescent, startRun: startRun,
    enterDescentFloor: enterDescentFloor,
    markGeneration: markGeneration, sweepIdentities: sweepIdentities
  };
  // `doc` and `floor` are values, not calls, read at the moment they are
  // asked for: a harness (and the debug console) can look at the save and
  // at the floor the hero is standing on without reaching for a function.
  Object.defineProperty(api, 'doc', { get: loadDoc });
  Object.defineProperty(api, 'floor', { get: floor });
  return api;
})();
