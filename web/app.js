/* VEFR — the workshop.
 *
 * A Norse game studio, well used and well loved.
 * Not a dashboard. A place. Games don't have chrome — they have rooms.
 *
 * The household lives here. One engine, many faces:
 *   The Desk     → The Storyteller    The Chronicle → Urðr
 *   The Map Room → The Cartographer   The Casting   → The Rune-Carver
 *   The Folks    → The Keeper of Faces The Archives  → Skuld
 *   The Vault    → The Hoard-Keeper   The Hall      → Ratatoskr, the ferry
 *   The Library  → Fróði, who writes on a paddle and never speaks
 *
 * Each resident has its own little toolkit of role templates and uses
 * the smallest model that passes its job (docs/guides/brain-roles.md),
 * often the same one. The squirrel is always watching.
 *
 * Where things live: this file is the shared house (residents, the folio,
 * the first walk, navigation). Each room is its own file in web/js/rooms/,
 * registering itself in `screens` through window.VEFR_STUDIO (the kit at the
 * bottom of this file); web/js/boot.js starts the studio once they've loaded.
 * A room that needs a new shared helper: add it to the kit.
 */

(function () {
  'use strict';

  var API = window.VEFR_API;
  var main = document.getElementById('main');
  var room = document.getElementById('room');
  var screens = {};
  var currentId = null;
  var currentScreen = null;

  /* ── Helpers ──────────────────────────────────────────── */

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function truncate(s, n) {
    if (!s) return '';
    return s.length > n ? s.slice(0, n) + '\u2026' : s;
  }

  function formatTime(t) {
    if (!t) return '';
    try {
      var d = new Date(t);
      if (isNaN(d.getTime())) return String(t);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) { return String(t); }
  }

  function h(tag, attrs, children) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === 'className') e.className = attrs[k];
      else if (k === 'textContent') e.textContent = attrs[k];
      else if (k === 'innerHTML') e.innerHTML = attrs[k];
      else if (k === 'hidden') e.hidden = attrs[k];
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), attrs[k]);
      else if (k === 'ariaExpanded') e.setAttribute('aria-expanded', attrs[k]);
      else e.setAttribute(k, attrs[k]);
    });
    if (children) {
      if (typeof children === 'string') e.innerHTML = children;
      else if (Array.isArray(children)) children.forEach(function (c) { if (c) e.appendChild(c); });
      else e.appendChild(children);
    }
    return e;
  }

  /* ── The workshop knows what you're building ──────────── */

  var SURFACE_MOOD = {
    combat:     { whisper: 'the air is tense',        accent: 'rgba(184, 84, 63, 0.06)' },
    mystery:    { whisper: 'something is hidden here', accent: 'rgba(108, 138, 168, 0.06)' },
    exploration:{ whisper: 'there is more to find',   accent: 'rgba(91, 138, 114, 0.06)' },
    survival:   { whisper: 'every choice matters',    accent: 'rgba(201, 169, 46, 0.06)' },
    social:     { whisper: 'someone is watching',     accent: 'rgba(181, 127, 139, 0.06)' },
    quiet:      { whisper: 'the world is resting',    accent: 'rgba(145, 133, 168, 0.04)' }
  };

  // The phase of the world becomes the light in the room.
  var PHASE_LIGHT = { dawn: 'dawn', dusk: 'dusk', day: 'day', night: 'night' };

  function phaseFor(phases) {
    if (!phases || !phases.length) return 'dawn';
    return PHASE_LIGHT[phases[0]] || 'dawn';
  }

  function inhabitWorld(world) {
    if (!world) return;

    // The world's name hangs under the room sign
    var worldSign = document.getElementById('rs-world');
    if (worldSign) worldSign.textContent = world.title || '';

    // The world's whisper is pinned to the wall
    var whisper = document.getElementById('mood-note');
    if (whisper) {
      var mood = SURFACE_MOOD[world.surface] || SURFACE_MOOD.quiet;
      whisper.textContent = '\u2726 ' + mood.whisper;
    }

    // The world's phase lights the room
    if (room) room.setAttribute('data-phase', phaseFor(world.phases));

    // The surface mood adds a subtle warmth to the work surface
    var foot = document.getElementById('foot-world');
    if (foot) foot.textContent = world.title ? 'on the table: ' + world.title : '';
    var joke = document.getElementById('foot-joke');
    if (joke) {
      var jk = Math.floor(Math.random() * FOOT_JOKES.length);
      joke.textContent = FOOT_JOKES[jk];
      window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('foot_joke', { joke: jk });
    }

    // The lantern burns: the storyteller is reachable
    setLantern(true, 'Storyteller ready');
  }

  function setLantern(lit, text) {
    storytellerAwake = !!lit;
    var lantern = document.getElementById('lantern');
    var label = document.getElementById('lantern-label');
    if (!lantern || !label) return;
    lantern.classList.toggle('lantern--cold', !lit);
    label.textContent = text || '';
  }

  /* A note from the ferry — pinned where you'll see it */
  var ferryTimer = null;
  function ferryNote(text) {
    var el = document.getElementById('ferry-note');
    if (!el) return;
    el.textContent = text;
    el.classList.add('ferry-note--show');
    clearTimeout(ferryTimer);
    ferryTimer = setTimeout(function () {
      el.classList.remove('ferry-note--show');
    }, 4200);
  }

  /* ── States — honest and warm ─────────────────────────── */

  /* Each room's resident waits in it while it is empty. */
  var ROOM_EMPTY = {
    workshop: 'desk', map: 'map-room', characters: 'folks', items: 'vault', journal: 'chronicle',
    library: 'library', runes: 'casting-table', evidence: 'archives', hall: 'hall', settings: 'boiler-room'
  };

  function emptyState(text, hint, squirrel) {
    var children = [];
    if (squirrel) {
      var room = ROOM_EMPTY[document.documentElement.getAttribute('data-screen')];
      var sq = h('div', { className: 'empty__squirrel' + (room ? ' empty__squirrel--room' : ''), 'aria-hidden': 'true' });
      sq.innerHTML = room
        ? '<img src="' + ART + 'poses/' + room + '-empty.webp" alt="" width="240" height="160">'
        : '<img src="' + ART + 'poses/ratatoskr-asleep-letter-pile.webp" alt="" width="140" height="140">';
      children.push(sq);
    }
    children.push(h('p', { className: 'empty__text', textContent: text }));
    if (hint) children.push(h('p', { className: 'empty__hint', textContent: hint }));
    return h('div', { className: 'empty', role: 'status' }, children);
  }

  var FERRY_LINES = [
    'Ratatoskr is fetching it…',
    'Ratatoskr is looking…',
    'Ratatoskr is on the way…',
    'Just a moment…'
  ];
  var ferry_i = 0;
  function ferryLine() {
    var line = FERRY_LINES[ferry_i % FERRY_LINES.length];
    ferry_i++;
    return line;
  }

  function loadingState(text) {
    return h('div', { className: 'loading', role: 'status', 'aria-live': 'polite' },
      [
        h('span', { className: 'loading__squirrel', 'aria-hidden': 'true', innerHTML: '<img src="/static/art/poses/ratatoskr-searching-lantern.webp" alt="" width="56" height="56">' }),
        h('span', { textContent: text || ferryLine() })
      ]
    );
  }

  /* ── The rooms ────────────────────────────────────────── */

  var SCREEN_TITLES = {
    library:    'The Library',
    floor:      'The Studio Floor',
    launcher:   'The Studio',
    workshop:   'The Desk',
    map:        'The Map Room',
    characters: 'The Folks',
    items:      'The Vault',
    journal:    'The Chronicle',
    runes:      'The Casting Table',
    evidence:   'The Archives',
    hall:       'The Hall',
    settings:   'Settings'
  };

  var SCREEN_SUBTITLES = {
    library:    'Every book the studio keeps, and every book its worlds hide. Pull one off the shelf to read it.',
    floor:      'Ten rooms, one resident each. Every room is a department a real studio has, and every game passes through them.',
    launcher:   'Your worlds, the latest news, and the team',
    workshop:   'Write, and ask the Storyteller what happens next',
    map:        'The world’s map, and a table to sketch new land',
    characters: 'The people of this world',
    items:      'Things worth keeping, and the stories behind them',
    journal:    'Everything that has happened, newest first',
    runes:      'The elder futhark, and a three-stone cast for when you’re stuck',
    evidence:   'The story bible: what is true in this world',
    hall:       'Everything you’ve kept, in one place',
    settings:   'Look, sound, motion and the local model'
  };

  // Residents greet a little differently each visit (their first
  // greeting stays in RESIDENTS; these are the other moods)
  var MORE_GREETINGS = {
    workshop: ['The candle has been waiting. So have I.', 'Sit. The page is still warm from last time.'],
    map: ['Mind the edges; they are not finished yet.', 'I drew a road last night. It goes somewhere now.'],
    characters: ['Someone knocked while you were out. Shall we see who?', 'Every face here wants something. Let us ask what.'],
    library: ['Every book on these shelves was written by a person. Read slowly.', 'Take one down. I will know where it goes.'],
    items: ['Please do not lick the rings.', 'I polished the small things. The big things polished themselves.'],
    journal: ['I heard that. I hear everything.', 'The ink dried on the last page. Ready for the next?'],
    runes: ['The stones are quiet today. That is also an answer.', 'Pick one without looking. That is the whole trick.'],
    evidence: ['Watch the third step; it has opinions.', 'The truth is down here. It is patient.'],
    hall: ['I dusted every frame. Twice. With my tail.', 'Acorns counted, letters carried, doors propped. Hello!'],
    settings: ['Bolt is napping on the boiler. Speak softly.', 'Every knob down here does exactly one thing. I checked.']
  };
  var visits = {};
  function greetingFor(id) {
    var r = RESIDENTS[id];
    var all = [r.greeting].concat(MORE_GREETINGS[id] || []);
    var n = visits[id] = (visits[id] || 0) + 1;
    return all[(n - 1) % all.length];
  }
  // A note pinned to each door on the Floor
  var DOOR_NOTES = {
    workshop: 'the candle is still going', map: 'unfinished edges, mind your step',
    characters: 'a chair by the window is still warm', items: 'please do not lick the rings',
    journal: 'Urðr hears everything', library: 'no book is lost here', runes: 'the stones will not flatter you',
    evidence: 'watch the third step', hall: 'dusted on Tuesdays, by tail',
    settings: 'Bolt is napping on the boiler'
  };
  var FOOT_JOKES = [
    'no squirrels were harmed in the making of this studio',
    'Ratatoskr has counted every acorn. twice.',
    'the boiler hums in a minor key; nobody minds',
    'made under the world tree, one page at a time'
  ];

  // The department each room is, in studio words
  var SCREEN_DEPTS = {
    launcher: 'Welcome', floor: 'Every department', library: 'Books \u00B7 kept by Fr\u00F3\u00F0i', workshop: 'Concept \u00B7 the brief',
    map: 'Level design', characters: 'Characters', items: 'Items \u0026 economy',
    journal: 'Production records', runes: 'Inspiration', evidence: 'The story bible',
    hall: 'Launch \u00B7 on display', settings: 'The machinery'
  };
  // Rooms reached through the Floor light the Floor in the nav
  var NAV_HOME = { map: 'floor', characters: 'floor', items: 'floor', runes: 'floor', evidence: 'floor', settings: 'floor' };

  // Each room has a quiet sound — a diegetic line, never a claim
  // about engine state. It just tells you the room is lived in.
  var AMBIENCE = {
    launcher:   'the fire settles in the grate',
    workshop:   'the ink is still wet on the map',
    map:        'a compass needle wavers in the drawer',
    characters: 'a chair by the window is still warm',
    items:      'the tray of keepsakes catches the lamplight',
    journal:    'the pages smell of beeswax',
    runes:      'rune dust flecks the cloth',
    evidence:   'the stairs creak, one at a time',
    hall:       'the walls remember every kept thing',
    settings:   'the boiler hums a steady note'
  };

  function ambienceNode(id) {
    if (!AMBIENCE[id]) return null;
    return h('p', { className: 'room-ambience', textContent: AMBIENCE[id] });
  }

  /* ── Sound — the hearth, always paired with what you can see ──
     Off by default (the prefs contract starts at silence). Every
     sound fires alongside a visible event: the clank lands with the
     ferry note, the squeak lands with the whisper row, the hearth
     crackle is the room itself. */
  var studioAudio = (function () {
    var ctx = null;
    var ambGain = null;
    var unlocked = false;
    function soundPrefs() {
      var P = window.VEFR_PREFS;
      var s = (P && P.get) ? (P.get().sound || {}) : {};
      return { fx: (s.effects || 0) > 0, amb: (s.ambience || 0) > 0 };
    }
    function ensure() {
      if (!ctx) {
        var AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return null;
        try { ctx = new AC(); } catch (e) { return null; }
      }
      if (ctx.state === 'suspended') ctx.resume();
      return ctx;
    }
    function ambient(on) {
      var st = soundPrefs();
      if (!st.amb) {
        if (ambGain) { try { ambGain.gain.value = 0; } catch (e) {} }
        return;
      }
      var c = ensure();
      if (!c) return;
      if (ambGain) { ambGain.gain.value = on ? 0.06 : 0; return; }
      var len = c.sampleRate * 2;
      var buf = c.createBuffer(1, len, c.sampleRate);
      var data = buf.getChannelData(0);
      var last = 0;
      for (var i = 0; i < len; i++) {
        last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02;
        data[i] = last * 3.5;
      }
      var src = c.createBufferSource();
      src.buffer = buf;
      src.loop = true;
      var filter = c.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.value = 150;
      var g = c.createGain();
      g.gain.value = on ? 0.06 : 0;
      src.connect(filter);
      filter.connect(g);
      g.connect(c.destination);
      try { src.start(); } catch (e) { return; }
      ambGain = g;
    }
    function blip(freq0, freq1, dur, vol, type) {
      var st = soundPrefs();
      if (!st.fx) return;
      var c = ensure();
      if (!c) return;
      var t0 = c.currentTime;
      var osc = c.createOscillator();
      osc.type = type || 'sine';
      osc.frequency.setValueAtTime(freq0, t0);
      osc.frequency.exponentialRampToValueAtTime(Math.max(freq1, 1), t0 + dur);
      var g = c.createGain();
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(vol, t0 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      osc.connect(g);
      g.connect(c.destination);
      osc.start(t0);
      osc.stop(t0 + dur + 0.05);
    }
    function clank() { blip(220, 180, 0.16, 0.12, 'triangle'); blip(330, 300, 0.12, 0.07, 'square'); }
    function squeak() { blip(980, 1500, 0.12, 0.06, 'sine'); }
    function unlock() {
      if (unlocked) return;
      unlocked = true;
      var c = ensure();
      if (c) ambient(true);
    }
    return { ambient: ambient, clank: clank, squeak: squeak, unlock: unlock, on: function () { var s = soundPrefs(); return s.amb || s.fx; } };
  })();

  /* The folio remembers — each resident's conversation persists,
     so the Cartographer still knows what you asked two visits ago. */
  function saveHistories() {
    try { window.localStorage.setItem('vefr.histories', JSON.stringify(histories)); } catch (e) {}
  }
  function loadHistories() {
    try {
      var raw = window.localStorage && localStorage.getItem('vefr.histories');
      if (raw) {
        var parsed = JSON.parse(raw);
        if (parsed && typeof parsed === 'object') {
          Object.keys(parsed).forEach(function (k) {
            if (Array.isArray(parsed[k])) histories[k] = parsed[k].slice(-40);
          });
        }
      }
    } catch (e) {}
  }

  /* The studio listens — real engine events, carried to the hall.
     Every whisper is a traced event that actually ran; nothing is
     invented. New ones arrive slowly, honestly, and are echoed. */
  var watch = { seen: {}, buffer: [], strip: null, timer: null };
  function routeVerb(route) {
    var known = {
      '/api/forge': 'An item was drafted',
      '/api/rumor': 'A rumor was written',
      '/api/npc': 'A character spoke',
      '/api/stefna': 'A relationship was checked',
      '/api/runes/cast': 'Runes were cast',
      '/api/builder/chat': 'A resident was asked',
      '/api/builder/enhance/map': 'A landmark’s description grew',
      '/api/builder/enhance/item': 'An item’s story grew',
      '/api/builder/map/propose': 'New land was sketched',
      '/api/builder/map/check': 'A map sketch was checked',
      '/api/builder/face/roll': 'A new character was drafted',
      '/api/spark/task': 'Spark ran a task'
    };
    return known[route] || 'The engine ran';
  }
  function watchNew(events) {
    var added = [];
    (events || []).forEach(function (e) {
      if (!e || !e.at || !e.route) return;
      var key = e.at + '|' + e.route;
      if (watch.seen[key]) return;
      watch.seen[key] = true;
      added.push(e);
    });
    var keys = Object.keys(watch.seen);
    if (keys.length > 400) {
      keys.slice(0, keys.length - 200).forEach(function (k) { delete watch.seen[k]; });
    }
    return added;
  }
  function pushWhisper(e) {
    var ok = e.ok !== false;
    var row = h('div', { className: 'watch-whisper' + (ok ? '' : ' watch-whisper--flat'), role: 'status' });
    row.appendChild(h('span', { className: 'watch-whisper__time', textContent: formatTime(e.at) || 'just now' }));
    row.appendChild(h('span', { className: 'watch-whisper__word',
      textContent: routeVerb(e.route) + (ok ? '' : ' \u2014 it didn\u2019t land') }));
    watch.buffer.push({ at: e.at, el: row });
    while (watch.buffer.length > 8) watch.buffer.shift();
    if (watch.strip) {
      watch.strip.appendChild(row);
      while (watch.strip.childElementCount > 8) watch.strip.removeChild(watch.strip.firstChild);
      if (ok) studioAudio.squeak();
    }
  }
  function startWatch() {
    if (watch.timer) return;
    watch.timer = setInterval(function () {
      if (document.hidden) return;
      API.trace().catch(function () { return { events: [] }; }).then(function (res) {
        watchNew((res && res.events) || []).forEach(pushWhisper);
      });
    }, 10000);
  }

  /* The first walk — a hand on the latch. On a first visit
     Ratatoskr pins a short note under the sign: five real actions,
     one in each room, each checked off only when it truly happens.
     Skipping is one press; the walk can be re-run any time from
     Settings, and the "how to read this house" sheet stays on
     paper always. Nothing here is invented — a step completes only
     when the real button really fires. */
  var WALK_STEPS = [
    { id: 'bell', screen: 'workshop', room: 'The Desk', do: 'Press Ring for the Storyteller.', for: 'The Storyteller answers.' },
    { id: 'map', screen: 'map', room: 'The Map Room', do: 'Paint one square on the drawing table.', for: 'Your sketch saves as you go.' },
    { id: 'chronicle', screen: 'journal', room: 'The Chronicle', do: 'Press Keep in the Hall on any entry.', for: 'It waits for you in the Hall.' },
    { id: 'folks', screen: 'characters', room: 'The Folks', do: 'Open anyone’s card.', for: 'See who they are and what they want.' },
    { id: 'hall', screen: 'hall', room: 'The Hall', do: 'Visit the Hall.', for: 'Everything you kept is here.' }
  ];
  var WALK_KEY = 'vefr.walk';
  var walk = { state: null, rail: null, sheet: null, sheetOpener: null, pendingGo: null, timer: null };
  function walkLoad() {
    try {
      var raw = window.localStorage && localStorage.getItem(WALK_KEY);
      walk.state = raw ? JSON.parse(raw) : null;
    } catch (e) { walk.state = null; }
    if (!walk.state) walk.state = { steps: {}, skipped: false, done: false };
    /* ?tour=off: a link (or a browser test) that opens the studio without the walk,
       for this visit only; nothing is saved, so the walk still waits for real visitors */
    try {
      if (/(^|[?&])tour=off(&|$)/.test(window.location.search.slice(1))) walk.state.skipped = true;
    } catch (e) {}
  }
  function walkSave() {
    try { localStorage.setItem(WALK_KEY, JSON.stringify(walk.state)); } catch (e) {}
  }
  function walkRows() {
    return WALK_STEPS.map(function (s) {
      return { step: s, done: !!(walk.state && walk.state.steps[s.id]) };
    });
  }
  function walkCurrent() {
    var rows = walkRows();
    for (var i = 0; i < rows.length; i++) {
      if (!rows[i].done) return rows[i];
    }
    return null;
  }
  function walkComplete() { return !walkCurrent(); }
  function walkAttempt(id) {
    if (!walk.state || walk.state.skipped || walk.state.done) return;
    if (walk.state.steps[id]) return;
    walk.state.steps[id] = true;
    if (walkComplete()) { walk.state.done = true; window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('walk_done'); }
    walkSave();
    walkRender();
    try { studioAudio.squeak(); } catch (e) {}
    walkGo();
  }
  /* The walk walks you — after each step, Ratatoskr tugs your
     sleeve toward the next room. If the folio is open (the bell
     and the faces open it), the walk waits for you to close it,
     then sets off. Nothing here invents progress: the tug only
     follows a step the real action really completed. */
  function walkGo() {
    if (!walk.state || walk.state.done || walk.state.skipped) return;
    var cur = walkCurrent();
    if (!cur || !cur.step.screen) return;
    walk.pendingGo = cur.step.screen;
    clearTimeout(walk.timer);
    walk.timer = setTimeout(function () {
      if (!walk.pendingGo) return;
      if (folioOpen()) return; // closing the folio carries us
      var go = walk.pendingGo;
      walk.pendingGo = null;
      navigate(go);
      ferryNote('Next stop: ' + walkRoomName(go) + '\u2026');
    }, 650);
  }
  function walkRoomName(screen) {
    var s = null;
    WALK_STEPS.forEach(function (x) { if (!s && x.screen === screen) s = x.room; });
    return s || 'the next room';
  }
  function folioOpen() {
    return !!(folio && folio.classList && folio.classList.contains('folio--open'));
  }
  function walkSkip() {
    if (!walk.state) return;
    walk.state.skipped = true;
    walkSave();
    window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('walk_skip');
    if (walk.rail) walk.rail.hidden = true;
  }
  function walkReset() {
    window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('walk_restart');
    try { localStorage.removeItem(WALK_KEY); } catch (e) {}
    walk.state = null;
    walkStart();
  }
  function walkRender() {
    if (!walk.rail) return;
    walk.rail.innerHTML = '';
    var head = h('div', { className: 'walk-rail__head' });
    head.appendChild(h('h2', { className: 'walk-rail__title', id: 'walk-title', textContent: 'Your first walk' }));
    head.appendChild(h('p', { className: 'walk-rail__byline', textContent: 'Five things to try, one in each room' }));
    walk.rail.appendChild(head);

    if (walkComplete() && walk.state && walk.state.done) {
      var done = h('div', { className: 'walk-rail__done', role: 'status', 'aria-live': 'polite' });
      done.appendChild(h('p', { className: 'walk-rail__done-line', textContent: 'That’s the tour. You know your way around now.' }));
      done.appendChild(h('p', { className: 'walk-rail__done-sub',
        textContent: 'Everything you make stays in its room. You can take the tour again from the Boiler Room.' }));
      var acts = h('div', { className: 'walk-rail__acts' });
      var keepSheet = h('button', { className: 'walk-rail__btn', type: 'button', textContent: 'Open the guide' });
      keepSheet.addEventListener('click', walkOpenSheet);
      var foldBtn = h('button', { className: 'walk-rail__btn walk-rail__btn--ghost', type: 'button', textContent: 'Close' });
      foldBtn.addEventListener('click', function () { if (walk.rail) walk.rail.hidden = true; });
      acts.appendChild(keepSheet);
      acts.appendChild(foldBtn);
      done.appendChild(acts);
      walk.rail.appendChild(done);
      return;
    }

    var cur = walkCurrent();
    var ol = h('ol', { className: 'walk-rail__steps' });
    walkRows().forEach(function (row) {
      var now = cur && cur.step.id === row.step.id;
      var li = h('li', { className: 'walk-rail__step'
        + (row.done ? ' walk-rail__step--done' : '')
        + (now ? ' walk-rail__step--now' : '') });
      if (now) li.setAttribute('aria-current', 'step');
      li.appendChild(h('span', { className: 'walk-rail__tick', textContent: row.done ? '\u2713' : '\u00B7' }));
      li.appendChild(h('span', { className: 'walk-rail__room', textContent: row.step.room }));
      li.appendChild(h('span', { className: 'walk-rail__do', textContent: row.step.do }));
      ol.appendChild(li);
    });
    walk.rail.appendChild(ol);

    var live = h('p', { className: 'walk-rail__live', role: 'status', 'aria-live': 'polite' });
    live.appendChild(h('strong', { textContent: cur.step.do + ' ' }));
    live.appendChild(document.createTextNode(cur.step.for));
    walk.rail.appendChild(live);

    // A hand on your shoulder — one press, and Ratatoskr walks you
    // to where the current step takes place (hidden when you're there)
    if (cur.step.screen && currentId !== cur.step.screen && screens[cur.step.screen]) {
      var goNow = h('button', { className: 'walk-rail__btn walk-rail__go', type: 'button',
        textContent: 'Take me to ' + cur.step.room + ' \u2192' });
      goNow.addEventListener('click', function () {
        walk.pendingGo = null;
        navigate(cur.step.screen);
        ferryNote('Heading to ' + cur.step.room + '\u2026');
      });
      walk.rail.appendChild(goNow);
    }

    var acts = h('div', { className: 'walk-rail__acts' });
    var skipBtn = h('button', { className: 'walk-rail__btn', type: 'button', textContent: 'Skip the tour' });
    skipBtn.addEventListener('click', walkSkip);
    var sheetBtn = h('button', { className: 'walk-rail__btn walk-rail__btn--ghost', type: 'button', textContent: 'How the studio works' });
    sheetBtn.addEventListener('click', walkOpenSheet);
    acts.appendChild(skipBtn);
    acts.appendChild(sheetBtn);
    walk.rail.appendChild(acts);
  }
  function walkStart() {
    if (!window.localStorage) return;
    walkLoad();
    if (walk.state.skipped || walk.state.done) return;
    if (!walk.rail) {
      walk.rail = h('section', { className: 'walk-rail', 'aria-labelledby': 'walk-title' });
      room.appendChild(walk.rail);
    }
    walk.rail.hidden = false;
    walkRender();
  }
  function walkOpenSheet() {
    if (!walk.sheet) walkBuildSheet();
    walk.sheetOpener = document.activeElement;
    walk.sheet.hidden = false;
    if (walk.sheet.querySelector) walk.sheet.querySelector('.sheet__close').focus();
  }
  function walkCloseSheet() {
    if (!walk.sheet) return;
    walk.sheet.hidden = true;
    if (walk.sheetOpener && walk.sheetOpener.focus) walk.sheetOpener.focus();
  }
  function walkBuildSheet() {
    walk.sheet = h('div', { className: 'sheet', role: 'dialog', 'aria-modal': 'true',
      'aria-labelledby': 'sheet-title', hidden: true });
    var paper = h('div', { className: 'sheet__paper' });
    paper.appendChild(h('h2', { id: 'sheet-title', textContent: 'How the studio works' }));
    paper.appendChild(h('p', { className: 'sheet__byline',
      textContent: 'One thing to try in each room' }));
    var rooms = [
      ['The Desk', 'where the Storyteller works. Ring for the Storyteller and ask what happens next.'],
      ['The Map Room', 'where the Cartographer keeps the map. Sketch new land and save it.'],
      ['The Folks', 'where the Keeper of Faces keeps the people. Meet someone, or invite a new character.'],
      ['The Chronicle', 'where Urðr writes down what happened. Keep the moments that matter.'],
      ['The Hall', 'everything you kept, carried up by Ratatoskr.'],
      ['The Vault', 'where the Hoard-Keeper keeps items. Draft one, or grow an item’s story.'],
      ['The Casting Table', 'where the Rune-Carver keeps the runes. Cast three when you’re stuck.'],
      ['The Archives', 'where Skuld keeps the story bible. Read what is true.'],
      ['The Boiler Room', 'the settings: look, sound, motion and the local model.']
    ];
    var dl = h('dl', { className: 'sheet__rows' });
    rooms.forEach(function (r) {
      var row = h('div', { className: 'sheet__row' });
      row.appendChild(h('dt', { className: 'sheet__room', textContent: r[0] }));
      row.appendChild(h('dd', { className: 'sheet__how', textContent: r[1] }));
      dl.appendChild(row);
    });
    paper.appendChild(dl);
    paper.appendChild(h('p', { className: 'sheet__rules',
      textContent: 'Three rules: everything you make is yours; nothing is made up behind your back; the engine checks a map before it’s saved.' }));
    var close = h('button', { className: 'sheet__close', type: 'button', textContent: 'Close' });
    close.addEventListener('click', walkCloseSheet);
    paper.appendChild(close);
    walk.sheet.appendChild(paper);
    room.appendChild(walk.sheet);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && walk.sheet && !walk.sheet.hidden) walkCloseSheet();
    });
  }
  var firstWalk = { start: walkStart, attempt: walkAttempt, reset: walkReset, openSheet: walkOpenSheet };

  function navigate(id) {
    if (!screens[id] || currentId === id) return;
    window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('room_visit', { room: id });
    if (currentScreen && currentScreen.leave) currentScreen.leave();
    var prev = main.querySelector('.screen--active');
    if (prev) prev.classList.remove('screen--active');
    currentId = id;
    currentScreen = screens[id];
    if (!currentScreen._init) {
      currentScreen.init();
      currentScreen._init = true;
    }
    var s = main.querySelector('#screen-' + id);
    if (s) s.classList.add('screen--active');
    currentScreen.enter();
    updateRoom(id);
    closeFolio();
    try { localStorage.setItem('vefr-screen', id); } catch (e) {}
    history.replaceState(null, '', '#' + id);
    window.scrollTo(0, 0);
  }

  function updateRoom(id) {
    document.documentElement.setAttribute('data-screen', id);
    var navKey = NAV_HOME[id] || id;
    document.querySelectorAll('.go[data-screen]').forEach(function (item) {
      if (item.dataset.screen === navKey) item.setAttribute('aria-current', 'page');
      else item.removeAttribute('aria-current');
    });
    document.getElementById('rs-title').textContent = SCREEN_TITLES[id] || '';
    document.getElementById('rs-subtitle').textContent = SCREEN_SUBTITLES[id] || '';
    document.getElementById('rs-dept').textContent = SCREEN_DEPTS[id] || '';
    var head = document.getElementById('room-sign');
    if (head) head.style.setProperty('--room-banner', ROOM_BANNERS[id] ? 'url(' + ART + 'banners/' + ROOM_BANNERS[id] + '.webp)' : 'none');
    renderGreeter(id);
  }

  /* The resident who tends this room greets you in its header. */
  function renderGreeter(id) {
    var slot = document.getElementById('rs-greeter');
    var resident = RESIDENTS[id];
    if (!slot) return;
    slot.innerHTML = '';
    if (!resident) { slot.hidden = true; return; }
    slot.hidden = false;
    var face = portrait(id, resident, 'greeter__portrait');
    if (!storytellerAwake) {
      var fimg = face.querySelector('img');
      if (fimg && faceSrc(id, 'sleepy')) fimg.src = faceSrc(id, 'sleepy');
    }
    slot.appendChild(face);
    var who = h('div', { className: 'greeter__who' });
    who.appendChild(h('b', { className: 'greeter__name', textContent: resident.name }));
    who.appendChild(h('span', { className: 'greeter__craft', textContent: resident.craft }));
    /* The secret name: what this room's job is called in a real studio. Shown when
       the slider says "Show me how things work" (Gee: just in time, on demand). */
    if (REAL_NAMES[id]) {
      who.appendChild(h('p', { className: 'greeter__real workings-only',
        textContent: 'In a real studio: ' + REAL_NAMES[id] }));
    }
    if (id === 'library') {
      /* Fr\u00F3\u00F0i never speaks: the words come up on a note pinned to a
         little wooden paddle (docs/guides/residents.md). */
      var paddle = h('div', { className: 'paddle', role: 'note', 'aria-label': 'Fr\u00F3\u00F0i writes' });
      paddle.appendChild(h('p', { className: 'paddle__note', textContent: greetingFor(id) }));
      paddle.appendChild(h('span', { className: 'paddle__handle', 'aria-hidden': 'true' }));
      who.appendChild(paddle);
    } else {
      who.appendChild(h('p', { className: 'greeter__says', textContent: '\u201C' + greetingFor(id) + '\u201D' }));
    }
    var ask = h('button', { className: 'cta cta--line greeter__ask', type: 'button', textContent: 'Ask ' + resident.name });
    ask.addEventListener('click', function () { openFolio(id, ask); });
    who.appendChild(ask);
    slot.appendChild(who);
  }

  /* A resident's portrait: a drawn face where the studio has one,
     otherwise their carved mark in a round frame. */
  var ART = '/static/art/';
  var RESIDENT_ART = {
    hall: 'ratatoskr', workshop: 'storyteller', journal: 'urdr', map: 'cartographer',
    characters: 'keeper-of-faces', items: 'hoard-keeper', runes: 'rune-carver',
    evidence: 'skuld', settings: 'volundr', spark: 'bolt', library: 'frodi'
  };
  /* Real-world names for each room's job (the Library book "The Secret Names"
     says the same, so the cosy word and the real word always match). */
  var REAL_NAMES = {
    workshop: 'writing and narrative design', map: 'level design', characters: 'character design',
    items: 'the item database', journal: 'version history (the log)', runes: 'procedural generation',
    evidence: 'the story bible (the source of truth)', hall: 'the archive of everything kept', settings: 'settings and operations',
    library: 'documentation', spark: 'a local AI model'
  };
  var ROOM_BANNERS = {
    workshop: 'desk', map: 'map-room', characters: 'folks', items: 'vault', journal: 'chronicle',
    runes: 'casting-table', evidence: 'archives', hall: 'hall', settings: 'boiler-room', floor: 'hall', library: 'library'
  };
  /* A resident's action pose, set beside the thing they tend. Decorative:
     the words around it always carry the meaning. */
  function spot(pose, cls) {
    return h('img', { className: 'spot ' + (cls || ''), src: ART + 'poses/' + pose + '.webp',
      alt: '', 'aria-hidden': 'true', loading: 'lazy', width: '180', height: '180' });
  }
  var EXPRESSIVE = ['storyteller', 'urdr', 'cartographer', 'keeper-of-faces', 'hoard-keeper', 'rune-carver', 'skuld', 'volundr'];
  /* A resident's face for a moment: 'thinking', 'happy', 'sleepy' or the plain portrait */
  function faceSrc(id, mood) {
    var art = RESIDENT_ART[id];
    if (!art) return null;
    if (mood && EXPRESSIVE.indexOf(art) !== -1) return ART + 'expressions/' + art + '-' + mood + '.webp';
    return ART + 'residents/' + art + '.webp';
  }
  var storytellerAwake = true;

  function portrait(id, resident, cls) {
    var art = RESIDENT_ART[id];
    var wrap = h('span', { className: 'portrait ' + (cls || ''), role: 'img', 'aria-label': resident.name });
    if (art) {
      wrap.appendChild(h('img', { src: ART + 'residents/' + art + '.webp', alt: '', loading: 'lazy', width: '160', height: '160' }));
    } else {
      var icon = (DEPARTMENTS.filter(function (d) { return d[0] === id; })[0] || [])[1] || 'i-hall';
      wrap.innerHTML = '<svg class="portrait__icon" viewBox="0 0 24 24" aria-hidden="true"><use href="#' + icon + '"/></svg>';
    }
    return wrap;
  }

  /* ══════════════════════════════════════════════════════
     THE HOUSEHOLD — the residents and the speaking folio
     ══════════════════════════════════════════════════════ */

  var RESIDENTS = {
    workshop: {
      name: 'The Storyteller', mark: '\u270E',
      craft: 'holds the current world',
      greeting: 'I was mid-thought when you rang. What are we making today?',
      roles: [
        'Draft a rumor for this world',
        'What happens next?',
        'Suggest a quiet beat',
        'Open the next act'
      ]
    },
    map: {
      name: 'The Cartographer', mark: '\u2727',
      craft: 'draws the world as it is found',
      greeting: 'The map answers when you ask it something specific. Where should we look?',
      roles: [
        'Describe this region as a place, not a grid',
        'Name an unexplored region',
        'What would a traveler notice first?',
        'Sketch a rumor that leads somewhere new'
      ]
    },
    characters: {
      name: 'The Keeper of Faces', mark: '\u2766',
      craft: 'tends the people of this world',
      greeting: 'Who are we meeting? Tell me who you want beside you.',
      roles: [
        'Propose a character who belongs here',
        'Give a person a want and a fear',
        'Who should appear next?',
        'Make a stranger who changes the mood'
      ]
    },
    items: {
      name: 'The Hoard-Keeper', mark: '\u2726',
      craft: 'minds what you\u2019ve gathered',
      greeting: 'Show me what you found. I can tell you whether it\u2019s worth keeping.',
      roles: [
        'Suggest a keepsake worth keeping',
        'What should this item mean to its holder?',
        'Forge a small object with a story',
        'What belongs on the shelf here?'
      ]
    },
    journal: {
      name: 'Ur\u00F0r', mark: '\u2767',
      craft: 'writes what has happened',
      greeting: 'Ask me what has happened. I keep the ledgers honest.',
      roles: [
        'What have we done so far?',
        'Summarize the arc in one breath',
        'Which moment should we honor?',
        'What threads are still open?'
      ]
    },
    library: {
      /* Fr\u00F3\u00F0i never speaks: he writes on a notepad on a little wooden
         paddle (Rylee, 2026-09-26; docs/guides/residents.md). */
      name: 'Fr\u00F3\u00F0i', mark: '\u16A0',
      craft: 'keeper of the Library',
      greeting: 'No book is lost here.',
      roles: [
        'Which book should I read first?',
        'What would a found note in this world sound like?',
        'Where could a book be hidden in this town?',
        'What should the next book be about?'
      ]
    },
    runes: {
      name: 'The Rune-Carver', mark: '\u16B1',
      craft: 'consults the stones',
      greeting: 'Cast in your mind, then ask. The stones will not flatter you.',
      roles: [
        'Cast a rune and read it',
        'What does this rune ask of us?',
        'Interpret the last cast honestly',
        'Which rune suits this moment?'
      ]
    },
    evidence: {
      name: 'Skuld', mark: '\u2B21',
      craft: 'keeps the truth beneath',
      greeting: 'Ask what lies beneath. I answer in plain terms.',
      roles: [
        'What is beneath this?',
        'Question an assumption',
        'What are we avoiding?',
        'Show me what the evidence contradicts'
      ]
    },
    hall: {
      name: 'Ratatoskr', mark: '\u{1F43F}\uFE0F',
      craft: 'the ferry; runs between every room',
      greeting: 'I\u2019m on the move, but I can carry a message. What should the tree hear?',
      roles: [
        'What have we kept?',
        'Find something worth keeping',
        'What did the tree whisper today?',
        'Carry a rumor to the storyteller'
      ]
    },
    settings: {
      name: 'V\u00F6lundr', mark: '\u2699',
      craft: 'minds the works behind the rooms',
      greeting: 'The pipes answered when you came down. Tell me how this studio should feel, and I\u2019ll turn the knobs.',
      roles: [
        'Which reading mode should I pick?',
        'Walk me through the motion setting',
        'What does each switch here change?',
        'Set this studio up for an easier day'
      ]
    }
  };

  /* The speaking folio — one place to talk to the household */
  var folio = null;
  var folioLog = null;
  var folioInput = null;
  var folioSend = null;
  var folioStatus = null;
  var histories = {};
  var folioResident = null;
  var folioOpener = null;
  var folioPending = false;

  function initFolio() {
    folio = h('div', { className: 'folio', role: 'dialog', 'aria-label': 'Ask a resident' });
    folio.innerHTML = ''
      + '<div class="folio__card">'
      + '  <div class="folio__mark" id="folio-mark"></div>'
      + '  <div class="folio__who">'
      + '    <div class="folio__name"><span id="folio-name"></span><span class="folio__craft" id="folio-craft"></span></div>'
      + '    <div class="folio__honest">one engine, many faces \u00B7 speaking through the model</div>'
      + '  </div>'
      + '  <button class="folio__close" id="folio-close" aria-label="Close">\u00D7</button>'
      + '</div>'
      + '<div class="folio__roles" id="folio-roles" aria-label="Things you can ask"></div>'
      /* One scrolling area: the live log (read aloud as it grows), then Fróði's notes
         outside it, so a note never talks over anyone. An opt-in setting ("Tell me
         when there's a word") speaks one line instead. */
      + '<div class="folio__scroll" id="folio-scroll">'
      + '  <div class="folio__log" id="folio-log" aria-live="polite"></div>'
      + '  <div class="folio__notes" id="folio-notes"></div>'
      + '</div>'
      + '<p class="sr-only" id="folio-teach-live" role="status" aria-live="polite"></p>'
      + '<div class="folio__composer">'
      + '  <textarea class="folio__input" id="folio-input" rows="1" placeholder="Ask the household\u2026" aria-label="Your message"></textarea>'
      + '  <button class="folio__send" id="folio-send">Ask</button>'
      + '  <button class="folio__forget" id="folio-forget" title="Forget this conversation">forget this talk</button>'
      + '</div>';

    folioLog = folio.querySelector('#folio-log');
    folioInput = folio.querySelector('#folio-input');
    folioSend = folio.querySelector('#folio-send');
    folioStatus = folioLog;

    folio.querySelector('#folio-close').addEventListener('click', closeFolio);
    folioSend.addEventListener('click', folioSendMessage);
    folioInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        folioSendMessage();
      }
    });
    folio.querySelector('#folio-forget').addEventListener('click', function () {
      if (!folioResident) return;
      window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('forget_talk');
      histories[folioResident] = [];
      saveHistories();
      openFolio(folioResident, folioOpener);
    });

    room.appendChild(folio);
  }

  function openFolio(screenId, opener) {
    var resident = RESIDENTS[screenId];
    if (!resident) return;
    window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('resident_ask', { room: screenId });
    if (!folio) initFolio();

    folioResident = screenId;
    folioOpener = opener || null;

    setFolioFace(storytellerAwake ? null : 'sleepy');
    folio.querySelector('#folio-name').textContent = resident.name;
    folio.querySelector('#folio-craft').textContent = resident.craft;

    // Role templates — the resident's little toolkits
    var rolesWrap = folio.querySelector('#folio-roles');
    rolesWrap.innerHTML = '';
    resident.roles.forEach(function (role) {
      var b = h('button', { className: 'folio__role', textContent: role });
      b.addEventListener('click', function () {
        folioInput.value = role;
        folioInput.focus();
      });
      rolesWrap.appendChild(b);
    });

    // The conversation so far (or the greeting, if we're starting fresh)
    var history = histories[screenId] || [];
    folioLog.innerHTML = '';
    if (!history.length) {
      folioLog.appendChild(h('div', { className: 'folio__msg folio__msg--resident', textContent: resident.greeting }));
    } else {
      history.forEach(function (turn) {
        var cls = turn.role === 'user' ? 'folio__msg--user' : 'folio__msg--resident';
        folioLog.appendChild(h('div', { className: 'folio__msg ' + cls, textContent: turn.content }));
      });
    }

    folioInput.value = '';
    folioInput.placeholder = 'Ask ' + resident.name + '\u2026';
    folioInput.disabled = false;
    folioSend.disabled = false;
    folioPending = false;
    folio.classList.add('folio--open');
    folioInput.focus();
  }

  function setFolioFace(mood) {
    var mark = folio && folio.querySelector('#folio-mark');
    if (!mark || !folioResident) return;
    var src = faceSrc(folioResident, mood);
    if (src) {
      mark.textContent = '';
      var img = mark.querySelector('img') || mark.appendChild(h('img', { alt: '', width: '64', height: '64' }));
      img.src = src;
    } else {
      mark.textContent = (RESIDENTS[folioResident] || {}).mark || '';
    }
  }

  function closeFolio(returnFocus) {
    if (!folio || !folio.classList.contains('folio--open')) return;
    folio.classList.remove('folio--open');
    if (returnFocus && folioOpener) {
      var opener = folioOpener;
      folioOpener = null;
      try { opener.focus(); } catch (e) {}
    }
    folioResident = null;
    folioPending = false;

    // The walk waits for the folio — now that it's closed, onward
    if (walk.pendingGo) {
      var go = walk.pendingGo;
      walk.pendingGo = null;
      navigate(go);
      ferryNote('Next stop: ' + walkRoomName(go) + '\u2026');
    }
  }

  /* Teach while building (Book Girl): after a reply is on screen, ask whether the
     author just used a design idea, and let Fróði hold up the paddle with its name.
     Recognition, never correction; at most one note every few turns. */
  var teachState = { turnsSince: 99, sessionNotes: 0 };
  function maybeTeach(authorText) {
    var P = window.VEFR_PREFS;
    var mode = (P && P.get && P.get().teach) || 'build';
    teachState.turnsSince += 1;
    if (mode === 'off') return;
    if (mode === 'tips' && teachState.sessionNotes >= 1) return;
    if (mode === 'build' && teachState.turnsSince < 3) return;
    API.teachRecognize({ message: authorText })
      .then(function (res) {
        var t = res && res.teach;
        var notes = folio && folio.querySelector('#folio-notes');
        if (!t || !notes) return;
        teachState.turnsSince = 0;
        teachState.sessionNotes += 1;
        notes.innerHTML = '';
        notes.appendChild(teachNote(t));
        window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('teach_note', { term: t.term, stage: t.stage });
        scrollFolio();
        var live = folio.querySelector('#folio-teach-live');
        var typing = document.activeElement === folioInput && folioInput.value.trim();
        if (live && P && P.get && P.get().teachAnnounce === 'on' && !typing) {
          live.textContent = 'Fróði has a word for what you just made: ' + t.term + '.';
        }
      })
      .catch(function () { /* no note is always fine */ });
  }

  function scrollFolio() {
    var box = folio && folio.querySelector('#folio-scroll');
    if (box) box.scrollTop = box.scrollHeight;
  }

  function teachNote(t) {
    var headId = 'paddle-head-' + Date.now();
    var note = h('section', { className: 'paddle-note', role: 'region', 'aria-labelledby': headId });
    var who = h('div', { className: 'paddle-note__who' });
    who.appendChild(h('img', { src: ART + 'residents/frodi.webp', alt: '', width: 40, height: 40 }));
    who.appendChild(h('span', { textContent: 'Fróði holds up the paddle' }));
    note.appendChild(who);
    var card = h('div', { className: 'paddle-note__card' });
    var name = t.term.charAt(0).toUpperCase() + t.term.slice(1);
    var lead = h('h3', { className: 'paddle-note__lead', id: headId });
    lead.appendChild(h('img', { src: ART + 'icons/library/kind-book.webp', alt: '', width: 24, height: 24 }));
    lead.appendChild(h('span', { textContent: (t.stage === 'again' && t.first_context)
      ? 'You’ve seen this idea before. Remember ' + t.first_context + '? Same idea:'
      : 'There’s a name for part of what you just made.' }));
    card.appendChild(lead);
    var def = h('p', {});
    def.appendChild(h('strong', { textContent: name }));
    def.appendChild(document.createTextNode(': ' + t.plain));
    card.appendChild(def);
    if (t.context) card.appendChild(h('p', { className: 'paddle-note__here', textContent: 'Here: ' + t.context + '.' }));
    if (t.local) card.appendChild(h('p', { className: 'paddle-note__here', textContent: 'In VEFR: ' + t.local + '.' }));
    var why = h('p', { className: 'paddle-note__why', textContent: t.why, hidden: true });
    card.appendChild(why);
    var row = h('div', { className: 'paddle-note__actions' });
    var whyBtn = h('button', { className: 'cta cta--line', type: 'button', textContent: 'Why designers use this', 'aria-expanded': 'false' });
    whyBtn.addEventListener('click', function () {
      why.hidden = !why.hidden;
      whyBtn.setAttribute('aria-expanded', String(!why.hidden));
    });
    var got = h('button', { className: 'cta cta--gold', type: 'button', textContent: 'Got it' });
    got.addEventListener('click', function () {
      API.teachGotIt({ term: t.term }).catch(function () {});
      window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('teach_got_it');
      note.remove();
      /* back to the reply the note was about, not to the text box */
      var replies = folioLog ? folioLog.querySelectorAll('.folio__msg--resident') : [];
      var last = replies[replies.length - 1];
      if (last) { last.setAttribute('tabindex', '-1'); last.focus(); } else if (folioInput) folioInput.focus();
    });
    if (t.why) row.appendChild(whyBtn);
    row.appendChild(got);
    card.appendChild(row);
    note.appendChild(card);
    return note;
  }

  function folioSendMessage() {
    if (!folioResident || folioPending) return;
    var text = folioInput.value.trim();
    if (!text) return;

    var oldNotes = folio && folio.querySelector('#folio-notes');
    if (oldNotes) oldNotes.innerHTML = '';
    var teachLive = folio && folio.querySelector('#folio-teach-live');
    if (teachLive) teachLive.textContent = '';
    window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('chat_sent');
    folioPending = true;
    folioSend.disabled = true;
    folioInput.disabled = true;

    folioLog.appendChild(h('div', { className: 'folio__msg folio__msg--user', textContent: text }));
    var status = h('div', { className: 'folio__status', role: 'status', 'aria-live': 'polite', textContent: ferryLine() });
    folioLog.appendChild(status);
    setFolioFace('thinking');
    scrollFolio();

    var history = histories[folioResident] || [];
    var requestHist = history.concat([{ role: 'user', content: text }]);

    API.chat({ message: text, history: requestHist })
      .then(function (data) {
        var reply = (data && data.reply) ? data.reply : '';
        if (status.parentNode) status.parentNode.removeChild(status);
        // chat.py answers a failed model call with a sentinel reply, not an error
        if (reply.indexOf('(draft failed') === 0) {
          setFolioFace('sleepy');
          folioLog.appendChild(h('div', { className: 'folio__error', role: 'status',
            textContent: (RESIDENTS[folioResident] || {}).name + ' can’t answer right now because no model is running. Try again later, or write it yourself.' }));
          return;
        }
        setFolioFace('happy');
        if (!reply) {
          folioLog.appendChild(h('div', { className: 'folio__error', role: 'status',
            textContent: 'That answer came back empty. Ask again, or write it yourself.' }));
          return;
        }
        histories[folioResident] = requestHist.concat([{ role: 'assistant', content: reply }]);
        saveHistories();
        var box = h('div', { className: 'folio__msg folio__msg--resident' });
        box.appendChild(h('div', { textContent: reply }));
        var keep = h('button', { className: 'folio__keep', type: 'button', textContent: 'Keep this note' });
        keep.addEventListener('click', function () {
          keep.disabled = true;
          var name = truncate(reply, 42) || 'A note from the residents';
          API.vaultKeep({ name: name, kind: 'note', bond: 'tended', lore: reply })
            .then(function () {
              studioAudio.clank();
              window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('keep');
              ferryNote('Ratatoskr is carrying \u201c' + truncate(name, 32) + '\u201d into the vault\u2026');
            })
            .catch(function () { keep.disabled = false; });
        });
        box.appendChild(keep);
        folioLog.appendChild(box);
        scrollFolio();
        maybeTeach(text);
      })
      .catch(function () {
        setFolioFace('sleepy');
        if (status.parentNode) status.parentNode.removeChild(status);
        folioLog.appendChild(h('div', { className: 'folio__error', role: 'status',
          textContent: 'Couldn’t get an answer. Your words are still here, so ask again.' }));
      })
      .finally(function () {
        folioPending = false;
        folioSend.disabled = false;
        folioInput.disabled = false;
        folioInput.value = '';
        folioInput.focus();
      });
  }

  // Escape closes the folio
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && folio && folio.classList.contains('folio--open')) {
      closeFolio(true);
    }
  });

  /* A quiet line in each room: who tends it, how to ask, and the
     room's own sound. Returns a fragment so one append gets both. */
  function residentLine(screenId) {
    // The resident now greets from the room's header (renderGreeter);
    // in the room itself only the room's quiet ambience line remains.
    var frag = document.createDocumentFragment();
    var amb = ambienceNode(screenId);
    if (amb) frag.appendChild(amb);
    return frag;
  }

  /* ══════════════════════════════════════════════════════
     THE FLOOR — every department, one door each
     ══════════════════════════════════════════════════════ */

  var DEPARTMENTS = [
    ['workshop', 'i-desk', 'Concept and pre-production: the brief, the pitch, the next beat.'],
    ['map', 'i-map', 'Level design: the town, the floors below, the roads between.'],
    ['characters', 'i-folks', 'Characters: who lives here, what they want, what they fear.'],
    ['items', 'i-vault', 'Items and economy: what you carry, and what it means.'],
    ['journal', 'i-chronicle', 'Production records: what happened, and when.'],
    ['library', 'i-library', 'Books: the studio handbook, and every book the worlds hide.'],
    ['runes', 'i-runes', 'Inspiration, for when you are stuck.'],
    ['evidence', 'i-archives', 'The story bible: the truth beneath the world.'],
    ['hall', 'i-hall', 'Launch and display: finished work on the walls.'],
    ['settings', 'i-gear', 'The machinery: the engine, the tools, the little local brain.']
  ];

  function carved(tag, cls, attrs) {
    var a = attrs || {};
    a.className = 'carved ' + (cls || '');
    return h(tag, a);
  }
  function sectionHead(label, title, id, action) {
    var head = h('div', { className: 'section-head' });
    var left = h('div');
    left.appendChild(h('span', { className: 'label', textContent: label }));
    left.appendChild(h('h2', { className: 'section-head__title', id: id, textContent: title }));
    head.appendChild(left);
    if (action) head.appendChild(action);
    return head;
  }
  function door(screenId, text, cls) {
    return h('a', { className: 'go cta ' + (cls || 'cta--line'), href: '#' + screenId, 'data-screen': screenId, textContent: text });
  }

  /* A poster for a world: drawn from its phases, never from a name */
  var PHASE_SKY = {
    dawn: ['#2A2030', '#B0704A', '#F0B862'], dusk: ['#1A1426', '#4A2E3A', '#9A5A36'],
    day: ['#1E3A4A', '#4E7A8A', '#C9D8C0'], night: ['#08131A', '#16333A', '#2A4A45']
  };
  function posterSvg(world, i) {
    var ph = (world.phases && world.phases[0]) || 'dusk';
    var sky = PHASE_SKY[ph] || PHASE_SKY.dusk;
    var gid = 'poster-sky-' + i;
    return '<svg viewBox="0 0 300 400" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
      + '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + sky[0] + '"/><stop offset=".65" stop-color="' + sky[1] + '"/><stop offset="1" stop-color="' + sky[2] + '"/></linearGradient></defs>'
      + '<rect width="300" height="400" fill="url(#' + gid + ')"/>'
      + '<g fill="#F0B862" opacity=".8"><circle cx="' + (60 + (i * 47) % 180) + '" cy="110" r="2"/><circle cx="' + (140 + (i * 31) % 120) + '" cy="80" r="1.6"/><circle cx="220" cy="140" r="1.8"/></g>'
      + '<g fill="#140E14"><path d="M20 300 L60 262 L100 300 Z"/><rect x="28" y="298" width="64" height="60"/><path d="M110 290 L160 240 L210 290 Z"/><rect x="120" y="288" width="80" height="70"/><rect x="226" y="220" width="30" height="138"/><path d="M220 222 L241 186 L262 222 Z"/><rect x="0" y="356" width="300" height="44"/></g>'
      + '<g fill="#F0B862"><rect x="150" y="310" width="10" height="14"/><rect x="50" y="318" width="8" height="12"/><circle cx="241" cy="240" r="5"/></g></svg>';
  }

  /* The Chronicle's reading rules live in js/chronicle.js (tested alone) */
  var KIND_MARKS = { rumor: 'm-quill', npc_line: 'm-speech', stefna_letter: 'm-letter', combat_action: 'm-swords' };
  var chronicleLine = window.VEFR_CHRONICLE.line;
  var foldChronicle = window.VEFR_CHRONICLE.fold;
  var actionsLine = window.VEFR_CHRONICLE.actions;

  /* The hero's night: hills, a lit town, wind, and the World Tree */
  /* The hero: the owner's World Tree key art, calm on the left for words */
  var HERO_ART = '<img class="hero__art hero__art--night" src="' + ART + 'banners/studio-hero.webp" alt="" width="2000" height="833">'
    + '<img class="hero__art hero__art--day" src="' + ART + 'banners/studio-hero-day.webp" alt="" width="1920" height="800">'
    + '<span class="hero__scrim" aria-hidden="true"></span>';

  /* ══ The studio kit ══
     What the rooms in web/js/rooms/*.js share. They load after this file and
     register themselves in `screens`; web/js/boot.js then calls S.boot(). */
  var S = window.VEFR_STUDIO = {
    AMBIENCE: AMBIENCE,
    API: API,
    ART: ART,
    DEPARTMENTS: DEPARTMENTS,
    DOOR_NOTES: DOOR_NOTES,
    HERO_ART: HERO_ART,
    KIND_MARKS: KIND_MARKS,
    RESIDENTS: RESIDENTS,
    ROOM_BANNERS: ROOM_BANNERS,
    SCREEN_DEPTS: SCREEN_DEPTS,
    SCREEN_TITLES: SCREEN_TITLES,
    actionsLine: actionsLine,
    carved: carved,
    chronicleLine: chronicleLine,
    door: door,
    emptyState: emptyState,
    esc: esc,
    ferryNote: ferryNote,
    firstWalk: firstWalk,
    foldChronicle: foldChronicle,
    formatTime: formatTime,
    h: h,
    inhabitWorld: inhabitWorld,
    loadingState: loadingState,
    main: main,
    navigate: navigate,
    openFolio: openFolio,
    portrait: portrait,
    posterSvg: posterSvg,
    residentLine: residentLine,
    screens: screens,
    sectionHead: sectionHead,
    setLantern: setLantern,
    spot: spot,
    studioAudio: studioAudio,
    truncate: truncate,
    watch: watch
  };
  Object.defineProperty(S, 'folioInput', { get: function () { return folioInput; } });

  S.boot = function () {
    window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('visit');
    /* ══════════════════════════════════════════════════════
       INIT — the room comes alive
       ══════════════════════════════════════════════════════ */

    // The shelf — a low shelf of carved placards
    document.addEventListener('click', function (e) {
      var door = e.target.closest('.go[data-screen]');
      if (!door || !screens[door.dataset.screen]) return;
      e.preventDefault();
      navigate(door.dataset.screen);
    });
    window.addEventListener('hashchange', function () {
      var id = location.hash.slice(1);
      if (screens[id]) navigate(id);
      else if (id) window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('unknown_room');
    });

    // Night by candle, or day in the hall. Separate from the contrast
    // tiers (data-theme), which keep working in either light.
    function setLight(light) {
      document.documentElement.setAttribute('data-light', light);
      var btn = document.getElementById('light-toggle');
      if (btn) {
        btn.setAttribute('aria-label', light === 'day' ? 'Switch to night' : 'Switch to day');
        btn.querySelector('use').setAttribute('href', light === 'day' ? '#i-moon' : '#i-sun');
      }
      try { localStorage.setItem('vefr-light', light); } catch (e) {}
    }
    var savedLight = null;
    try { savedLight = localStorage.getItem('vefr-light'); } catch (e) {}
    setLight(savedLight === 'day' ? 'day' : 'night');
    document.getElementById('light-toggle').addEventListener('click', function () {
      setLight(document.documentElement.getAttribute('data-light') === 'day' ? 'night' : 'day');
      window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('light_toggle');
    });

    // The world hangs its name over the door; the lantern lights
    API.world()
      .then(function (data) {
        inhabitWorld(data);
      })
      .catch(function () {
        setLantern(false, 'Storyteller offline');
      });

    // Initial route — the foyer is the door you always step through
    var initial = location.hash.slice(1) || 'launcher';
    if (!screens[initial]) initial = 'launcher';

    // The studio remembers, listens, and only sounds once asked
    loadHistories();
    startWatch();
    document.addEventListener('pointerdown', studioAudio.unlock);
    document.addEventListener('keydown', studioAudio.unlock);

    navigate(initial);

    // The house shows a first-time visitor where the doors are
    firstWalk.start();

  };
})();