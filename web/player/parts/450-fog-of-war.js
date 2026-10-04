  // ---- fog of war ----
  // A region may declare `fog`: only what the hero has seen is drawn, a
  // radius around them is lit, and the rest of the memory is dimmed.
  // Explored tiles are remembered per region, per world.
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
  function loadFog() {
    explored = {};
    var a = store.getJSON(fogKey(), []);
    (Array.isArray(a) ? a : []).forEach(function (k) { explored[k] = 1; });
  }
  function saveFog() {
    store.setJSON(fogKey(), Object.keys(explored));
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

