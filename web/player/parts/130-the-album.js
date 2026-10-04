// ---- the album: stickers a world keeps, earned in play ----
// A pack may bake a sticker album (window.VEFR_ALBUM_DEF): `open`
// stickers show their name from the start, `riddle` stickers show only
// their riddle until earned, and `secret` stickers only ever appear as
// a count. Rewards only add: nothing is ever removed from the found
// list. The pure engine lives between the "-- album start/end --"
// markers, mirroring the rules block.
var ALBUM_KEY = 'vefr-album-'
  + ((window.VEFR_WORLD && window.VEFR_WORLD.name) || 'world');
var ALBUM_DEF = Array.isArray(window.VEFR_ALBUM_DEF) ? window.VEFR_ALBUM_DEF : null;
// The in-memory fallback when storage is blocked (a sandboxed iframe).
var ALBUM_MEMORY = null;

function albumFoundIds() {
  if (ALBUM_MEMORY !== null) return ALBUM_MEMORY.slice();
  var ids = [];
  var raw = store.getJSON(ALBUM_KEY, []);
  if (Array.isArray(raw)) {
    ids = raw.filter(function (id) { return typeof id === 'string'; });
  }
  return ids;
}
function albumRemember(ids) {
  ALBUM_MEMORY = ids.slice();
  store.setJSON(ALBUM_KEY, ids);
}
// window.VEFR_ALBUM is the harness snapshot, and exists ONLY when the
// pack has an album: a pack without one leaves it undefined.
function albumSync() {
  if (!ALBUM_DEF) return;
  window.VEFR_ALBUM = { found: albumFoundIds(), total: ALBUM_DEF.length };
}
function albumName(id) {
  var defs = ALBUM_DEF || [];
  for (var i = 0; i < defs.length; i++) {
    if (defs[i] && defs[i].id === id) return defs[i].name || id;
  }
  return id;
}
// One announce per sticker, ever: a reload that already has it found
// earns nothing, so nothing is said again.
function albumEarn(ids) {
  var found = albumFoundIds();
  var added = [];
  ids.forEach(function (id) {
    if (found.indexOf(id) === -1) { found.push(id); added.push(id); }
  });
  if (!added.length) return;
  soundCue('sticker');
  albumRemember(found);
  albumSync();
  renderAlbumPanel();
  combatSay('You found a sticker: ' + albumName(added[0]) + '.');
}
// The one seam from every event into the album. Called at the very top
// of fireRule, before its rules early return: a pack with an album but
// no rules bakes VEFR_RULES = null, and that return would otherwise
// skip the sticker a `starts` earns.
function albumNotify(eventName, data) {
  if (!ALBUM_DEF || !window.VEFR_ALBUM_ENGINE) return;
  var earned = window.VEFR_ALBUM_ENGINE.earn(ALBUM_DEF, albumFoundIds(),
                                             { name: eventName, data: data || {} });
  if (earned.length) albumEarn(earned);
}
function renderAlbumPanel() {
  var list = document.getElementById('album-list');
  var count = document.getElementById('album-count');
  var secretsLine = document.getElementById('album-secrets');
  if (!list) return;
  var defs = ALBUM_DEF || [];
  var found = albumFoundIds();
  list.textContent = '';
  var secrets = 0;
  defs.forEach(function (d) {
    if (!d || typeof d.id !== 'string') return;
    if (found.indexOf(d.id) !== -1) {
      // Found: its name, plain.
      var row = document.createElement('p');
      row.className = 'status';
      row.textContent = d.name || d.id;
      list.appendChild(row);
      return;
    }
    if (d.kind === 'riddle') {
      // Unfound riddle: only its riddle, never its name.
      var r = document.createElement('p');
      r.className = 'status';
      r.textContent = d.riddle || '';
      list.appendChild(r);
      return;
    }
    if (d.kind === 'secret') { secrets++; return; }   // only a count
    // Unfound open: its name, marked not yet.
    var o = document.createElement('p');
    o.className = 'status';
    o.textContent = (d.name || d.id) + ' - not yet';
    list.appendChild(o);
  });
  if (count) count.textContent = found.length + ' of ' + defs.length + ' found';
  if (secretsLine) {
    secretsLine.textContent = secrets
      ? secrets + (secrets === 1 ? ' secret' : ' secrets') : '';
  }
}
albumSync();

