// -- album start --
// The album engine: the baked defs, the ids already found, and one
// event in, the newly earned ids out. Pure logic only - no DOM, no
// clock, no randomness, no fetch, no network - so a harness can run
// this exact text in a bare node vm with nothing but the built-ins.
window.VEFR_ALBUM_ENGINE = (function () {
  function isObj(v) {
    return typeof v === 'object' && v !== null && !Array.isArray(v);
  }

  // Does this sticker's `when` describe the event? The same single
  // event vocabulary the validator checks; a `distance` reads as
  // "within N tiles", the way a rule's does.
  function whenMatches(when, name, data) {
    if (!isObj(when)) return false;
    var keys = Object.keys(when);
    if (keys.length !== 1 || keys[0] !== name) return false;
    var want = when[keys[0]];
    if (!isObj(want)) return false;
    var wantKeys = Object.keys(want);
    for (var i = 0; i < wantKeys.length; i++) {
      var k = wantKeys[i];
      if (k === 'distance') {
        if (typeof want[k] !== 'number' || typeof data[k] !== 'number'
            || data[k] > want[k]) return false;
      } else if (data[k] !== want[k]) {
        return false;
      }
    }
    return true;
  }

  // earn(defs, found, event) -> the ids newly earned, in declaration
  // order. It never mutates the arguments: the caller owns the record
  // and adds only what comes back.
  function earn(defs, found, event) {
    var out = [];
    if (!Array.isArray(defs) || !isObj(event)) return out;
    var have = {};
    (Array.isArray(found) ? found : []).forEach(function (id) {
      if (typeof id === 'string') have[id] = true;
    });
    var name = event.name;
    var data = isObj(event.data) ? event.data : {};
    for (var i = 0; i < defs.length; i++) {
      var d = defs[i];
      if (!isObj(d) || typeof d.id !== 'string' || !d.id) continue;
      if (have[d.id]) continue;
      if (whenMatches(d.when, name, data)) out.push(d.id);
    }
    return out;
  }

  return { earn: earn };
})();
// -- album end --
