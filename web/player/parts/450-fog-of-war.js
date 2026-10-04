  // ---- fog of war ----
  // A region may declare `fog`: only what the hero has seen is drawn, a
  // radius around them is lit, and the rest of the memory is dimmed.
  // Explored tiles are remembered per region, per world, as a bitset:
  // one bit per tile of the region map, row-major, most significant bit
  // first in each byte, base64 text under `vefr-fog2-...`. An old JSON
  // array of "x,y" strings under `vefr-fog-...` converts on load - the
  // bitset written, the old key dropped - so no tile is lost in the move.
  // A player preference on top of the pack's choice: a region may declare
  // fog, and the player may still turn the dark off for themselves. Kept
  // per world, beside the explored tiles.
  function fogPrefKey() {
    var w = (window.VEFR_WORLD && window.VEFR_WORLD.name) || 'world';
    return 'vefr-fogpref-' + w;
  }
  function fogPrefOn() {
    return store.get(fogPrefKey()) !== 'off';
  }
  function setFogPref(on) {
    store.set(fogPrefKey(), on ? 'on' : 'off');
  }
  function fogEnabled() { return !!town.fog && fogPrefOn(); }
  var fogOn = fogEnabled();
  var fogRadius = (town.fog && town.fog.radius) || 6;
  var explored = {};
  function fogKey() {
    var w = (window.VEFR_WORLD && window.VEFR_WORLD.name) || 'world';
    return 'vefr-fog-' + w + '-' + regionName;
  }
  function fog2Key() {
    var w = (window.VEFR_WORLD && window.VEFR_WORLD.name) || 'world';
    return 'vefr-fog2-' + w + '-' + regionName;
  }
  // One bit per tile: index = y*width + x over the region map, most
  // significant bit first in each byte, then base64. In-memory stays
  // keyed "x,y" - only the saved form is packed.
  function encodeFog() {
    var w = town.map[0].length, h = town.map.length;
    var bits = new Uint8Array((w * h + 7) >> 3);
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        if (!explored[x + ',' + y]) continue;
        var i = y * w + x;
        bits[i >> 3] |= 1 << (7 - (i & 7));
      }
    }
    var s = '';
    for (var b = 0; b < bits.length; b++) s += String.fromCharCode(bits[b]);
    return btoa(s);
  }
  function decodeFog(value) {
    var w = town.map[0].length, h = town.map.length;
    var raw = atob(value);
    for (var i = 0; i < w * h; i++) {
      if (!(raw.charCodeAt(i >> 3) & (1 << (7 - (i & 7))))) continue;
      explored[(i % w) + ',' + ((i / w) | 0)] = 1;
    }
  }
  function loadFog() {
    explored = {};
    var packed = store.get(fog2Key());
    if (packed) {
      try { decodeFog(packed); } catch (e) { /* unreadable memory: start dark */ }
      return;
    }
    // The old era's JSON array: read it either way, because fog off may
    // not write but must not forget. The move to the bitset happens on
    // the first save, which also drops the old key.
    var old = store.getJSON(fogKey(), null);
    if (!Array.isArray(old)) return;
    old.forEach(function (k) { explored[k] = 1; });
    if (fogOn) saveFog();
  }
  function saveFog() {
    if (!fogOn) return false;   // fog off, or no fog here: write nothing
    var value;
    // Encode first: a failure must leave the store untouched.
    try { value = encodeFog(); } catch (e) { return false; }
    store.set(fog2Key(), value);
    store.remove(fogKey());   // the bitset is saved; the JSON era is over
    return true;
  }
  function litNow() {
    var out = {};
    if (!fogOn) return out;
    for (var y = hero[1] - fogRadius; y <= hero[1] + fogRadius; y++) {
      for (var x = hero[0] - fogRadius; x <= hero[0] + fogRadius; x++) {
        if (x < 0 || y < 0 || y >= town.map.length || x >= town.map[0].length) continue;
        if ((x - hero[0]) * (x - hero[0]) + (y - hero[1]) * (y - hero[1]) <= fogRadius * fogRadius) {
          out[x + ',' + y] = 1;
        }
      }
    }
    return out;
  }
  function seeNow() {
    var lit = litNow();
    var changed = false;
    Object.keys(lit).forEach(function (k) {
      if (!explored[k]) { explored[k] = 1; changed = true; }
    });
    if (changed) saveFog();
    return lit;
  }
  function hideUnseen(x, y) {
    return fogOn && !explored[x + ',' + y];
  }

