// ---- where next: the point-to hints, kept as player-facing
// intentions ("Go toward Saltreach.") instead of thrown-away
// narration. Authored by rules; nothing is inferred. Same wrapped
// storage discipline as the why-log.
window.VEFR_NEXT = [];
var rulesNextLoaded = false;
function rulesNextKey() {
  return 'vefr-next-' + ((window.VEFR_WORLD && window.VEFR_WORLD.name) || 'world');
}
function rulesNextLoad() {
  if (rulesNextLoaded) return;
  rulesNextLoaded = true;
  try {
    var a = JSON.parse(localStorage.getItem(rulesNextKey()) || '[]');
    window.VEFR_NEXT = Array.isArray(a) ? a.filter(function (e) {
      return e && typeof e.place === 'string' && typeof e.line === 'string';
    }) : [];
  } catch (e) { window.VEFR_NEXT = []; }
}
function rulesNextRecord(place, line) {
  if (typeof place !== 'string' || !place) return;
  rulesNextLoad();
  // one row per place: the newest word wins
  window.VEFR_NEXT = window.VEFR_NEXT.filter(function (e) { return e.place !== place; });
  window.VEFR_NEXT.push({ place: place, line: line || ('To reach ' + place + '.') });
  try { localStorage.setItem(rulesNextKey(), JSON.stringify(window.VEFR_NEXT)); } catch (e) {}
}

// The two evidence panels the menu shows: where the world pointed,
// and why it did what it did. Both render only real records - the
// point-to hints and the fired rules - and invent nothing.
function renderNextPanel() {
  var list = document.getElementById('next-list');
  var count = document.getElementById('next-count');
  if (!list) return;
  rulesNextLoad();
  list.textContent = '';
  var rows = window.VEFR_NEXT.slice().reverse();   // newest word first
  rows.forEach(function (e) {
    var p = document.createElement('p');
    p.className = 'status';
    var b = document.createElement('b');
    b.textContent = e.place + ' - ';
    p.appendChild(b);
    p.appendChild(document.createTextNode(e.line));
    list.appendChild(p);
  });
  if (!rows.length) {
    var empty = document.createElement('p');
    empty.className = 'empty';
    empty.textContent = 'Nothing has pointed the way yet.';
    list.appendChild(empty);
  }
  if (count) count.textContent = rows.length
    ? rows.length + (rows.length === 1 ? ' place to aim at.' : ' places to aim at.')
    : '';
}
function renderWhyPanel() {
  var list = document.getElementById('why-list');
  var count = document.getElementById('why-count');
  if (!list) return;
  rulesWhyLoad();
  list.textContent = '';
  var rows = window.VEFR_WHY.slice().reverse();   // newest first
  rows.forEach(function (e) {
    var p = document.createElement('p');
    p.className = 'status';
    var b = document.createElement('b');
    // the rule's own id, as words: "light-the-causeway-lamp"
    b.textContent = (e.id || '').replace(/-/g, ' ') + ' - ';
    p.appendChild(b);
    p.appendChild(document.createTextNode(e.why || ''));
    list.appendChild(p);
  });
  if (!rows.length) {
    var empty = document.createElement('p');
    empty.className = 'empty';
    empty.textContent = 'Nothing has happened yet that needs explaining.';
    list.appendChild(empty);
  }
  if (count) count.textContent = rows.length
    ? 'The last ' + rows.length + ' things the world did.'
    : '';
}

