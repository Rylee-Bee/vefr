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
 *
 * Every resident is the same model wearing a different face, with its
 * little toolkit of role templates. The squirrel is always watching.
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
    if (joke) joke.textContent = FOOT_JOKES[Math.floor(Math.random() * FOOT_JOKES.length)];

    // The lantern burns: the storyteller is reachable
    setLantern(true, 'the lantern burns warm');
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
    'the squirrel is ferrying that up the tree\u2026',
    'the squirrel is checking the branches\u2026',
    'the squirrel is on the way\u2026',
    'the squirrel has middens to consult\u2026'
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
    launcher:   'come in, sit by the fire',
    workshop:   'where worlds begin',
    map:        'the world laid out',
    characters: 'who lives here',
    items:      'what you\u2019ve gathered',
    journal:    'what has happened',
    runes:      'the elder futhark',
    evidence:   'descending through truth',
    hall:       'what you\u2019ve kept',
    settings:   'the boiler room'
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
    journal: 'Urðr hears everything', library: 'read everything; that is what it is for', runes: 'the stones will not flatter you',
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
    launcher: 'Welcome', floor: 'Every department', library: 'Books \u00B7 kept by Ur\u00F0r', workshop: 'Concept \u00B7 the brief',
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
      '/api/forge': 'the forge was asked',
      '/api/rumor': 'a rumor was drawn',
      '/api/npc': 'a voice spoke',
      '/api/stefna': 'a bond was traced',
      '/api/runes/cast': 'a rune was cast',
      '/api/builder/chat': 'someone asked the household',
      '/api/builder/enhance/map': 'a landmark was deepened',
      '/api/builder/enhance/item': 'a keepsake was deepened',
      '/api/builder/map/propose': 'new land was sketched',
      '/api/builder/map/check': 'a sketch was checked',
      '/api/builder/face/roll': 'a new face was invited',
      '/api/spark/task': 'the resident spark stirred'
    };
    return known[route] || 'the engine stirred';
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
    { id: 'bell', screen: 'workshop', room: 'The Desk', do: 'Ring the bell.', for: 'the house answers.' },
    { id: 'map', screen: 'map', room: 'The Map Room', do: 'Press the ground once.', for: 'the land says what it is.' },
    { id: 'chronicle', screen: 'journal', room: 'The Chronicle', do: 'Press a leaf.', for: 'what mattered stays.' },
    { id: 'folks', screen: 'characters', room: 'The Folks', do: 'Open a face.', for: 'people are doors.' },
    { id: 'hall', screen: 'hall', room: 'The Hall', do: 'Look out the window.', for: 'what you kept is waiting.' }
  ];
  var WALK_KEY = 'vefr.walk';
  var walk = { state: null, rail: null, sheet: null, sheetOpener: null, pendingGo: null, timer: null };
  function walkLoad() {
    try {
      var raw = window.localStorage && localStorage.getItem(WALK_KEY);
      walk.state = raw ? JSON.parse(raw) : null;
    } catch (e) { walk.state = null; }
    if (!walk.state) walk.state = { steps: {}, skipped: false, done: false };
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
    if (walkComplete()) walk.state.done = true;
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
      ferryNote('Ratatoskr tugs your sleeve \u2014 onward to ' + walkRoomName(go) + '\u2026');
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
    if (walk.rail) walk.rail.hidden = true;
  }
  function walkReset() {
    try { localStorage.removeItem(WALK_KEY); } catch (e) {}
    walk.state = null;
    walkStart();
  }
  function walkRender() {
    if (!walk.rail) return;
    walk.rail.innerHTML = '';
    var head = h('div', { className: 'walk-rail__head' });
    head.appendChild(h('h2', { className: 'walk-rail__title', id: 'walk-title', textContent: 'the first walk' }));
    head.appendChild(h('p', { className: 'walk-rail__byline', textContent: 'a note pinned under the sign by Ratatoskr' }));
    walk.rail.appendChild(head);

    if (walkComplete() && walk.state && walk.state.done) {
      var done = h('div', { className: 'walk-rail__done', role: 'status', 'aria-live': 'polite' });
      done.appendChild(h('p', { className: 'walk-rail__done-line', textContent: 'the house knows you now.' }));
      done.appendChild(h('p', { className: 'walk-rail__done-sub',
        textContent: 'Go gently \u2014 everything you keep stays in the rooms, and this sheet stays under Settings any time you want it back.' }));
      var acts = h('div', { className: 'walk-rail__acts' });
      var keepSheet = h('button', { className: 'walk-rail__btn', type: 'button', textContent: 'keep this sheet' });
      keepSheet.addEventListener('click', walkOpenSheet);
      var foldBtn = h('button', { className: 'walk-rail__btn walk-rail__btn--ghost', type: 'button', textContent: 'fold the note away' });
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
        textContent: 'walk me to ' + cur.step.room + ' \u2192' });
      goNow.addEventListener('click', function () {
        walk.pendingGo = null;
        navigate(cur.step.screen);
        ferryNote('Ratatoskr walks you to ' + cur.step.room + '\u2026');
      });
      walk.rail.appendChild(goNow);
    }

    var acts = h('div', { className: 'walk-rail__acts' });
    var skipBtn = h('button', { className: 'walk-rail__btn', type: 'button', textContent: 'skip \u2014 I know this house' });
    skipBtn.addEventListener('click', walkSkip);
    var sheetBtn = h('button', { className: 'walk-rail__btn walk-rail__btn--ghost', type: 'button', textContent: 'how to read this house' });
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
    paper.appendChild(h('h2', { id: 'sheet-title', textContent: 'How to read this house' }));
    paper.appendChild(h('p', { className: 'sheet__byline',
      textContent: 'a broadsheet from Ratatoskr \u2014 one room, one thing to try' }));
    var rooms = [
      ['The Desk', 'where the Storyteller works. Ring the bell; ask what to build.'],
      ['The Map Room', 'where the Cartographer keeps the land. Press the ground; keep a sketch.'],
      ['The Folks', 'where the Keeper of Faces keeps the people. Meet a face; invite a new one.'],
      ['The Chronicle', 'where Ur\u00F0r writes what happened. Press a leaf; keep what mattered.'],
      ['The Hall', 'what Ratatoskr carried up. Look out the window; keep what you love.'],
      ['The Vault', 'where the Hoard-Keeper keeps your hoard. Deepen a keepsake.'],
      ['The Casting Room', 'where the Rune-Carver cuts the runes. Cast one; let it be.'],
      ['The Archives', 'where Skuld shelves the stories. Browse the evidence.'],
      ['The Boiler Room', 'the Settings. Plain pipes; sound, light, and motion live here.']
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
      textContent: 'three rules of the house \u2014 every mark is yours; nothing is invented; the engine checks the ground before anything is kept.' }));
    var close = h('button', { className: 'sheet__close', type: 'button', textContent: 'close the sheet' });
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
    who.appendChild(h('p', { className: 'greeter__says', textContent: '\u201C' + greetingFor(id) + '\u201D' }));
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
    evidence: 'skuld', settings: 'volundr', spark: 'bolt', library: 'urdr'
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
      name: 'Ur\u00F0r', mark: '\u2767',
      craft: 'keeper of the Library',
      greeting: 'Read everything. That is what it is for.',
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
      + '<div class="folio__log" id="folio-log" aria-live="polite"></div>'
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
      histories[folioResident] = [];
      saveHistories();
      openFolio(folioResident, folioOpener);
    });

    room.appendChild(folio);
  }

  function openFolio(screenId, opener) {
    var resident = RESIDENTS[screenId];
    if (!resident) return;
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
      ferryNote('Ratatoskr tugs your sleeve \u2014 onward to ' + walkRoomName(go) + '\u2026');
    }
  }

  function folioSendMessage() {
    if (!folioResident || folioPending) return;
    var text = folioInput.value.trim();
    if (!text) return;

    folioPending = true;
    folioSend.disabled = true;
    folioInput.disabled = true;

    folioLog.appendChild(h('div', { className: 'folio__msg folio__msg--user', textContent: text }));
    var status = h('div', { className: 'folio__status', role: 'status', 'aria-live': 'polite', textContent: ferryLine() });
    folioLog.appendChild(status);
    setFolioFace('thinking');
    folioLog.scrollTop = folioLog.scrollHeight;

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
            textContent: (RESIDENTS[folioResident] || {}).name + ' is napping: no model is answering right now. Ask again later, or keep your own words.' }));
          return;
        }
        setFolioFace('happy');
        if (!reply) {
          folioLog.appendChild(h('div', { className: 'folio__error', role: 'status',
            textContent: 'The resident drew nothing usable \u2014 ask again, or keep your own words.' }));
          return;
        }
        histories[folioResident] = requestHist.concat([{ role: 'assistant', content: reply }]);
        saveHistories();
        var box = h('div', { className: 'folio__msg folio__msg--resident' });
        box.appendChild(h('div', { textContent: reply }));
        var keep = h('button', { className: 'folio__keep', type: 'button', textContent: 'keep this note' });
        keep.addEventListener('click', function () {
          keep.disabled = true;
          var name = truncate(reply, 42) || 'a note from the household';
          API.vaultKeep({ name: name, kind: 'note', bond: 'tended', lore: reply })
            .then(function () {
              studioAudio.clank();
              ferryNote('Ratatoskr is carrying \u201c' + truncate(name, 32) + '\u201d into the vault\u2026');
            })
            .catch(function () { keep.disabled = false; });
        });
        box.appendChild(keep);
        folioLog.appendChild(box);
        folioLog.scrollTop = folioLog.scrollHeight;
      })
      .catch(function () {
        setFolioFace('sleepy');
        if (status.parentNode) status.parentNode.removeChild(status);
        folioLog.appendChild(h('div', { className: 'folio__error', role: 'status',
          textContent: 'The resident couldn\u2019t reach you just now. Your words are still on the page \u2014 ask again.' }));
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

  screens.floor = (function () {
    var el_screen;
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-floor' });
      main.appendChild(el_screen);
    }
    function enter() {
      el_screen.innerHTML = '';
      var wrap = h('div', { className: 'wrap band floor-room' });
      var cut = h('figure', { className: 'carved floor-cutaway' });
      cut.appendChild(h('img', { src: ART + 'illustrations/floor-cutaway.webp', width: '1400', height: '933', loading: 'lazy',
        alt: 'The World Tree cut open like a dollhouse: a desk and a portrait gallery near the top, a map room and a library on the right, a vault and a spiral staircase in the trunk, a table of rune stones, an archive, and a boiler room among the roots.' }));
      cut.appendChild(h('figcaption', { textContent: 'The studio, cut open. Every door below leads into one of these rooms.' }));
      wrap.appendChild(cut);
      var grid = h('div', { className: 'floor-grid' });
      DEPARTMENTS.forEach(function (d) {
        var r = RESIDENTS[d[0]] || {};
        var card = carved('a', 'dept go', { href: '#' + d[0], 'data-screen': d[0] });
        card.appendChild(h('img', { className: 'dept__emblem', src: ART + 'emblems/' + (ROOM_BANNERS[d[0]] || 'hall') + '.svg',
          alt: '', 'aria-hidden': 'true', width: '64', height: '64' }));
        card.appendChild(h('h3', { className: 'dept__name', textContent: SCREEN_TITLES[d[0]] || d[0] }));
        card.appendChild(h('span', { className: 'dept__who', textContent: r.name || '' }));
        card.appendChild(h('p', { className: 'dept__what', textContent: d[2] }));
        if (DOOR_NOTES[d[0]]) card.appendChild(h('span', { className: 'door-note', textContent: DOOR_NOTES[d[0]] }));
        grid.appendChild(card);
      });
      wrap.appendChild(grid);
      el_screen.appendChild(wrap);
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();

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

  /* ══════════════════════════════════════════════════════
     THE DESK — the writing desk where worlds are made
     ══════════════════════════════════════════════════════ */

  screens.launcher = (function () {
    // The foyer — the first room you step into. A launcher like a
    // game's: the project on the table, every other pack in the
    // pantry, what the house remembers, and the quick options at
    // the mantel. Everything is real — packs from /api/builder/worlds,
    // keepsakes from the vault, stars from the journal, threads the
    // house has already heard. Nothing is invented.
    var el_screen;
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-launcher' });
      main.appendChild(el_screen);
    }
    function enter() {
      // The studio's front page: what is on the table, every world on
      // the walls, how the studio works, the latest from the Chronicle,
      // and the residents. Everything is real data; nothing is invented.
      el_screen.innerHTML = '<div class="studio-home" id="foyer-content"></div>';
      var c = el_screen.querySelector('#foyer-content');

      var hearth = h('div', { className: 'foyer-hearth' });
      hearth.appendChild(h('div', { className: 'foyer-holder' }));
      c.appendChild(hearth);

      var games = h('div', { className: 'wrap band' });
      var pantry = h('section', { className: 'foyer-pantry', 'aria-labelledby': 'home-games' });
      pantry.appendChild(sectionHead('Our worlds', 'On the walls', 'home-games', door('floor', 'Walk the floor')));
      var holder = h('div', { className: 'foyer-holder' });
      holder.appendChild(loadingState('the studio is looking\u2026'));
      pantry.appendChild(holder);
      games.appendChild(pantry);
      c.appendChild(games);

      var creed = h('section', { className: 'creed-band', 'aria-label': 'How the studio works', id: 'home-creed' });
      c.appendChild(creed);

      var two = h('div', { className: 'wrap band home-two' });
      var news = h('section', { 'aria-labelledby': 'home-news' });
      news.appendChild(sectionHead('From the Chronicle', 'Latest from the studio', 'home-news', door('journal', 'All news')));
      var newsList = h('div', { className: 'news-list' });
      newsList.appendChild(loadingState('Urðr is turning the pages\u2026'));
      news.appendChild(newsList);
      var begin = h('section', { 'aria-labelledby': 'home-begin' });
      begin.appendChild(sectionHead('New project', 'Begin a new world', 'home-begin'));
      var beginCard = carved('div', 'begin-card');
      beginCard.appendChild(beginWorldForm(hearth, pantry));
      begin.appendChild(beginCard);
      two.appendChild(news);
      two.appendChild(begin);
      c.appendChild(two);

      var team = h('section', { className: 'wrap band', 'aria-labelledby': 'home-team' });
      team.appendChild(sectionHead('The team', 'Meet the residents', 'home-team', door('floor', 'Every department')));
      team.appendChild(h('img', { className: 'team-photo', src: ART + 'illustrations/team-photo.webp', width: 1600, height: 1000, loading: 'lazy',
        alt: 'All ten residents together on a branch of the World Tree, smiling for a group photo.' }));
      team.appendChild(teamGrid());
      c.appendChild(team);

      var mantel = h('div', { className: 'wrap band band--last' });
      mantel.appendChild(optionsPanel());
      c.appendChild(mantel);

      loadProjects(hearth, pantry);
      API.journal()
        .then(function (data) { renderNews(newsList, (data && data.entries) || []); })
        .catch(function () {
          newsList.innerHTML = '';
          newsList.appendChild(emptyState('the Chronicle is closed right now', 'try again in a moment'));
        });
    }

    function renderNews(list, entries) {
      list.innerHTML = '';
      var folded = foldChronicle(entries).reverse().slice(0, 3);
      if (!folded.length) {
        list.appendChild(emptyState('nothing has happened yet', 'every story leaves traces'));
        return;
      }
      folded.forEach(function (f, i) {
        var line = f.kind === 'combat_action' ? actionsLine(f) : chronicleLine(f.entry);
        var post = carved('a', 'post go' + (i === 0 ? ' post--lead' : ''), { href: '#journal', 'data-screen': 'journal' });
        post.appendChild(h('span', { className: 'post__date', textContent: formatTime(f.at) + ' \u00B7 ' + line.kind }));
        post.appendChild(h('p', { className: 'post__text', textContent: truncate(line.text || '', 180) }));
        if (line.who) post.appendChild(h('span', { className: 'post__who', textContent: '\u2014 ' + line.who }));
        list.appendChild(post);
      });
    }

    function teamGrid() {
      var grid = h('div', { className: 'team-grid' });
      ['hall', 'workshop', 'journal', 'map', 'characters', 'items', 'runes', 'evidence', 'settings'].forEach(function (id) {
        var r = RESIDENTS[id];
        if (!r) return;
        var card = carved('a', 'member go', { href: '#' + id, 'data-screen': id });
        card.appendChild(portrait(id, r, 'member__portrait'));
        card.appendChild(h('h3', { className: 'member__name', textContent: r.name }));
        card.appendChild(h('span', { className: 'member__role', textContent: (SCREEN_DEPTS[id] || '') + ' \u00B7 ' + (SCREEN_TITLES[id] || '') }));
        card.appendChild(h('p', { className: 'member__craft', textContent: r.craft }));
        grid.appendChild(card);
      });
      return grid;
    }

    function loadProjects(hearth, pantry) {
      Promise.all([API.world(), API.builderWorlds()])
        .then(function (rs) { renderProjects(hearth, pantry, rs[0], (rs[1] && rs[1].worlds) || []); })
        .catch(function () {
          setSection(hearth, emptyState('the house can’t find the project right now', 'check that the house is running'));
          setSection(pantry, emptyState('the shelves wouldn’t open', 'try again in a moment'));
        });
    }

    /* The launcher's front door for a phone with no terminal: name,
       title, one-line premise, and the engine does the rest. This is
       the page's twin of `norns chat` - the same scaffold copy, the
       same world.json fields. The name is the folder id; the server
       owns the path and refuses anything that isn't a bare pack name. */
    function beginWorldForm(hearth, pantry) {
      var form = h('form', { className: 'world-begin', id: 'begin-world-form' });
      form.setAttribute('novalidate', 'novalidate');
      form.appendChild(field('begin-world-name', 'Name',
        'a short id for the folder — letters, numbers, dashes, underscores',
        'quiet-town', '^[A-Za-z0-9][A-Za-z0-9_-]*$'));
      form.appendChild(field('begin-world-title', 'Title',
        'what you call it in play', 'The name of your world', null));
      form.appendChild(field('begin-world-premise', 'Premise',
        'one line — the story under everything', 'A town keeps a quiet secret', null));

      var create = h('button', { className: 'btn btn--primary world-begin__submit',
        type: 'submit', textContent: 'Create' });
      form.appendChild(create);

      var status = h('p', { className: 'world-begin__status', id: 'begin-world-status',
        role: 'status', 'aria-live': 'polite' });
      form.appendChild(status);

      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var nameEl = form.querySelector('#begin-world-name');
        var name = nameEl.value.trim();
        var title = form.querySelector('#begin-world-title').value.trim();
        var premise = form.querySelector('#begin-world-premise').value.trim();
        if (!name) {
          status.textContent = 'a world needs a name before it can begin.';
          nameEl.focus();
          return;
        }
        create.disabled = true;
        status.textContent = 'the house is clearing a table for “' + name + '”…';
        API.createWorld({ name: name, title: title || null, premise: premise || null })
          .then(function (created) {
            status.textContent = 'the world “' + (created.title || name) + '” is on the table.';
            navigate('workshop');
          })
          .catch(function (err) {
            var code = String((err && err.message) || '');
            if (code.indexOf('409') === 0) {
              status.textContent = 'a world by that name already lives here — try another.';
            } else if (code.indexOf('400') === 0) {
              status.textContent = 'names are letters, numbers, dashes, underscores — no spaces or slashes.';
            } else {
              status.textContent = 'the house couldn’t start that world just now — try again.';
            }
            create.disabled = false;
            nameEl.focus();
          });
      });
      return form;
    }

    function field(id, label, hint, placeholder, pattern) {
      var wrap = h('div', { className: 'world-begin__field' });
      var hintId = id + '-hint';
      wrap.appendChild(h('label', { className: 'world-begin__label', 'for': id, textContent: label }));
      var input = h('input', { className: 'world-begin__input', id: id, name: id, type: 'text',
        placeholder: placeholder, 'aria-describedby': hintId, autocomplete: 'off' });
      if (pattern) input.setAttribute('pattern', pattern);
      wrap.appendChild(input);
      wrap.appendChild(h('span', { className: 'world-begin__hint', id: hintId, textContent: hint }));
      return wrap;
    }

    /* Put an existing pack on the table: the web twin of setting
       VEFR_WORLD, no restart. Keeps the current room steady while
       the house re-reads the world it now serves. */
    function makeActive(name, btn, hearth, pantry) {
      var label = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'setting the table…';
      API.setActiveWorld({ name: name })
        .then(function () { return API.world(); })
        .then(function (w) {
          inhabitWorld(w);
          ferryNote('the table is set for “' + name + '”.');
          loadProjects(hearth, pantry);
        })
        .catch(function () {
          btn.disabled = false;
          btn.textContent = label;
          ferryNote('the house couldn’t set that table — try again.');
        });
    }

    function section(c, cls, title) {
      var id = 'foyer-' + cls.replace('foyer-', '');
      var s = h('section', { className: cls, 'aria-labelledby': id });
      s.appendChild(h('h2', { className: 'foyer-h2', id: id, textContent: title }));
      var holder = h('div', { className: 'foyer-holder' });
      holder.appendChild(loadingState('the house is looking\u2026'));
      s.appendChild(holder);
      c.appendChild(s);
      return s;
    }
    function setSection(s, node) {
      var holder = s.querySelector('.foyer-holder');
      if (!holder) return;
      holder.innerHTML = '';
      holder.appendChild(node);
    }

    function renderProjects(hearth, pantry, w, packs) {
      var currentName = null;
      if (w && w.title) {
        packs.forEach(function (p) {
          if (currentName === null && p.title === w.title) currentName = p.name;
        });
      }
      setSection(hearth, projectTable(w));
      setSection(pantry, pantryGrid(packs, currentName, hearth, pantry));
    }
    function projectTable(w) {
      if (!w || !w.title) return emptyState('the studio doesn\u2019t know its project yet', 'check that a world is mounted');
      var hero = h('section', { className: 'hero', 'aria-labelledby': 'hero-title' });
      hero.innerHTML = HERO_ART;
      var copy = h('div', { className: 'wrap hero__copy' });
      copy.appendChild(h('span', { className: 'hero__kicker', textContent: 'On the table \u00B7 in development' }));
      copy.appendChild(h('h2', { className: 'hero__title', id: 'hero-title', textContent: w.title }));
      if (w.creed) copy.appendChild(h('p', { className: 'hero__creed', textContent: w.creed }));
      var facts = h('div', { className: 'hero__facts' });
      var bits = [];
      if (w.act && w.act.title && w.act.title !== w.title) bits.push(w.act.title);
      if (w.phases && w.phases.length) bits.push(w.phases.join(' \u00B7 '));
      if (w.act && w.act.ruleset) bits.push(w.act.ruleset);
      bits.forEach(function (b) { facts.appendChild(h('span', { className: 'hero__fact', textContent: b })); });
      copy.appendChild(facts);
      var actions = h('div', { className: 'hero__actions' });
      actions.appendChild(door('workshop', 'Open the Desk', 'cta--gold'));
      actions.appendChild(door('floor', 'Walk the floor', 'cta--ghost'));
      copy.appendChild(actions);
      hero.appendChild(copy);
      var band = document.getElementById('home-creed');
      if (band) {
        band.innerHTML = '';
        var inner = h('div', { className: 'wrap creed-band__row' });
        [[w.creed || 'Walk gently.', 'carved above the door'],
         ['Every sitting ends with something alive.', 'how the studio works'],
         ['You write the stories. The studio builds the halls.', 'who does what']].forEach(function (l) {
          var d = h('div', { className: 'creed-band__line' });
          d.appendChild(h('b', { textContent: l[0] }));
          d.appendChild(h('small', { textContent: l[1] }));
          inner.appendChild(d);
        });
        band.appendChild(inner);
      }
      return hero;
    }
    function pantryGrid(packs, currentName, hearth, pantry) {
      if (!packs.length) return emptyState('no worlds on the walls yet', 'begin a new world below');
      var wrap = h('div', { className: 'poster-grid' });
      packs.forEach(function (p, i) {
        var current = p.name === currentName;
        var card = carved('article', 'poster');
        var key = h('div', { className: 'poster__key' });
        key.innerHTML = posterSvg(p, i);
        key.appendChild(h('h3', { className: 'poster__title', textContent: p.title || p.name }));
        if (current) {
          var seal = h('span', { className: 'wax-seal', 'aria-hidden': 'true' });
          seal.innerHTML = '<img src="' + ART + 'wax-seal.webp" alt="" width="64" height="64">';
          key.appendChild(seal);
        }
        card.appendChild(key);
        var body = h('div', { className: 'poster__body' });
        body.appendChild(h('span', { className: 'status' + (current ? ' status--now' : ''), textContent: current ? 'On the table' : 'On the wall' }));
        var bits = [];
        if (p.phases && p.phases.length) bits.push(p.phases.join(' \u00B7 '));
        if (p.speakers) bits.push(p.speakers.length + ' speaker' + (p.speakers.length !== 1 ? 's' : ''));
        if (bits.length) body.appendChild(h('p', { className: 'poster__meta', textContent: bits.join(' \u00B7 ') }));
        if (current) {
          body.appendChild(door('workshop', 'Open the Desk', 'cta--line'));
        } else {
          var put = h('button', { className: 'cta cta--line', type: 'button', textContent: 'Put on the table' });
          put.addEventListener('click', function () { makeActive(p.name, put, hearth, pantry); });
          body.appendChild(put);
        }
        card.appendChild(body);
        wrap.appendChild(card);
      });
      return wrap;
    }

    function optionsPanel() {
      // Quick options at the mantel — the same contracts the boiler
      // room owns: sound and motion via VEFR_PREFS, the walk and the
      // sheet via the first walk, the rest by walking through doors.
      var P = window.VEFR_PREFS;
      var current = (P && P.get) ? P.get() : {};
      var panel = h('section', { className: 'foyer-options', 'aria-labelledby': 'foyer-options-title' });
      panel.appendChild(h('h2', { className: 'foyer-h2', id: 'foyer-options-title', textContent: 'At the mantel' }));
      var optCard = h('div', { className: 'settings-card' });

      var soundRow = h('div', { className: 'settings-row' });
      soundRow.appendChild(h('span', { className: 'settings-row__label', textContent: 'Hearth sound' }));
      var soundOpts = h('div', { className: 'settings-row__options' });
      var snd = current.sound || {};
      var soundOn = (snd.effects || 0) > 0 || (snd.ambience || 0) > 0;
      [{ label: 'Off', on: false }, { label: 'On', on: true }].forEach(function (o) {
        var b = h('button', { className: 'settings-option' + (soundOn === o.on ? ' settings-option--active' : ''), textContent: o.label });
        b.addEventListener('click', function () {
          if (P && P.set) {
            P.set({ sound: o.on ? { effects: 0.7, ambience: 0.5, speech: 0.8 } : { effects: 0, ambience: 0, speech: 0 } });
          }
          soundOpts.querySelectorAll('.settings-option').forEach(function (x) { x.classList.remove('settings-option--active'); });
          b.classList.add('settings-option--active');
          if (o.on && studioAudio) { studioAudio.unlock(); studioAudio.ambient(true); }
          if (!o.on && studioAudio) studioAudio.ambient(false);
        });
        soundOpts.appendChild(b);
      });
      soundRow.appendChild(soundOpts);
      optCard.appendChild(soundRow);

      var motRow = h('div', { className: 'settings-row' });
      motRow.appendChild(h('span', { className: 'settings-row__label', textContent: 'Motion' }));
      var motOpts = h('div', { className: 'settings-row__options' });
      [{ label: 'Off', value: 'off' }, { label: 'Subtle', value: 'subtle' }, { label: 'Full', value: 'full' }].forEach(function (o) {
        var b = h('button', { className: 'settings-option' + ((current.motion || 'off') === o.value ? ' settings-option--active' : ''), textContent: o.label });
        b.addEventListener('click', function () {
          if (P && P.set) P.set({ motion: o.value });
          motOpts.querySelectorAll('.settings-option').forEach(function (x) { x.classList.remove('settings-option--active'); });
          b.classList.add('settings-option--active');
        });
        motOpts.appendChild(b);
      });
      motRow.appendChild(motOpts);
      optCard.appendChild(motRow);

      var doorsRow = h('div', { className: 'settings-row' });
      doorsRow.appendChild(h('span', { className: 'settings-row__label', textContent: 'Doorways' }));
      var doorOpts = h('div', { className: 'settings-row__options' });
      var walkBtn = h('button', { className: 'btn btn--warm settings-row__btn', type: 'button', textContent: 'walk the house again' });
      walkBtn.addEventListener('click', function () { if (firstWalk) firstWalk.reset(); });
      var sheetBtn = h('button', { className: 'btn btn--warm settings-row__btn', type: 'button', textContent: 'how to read this house' });
      sheetBtn.addEventListener('click', function () { if (firstWalk) firstWalk.openSheet(); });
      var boilerBtn = h('button', { className: 'btn btn--ghost settings-row__btn', type: 'button', textContent: 'the boiler room \u2192' });
      boilerBtn.addEventListener('click', function () { navigate('settings'); });
      doorOpts.appendChild(walkBtn);
      doorOpts.appendChild(sheetBtn);
      doorOpts.appendChild(boilerBtn);
      doorsRow.appendChild(doorOpts);
      optCard.appendChild(doorsRow);

      panel.appendChild(optCard);
      return panel;
    }

    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();

  screens.workshop = (function () {
    var el_screen, world = null, journal = [], lastWoven = null;

    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-workshop' });
      el_screen.innerHTML = ''
        + '<div class="wrap band workshop">'
        + '  <div class="workshop__story">'
        + '    <article class="carved desk-sheet">'
        + '      <img class="spot spot--right" src="/static/art/poses/storyteller-quill-notebook.webp" alt="" aria-hidden="true" width="180" height="180">'
        + '      <div class="workshop__story-header">'
        + '        <span class="label">The brief \u00B7 on the table</span>'
        + '        <h2 class="workshop__chapter" id="ws-chapter"></h2>'
        + '        <div class="workshop__meta" id="ws-meta"></div>'
        + '      </div>'
        + '      <div class="workshop__body"><div class="workshop__content" id="ws-content"></div></div>'
        + '    </article>'
        + '    <div class="carved desk-tools workshop__footer" role="group" aria-label="Desk tools">'
        + '      <div class="desk-tools__row">'
        + '        <button class="cta cta--gold" id="ws-bell" type="button">Ring for the Storyteller</button>'
        + '        <button class="cta cta--line" id="ws-continue" type="button" aria-label="Continue the story">What happens next?</button>'
        + '        <button class="cta cta--line" id="ws-toggle-ctx" type="button" aria-expanded="true" aria-label="Show or hide the notes">Notes</button>'
        + '      </div>'
        + '      <div class="desk-tools__row desk-tools__weave">'
        + '        <button class="cta cta--line" id="ws-weave" type="button" aria-describedby="ws-weave-status">Make shareable file</button>'
        + '        <span class="weave-status" id="ws-weave-status" role="status" aria-live="polite"></span>'
        + '        <a class="cta cta--line weave-action" id="ws-weave-download" download hidden>Download</a>'
        + '        <button class="cta cta--line weave-action" id="ws-weave-share" type="button" hidden>Share</button>'
        + '      </div>'
        + '      <p class="desk-tools__hint">One file, plays offline, no install. Send it to a friend.</p>'
        + '    </div>'
        + '  </div>'
        + '  <aside class="workshop__context" id="ws-context" role="complementary" aria-label="What the world knows">'
        + '    <section class="carved context__section">'
        + '      <h3 class="context__heading">What the world knows</h3>'
        + '      <div id="ws-ctx-items"></div>'
        + '    </section>'
        + '    <section class="carved context__section">'
        + '      <h3 class="context__heading">Recent</h3>'
        + '      <div id="ws-ctx-recent"></div>'
        + '      <a class="go context__more" href="#journal" data-screen="journal">The whole Chronicle \u2192</a>'
        + '    </section>'
        + '    <button class="carved context__link" id="ws-evidence" type="button">'
        + '      <span class="label">The story bible</span><span>Descend into the archives \u2192</span>'
        + '      <span class="door-note">watch the third step</span>'
        + '    </button>'
        + '  </aside>'
        + '</div>';

      el_screen.querySelector('#ws-bell').addEventListener('click', function (e) {
        firstWalk.attempt('bell');
        openFolio('workshop', e.currentTarget);
      });
      el_screen.querySelector('#ws-continue').addEventListener('click', continueStory);
      el_screen.querySelector('#ws-toggle-ctx').addEventListener('click', toggleContext);
      el_screen.querySelector('#ws-weave').addEventListener('click', makeShareable);
      el_screen.querySelector('#ws-weave-share').addEventListener('click', shareWoven);
      el_screen.querySelector('#ws-evidence').addEventListener('click', function () { navigate('evidence'); });
      main.appendChild(el_screen);
    }

    function enter() { load(); }
    function leave() {}

    function load() {
      setContent(loadingState('The storyteller is considering it\u2026'));
      Promise.all([API.world(), API.journal().catch(function () { return { entries: [] }; })])
        .then(function (results) {
          world = results[0];
          journal = Array.isArray(results[1]) ? results[1] : (results[1].entries || []);
          render();
          inhabitWorld(world);
        })
        .catch(function () {
          world = null;
          journal = [];
          render();
          setLantern(false, 'the storyteller can\u2019t be reached');
        });
    }

    function render() {
      renderChapter();
      renderContent();
      renderMeta();
      renderContextItems();
      renderRecent();
    }

    function renderChapter() {
      var ch = el_screen.querySelector('#ws-chapter');
      if (!world) { ch.textContent = ''; return; }
      var act = world.act;
      ch.textContent = (act && typeof act === 'object') ? act.title : (act || world.title || '');
    }

    function renderMeta() {
      var m = el_screen.querySelector('#ws-meta');
      if (!world) { m.innerHTML = ''; return; }
      var parts = [];
      if (world.surface) parts.push('<span>' + esc(world.surface) + '</span>');
      if (world.phases && world.phases.length) parts.push('<span>' + esc(world.phases.join(' \u00b7 ')) + '</span>');
      m.innerHTML = parts.join('');
    }

    function renderContent() {
      var c = el_screen.querySelector('#ws-content');
      if (!world) {
        c.innerHTML = '';
        c.appendChild(emptyState(
          'The world is quiet.\nThat\u2019s not the same as empty.',
          'Continue the story to see what happens.',
          true
        ));
        return;
      }

      var parts = [];

      // The room's quiet sound — pinned at the top of the desk
      parts.push('<p class="room-ambience">' + esc(AMBIENCE.workshop) + '</p>');
      parts.push('<p class="desk-hint">This is the brief everything else follows. The Storyteller keeps it open; the words are yours.</p>');

      // The creed — cast in brass above the desk
      if (world.creed) {
        parts.push('<p class="workshop__creed">' + esc(world.creed) + '</p>');
      }

      // The map — a scrap pinned to the desk
      if (world.map && world.map.length) {
        parts.push('<div class="workshop__map">' + esc(world.map.join('\n')) + '</div>');
      }

      // Status — the instruments on the desk
      if (world.phases || world.hp) {
        parts.push('<div class="workshop__status">');
        if (world.phases && world.phases.length) {
          parts.push('<div class="workshop__status-item">'
            + '<span class="workshop__status-label">The world turns between</span>'
            + '<span class="workshop__status-value">' + esc(world.phases.join(' and ')) + '</span>'
            + '</div>');
        }
        if (world.hp) {
          var hearts = '';
          for (var i = 0; i < world.hp.max; i++) {
            hearts += i < world.hp.current ? '\u2764\uFE0F' : '\u{1F90D}';
          }
          parts.push('<div class="workshop__status-item">'
            + '<span class="workshop__status-label">Hearts</span>'
            + '<span class="workshop__status-value">' + world.hp.current + ' of ' + world.hp.max
            + ' <span class="workshop__status-hearts" aria-hidden="true">' + hearts + '</span></span>'
            + '</div>');
        }
        parts.push('</div>');
      }

      c.innerHTML = parts.join('\n');
    }

    function renderContextItems() {
      var container = el_screen.querySelector('#ws-ctx-items');
      if (!world) {
        container.innerHTML = '<div class="context__empty">The world is quiet.</div>';
        return;
      }
      var items = [];
      if (world.phases && world.phases.length)
        items.push({ label: 'Phases', value: world.phases.join(', ') });
      if (world.surface)
        items.push({ label: 'Surface', value: world.surface });
      if (world.creed)
        items.push({ label: 'Creed', value: world.creed });
      if (world.hp)
        items.push({ label: 'HP', value: world.hp.current + '/' + world.hp.max });

      if (!items.length) {
        container.innerHTML = '<div class="context__empty">The world is quiet.</div>';
        return;
      }
      container.innerHTML = items.map(function (item) {
        return '<div class="context__item">'
          + '<span class="context__item-label">' + esc(item.label) + '</span>'
          + '<span class="context__item-value">' + esc(item.value) + '</span>'
          + '</div>';
      }).join('');
    }

    function renderRecent() {
      var container = el_screen.querySelector('#ws-ctx-recent');
      if (!journal.length) {
        container.innerHTML = '<div class="context__empty">Nothing yet. The chronicle is waiting.</div>';
        return;
      }
      container.innerHTML = foldChronicle(journal).slice(-5).reverse().map(function (f) {
        var line = f.kind === 'combat_action' ? actionsLine(f) : chronicleLine(f.entry);
        return '<div class="context__event">'
          + '<span class="context__event-time">' + esc(formatTime(f.at)) + ' \u00B7 ' + esc(line.kind) + '</span>'
          + '<span class="context__event-text">' + esc(truncate(line.text || '', 90)) + '</span>'
          + '</div>';
      }).join('');
    }

    function setContent(node) {
      var c = el_screen.querySelector('#ws-content');
      c.innerHTML = '';
      c.appendChild(node);
    }

    function continueStory() {
      var btn = el_screen.querySelector('#ws-continue');
      btn.disabled = true;
      btn.textContent = 'the storyteller is considering it\u2026';
      API.rumor()
        .then(function () { load(); })
        .catch(function (err) { console.error('[desk] rumor failed:', err); })
        .finally(function () {
          btn.disabled = false;
          btn.textContent = 'What happens next?';
        });
    }

    function toggleContext() {
      var btn = el_screen.querySelector('#ws-toggle-ctx');
      var ctx = el_screen.querySelector('#ws-context');
      var open = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', String(!open));
      ctx.style.display = open ? 'none' : '';
      el_screen.querySelector('.workshop').classList.toggle('workshop--no-context', open);
    }

    /* ── The shareable file — weave the world into one HTML ── */
    function sizeWords(bytes) {
      if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
      if (bytes >= 1024) return Math.round(bytes / 1024) + ' KB';
      return bytes + ' B';
    }

    function setWeaveStatus(text) {
      var s = el_screen.querySelector('#ws-weave-status');
      if (s) s.textContent = text || '';
    }

    function canShareFiles() {
      if (!navigator.canShare || !navigator.share || typeof File === 'undefined') return false;
      try {
        return navigator.canShare({ files: [new File(['x'], 'world.html', { type: 'text/html' })] });
      } catch (err) {
        return false;
      }
    }

    function makeShareable() {
      var btn = el_screen.querySelector('#ws-weave');
      var dl = el_screen.querySelector('#ws-weave-download');
      var share = el_screen.querySelector('#ws-weave-share');
      btn.disabled = true;
      dl.hidden = true;
      share.hidden = true;
      setWeaveStatus('Weaving…');
      API.weaveBuild()
        .then(function (info) {
          lastWoven = info;
          dl.href = info.download_url;
          dl.setAttribute('download', info.name);
          dl.hidden = false;
          share.hidden = !canShareFiles();
          setWeaveStatus('Ready · ' + sizeWords(info.size_bytes));
        })
        .catch(function (err) {
          lastWoven = null;
          setWeaveStatus('The weave failed. ' + (err && err.message ? err.message : 'Try again.'));
        })
        .finally(function () {
          btn.disabled = false;
        });
    }

    function shareWoven() {
      if (!lastWoven) return;
      var share = el_screen.querySelector('#ws-weave-share');
      share.disabled = true;
      setWeaveStatus('Preparing the file…');
      fetch(lastWoven.download_url)
        .then(function (r) {
          if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
          return r.blob();
        })
        .then(function (blob) {
          var file = new File([blob], lastWoven.name, { type: 'text/html' });
          return navigator.share({
            files: [file],
            title: 'A world to keep',
            text: 'Open this file and play.'
          });
        })
        .then(function () {
          setWeaveStatus('Ready · ' + sizeWords(lastWoven.size_bytes));
        })
        .catch(function (err) {
          if (err && err.name === 'AbortError') {
            setWeaveStatus('Ready · ' + sizeWords(lastWoven.size_bytes));
            return;
          }
          setWeaveStatus('Could not share. Download instead.');
        })
        .finally(function () {
          share.disabled = false;
        });
    }

    return { init: init, enter: enter, leave: leave };
  })();

  /* ══════════════════════════════════════════════════════
     THE MAP ROOM — spatial, the world laid out
     ══════════════════════════════════════════════════════ */

  screens.map = (function () {
    var el_screen;
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-map' });
      main.appendChild(el_screen);
    }
    function enter() {
      el_screen.innerHTML = '<div class="wrap band map-room" id="map-content"></div>';
      var container = el_screen.querySelector('#map-content');
      container.appendChild(loadingState('The map is drawing itself\u2026'));

      Promise.all([
        API.world().catch(function () { return null; }),
        API.validate().catch(function () { return { ok: false, errors: ['the pack won\u2019t answer'] }; })
      ]).then(function (results) {
        var data = results[0];
        var packCheck = results[1];
        container.innerHTML = '';
        if (!data) {
          container.appendChild(emptyState(
            'Couldn\u2019t reach the map room.',
            'The world might not be ready yet.'
          ));
          return;
        }
        var rl = residentLine('map');
        if (rl) container.appendChild(rl);

        var regions = data.regions || {};
        var names = Object.keys(regions);
        if (!names.length) {
          container.appendChild(emptyState(
            'The map is blank.\nBut every world starts somewhere.',
            'Regions appear as you explore.',
            true
          ));
          return;
        }

        var bench = h('div', { className: 'map-bench' });
        var wrap = h('div', { className: 'map-regions' });
        names.forEach(function (name) { wrap.appendChild(regionCard(name, regions[name])); });
        bench.appendChild(wrap);
        bench.appendChild(packCheckRow(packCheck));
        container.appendChild(bench);
        container.appendChild(drawingTable(data));
      });
    }

    /* The survey — real numbers read off the map itself */
    function surveyOf(mapText) {
      var rows = mapText.length;
      var cols = 0;
      var census = {};
      mapText.forEach(function (ln) {
        if (ln.length > cols) cols = ln.length;
        ln.split('').forEach(function (ch) {
          if (ch === ' ' || ch === '\n' || ch === '\r') return;
          census[ch] = (census[ch] || 0) + 1;
        });
      });
      return { rows: rows, cols: cols, census: census };
    }

    function regionCard(name, region) {
      var mapText = (region && region.map_text) || [];
      var card = h('section', { className: 'map-region' });
      card.appendChild(h('h3', { className: 'map-region__name', textContent: name }));
      if (!mapText.length) return card;

      var survey = surveyOf(mapText);
      var kinds = Object.keys(survey.census).length;
      card.appendChild(h('p', { className: 'map-region__survey',
        textContent: 'a ' + survey.cols + '\u00d7' + survey.rows + ' stretch \u00b7 '
          + kinds + ' kind' + (kinds === 1 ? '' : 's') + ' of ground' }));
      card.appendChild(h('pre', { className: 'map-region__grid', textContent: mapText.join('\n') }));

      /* Each kind of ground is a door — press it and ask what lives there */
      var marks = h('div', { className: 'map-marks' });
      marks.appendChild(h('span', { className: 'map-marks__label',
        textContent: 'press a mark to ask what lives under it' }));
      Object.keys(survey.census).forEach(function (ch) {
        var chip = h('button', { className: 'map-mark', type: 'button',
          textContent: '\u201c' + ch + '\u201d \u00b7 ' + survey.census[ch] });
        chip.addEventListener('click', function () {
          openFolio('map', chip);
          folioInput.value = 'What is the mark \u201c' + ch + '\u201d in ' + name + '? What lives under it?';
          folioInput.focus();
        });
        marks.appendChild(chip);
      });
      card.appendChild(marks);

      card.appendChild(deepenTool(name));
      return card;
    }

    /* Deepen a landmark — the surveyor walks the ground (real enhance) */
    function deepenTool(name) {
      var div = h('div', { className: 'map-deepen' });
      div.appendChild(h('span', { className: 'map-deepen__label', textContent: 'deepen a landmark' }));
      var row = h('div', { className: 'map-deepen__row' });
      var inp = h('input', { className: 'map-deepen__input', type: 'text',
        placeholder: 'e.g. the old mill', 'aria-label': 'Landmark to deepen in ' + name });
      var btn = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Deepen' });
      var out = h('div', { className: 'map-deepen__out' });
      function run() {
        var poi = inp.value.trim();
        if (!poi) { inp.focus(); return; }
        btn.disabled = true;
        out.innerHTML = '';
        out.appendChild(loadingState('the surveyor is walking that ground\u2026'));
        API.enhanceMap({ region: name, poi_name: poi })
          .then(function (res) {
            out.innerHTML = '';
            var box = h('div', { className: 'map-enhance' });
            box.appendChild(h('div', { className: 'map-enhance__title', textContent: res.title || poi }));
            if (res.description) {
              box.appendChild(h('p', { className: 'map-enhance__desc', textContent: res.description }));
            }
            if (res.details && res.details.length) {
              var ul = h('ul', { className: 'map-enhance__details' });
              res.details.forEach(function (d) { ul.appendChild(h('li', { textContent: d })); });
              box.appendChild(ul);
            }
            out.appendChild(box);
          })
          .catch(function () {
            out.innerHTML = '';
            out.appendChild(h('p', { className: 'map-deepen__err',
              textContent: 'the surveyor couldn\u2019t reach that ground \u2014 ask again, or name it differently' }));
          })
          .finally(function () { btn.disabled = false; });
      }
      btn.addEventListener('click', run);
      inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') run(); });
      row.appendChild(inp);
      row.appendChild(btn);
      div.appendChild(row);
      div.appendChild(out);
      return div;
    }

    /* The pack's own word — real validation, shown plainly */
    function packCheckRow(first) {
      var row = h('div', { className: 'map-check' });
      row.appendChild(h('span', { className: 'map-check__label', textContent: 'the pack' }));
      var val = h('span', { className: 'map-check__value', role: 'status' });
      var btn = h('button', { className: 'btn btn--ghost', type: 'button', textContent: 'check the pack' });
      function paint(res) {
        if (!res) {
          val.textContent = 'didn\u2019t answer';
          val.className = 'map-check__value map-check__value--warn';
          return;
        }
        var ok = !!res.ok;
        val.textContent = ok
          ? 'holds \u2014 nothing to fix'
          : ((res.errors && res.errors.length) ? res.errors.join(' \u00b7 ') : 'has things to fix');
        val.className = 'map-check__value' + (ok ? ' map-check__value--ok' : ' map-check__value--warn');
      }
      paint(first);
      btn.addEventListener('click', function () {
        btn.disabled = true;
        val.textContent = 'checking\u2026';
        API.validate().catch(function () { return null; }).then(paint)
          .finally(function () { btn.disabled = false; });
      });
      row.appendChild(val);
      row.appendChild(btn);
      return row;
    }

    /* ── The drawing table — a map maker with no markdown ── */
    function drawingTable(data) {
      var regions = data.regions || {};
      var names = Object.keys(regions);
      var useName = names.indexOf('town') !== -1 ? 'town' : (names[0] || 'town');
      var region = regions[useName] || {};
      var legend = data.legend || {};
      var sanctuary = data.sanctuary_tiles || [];
      var packLines = (region.map_text && region.map_text.length)
        ? region.map_text.slice()
        : (data.map || []).slice();
      var legendKeys = Object.keys(legend);

      var section = h('section', { className: 'map-draw' });
      section.appendChild(spot('cartographer-long-map', 'spot--right'));
      section.appendChild(h('h3', { className: 'map-draw__title', textContent: 'The drawing table' }));
      section.appendChild(h('p', { className: 'map-draw__hint',
        textContent: 'No markdown here \u2014 dip a brush and press the ground. The engine checks every sketch; only you decide what\u2019s kept.' }));

      if (!legendKeys.length || !packLines.length) {
        section.appendChild(h('p', { className: 'map-draw__note',
          textContent: 'This world has no ink yet \u2014 there is nothing to sketch until the pack names a map and its marks.' }));
        return section;
      }

      var grid = packLines.map(function (ln) { return ln.split(''); });
      var rows = grid.length;
      var cols = grid[0] ? grid[0].length : 0;
      var brush = legendKeys.indexOf('.') !== -1 ? '.' : legendKeys[0];
      var dirty = false;
      var tool = 'brush';                // the hand at the table: brush | bucket
      var undoStack = [];
      var MAX_UNDO = 40;
      function snapshot() {
        undoStack.push(grid.map(function (r) { return r.slice().join(''); }));
        if (undoStack.length > MAX_UNDO) undoStack.shift();
        if (undoBtn) undoBtn.hidden = false;
      }
      function undo() {
        if (!undoStack.length) return;
        grid = undoStack.pop().map(function (ln) { return ln.split(''); });
        saveSketch();
        render();
        if (undoBtn) undoBtn.hidden = undoStack.length === 0;
      }
      var sketchKey = 'vefr.sketch.' + String(data.title || 'world')
        .replace(/[^a-z0-9]/gi, '-').toLowerCase() + '.' + useName;
      try {
        var saved = window.localStorage && localStorage.getItem(sketchKey);
        if (saved) {
          var parsed = JSON.parse(saved);
          if (parsed && Array.isArray(parsed.grid) && parsed.grid.length === rows &&
              parsed.grid.every(function (r) { return Array.isArray(r) && r.length === cols; })) {
            grid = parsed.grid.map(function (r) { return r.slice(); });
            if (parsed.brush && legend[parsed.brush]) brush = parsed.brush;
            dirty = true;
          }
        }
      } catch (e) {}

      var canvas = h('div', { className: 'map-canvas', role: 'grid', tabindex: '0',
        'aria-label': 'Map of ' + useName + ' \u2014 press the arrows to move, Enter to ink' });
      var inkLine = h('p', { className: 'map-draw__ink', role: 'status' });
      var focusR = 0, focusC = 0, cells = [];

      function cellColor(ch) {
        var spec = legend[ch];
        if (!spec || !spec.base || !spec.base.length) return '';
        return spec.base[0];
      }
      function cellSolid(ch) {
        var s = legend[ch];
        return !!(s && s.solid === true);
      }
      function saveSketch() {
        try {
          window.localStorage.setItem(sketchKey, JSON.stringify({
            grid: grid.map(function (r) { return r.slice(); }), brush: brush }));
        } catch (e) {}
      }
      function census() {
        var chr = {};
        for (var r = 0; r < rows; r++) {
          for (var c = 0; c < cols; c++) {
            var ch = grid[r][c];
            if (ch && ch !== ' ') chr[ch] = (chr[ch] || 0) + 1;
          }
        }
        var parts = Object.keys(chr).map(function (k) { return '\u201c' + k + '\u201d \u00d7 ' + chr[k]; });
        inkLine.textContent = rows + ' rows \u00d7 ' + cols + ' cols \u00b7 '
          + (parts.length ? parts.join(', ') : 'nothing inked yet');
      }
      function paint(r, c) {
        if (r < 0 || r >= rows || c < 0 || c >= cols) return;
        var cell = cells[r] && cells[r][c];
        if (!cell) return;
        if (grid[r][c] === brush) return;
        snapshot();
        grid[r][c] = brush;
        cell.textContent = brush;
        cell.style.background = cellColor(brush) || 'transparent';
        cell.classList.toggle('map-cell--solid', cellSolid(brush));
        cell.classList.toggle('map-cell--marked', !!(legend[brush] && legend[brush].deco));
        cell.title = 'row ' + (r + 1) + ', column ' + (c + 1) + ' \u00b7 \u201c' + brush + '\u201d';
        dirty = true;
        saveSketch();
        census();
        cansBtn.hidden = false;
        btnKeep.disabled = false;
        btnUse.disabled = false;
        firstWalk.attempt('map');
      }
      function floodFill(r, c) {
        if (r < 0 || r >= rows || c < 0 || c >= cols) return;
        var target = grid[r][c];
        if (target === brush) return;
        snapshot();
        var open = [[r, c]];
        var seen = {};
        seen[r * cols + c] = true;
        while (open.length) {
          var cur = open.pop();
          var cr = cur[0], cc = cur[1];
          grid[cr][cc] = brush;
          var cell = cells[cr] && cells[cr][cc];
          if (cell) {
            cell.textContent = brush;
            cell.style.background = cellColor(brush) || 'transparent';
            cell.classList.toggle('map-cell--solid', cellSolid(brush));
            cell.classList.toggle('map-cell--marked', !!(legend[brush] && legend[brush].deco));
            cell.title = 'row ' + (cr + 1) + ', column ' + (cc + 1) + ' \u00B7 \u201C' + brush + '\u201D';
          }
          var dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
          for (var d = 0; d < 4; d++) {
            var nr = cr + dirs[d][0], nc = cc + dirs[d][1];
            if (nr >= 0 && nr < rows && nc >= 0 && nc < cols &&
                !seen[nr * cols + nc] && grid[nr][nc] === target) {
              seen[nr * cols + nc] = true;
              open.push([nr, nc]);
            }
          }
        }
        dirty = true;
        saveSketch();
        census();
        cansBtn.hidden = false;
        btnKeep.disabled = false;
        btnUse.disabled = false;
        firstWalk.attempt('map');
      }
      function focusCell(r, c) {
        var old = cells[focusR] && cells[focusR][focusC];
        if (old) old.tabIndex = -1;
        focusR = r; focusC = c;
        var cell = cells[r] && cells[r][c];
        if (cell) {
          cell.tabIndex = 0;
          cell.focus();
        }
      }
      function makeCell(r, c) {
        var ch = grid[r][c];
        var cell = h('div', { className: 'map-cell' + (cellSolid(ch) ? ' map-cell--solid' : ''),
          role: 'gridcell', tabindex: '-1', textContent: ch,
          'data-xy': String(r * cols + c) });
        var bg = cellColor(ch);
        if (bg) cell.style.background = bg;
        if (legend[ch] && legend[ch].deco) cell.classList.add('map-cell--marked');
        cell.title = 'row ' + (r + 1) + ', column ' + (c + 1) + ' \u00b7 \u201c' + ch + '\u201d';
        cell.addEventListener('click', function () {
          var idx = Number(cell.getAttribute('data-xy'));
          var rr = Math.floor(idx / cols), cc = idx % cols;
          if (tool === 'bucket') floodFill(rr, cc); else paint(rr, cc);
          focusCell(rr, cc);
        });
        return cell;
      }
      function render() {
        var hadFocus = canvas.contains(document.activeElement);
        canvas.innerHTML = '';
        cells = [];
        focusR = Math.min(focusR, rows - 1);
        focusC = Math.min(focusC, cols - 1);
        for (var r = 0; r < rows; r++) {
          cells.push([]);
          var rowEl = h('div', { className: 'map-canvas__row', role: 'row' });
          for (var c = 0; c < cols; c++) {
            var cell = makeCell(r, c);
            if (r === focusR && c === focusC) cell.tabIndex = 0;
            cells[r].push(cell);
            rowEl.appendChild(cell);
          }
          canvas.appendChild(rowEl);
        }
        census();
        if (hadFocus) focusCell(focusR, focusC);
      }
      canvas.addEventListener('keydown', function (e) {
        var r = focusR, c = focusC;
        if (e.key === 'ArrowUp') r = Math.max(0, r - 1);
        else if (e.key === 'ArrowDown') r = Math.min(rows - 1, r + 1);
        else if (e.key === 'ArrowLeft') c = Math.max(0, c - 1);
        else if (e.key === 'ArrowRight') c = Math.min(cols - 1, c + 1);
        else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); paint(r, c); return; }
        else return;
        e.preventDefault();
        focusCell(r, c);
      });

      /* Drag to paint with the brush — press, sweep, lift */
      var dragging = false;
      canvas.addEventListener('pointerdown', function (e) {
        var cell = e.target.closest && e.target.closest('.map-cell');
        if (!cell) return;
        dragging = true;
        var idx = Number(cell.getAttribute('data-xy'));
        var rr = Math.floor(idx / cols), cc = idx % cols;
        if (tool === 'bucket') floodFill(rr, cc); else paint(rr, cc);
      });
      canvas.addEventListener('pointerover', function (e) {
        if (!dragging || tool !== 'brush') return;
        var cell = e.target.closest && e.target.closest('.map-cell');
        if (!cell) return;
        var idx = Number(cell.getAttribute('data-xy'));
        var rr = Math.floor(idx / cols), cc = idx % cols;
        paint(rr, cc);
      });
      document.addEventListener('pointerup', function () { dragging = false; });

      /* The ink pots — one brush per mark the pack really knows */
      var pots = h('div', { className: 'map-pots', role: 'group',
        'aria-label': 'Ink pots \u2014 one brush per mark' });
      function potLabel(ch) {
        var spec = legend[ch] || {};
        if (spec.solid === true) return 'solid';
        if (sanctuary.indexOf(ch) !== -1) return 'sanctuary';
        if (spec.deco) return 'marked';
        return 'open ground';
      }
      function paintPots() {
        pots.innerHTML = '';
        legendKeys.forEach(function (ch) {
          var b = h('button', { className: 'map-inked' + (brush === ch ? ' map-inked--active' : ''),
            type: 'button', 'aria-pressed': String(brush === ch) });
          b.appendChild(h('span', { className: 'map-inked__char', textContent: ch }));
          b.appendChild(h('span', { className: 'map-inked__label', textContent: potLabel(ch) }));
          var bg = cellColor(ch);
          if (bg) b.style.setProperty('--ink', bg);
          b.addEventListener('click', function () {
            brush = ch;
            paintPots();
            if (dirty) { cansBtn.hidden = false; btnKeep.disabled = false; btnUse.disabled = false; }
          });
          pots.appendChild(b);
        });
      }

      /* The tools — brush, bucket, undo */
      var tools = h('div', { className: 'map-draw__tools', role: 'group', 'aria-label': 'Table tools' });
      var brushTool = h('button', { className: 'map-tool map-tool--active', type: 'button',
        'aria-pressed': 'true', textContent: 'brush' });
      var bucketTool = h('button', { className: 'map-tool', type: 'button',
        'aria-pressed': 'false', textContent: 'fill' });
      var undoBtn = h('button', { className: 'map-tool map-tool--undo', type: 'button',
        textContent: 'undo', hidden: true });
      function setTool(t) {
        tool = t;
        brushTool.classList.toggle('map-tool--active', t === 'brush');
        bucketTool.classList.toggle('map-tool--active', t === 'bucket');
        brushTool.setAttribute('aria-pressed', String(t === 'brush'));
        bucketTool.setAttribute('aria-pressed', String(t === 'bucket'));
      }
      brushTool.addEventListener('click', function () { setTool('brush'); });
      bucketTool.addEventListener('click', function () { setTool('bucket'); });
      undoBtn.addEventListener('click', function () {
        undo();
        undoBtn.hidden = undoStack.length === 0;
      });
      tools.appendChild(brushTool);
      tools.appendChild(bucketTool);
      tools.appendChild(undoBtn);

      /* Sketches kept from this very table, pinned by the ferry */
      var pinned = h('div', { className: 'map-draw__pinned' });
      API.vault().catch(function () { return { items: [] }; }).then(function (v) {
        var sketches = ((v && v.items) || []).filter(function (i) { return i.kind === 'sketch'; });
        if (!sketches.length) return;
        pinned.appendChild(h('h4', { className: 'map-draw__pinned-title', textContent: 'sketches pinned from this table' }));
        var shelf = h('div', { className: 'folks-shelf' });
        sketches.forEach(function (s) {
          var card = h('button', { className: 'pinned-card', type: 'button',
            'aria-label': 'Ask about ' + (s.name || 'a sketch') });
          card.appendChild(h('span', { className: 'pinned-card__name', textContent: s.name || 'a sketch' }));
          card.appendChild(h('span', { className: 'pinned-card__lore', textContent: truncate(s.lore || '', 90) }));
          card.addEventListener('click', function () {
            openFolio('map', card);
            folioInput.value = 'Tell me about \u201C' + (s.name || 'this sketch') + '\u201D \u2014 what does the land want?';
            folioInput.focus();
          });
          shelf.appendChild(card);
        });
        pinned.appendChild(shelf);
      });

      /* The actions — reset, sketch new land, keep, ask */
      var actions = h('div', { className: 'map-draw__row' });
      var cansBtn = h('button', { className: 'btn btn--ghost', type: 'button', textContent: 'reset the ink', hidden: true });
      var sketchBtn = h('button', { className: 'btn btn--ghost', type: 'button', textContent: 'sketch new land' });
      var keepName = h('input', { className: 'map-draw__keep-name', type: 'text',
        value: 'map sketch of ' + useName + ' (hand-inked)',
        'aria-label': 'Name for the kept sketch' });
      var btnKeep = h('button', { className: 'btn btn--bell', type: 'button', textContent: 'keep this sketch', disabled: true });
      var keepWrap = h('div', { className: 'map-draw__keep' });
      keepWrap.appendChild(keepName);
      keepWrap.appendChild(btnKeep);
      var btnUse = h('button', { className: 'btn btn--warm', type: 'button',
        textContent: 'use as this world\u2019s map', disabled: true });
      actions.appendChild(cansBtn);
      actions.appendChild(sketchBtn);
      actions.appendChild(keepWrap);
      actions.appendChild(btnUse);

      /* Committing the drawing to the world — the one action that
         writes. A refusal (422) is the engine's own words; an
         existing map (409) is a question, never a silent clobber. */
      var useNote = h('p', { className: 'map-draw__check', role: 'status',
        'aria-live': 'polite', hidden: true });
      var replaceRow = h('div', { className: 'map-draw__replace', hidden: true });
      replaceRow.appendChild(h('p', { className: 'map-draw__replace-q',
        textContent: 'Replace the current map? A backup is kept.' }));
      var replaceYes = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Replace' });
      var replaceNo = h('button', { className: 'btn btn--ghost', type: 'button', textContent: 'Cancel' });
      replaceRow.appendChild(replaceYes);
      replaceRow.appendChild(replaceNo);

      function commitMap(force) {
        if (!dirty) return;
        btnUse.disabled = true;
        replaceRow.hidden = true;
        useNote.hidden = false;
        useNote.classList.remove('map-draw__check--good', 'map-draw__check--bad');
        useNote.textContent = 'the engine is walking your new ground\u2026';
        API.mapBuild({
          grid: grid.map(function (r) { return r.join(''); }),
          force: !!force
        })
          .then(function (res) {
            dirty = false;
            /* The world's map is now the truth; the local sketch is redundant. */
            try { window.localStorage.removeItem(sketchKey); } catch (e) {}
            studioAudio.clank();
            ferryNote('your map is committed to this world'
              + (res && res.backup_rel ? ' \u2014 the old map is kept beside it' : '') + '.');
            enter();
          })
          .catch(function (err) {
            if (err && err.status === 409) {
              useNote.hidden = true;
              replaceRow.hidden = false;
              replaceYes.focus();
              return;
            }
            useNote.textContent = (err && err.detail)
              ? String(err.detail)
              : 'the engine refused that map \u2014 check the ground and try again';
            useNote.classList.add('map-draw__check--bad');
          })
          .finally(function () { btnUse.disabled = false; });
      }
      btnUse.addEventListener('click', function () { commitMap(false); });
      replaceYes.addEventListener('click', function () { commitMap(true); });
      replaceNo.addEventListener('click', function () {
        replaceRow.hidden = true;
        useNote.hidden = false;
        useNote.classList.remove('map-draw__check--good', 'map-draw__check--bad');
        useNote.textContent = 'left as it was \u2014 this world\u2019s map is unchanged.';
      });

      var askBtn = h('button', { className: 'btn btn--ghost', type: 'button',
        textContent: 'ask the Cartographer about it' });
      actions.appendChild(askBtn);
      var checkBtn = h('button', { className: 'btn btn--ghost', type: 'button',
        textContent: 'check the ground' });
      actions.appendChild(checkBtn);
      var checkNote = h('p', { className: 'map-draw__check', role: 'status',
        'aria-live': 'polite', hidden: true });
      checkBtn.addEventListener('click', function () {
        checkBtn.disabled = true;
        checkNote.hidden = false;
        checkNote.textContent = 'the engine is pacing the ground\u2026';
        checkNote.classList.remove('map-draw__check--good', 'map-draw__check--bad');
        API.mapCheck({ grid: grid.map(function (r) { return r.join(''); }) })
          .then(function (res) {
            if (res && res.ok) {
              checkNote.textContent = 'the engine holds your sketch \u2014 every path reaches, every door is heard.';
              checkNote.classList.add('map-draw__check--good');
              studioAudio.squeak();
            } else {
              var errs = (res && res.errors && res.errors.length)
                ? res.errors.join(' \u00B7 ')
                : 'something in this sketch doesn\u2019t hold \u2014 the pack won\u2019t walk it';
              checkNote.textContent = errs;
              checkNote.classList.add('map-draw__check--bad');
            }
          })
          .catch(function () {
            checkNote.textContent = 'the engine couldn\u2019t pace the ground just now \u2014 try again';
            checkNote.classList.add('map-draw__check--bad');
          })
          .finally(function () {
            checkBtn.disabled = false;
            checkNote.hidden = false;
          });
      });

      cansBtn.addEventListener('click', function () {
        grid = packLines.map(function (ln) { return ln.split(''); });
        dirty = false;
        saveSketch();
        render();
        cansBtn.hidden = true;
        btnKeep.disabled = true;
        btnUse.disabled = true;
      });

      btnKeep.addEventListener('click', function () {
        if (!dirty) return;
        btnKeep.disabled = true;
        var name = keepName.value.trim() || ('map sketch of ' + useName);
        var marks = {};
        for (var r = 0; r < rows; r++) {
          for (var c = 0; c < cols; c++) {
            var ch = grid[r][c];
            if (ch && ch !== ' ') marks[ch] = (marks[ch] || 0) + 1;
          }
        }
        var lore = 'A hand-inked map sketch of ' + useName + ' kept from the drawing table \u2014 '
          + (Object.keys(marks).map(function (k) { return '\u201c' + k + '\u201d \u00d7 ' + marks[k]; }).join(', ') || 'nothing inked');
        API.vaultKeep({ name: name, kind: 'sketch', bond: 'assigned', lore: lore })
          .then(function () {
            studioAudio.clank();
            ferryNote('Ratatoskr is carrying \u201c' + truncate(name, 36) + '\u201d into the vault\u2026');
          })
          .catch(function () {
            btnKeep.disabled = false;
            ferryNote('the vault turned the sketch away \u2014 try again');
          });
      });

      /* Sketch new land — the surveyor proposes, the engine checks */
      var sketchRow = h('div', { className: 'map-sketch', hidden: true });
      var sketchInp = h('input', { className: 'map-sketch__input', type: 'text',
        placeholder: 'what should the land feel like? e.g. a hollow with one path and a standing stone',
        'aria-label': 'Describe the new land' });
      var sketchGo = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Sketch it' });
      var sketchErr = h('p', { className: 'map-sketch__err', role: 'status', hidden: true });
      sketchRow.appendChild(sketchInp);
      sketchRow.appendChild(sketchGo);
      sketchRow.appendChild(sketchErr);
      sketchBtn.addEventListener('click', function () {
        sketchRow.hidden = !sketchRow.hidden;
        if (!sketchRow.hidden) sketchInp.focus();
      });
      function runSketch() {
        var story = sketchInp.value.trim();
        if (!story) { sketchInp.focus(); return; }
        sketchGo.disabled = true;
        sketchErr.hidden = true;
        API.mapPropose({ story: story })
          .then(function (res) {
            if (!res || !res.ok || !res.grid || !res.grid.length) {
              sketchErr.textContent = (res && res.reason) || 'the surveyor drew nothing usable \u2014 paint it yourself';
              sketchErr.hidden = false;
              return;
            }
            grid = res.grid.map(function (ln) { return ln.split(''); });
            rows = grid.length;
            cols = grid[0] ? grid[0].length : 0;
            if (res.legend && Object.keys(res.legend).length) {
              legend = res.legend;
              legendKeys = Object.keys(legend);
              if (!legend[brush]) brush = legendKeys.indexOf('.') !== -1 ? '.' : legendKeys[0];
              paintPots();
            }
            dirty = true;
            saveSketch();
            render();
            cansBtn.hidden = false;
            btnKeep.disabled = false;
            btnUse.disabled = false;
            ferryNote('the surveyor sketched \u201c' + truncate(story, 42) + '\u201d into new land\u2026');
          })
          .catch(function () {
            sketchErr.textContent = 'the surveyor couldn\u2019t reach a pen just now \u2014 paint it yourself';
            sketchErr.hidden = false;
          })
          .finally(function () { sketchGo.disabled = false; });
      }
      sketchGo.addEventListener('click', runSketch);
      sketchInp.addEventListener('keydown', function (e) { if (e.key === 'Enter') runSketch(); });

      askBtn.addEventListener('click', function () {
        openFolio('map', askBtn);
        folioInput.value = 'Tell me about the map I just sketched \u2014 '
          + (sketchInp.value.trim() || 'a place I painted by hand');
        folioInput.focus();
      });

      section.appendChild(pots);
      section.appendChild(inkLine);
      section.appendChild(tools);
      section.appendChild(canvas);
      section.appendChild(sketchRow);
      section.appendChild(actions);
      section.appendChild(useNote);
      section.appendChild(replaceRow);
      section.appendChild(checkNote);
      section.appendChild(pinned);
      paintPots();
      render();
      cansBtn.hidden = !dirty;
      btnKeep.disabled = !dirty;
      btnUse.disabled = !dirty;
      return section;
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();

  /* ══════════════════════════════════════════════════════
     THE FOLKS — people, not records
     ══════════════════════════════════════════════════════ */

  screens.characters = (function () {
    var el_screen;
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-characters' });
      main.appendChild(el_screen);
    }
    function enter() {
      el_screen.innerHTML = '<div class="wrap band folks-room" id="folks-content"></div>';
      var container = el_screen.querySelector('#folks-content');
      container.appendChild(loadingState('Looking for familiar faces\u2026'));

      Promise.all([
        API.wiki().catch(function () { return { characters: [] }; }),
        API.world().catch(function () { return { speakers: [], phases: [] }; }),
        API.vault().catch(function () { return { items: [] }; })
      ]).then(function (results) {
        container.innerHTML = '';
        var worldChars = (results[0] && results[0].characters) || [];
        var packSpeakers = (results[1] && results[1].speakers) || [];
        var phases = (results[1] && results[1].phases) || [];
        var keptFaces = ((results[2] && results[2].items) || []).filter(function (i) {
          return i.kind === 'face';
        });

        var rl = residentLine('characters');
        if (rl) container.appendChild(rl);

        /* The bench — a new face can join by hand */
        container.appendChild(inviteBench());

        /* The pack's voices, as living cards: where they stand,
           what they say, what they've already said */
        var byName = {};
        packSpeakers.forEach(function (s) { byName[s.name] = s; });
        worldChars.forEach(function (c) {
          var k = c.name || c.key;
          if (!k) return;
          if (!byName[k]) byName[k] = { name: k, key: c.key || k };
          byName[k].lines = c.lines;
          if (!byName[k].key) byName[k].key = c.key || k;
        });
        var voices = Object.keys(byName).map(function (k) { return byName[k]; });

        if (voices.length) {
          container.appendChild(h('h3', { className: 'folks-room__sub', textContent: 'the pack\u2019s voices' }));
          var grid = h('div', { className: 'folks-grid' });
          voices.forEach(function (v) {
            grid.appendChild(voiceCard(v, phases));
          });
          container.appendChild(grid);
        } else {
          container.appendChild(h('p', { className: 'folks-room__quiet',
            textContent: 'The world hasn\u2019t named its people yet \u2014 invite the first one above.' }));
        }

        /* Faces the storyteller kept — the household grew by hand */
        if (keptFaces.length) {
          container.appendChild(h('h3', { className: 'folks-room__sub', textContent: 'faces you\u2019ve invited' }));
          var shelf = h('div', { className: 'folks-shelf' });
          keptFaces.forEach(function (f) { shelf.appendChild(faceCard(f)); });
          container.appendChild(shelf);
        }
      })
      .catch(function () {
        container.innerHTML = '';
        container.appendChild(emptyState(
          'Couldn\u2019t find the folks.',
          'The storyteller might be resting.'
        ));
      });
    }

    function voiceCard(v, phases) {
      var card = h('div', { className: 'folk-card', role: 'button', tabindex: '0',
        'aria-label': 'Ask about ' + v.name });
      var initial = v.name.charAt(0).toUpperCase();
      card.appendChild(h('div', { className: 'folk-card__portrait', textContent: initial }));
      var who = h('div', { className: 'folk-card__who' });
      who.appendChild(h('div', { className: 'folk-card__name', textContent: v.name }));
      var bits = [];
      if (v.at) bits.push('stands at ' + v.at[0] + ', ' + v.at[1]);
      if (v.near) bits.push('near ' + v.near);
      if (v.lines !== undefined) bits.push(v.lines + ' line' + (v.lines !== 1 ? 's' : ''));
      who.appendChild(h('div', { className: 'folk-card__bits', textContent: bits.join(' \u00B7 ') }));
      if (v.seeds && typeof v.seeds === 'object') {
        var keys = Object.keys(v.seeds);
        var seed = keys.length ? v.seeds[phases[0]] || v.seeds[keys[0]] : null;
        if (seed) who.appendChild(h('div', { className: 'folk-card__seed', textContent: '\u201C' + seed + '\u201D' }));
      }
      card.appendChild(who);
      card.addEventListener('click', function () {
        firstWalk.attempt('folks');
        openFolio('characters', card);
        folioInput.value = 'Tell me about ' + v.name + ' \u2014 who are they, and what do they want?';
        folioInput.focus();
      });
      card.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); card.click(); }
      });
      return card;
    }

    function faceCard(f) {
      var card = h('div', { className: 'folk-card folk-card--invited' });
      var initial = (f.name || '?').charAt(0).toUpperCase();
      card.appendChild(h('div', { className: 'folk-card__portrait', textContent: initial }));
      var who = h('div', { className: 'folk-card__who' });
      who.appendChild(h('div', { className: 'folk-card__name', textContent: f.name || 'The new face' }));
      if (f.lore) who.appendChild(h('div', { className: 'folk-card__bits', textContent: truncate(f.lore, 140) }));
      var btn = h('button', { className: 'folk-card__ask', type: 'button', textContent: 'Ask about them' });
      btn.addEventListener('click', function () {
        firstWalk.attempt('folks');
        openFolio('characters', btn);
        folioInput.value = 'Meet ' + (f.name || 'the new face') + ': ' + truncate(f.lore || '', 180);
        folioInput.focus();
      });
      who.appendChild(btn);
      card.appendChild(who);
      return card;
    }

    function inviteBench() {
      var bench = h('section', { className: 'folk-invite' });
      bench.appendChild(spot('keeper-of-faces-show-sketch', 'spot--right'));
      bench.appendChild(h('h3', { className: 'map-draw__title', textContent: 'Invite a new face' }));
      bench.appendChild(h('p', { className: 'map-draw__hint',
        textContent: 'Ask the Keeper to name someone who belongs here. They stand on real ground \u2014 reachable, unclaimed, dry \u2014 and they only join the house when you keep them.' }));
      var row = h('div', { className: 'forge__row' });
      var rollBtn = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Ask the Keeper for a new face' });
      var result = h('div', { className: 'folk-invite__result', role: 'status', 'aria-live': 'polite' });
      rollBtn.addEventListener('click', function () {
        rollBtn.disabled = true;
        rollBtn.textContent = 'the Keeper is sharpening a quill\u2026';
        result.innerHTML = '';
        API.faceRoll({}).then(function (data) {
          rollBtn.disabled = false;
          rollBtn.textContent = 'Ask the Keeper for a new face';
          if (!data || !data.ok || !data.face) {
            result.appendChild(h('p', { className: 'folk-invite__cold',
              textContent: (data && data.reason) || 'the Keeper drew nothing usable \u2014 maybe the inkmill is cold. Try again, or write the face yourself.' }));
            return;
          }
          result.appendChild(faceDraft(data.face));
        }).catch(function () {
          rollBtn.disabled = false;
          rollBtn.textContent = 'Ask the Keeper for a new face';
          result.appendChild(h('p', { className: 'folk-invite__cold',
            textContent: 'the Keeper couldn\u2019t reach a pen just now \u2014 try again.' }));
        });
      });
      row.appendChild(rollBtn);
      bench.appendChild(row);
      bench.appendChild(result);
      return bench;
    }

    function faceDraft(f) {
      var panel = h('div', { className: 'face-draft', role: 'group', 'aria-label': 'Draft of the new face' });
      var nameF = h('input', { className: 'draft__field', type: 'text', id: 'face-name', value: f.name || '', 'aria-label': 'Name' });
      var roleF = h('input', { className: 'draft__field', type: 'text', id: 'face-role', value: f.role || '', 'aria-label': 'What they do' });
      var seedF = h('input', { className: 'draft__field', type: 'text', id: 'face-seed', value: f.seed || '', 'aria-label': 'What they first say' });
      var err = h('p', { className: 'draft__error', role: 'status', hidden: true });
      var at = f.at ? ('at ' + f.at[0] + ', ' + f.at[1]) : 'somewhere reachable';
      var row = h('div', { className: 'forge__row' });
      var keepBtn = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Keep this face' });
      row.appendChild(keepBtn);

      function label(forId, text) {
        var l = h('label', { className: 'face-draft__label', textContent: text });
        l.setAttribute('for', forId);
        return l;
      }

      keepBtn.addEventListener('click', function () {
        var name = nameF.value.trim();
        var role = roleF.value.trim();
        var seed = seedF.value.trim();
        if (!name || !role || !seed) {
          err.textContent = 'a face needs a name, a role, and one line to say';
          err.hidden = false;
          return;
        }
        keepBtn.disabled = true;
        API.vaultKeep({
          name: name,
          kind: 'face',
          bond: 'invited',
          lore: 'Role: ' + role + '. First words: \u201C' + seed + '\u201D. The Keeper stands them ' + at + '.'
        }).then(function () {
          studioAudio.clank();
          ferryNote('Ratatoskr is carrying \u201c' + truncate(name, 32) + '\u201D to the people\u2026');
          enter();
        }).catch(function () {
          err.textContent = 'the vault turned the face away \u2014 try again';
          err.hidden = false;
          keepBtn.disabled = false;
        });
      });

      panel.appendChild(label('face-name', 'name'));
      panel.appendChild(nameF);
      panel.appendChild(label('face-role', 'what they do'));
      panel.appendChild(roleF);
      panel.appendChild(label('face-seed', 'what they first say'));
      panel.appendChild(seedF);
      panel.appendChild(h('p', { className: 'face-draft__at', textContent: 'The Keeper stands them ' + at + '.' }));
      panel.appendChild(row);
      panel.appendChild(err);
      return panel;
    }

    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();

  /* ══════════════════════════════════════════════════════
     THE VAULT — kept objects on a tray
     ══════════════════════════════════════════════════════ */

  screens.items = (function () {
    var el_screen;
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-items' });
      main.appendChild(el_screen);
    }
    function enter() {
      el_screen.innerHTML = '<div class="wrap band vault-room" id="vault-content"></div>';
      var container = el_screen.querySelector('#vault-content');
      container.appendChild(loadingState('Checking the vault\u2026'));

      /* The anvil — one shared place to shape a keepsake */
      var draft = draftArea(refresh);

      function askForge() {
        API.forge({}).catch(function () { return null; }).then(function (card) {
          if (!card || !card.name) {
            draft.show({}, true, 'the forge is cold just now \u2014 no fire to draw on. shape the card yourself and keep it.');
            return;
          }
          ferryNote('Ratatoskr is carrying a draft from the fire\u2026');
          draft.show(card, true);
        });
      }
      draft.setReroll(askForge);

      API.vault()
        .then(function (data) {
          container.innerHTML = '';
          var items = (data && data.items) || [];
          var rl = residentLine('items');
          if (rl) container.appendChild(rl);

          /* The forge — the fire has a draft for you; shape it, keep it */
          var forgeWrap = h('div', { className: 'forge' });
          forgeWrap.appendChild(spot('hoard-keeper-inspect-gem', 'spot--right'));
          forgeWrap.appendChild(h('div', { className: 'forge__title', textContent: 'The forge' }));
          forgeWrap.appendChild(h('p', { className: 'forge__hint',
            textContent: 'Ask the fire for a keepsake the world would offer \u2014 then shape it by hand and keep it. The vault remembers everything it\u2019s given.' }));
          var askRow = h('div', { className: 'forge__row' });
          var askBtn = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Ask the forge for a keepsake' });
          askBtn.addEventListener('click', function () {
            askBtn.disabled = true;
            askBtn.textContent = 'the fire is puffing\u2026';
            askForge().finally(function () {
              askBtn.disabled = false;
              askBtn.textContent = 'Ask the forge for a keepsake';
            });
          });
          askRow.appendChild(askBtn);
          forgeWrap.appendChild(askRow);
          container.appendChild(forgeWrap);
          container.appendChild(draft.panel);

          if (!items.length) {
            container.appendChild(emptyState(
              'The vault is empty.\nBut the forge is warm.',
              'Ask the fire for a keepsake above \u2014 then shape it and keep it.',
              true
            ));
            return;
          }
          var tray = h('div', { className: 'vault-tray' });
          items.forEach(function (item, i) { tray.appendChild(vaultObject(item, i, draft)); });
          container.appendChild(tray);
        })
        .catch(function () {
          container.innerHTML = '';
          container.appendChild(emptyState(
            'Couldn\u2019t reach the vault.',
            'The world might not be ready yet.'
          ));
        });
    }

    function refresh() { enter(); }

    /* The anvil itself — editable fields, one obeyable action */
    function draftArea(refresh) {
      var panel = h('div', { className: 'draft', hidden: true });
      panel.appendChild(h('div', { className: 'draft__title', textContent: 'On the anvil' }));

      function field(cls, label, type) {
        return h('input', { className: cls, type: type || 'text', placeholder: label, 'aria-label': label });
      }
      var nameF = field('draft__name', 'Name', 'text');
      var kindF = field('draft__kind', 'Kind', 'text');
      var bondF = field('draft__bond', 'Bond', 'text');
      var loreF = h('textarea', { className: 'draft__lore', rows: '3',
        placeholder: 'Lore \u2014 why it matters', 'aria-label': 'Lore' });
      var enF = field('draft__enchant', 'Enchant (optional)', 'text');
      var cuF = field('draft__curse', 'Curse (optional)', 'text');

      var err = h('p', { className: 'draft__err', role: 'status', hidden: true });
      var row = h('div', { className: 'draft__row' });
      var keepBtn = h('button', { className: 'btn btn--bell', type: 'button', textContent: 'Keep it' });
      var againBtn = h('button', { className: 'btn btn--ghost', type: 'button',
        textContent: 'the fire wants another try', hidden: true });
      row.appendChild(keepBtn);
      row.appendChild(againBtn);

      function show(card, rerollable, note) {
        var c = card || {};
        nameF.value = c.name || '';
        kindF.value = c.kind || 'relic';
        bondF.value = c.bond || 'assigned';
        loreF.value = c.lore || '';
        enF.value = c.enchant || '';
        cuF.value = c.curse || '';
        againBtn.hidden = !rerollable;
        if (note) { err.textContent = note; err.hidden = false; }
        else { err.hidden = true; }
        panel.hidden = false;
        panel.scrollIntoView({ block: 'nearest' });
        nameF.focus();
      }

      function keep() {
        var name = nameF.value.trim();
        var lore = loreF.value.trim();
        if (!name || !lore) {
          err.textContent = 'the fire needs a name and a reason';
          err.hidden = false;
          return;
        }
        keepBtn.disabled = true;
        var card = {
          name: name,
          kind: kindF.value.trim() || 'relic',
          bond: bondF.value.trim() || 'assigned',
          lore: lore
        };
        if (enF.value.trim()) card.enchant = enF.value.trim();
        if (cuF.value.trim()) card.curse = cuF.value.trim();
        API.vaultKeep(card)
          .then(function () {
            studioAudio.clank();
            ferryNote('Ratatoskr is carrying \u201c' + truncate(name, 32) + '\u201d into the vault\u2026');
            refresh();
          })
          .catch(function () {
            err.textContent = 'the vault turned it away \u2014 check the fields and try again';
            err.hidden = false;
            keepBtn.disabled = false;
          });
      }
      keepBtn.addEventListener('click', keep);
      [nameF, kindF, bondF, enF, cuF].forEach(function (f) {
        f.addEventListener('keydown', function (e) { if (e.key === 'Enter') keep(); });
      });

      panel.appendChild(nameF);
      var slim = h('div', { className: 'draft__slim' });
      slim.appendChild(kindF);
      slim.appendChild(bondF);
      panel.appendChild(slim);
      panel.appendChild(loreF);
      panel.appendChild(enF);
      panel.appendChild(cuF);
      panel.appendChild(row);
      panel.appendChild(err);

      return {
        panel: panel,
        show: show,
        setReroll: function (fn) { againBtn.addEventListener('click', fn); }
      };
    }

    function vaultObject(item, i, draft) {
      var starred = item.starred || item.star;
      var obj = h('div', { className: 'vault-object' + (starred ? ' vault-object--starred' : '') });
      obj.appendChild(h('span', { className: 'vault-object__icon', textContent: '\u{1F4E6}' }));
      obj.appendChild(h('span', { className: 'vault-object__name',
        textContent: item.name || item.title || 'Something treasured' }));
      obj.appendChild(h('span', { className: 'vault-object__kind',
        textContent: item.kind || 'relic' }));
      var starBtn = h('button', { className: 'vault-object__star',
        'aria-label': starred ? 'Unstar' : 'Star',
        textContent: starred ? '\u2B50' : '\u2606' });
      starBtn.addEventListener('click', function () {
        if (starred) {
          ferryNote('that one is already hanging in the hall\u2026');
        } else {
          var name = item.name || item.title || 'that';
          studioAudio.squeak();
          ferryNote('Ratatoskr is carrying \u201c' + truncate(name, 36) + '\u201d to the hall\u2026');
        }
        API.vaultStar(i).then(function () { enter(); });
      });
      obj.appendChild(starBtn);
      var deepenBtn = h('button', { className: 'vault-deepen', type: 'button', textContent: 'deepen' });
      deepenBtn.addEventListener('click', function () {
        deepenBtn.disabled = true;
        deepenBtn.textContent = 'asking the hoard-keeper\u2026';
        API.enhanceItem({
          base_name: item.name || item.title,
          kind: item.kind || 'relic',
          intent: 'deepen its story, and any quiet curse it might carry'
        }).catch(function () { return null; }).then(function (res) {
          deepenBtn.disabled = false;
          deepenBtn.textContent = 'deepen';
          if (!res || !res.name) {
            draft.show({}, false, 'the hoard-keeper couldn\u2019t deepen it just now \u2014 try again later');
            return;
          }
          ferryNote('the hoard-keeper brought a deepening draft\u2026');
          draft.show(res, false);
        });
      });
      obj.appendChild(deepenBtn);
      return obj;
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();

  /* ══════════════════════════════════════════════════════
     THE LIBRARY — Urðr's shelves: the studio's books and the world's
     ══════════════════════════════════════════════════════ */

  screens.library = (function () {
    var el_screen, reader = null, open = { book: null, page: 0 };
    var L = window.VEFR_LIBRARY;
    var SPINES = ['#2F5553', '#563F63', '#6B4B28', '#3F5A38', '#6A3535', '#33496A', '#4E5A2E', '#5A4B38'];
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-library' });
      main.appendChild(el_screen);
    }
    function shelf(title, sub, books, empty) {
      var s = h('section', { className: 'carved lib-shelf', 'aria-label': title });
      var head = h('div', { className: 'lib-shelf__head' });
      head.appendChild(h('h2', { className: 'lib-shelf__title', textContent: title }));
      head.appendChild(h('span', { className: 'label', textContent: sub }));
      s.appendChild(head);
      var row = h('div', { className: 'lib-books', role: 'group', 'aria-label': title + ' books' });
      if (!books.length) {
        row.appendChild(empty);
      }
      books.forEach(function (b, i) {
        var spine = h('button', { className: 'lib-spine lib-spine--' + (b.kind || 'book'), type: 'button',
          'aria-pressed': 'false', 'aria-label': b.title + ', ' + b.pages.length + ' page' + (b.pages.length === 1 ? '' : 's') });
        spine.style.setProperty('--spine', SPINES[i % SPINES.length]);
        spine.style.setProperty('--spine-h', (118 + ((i * 37) % 30)) + 'px');
        spine.appendChild(h('span', { className: 'lib-spine__title', textContent: b.title }));
        spine.addEventListener('click', function () { read(b, spine); });
        row.appendChild(spine);
      });
      s.appendChild(row);
      return s;
    }
    function read(book, spine) {
      open.book = book;
      open.page = 0;
      el_screen.querySelectorAll('.lib-spine').forEach(function (x) { x.setAttribute('aria-pressed', x === spine ? 'true' : 'false'); });
      paint();
      var title = reader.querySelector('.lib-reader__title');
      if (title) title.focus();
    }
    function paint() {
      var b = open.book;
      reader.innerHTML = '';
      if (!b) {
        reader.appendChild(h('span', { className: 'label', textContent: 'The reading desk' }));
        reader.appendChild(h('p', { className: 'lib-reader__hint', textContent: 'Pull a book off a shelf to read it here, one page at a time.' }));
        return;
      }
      var n = b.pages.length;
      open.page = L.clampPage(open.page, n);
      var FOUND_ICON = { shelf: 'shelf', map: 'map', resident: 'given', earned: 'earned' };
      var found = h('span', { className: 'label lib-reader__found' });
      found.appendChild(h('img', { src: ART + 'icons/library/found-' + (FOUND_ICON[b.found] || 'shelf') + '.webp', alt: '', width: 28, height: 28 }));
      found.appendChild(h('img', { src: ART + 'icons/library/kind-' + (['note', 'terminal'].indexOf(b.kind) >= 0 ? b.kind : 'book') + '.webp', alt: '', width: 28, height: 28 }));
      found.appendChild(h('span', { textContent: b.found_words }));
      reader.appendChild(found);
      reader.appendChild(h('h2', { className: 'lib-reader__title', tabindex: '-1', textContent: b.title }));
      var page = h('div', { className: 'lib-page', 'aria-live': 'polite' });
      page.innerHTML = L.renderPage(b.pages[open.page]);
      reader.appendChild(page);
      var nav = h('div', { className: 'lib-reader__nav' });
      var prev = h('button', { className: 'cta cta--line', type: 'button', textContent: 'Previous page' });
      var next = h('button', { className: 'cta cta--gold', type: 'button', textContent: open.page >= n - 1 ? 'Close the book' : 'Next page' });
      prev.disabled = open.page === 0;
      prev.addEventListener('click', function () { open.page -= 1; paint(); focusPage(); });
      next.addEventListener('click', function () {
        if (open.page >= n - 1) { open.book = null; paint(); return; }
        open.page += 1; paint(); focusPage();
      });
      nav.appendChild(prev);
      nav.appendChild(h('span', { className: 'lib-reader__count', textContent: L.pageLabel(open.page, n) }));
      nav.appendChild(next);
      reader.appendChild(nav);
    }
    function focusPage() {
      var t = reader.querySelector('.lib-reader__title');
      if (t) t.focus();
    }
    function enter() {
      el_screen.innerHTML = '';
      var wrap = h('div', { className: 'wrap band lib-room' });
      var rl = residentLine('library');
      if (rl) wrap.appendChild(rl);
      var grid = h('div', { className: 'lib-grid' });
      var shelves = h('div', { className: 'lib-shelves' });
      shelves.appendChild(loadingState('Urðr is dusting the shelves…'));
      reader = h('aside', { className: 'carved lib-reader', 'aria-label': 'The reading desk' });
      reader.addEventListener('keydown', function (e) {
        if (!open.book) return;
        if (e.key === 'ArrowRight' && open.page < open.book.pages.length - 1) { open.page += 1; paint(); focusPage(); }
        if (e.key === 'ArrowLeft' && open.page > 0) { open.page -= 1; paint(); focusPage(); }
      });
      grid.appendChild(shelves);
      grid.appendChild(reader);
      wrap.appendChild(grid);
      el_screen.appendChild(wrap);
      open = { book: null, page: 0 };
      paint();
      API.library()
        .then(function (data) {
          shelves.innerHTML = '';
          var ladder = spot('urdr-library-ladder', 'spot--inline lib-ladder');
          var intro = h('div', { className: 'spot-row' });
          intro.appendChild(h('p', { className: 'archives-intro',
            textContent: 'Books are written by people, never by the model. A world keeps its own in its library folder.' }));
          intro.appendChild(ladder);
          shelves.appendChild(intro);
          var worldName = data.world || 'this world';
          var empty = h('p', { className: 'lib-empty',
            textContent: worldName + ' has no books yet. Write one as a markdown file in the pack’s library/ folder; it will appear here.' });
          shelves.appendChild(shelf('Found in ' + worldName, (data.books || []).length + ' written', data.books || [], empty));
          shelves.appendChild(shelf('How games are made', 'the studio handbook', data.studio || [], h('p', { className: 'lib-empty', textContent: 'The studio shelf is empty.' })));
        })
        .catch(function () {
          shelves.innerHTML = '';
          shelves.appendChild(emptyState('The Library is locked right now.', 'Try again in a moment.'));
        });
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();

  /* ══════════════════════════════════════════════════════
     THE CHRONICLE — written over time
     ══════════════════════════════════════════════════════ */

  screens.journal = (function () {
    var el_screen;
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-journal' });
      main.appendChild(el_screen);
    }
    function enter() {
      el_screen.innerHTML = '<div class="wrap band chronicle-room" id="chronicle-content"></div>';
      var container = el_screen.querySelector('#chronicle-content');
      container.appendChild(loadingState('Opening the chronicle\u2026'));
      API.journal()
        .then(function (data) {
          container.innerHTML = '';
          var entries = Array.isArray(data) ? data : ((data && data.entries) || []);
          if (!entries.length) {
            container.appendChild(emptyState(
              'The chronicle is waiting\nfor its first entry.',
              'Every story leaves traces.',
              true
            ));
            return;
          }
          var rl = residentLine('journal');
          if (rl) container.appendChild(rl);
          var folded = foldChronicle(entries);
          var list = h('ol', { className: 'timeline', 'aria-label': 'What has happened, newest first' });
          folded.slice(-40).reverse().forEach(function (f) {
            var line = f.kind === 'combat_action' ? actionsLine(f) : chronicleLine(f.entry);
            var starred = f.entry.starred || f.entry.star;
            var row = h('li', { className: 'entry' + (starred ? ' entry--starred' : '') });
            row.appendChild(h('span', { className: 'entry__date', textContent: formatTime(f.at) }));
            var body = h('div', { className: 'entry__body' });
            var kindRow = h('span', { className: 'entry__kind' });
            kindRow.innerHTML = '<svg class="entry__mark" viewBox="0 0 24 24" aria-hidden="true"><use href="#' + (KIND_MARKS[f.kind] || 'm-moment') + '"/></svg>';
            kindRow.appendChild(document.createTextNode(line.kind + (starred ? ' \u00B7 kept in the Hall' : '')));
            body.appendChild(kindRow);
            body.appendChild(h('p', { className: 'entry__text', textContent: line.text || '' }));
            if (line.who) body.appendChild(h('span', { className: 'entry__who', textContent: '\u2014 ' + line.who }));
            row.appendChild(body);
            if (f.kind !== 'combat_action') {
              var text = line.text || '';
              var starBtn = h('button', { className: 'cta cta--line entry__star', type: 'button',
                'aria-pressed': starred ? 'true' : 'false',
                textContent: starred ? 'Kept' : 'Keep in the Hall' });
              starBtn.addEventListener('click', function () {
                if (starred) {
                  ferryNote('those leaves are already pressed into the hall wall\u2026');
                } else {
                  studioAudio.squeak();
                  firstWalk.attempt('chronicle');
                  ferryNote('Ratatoskr is pressing \u201c' + truncate(text || 'this moment', 36) + '\u201d into the hall\u2026');
                }
                API.journalStar(f.index).then(function () { enter(); });
              });
              row.appendChild(starBtn);
            }
            list.appendChild(row);
          });
          container.appendChild(list);
        })
        .catch(function () {
          container.innerHTML = '';
          container.appendChild(emptyState(
            'Couldn\u2019t open the chronicle.',
            'The pages might be elsewhere.'
          ));
        });
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();

  /* ══════════════════════════════════════════════════════
     THE CASTING TABLE — tactile objects for examination
     ══════════════════════════════════════════════════════ */

  screens.runes = (function () {
    var el_screen;
    var POSITIONS = { what_was: 'What was', what_is: 'What is', what_asks: 'What it asks of you' };
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-runes' });
      main.appendChild(el_screen);
    }
    function stone(rune, big) {
      var st = h('button', { className: 'rune-stone' + (big ? ' rune-stone--cast' : ''), type: 'button',
        'aria-expanded': big ? 'true' : 'false', 'aria-label': rune.name + ': ' + rune.short });
      var pebble = h('span', { className: 'rune-stone__pebble', 'aria-hidden': 'true' });
      pebble.style.setProperty('--pebble', 'url(' + ART + 'runes/pebble-' + (1 + (rune.name.length % 4)) + '.webp)');
      pebble.appendChild(h('span', { className: 'rune-stone__stave', textContent: rune.stave }));
      st.appendChild(pebble);
      st.appendChild(h('span', { className: 'rune-stone__name', textContent: rune.name }));
      st.appendChild(h('span', { className: 'rune-stone__short', textContent: rune.short }));
      if (rune.long) st.appendChild(h('span', { className: 'rune-stone__long', textContent: rune.long }));
      if (!big) {
        st.addEventListener('click', function () {
          var open = st.getAttribute('aria-expanded') !== 'true';
          st.setAttribute('aria-expanded', String(open));
        });
      }
      return st;
    }
    function cast(spread, btn) {
      btn.disabled = true;
      spread.innerHTML = '';
      spread.appendChild(loadingState('The stones are tumbling…'));
      API.castRune()
        .then(function (data) {
          spread.innerHTML = '';
          (data.positions || []).forEach(function (p) {
            var slot = h('div', { className: 'cast-slot' });
            slot.appendChild(h('span', { className: 'label', textContent: POSITIONS[p.position] || p.position }));
            slot.appendChild(stone(p, true));
            spread.appendChild(slot);
          });
          studioAudio.squeak();
          ferryNote('three stones, cast at ' + (data.phase || 'this hour') + '. the Rune-Carver nods.');
        })
        .catch(function () {
          spread.innerHTML = '';
          spread.appendChild(emptyState('The stones would not tumble.', 'Try again in a moment.'));
        })
        .finally(function () { btn.disabled = false; btn.textContent = 'Cast again'; });
    }
    function enter() {
      el_screen.innerHTML = '<div class="wrap band casting-room" id="casting-content"></div>';
      var container = el_screen.querySelector('#casting-content');
      var rl = residentLine('runes');
      if (rl) container.appendChild(rl);

      var castCard = h('section', { className: 'carved cast-card', 'aria-labelledby': 'cast-title' });
      castCard.appendChild(spot('rune-carver-offer-stone', 'spot--right'));
      castCard.appendChild(h('span', { className: 'label', textContent: 'Stuck? Ask the stones' }));
      castCard.appendChild(h('h2', { className: 'section-head__title', id: 'cast-title', textContent: 'Pick three without looking' }));
      castCard.appendChild(h('p', { className: 'cast-card__hint', textContent: 'What was, what is, and what it asks of you. Not a prophecy: a nudge for the next thing you write.' }));
      var btn = h('button', { className: 'cta cta--gold', type: 'button', textContent: 'Cast the stones' });
      var spread = h('div', { className: 'cast-spread', 'aria-live': 'polite' });
      btn.addEventListener('click', function () { cast(spread, btn); });
      castCard.appendChild(btn);
      castCard.appendChild(spread);
      container.appendChild(castCard);

      var all = h('section', { className: 'rune-all', 'aria-labelledby': 'futhark-title' });
      all.appendChild(sectionHead('The elder futhark', 'All twenty-four stones', 'futhark-title'));
      var grid = h('div', { className: 'rune-scatter' });
      grid.appendChild(loadingState('The runes are settling…'));
      all.appendChild(grid);
      container.appendChild(all);

      API.runes()
        .then(function (data) {
          grid.innerHTML = '';
          var runes = (data && data.runes) || [];
          if (!runes.length) {
            grid.appendChild(emptyState('The casting table is bare.', 'The elder futhark awaits.'));
            return;
          }
          runes.forEach(function (rune) { grid.appendChild(stone(rune, false)); });
        })
        .catch(function () {
          grid.innerHTML = '';
          grid.appendChild(emptyState('Couldn’t reach the casting table.', 'The runes might need a moment.'));
        });
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();

  /* ══════════════════════════════════════════════════════
     THE ARCHIVES — descending through truth
     ══════════════════════════════════════════════════════ */

  screens.evidence = (function () {
    var el_screen;
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-evidence' });
      main.appendChild(el_screen);
    }
    function enter() {
      el_screen.innerHTML = '<div class="wrap band archives-room" id="archives-content"></div>';
      var container = el_screen.querySelector('#archives-content');
      container.appendChild(loadingState('Descending into the archives\u2026'));

      Promise.all([
        API.world().catch(function () { return null; }),
        API.aspects().catch(function () { return null; }),
        API.resolved().catch(function () { return null; }),
        API.weave().catch(function () { return { events: [] }; }),
        API.trace().catch(function () { return { events: [] }; }),
        API.sparkHealth().catch(function () { return { ok: false, spark: 'unavailable' }; })
      ]).then(function (results) {
        container.innerHTML = '';
        var world = results[0], aspects = results[1], resolved = results[2],
            weave = results[3], trace = results[4], spark = results[5];

        var rl = residentLine('evidence');
        if (rl) container.appendChild(rl);

        var introRow = h('div', { className: 'spot-row' });
        introRow.appendChild(h('p', { className: 'archives-intro',
          textContent: 'Each step goes further down. Start at the surface; go as deep as you need.' }));
        introRow.appendChild(spot('skuld-point-stairs', 'spot--inline'));
        container.appendChild(introRow);

        addLevel(container, 'What is true', function (box) {
          if (world && world.title) {
            box.innerHTML = '<p class="evidence-title">' + esc(world.title) + '</p>';
            if (world.creed) box.innerHTML += '<p class="evidence-creed">' + esc(world.creed) + '</p>';
          } else {
            box.innerHTML = '<p class="evidence-empty">No world loaded.</p>';
          }
        });

        addLevel(container, 'Where this comes from', function (box) {
          var parts = [];
          if (aspects && aspects.pack) parts.push('Pack: ' + esc(aspects.pack.name));
          if (aspects && aspects.act) parts.push('Act: ' + esc(aspects.act.title || aspects.act.id));
          if (world && world.phases) parts.push('Phases: ' + esc(world.phases.join(', ')));
          if (world && world.surface) parts.push('Surface: ' + esc(world.surface));
          box.innerHTML = parts.length
            ? parts.map(function (p) { return '<p>' + p + '</p>'; }).join('')
            : '<p class="evidence-empty">No context available.</p>';
        });

        addLevel(container, 'The evidence', function (box) {
          var parts = [];
          if (resolved && resolved.description) parts.push('<p><strong>Description:</strong> ' + esc(resolved.description) + '</p>');
          if (resolved && resolved.phases) {
            Object.keys(resolved.phases).forEach(function (k) {
              parts.push('<p><strong>' + esc(k) + ':</strong> ' + esc(resolved.phases[k]) + '</p>');
            });
          }
          if (weave && weave.events && weave.events.length) {
            parts.push('<p><strong>Weave events:</strong> ' + weave.events.length + '</p>');
          }
          box.innerHTML = parts.length ? parts.join('')
            : '<p class="evidence-empty">No evidence yet.</p>';
        });

        addLevel(container, 'The engine', function (box) {
          var parts = [];
          parts.push('<p><strong>Spark:</strong> ' + esc(spark.spark || 'unknown') + '</p>');
          if (spark.url) parts.push('<p><strong>Spark URL:</strong> ' + esc(spark.url) + '</p>');
          if (spark.profile) parts.push('<p><strong>Profile:</strong> ' + esc(spark.profile) + '</p>');
          if (trace && trace.events && trace.events.length) parts.push('<p><strong>Trace events:</strong> ' + trace.events.length + '</p>');
          box.innerHTML = parts.join('');
        });

        addLevel(container, 'Raw truth', function (box) {
          var raw = { world: world, aspects: aspects, resolved: resolved, spark: spark };
          box.innerHTML = '<details class="evidence-raw"><summary>Show the raw truth (JSON)</summary>'
            + '<pre tabindex="0" aria-label="Raw truth, as JSON">' + esc(JSON.stringify(raw, null, 2)) + '</pre></details>';
        });
      });
    }

    var STEP_NOTES = { 3: 'this step has opinions' };
    function addLevel(container, title, renderFn) {
      var depth = container.querySelectorAll('.evidence-level').length + 1;
      var section = h('section', { className: 'carved evidence-level evidence-level--' + depth });
      var head = h('div', { className: 'evidence-level__head' });
      head.appendChild(h('span', { className: 'label', textContent: 'Step ' + depth + (depth === 1 ? ' \u00B7 the surface' : depth === 5 ? ' \u00B7 the bottom' : '') }));
      head.appendChild(h('h3', { className: 'evidence-level__heading', textContent: title }));
      if (STEP_NOTES[depth]) head.appendChild(h('span', { className: 'door-note', textContent: STEP_NOTES[depth] }));
      section.appendChild(head);
      var content = h('div', { className: 'evidence-level__content' });
      renderFn(content);
      section.appendChild(content);
      container.appendChild(section);
    }

    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();

  /* ══════════════════════════════════════════════════════
     THE HALL — a keepsake wall of what you have kept
     ══════════════════════════════════════════════════════ */

  screens.hall = (function () {
    var el_screen;
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-hall' });
      main.appendChild(el_screen);
    }
    function enter() {
      el_screen.innerHTML = '<div class="wrap band hall-room" id="hall-content"></div>';
      firstWalk.attempt('hall');
      var container = el_screen.querySelector('#hall-content');
      container.appendChild(loadingState('The ferry is bringing the keepsakes\u2026'));

      Promise.all([
        API.world().catch(function () { return null; }),
        API.journal().catch(function () { return { entries: [] }; }),
        API.vault().catch(function () { return { items: [], starred: [] }; }),
        API.starred().catch(function () { return { starred: [] }; })
      ]).then(function (results) {
        container.innerHTML = '';
        var world = results[0], journalData = results[1], vaultData = results[2], starredData = results[3];

        var rl = residentLine('hall');
        if (rl) container.appendChild(rl);

        // The creed — framed above the studio door
        var rule = (world && (world.creed || world.title)) || '';
        if (rule) {
          container.appendChild(h('div', { className: 'hall-plaque', textContent: rule }));
        }

        // The world behind the glass — the town as it really stands
        var win = worldWindow(world);
        if (win) container.appendChild(win);

        // The fire keeps watch — real engine events, echoed quietly
        container.appendChild(watchStrip());

        var anyKept = false;

        // Keepsakes the ferry brought in
        var ferried = (starredData && starredData.starred) || [];
        if (ferried.length) {
          anyKept = true;
          container.appendChild(keepsakeShelf(
            'what the ferry brought in',
            ferried.map(function (k) {
              return { name: k.name || 'Something kept', note: k.lore || k.kind || '' };
            }),
            '\u2726'
          ));
        }

        // Pressed leaves from the chronicle
        var entries = Array.isArray(journalData) ? journalData : ((journalData && journalData.entries) || []);
        var pressed = entries.filter(function (e) { return e.starred || e.star; });
        if (pressed.length) {
          anyKept = true;
          container.appendChild(keepsakeShelf(
            'pressed leaves from the chronicle',
            pressed.map(function (e) {
              return { name: truncate(chronicleLine(e).text || '', 90), note: formatTime(e.timestamp || e.time || e.at) };
            }),
            '\u2767'
          ));
        }

        // Keepsakes on the shelf
        var kept = ((vaultData && vaultData.items) || []).filter(function (item) { return item.starred || item.star; });
        if (!kept.length && vaultData && vaultData.starred && vaultData.starred.length) {
          kept = vaultData.starred.map(function (k) {
            return { name: k.name || 'Something kept', lore: k.lore || '' };
          });
        }
        if (kept.length) {
          anyKept = true;
          container.appendChild(keepsakeShelf(
            'keepsakes on the shelf',
            kept.map(function (k) { return { name: k.name || k.title || 'Something kept', note: k.lore || '' }; }),
            '\u2726'
          ));
        }

        if (!anyKept) {
          container.appendChild(emptyState(
            'The hall is quiet.\nBut it remembers what you love.',
            'Star something you\u2019ve made \u2014 the ferry will bring it here.',
            true
          ));
        }

        // The household — who lives here
        var house = h('div', { className: 'hall-household' });
        var houseHead = h('div', { className: 'spot-row' });
        houseHead.appendChild(h('div', { className: 'hall-household__heading', textContent: 'The household' }));
        houseHead.appendChild(spot('ratatoskr-large-envelope', 'spot--inline'));
        house.appendChild(houseHead);
        house.appendChild(h('p', { className: 'hall-household__note',
          textContent: 'One engine, many faces. Each room is tended by someone who knows its craft.' }));
        var list = h('div', { className: 'hall-household__list' });
        Object.keys(RESIDENTS).forEach(function (key) {
          var res = RESIDENTS[key];
          var row = h('button', { className: 'hall-household__r', type: 'button' });
          row.appendChild(portrait(key, res, 'hall-household__face'));
          row.appendChild(h('span', { className: 'hall-household__name', textContent: res.name }));
          row.appendChild(h('span', { className: 'hall-household__craft', textContent: res.craft }));
          // Each face is a door into their room's folio
          row.addEventListener('click', function () { openFolio(key, row); });
          list.appendChild(row);
        });
        house.appendChild(list);
        container.appendChild(house);
      });
    }

    function worldWindow(w) {
      if (!w || !w.map || !w.map.length || !w.legend) return null;
      var phase = (w.phases && w.phases.length) ? w.phases[0] : 'dusk';
      var glass = h('div', { className: 'hall-window hall-window--' + phase });
      glass.appendChild(h('div', { className: 'hall-window__title', textContent: 'the town, at ' + phase }));
      var cols = w.map[0] ? w.map[0].length : 0;
      var frame = h('div', { className: 'hall-window__scene', role: 'img',
        'aria-label': 'A framed window looking out at ' + (w.title || 'this world')
          + ' at ' + phase + ' \u2014 ' + w.map.length + ' rows by ' + cols + ' columns' });
      var hero = w.hero_start || [1, 1];
      var speakers = w.speakers || [];
      var sanctuary = w.sanctuary_tiles || [];
      w.map.forEach(function (ln, r) {
        var row = h('div', { className: 'hall-window__row' });
        ln.split('').forEach(function (ch, c) {
          var t = h('span', { className: 'hall-window__tile'
            + (sanctuary.indexOf(ch) !== -1 ? ' hall-window__tile--holy' : '') });
          var spec = w.legend[ch] || {};
          if (spec.base && spec.base.length) t.style.background = spec.base[0];
          if (spec.solid === true) t.classList.add('hall-window__tile--solid');
          if (hero && hero[0] === c && hero[1] === r) {
            t.appendChild(h('span', { className: 'hall-window__dot hall-window__dot--hero' }));
          }
          row.appendChild(t);
        });
        frame.appendChild(row);
      });
      speakers.forEach(function (s) {
        var at = s.at;
        if (!at || at.length < 2) return;
        var row = frame.childNodes[at[1]];
        if (!row) return;
        var tile = row.childNodes[at[0]];
        if (tile) tile.appendChild(h('span', { className: 'hall-window__dot hall-window__dot--speaker' }));
      });
      glass.appendChild(frame);
      glass.appendChild(h('p', { className: 'hall-window__caption',
        textContent: (w.title || 'the town') + ' \u2014 where the story is walked, not drawn' }));
      return glass;
    }

    function watchStrip() {
      var sec = h('section', { className: 'watch-strip' });
      sec.appendChild(h('h3', { className: 'watch-strip__title', textContent: 'the fire keeps watch' }));
      sec.appendChild(h('p', { className: 'watch-strip__hint',
        textContent: 'A quiet echo of what actually ran \u2014 each whisper is a true engine event, carried here by the squirrel.' }));
      var list = h('div', { className: 'watch-strip__list' });
      watch.strip = list;
      watch.buffer.forEach(function (b) { list.appendChild(b.el); });
      sec.appendChild(list);
      return sec;
    }

    function keepsakeShelf(label, items, mark) {
      var shelf = h('div', { className: 'hall-shelf' });
      shelf.appendChild(h('div', { className: 'hall-shelf__label', textContent: label }));
      var row = h('div', { className: 'hall-row' });
      items.forEach(function (item) {
        var k = h('button', { className: 'hall-keepsake', type: 'button' });
        k.appendChild(h('span', { className: 'hall-keepsake__mark', 'aria-hidden': 'true', textContent: mark }));
        var body = h('div', { className: 'hall-keepsake__body' });
        body.appendChild(h('span', { className: 'hall-keepsake__name', textContent: item.name }));
        if (item.note) body.appendChild(h('span', { className: 'hall-keepsake__note', textContent: item.note }));
        k.appendChild(body);
        // A kept thing is a door: press it and ask the ferry about it
        k.addEventListener('click', function () {
          openFolio('hall', k);
          folioInput.value = 'Tell me about ' + item.name + '.';
          folioInput.focus();
        });
        row.appendChild(k);
      });
      shelf.appendChild(row);
      return shelf;
    }

    function leave() {
      watch.strip = null;
    }
    return { init: init, enter: enter, leave: leave };
  })();

  /* ══════════════════════════════════════════════════════
     SETTINGS — the boiler room (plain is kindness)
     ══════════════════════════════════════════════════════ */

  screens.settings = (function () {
    // VEFR_PREFS is the one canonical voice for how the studio reads
    // and moves: it writes the data-prefs tokens the foundation and
    // theme branch on. The boiler room just points at it.
    var el_screen,
        P = window.VEFR_PREFS,
        current = (P && P.get) ? P.get() : { contrast: 'm', font: 'atkinson', motion: 'off' };
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-settings' });
      main.appendChild(el_screen);
    }
    function enter() {
      el_screen.innerHTML = '<div class="wrap band settings-room" id="settings-content"></div>';
      var container = el_screen.querySelector('#settings-content');

      var boilerRow = h('div', { className: 'spot-row' });
      boilerRow.appendChild(h('p', { className: 'archives-intro',
        textContent: 'The boiler room. Even a loved studio keeps its pipes plain.' }));
      boilerRow.appendChild(spot('volundr-pipe-with-bolt', 'spot--inline'));
      container.appendChild(boilerRow);
      var rl = residentLine('settings');
      if (rl) container.appendChild(rl);

      // Spark, the little local brain, has a face: Bolt. The card says
      // in words whether Spark is running, and how he is doing.
      var bolt = h('section', { className: 'settings-card spark-card', 'aria-labelledby': 'spark-title' });
      bolt.appendChild(portrait('spark', { name: 'Bolt, the face of Spark' }, 'spark-card__face'));
      var boltImg = bolt.querySelector('.spark-card__face img');
      var boltText = h('div', { className: 'spark-card__text' });
      boltText.appendChild(h('h3', { className: 'settings-card__title', id: 'spark-title', textContent: 'Bolt \u00B7 Spark, the little local brain' }));
      var boltStatus = h('p', { className: 'spark-card__status', role: 'status', textContent: 'checking on Bolt\u2026' });
      if (boltImg) boltImg.src = ART + 'poses/bolt-thinking.webp';
      boltText.appendChild(boltStatus);
      boltText.appendChild(h('p', { className: 'settings-card__note',
        textContent: 'Spark is a small model that runs on this machine and helps every resident. Nothing leaves the house.' }));
      bolt.appendChild(boltText);
      container.appendChild(bolt);
      API.sparkHealth()
        .then(function (sp) {
          if (sp && sp.ok) {
            bolt.classList.add('spark-card--awake');
            if (boltImg) boltImg.src = ART + 'poses/bolt-awake-wave.webp';
            boltStatus.textContent = 'Awake. Spark is running' + (sp.profile ? ' (' + sp.profile + ' profile)' : '') + '.';
          } else {
            boltStatus.textContent = 'Napping on the boiler. Spark is not running on this machine yet.';
            if (boltImg) boltImg.src = ART + 'poses/bolt-boiler-nap.webp';
          }
        })
        .catch(function () {
          boltStatus.textContent = 'Unplugged. Spark could not be reached.';
          if (boltImg) boltImg.src = ART + 'poses/bolt-unplugged.webp';
        });

      // Appearance — one voice for all of it: the prefs engine
      current = (P && P.get) ? P.get() : current;

      var themeCard = makeCard('How it feels');
      addOptionRow(themeCard, 'Mood', [
        { label: 'Warm & Easy', value: 'm' },
        { label: 'Bright & Clear', value: 'high' },
        { label: 'Nothing Hides', value: 'ultra' }
      ], 'contrast');
      container.appendChild(themeCard);

      // Reading
      var fontCard = makeCard('How it reads');
      addOptionRow(fontCard, 'Font', [
        { label: 'Atkinson', value: 'atkinson' },
        { label: 'OpenDyslexic', value: 'opendyslexic' },
        { label: 'Serif', value: 'serif' },
        { label: 'System', value: 'system' }
      ], 'font');
      container.appendChild(fontCard);

      // Motion
      var motionCard = makeCard('How it moves');
      addOptionRow(motionCard, 'Motion', [
        { label: 'Off', value: 'off' },
        { label: 'Subtle', value: 'subtle' },
        { label: 'Full', value: 'full' }
      ], 'motion');
      container.appendChild(motionCard);

      // Sound — off by default; every sound pairs with a visible event
      var soundCard = makeCard('How it sounds');
      var soundOn = !!(current.sound && (current.sound.effects > 0 || current.sound.ambience > 0));
      var soundRow = h('div', { className: 'settings-row' });
      soundRow.appendChild(h('span', { className: 'settings-row__label', textContent: 'Hearth sound' }));
      var soundOpts = h('div', { className: 'settings-row__options' });
      [{ label: 'Off', on: false }, { label: 'On', on: true }].forEach(function (opt) {
        var btn = h('button', {
          className: 'settings-option' + (soundOn === opt.on ? ' settings-option--active' : ''),
          textContent: opt.label
        });
        btn.addEventListener('click', function () {
          if (P && P.set) {
            var s = opt.on ? { effects: 0.7, ambience: 0.5, speech: 0.8 } : { effects: 0, ambience: 0, speech: 0 };
            P.set({ sound: s });
            current = P.get();
          }
          soundOpts.querySelectorAll('.settings-option').forEach(function (b) { b.classList.remove('settings-option--active'); });
          btn.classList.add('settings-option--active');
          if (opt.on && studioAudio) { studioAudio.unlock(); studioAudio.ambient(true); }
          if (!opt.on && studioAudio) studioAudio.ambient(false);
        });
        soundOpts.appendChild(btn);
      });
      soundRow.appendChild(soundOpts);
      soundCard.appendChild(soundRow);
      soundCard.appendChild(h('p', { className: 'settings-card__note',
        textContent: 'Every sound is paired with something you can see \u2014 the clank with the ferry note, the squeak with a whisper. Off until you say otherwise.' }));
      container.appendChild(soundCard);

      // Learning — the walk and the sheet stay callable any time
      var learnCard = makeCard('The house, on paper');
      var learnA = h('div', { className: 'settings-row' });
      learnA.appendChild(h('span', { className: 'settings-row__label', textContent: 'The first walk' }));
      var learnAOpts = h('div', { className: 'settings-row__options' });
      var walkBtn = h('button', { className: 'btn btn--warm settings-row__btn', type: 'button',
        textContent: 'walk the house again' });
      walkBtn.addEventListener('click', function () { if (firstWalk) firstWalk.reset(); });
      learnAOpts.appendChild(walkBtn);
      learnA.appendChild(learnAOpts);
      learnCard.appendChild(learnA);
      var learnB = h('div', { className: 'settings-row' });
      learnB.appendChild(h('span', { className: 'settings-row__label', textContent: 'How to read this house' }));
      var learnBOpts = h('div', { className: 'settings-row__options' });
      var sheetBtn = h('button', { className: 'btn btn--warm settings-row__btn', type: 'button',
        textContent: 'open the sheet' });
      sheetBtn.addEventListener('click', function () { if (firstWalk) firstWalk.openSheet(); });
      learnBOpts.appendChild(sheetBtn);
      learnB.appendChild(learnBOpts);
      learnCard.appendChild(learnB);
      container.appendChild(learnCard);

      // Engine
      var engineCard = makeCard('The engine');
      API.health()
        .then(function (data) {
          addInfoRow(engineCard, 'Status', data.ok ? 'Healthy' : 'Unavailable');
          if (data.purpose) addInfoRow(engineCard, 'Purpose', data.purpose);
        })
        .catch(function () { addInfoRow(engineCard, 'Status', 'Disconnected'); });
      API.sparkHealth()
        .then(function (data) {
          addInfoRow(engineCard, 'Spark', data.spark || 'unavailable');
          if (data.profile) addInfoRow(engineCard, 'Profile', data.profile);
        })
        .catch(function () { addInfoRow(engineCard, 'Spark', 'unavailable'); });
      container.appendChild(engineCard);
    }

    function makeCard(title) {
      var card = h('div', { className: 'settings-card' });
      card.appendChild(h('h3', { className: 'settings-card__title', textContent: title }));
      return card;
    }
    function addOptionRow(card, label, options, prefKey) {
      var row = h('div', { className: 'settings-row' });
      row.appendChild(h('span', { className: 'settings-row__label', textContent: label }));
      var opts = h('div', { className: 'settings-row__options' });
      options.forEach(function (opt) {
        var active = current[prefKey] === opt.value;
        var btn = h('button', {
          className: 'settings-option' + (active ? ' settings-option--active' : ''),
          textContent: opt.label
        });
        btn.addEventListener('click', function () {
          if (P && P.set) {
            var patch = {};
            patch[prefKey] = opt.value;
            P.set(patch);
            current = P.get();
          }
          opts.querySelectorAll('.settings-option').forEach(function (b) { b.classList.remove('settings-option--active'); });
          btn.classList.add('settings-option--active');
        });
        opts.appendChild(btn);
      });
      row.appendChild(opts);
      card.appendChild(row);
    }
    function addInfoRow(card, label, value) {
      var row = h('div', { className: 'settings-row' });
      row.appendChild(h('span', { className: 'settings-row__label', textContent: label }));
      row.appendChild(h('span', { className: 'settings-row__value', textContent: value }));
      card.appendChild(row);
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();

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
  });

  // The world hangs its name over the door; the lantern lights
  API.world()
    .then(function (data) {
      inhabitWorld(data);
    })
    .catch(function () {
      setLantern(false, 'the storyteller can\u2019t be reached');
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

})();