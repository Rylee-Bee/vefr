/* vefr - the dev board. The pack's generators laid out as cards.
 *
 * One column per generator: whispers, voices, forge, bell. Cards are
 * drawn from the mounted pack (/api/world, fetched once for the whole
 * page by web/state.js and shared as a promise); a column the pack
 * cannot fill falls back to a seeded neutral pool, so the board is
 * never empty and never storyful. Dragging a card to another column
 * re-homes it and persists on this device (localStorage) - a fresh
 * seed per browser makes the seeded run reproducible.
 *
 * Deterministic surface: no model calls live here. The right rail's
 * "try it" button calls the column's endpoint like the game's own
 * buttons do; when the engine does not answer it says so plainly.
 *
 * Contract: window.VEFR_BOARD.{init, state, move, generateStore}.
 * Shipped JS - machine-tested by tests/test_board.py executing this
 * file in a node vm (see tests/fixtures/board_harness.mjs).
 */
window.VEFR_BOARD = (function () {
  'use strict';

  var COLUMNS = ['whispers', 'voices', 'forge', 'bell'];

  var SEED_KEY = 'vefr-board-seed';
  var CARDS_KEY = 'vefr-board-cards';

  /* The neutral fallback pool. Norse-coded names by engine tradition,
     engine-neutral prose by the bone-strip law: nothing here names a
     specific pack's people or places. A mounted pack's own speakers
     always win over this pool. */
  var NEUTRAL = {
    names: ['Asa', 'Bo', 'Caer', 'Dagny', 'Eilif', 'Fria', 'Hjor',
            'Isak', 'Jara', 'Keld', 'Liv', 'Moga', 'Nyf', 'Pern'],
    whispers: ['the wind shifts', 'a light flickers', 'a sound fades',
               'a mark lingers', 'a path splits'],
    voices: ['speak softly', 'listen closely', 'watch carefully',
             'move swiftly', 'wait patiently'],
    forge: ['a small stone', 'a thin thread', 'a dull knife',
            'a soft cloth', 'an empty cup'],
    bell: ['a short note', 'a quiet chime', 'a faint ring',
           'a low hum', 'a quick tap']
  };

  /* What the right rail shows per column. Real routes, real shapes. */
  var API = {
    whispers: {
      title: 'a rumor',
      endpoint: '/api/rumor', method: 'POST',
      request: '{ "phase": "<the pack\u2019s phase>", "theme": null }',
      response: '{ "speaker": "...", "whisper": "...",\n  "hook": "...", "is_true": true }'
    },
    voices: {
      title: 'a speaker\u2019s line',
      endpoint: '/api/npc', method: 'POST',
      request: '{ "phase": "<the pack\u2019s phase>",\n  "speaker": "keeper | null" }',
      response: '{ "speaker": "...", "line": "..." }'
    },
    forge: {
      title: 'an item',
      endpoint: '/api/forge', method: 'POST',
      request: '{}',
      response: '{ "name": "...", "lore": "...",\n  "bond": "assigned | attuned | cold" }'
    },
    bell: {
      title: 'the bell\u2019s letter',
      endpoint: '/api/stefna', method: 'POST',
      request: '{}',
      response: '{ "letter": "..." }'
    }
  };

  var state = {
    seed: 0,
    world: null,
    cards: null,   /* { column: [card...] } - card: {id,name,content,edited} */
    selected: null,
    selectedEl: null
  };

  /* --- seeded randomness ------------------------------------------- */

  function readSeed() {
    var raw = null;
    try { raw = localStorage.getItem(SEED_KEY); } catch (err) { raw = null; }
    var seed = raw === null ? NaN : parseInt(raw, 10);
    if (isNaN(seed)) {
      seed = Math.floor(Math.random() * 1000000);
      try { localStorage.setItem(SEED_KEY, String(seed)); } catch (err) { /* no storage */ }
    }
    return seed;
  }

  function rng(seed) {
    var s = seed % 233280;
    if (s <= 0) s += 233280;
    return function () {
      s = (s * 9301 + 49297) % 233280;
      return s / 233280;
    };
  }

  function pick(r, list) {
    return list[Math.floor(r() * list.length)];
  }

  /* --- the card store ---------------------------------------------- */

  function loadStore() {
    var raw = null;
    try { raw = localStorage.getItem(CARDS_KEY); } catch (err) { raw = null; }
    if (!raw) return null;
    try {
      var parsed = JSON.parse(raw);
      var ok = parsed && typeof parsed === 'object'
        && COLUMNS.every(function (c) { return Array.isArray(parsed[c]); });
      if (ok) return parsed;
    } catch (err) { /* unreadable store - reseed below */ }
    return null;
  }

  function saveStore() {
    try {
      localStorage.setItem(CARDS_KEY, JSON.stringify(state.cards));
    } catch (err) { /* no storage - the board just won't persist */ }
  }

  /* One card per speaker in voices (the pack is the source of truth);
     five seeded cards everywhere else. A world without speakers gets
     two neutral filler cards so the column is not bare. */
  function generateStore(world, seed) {
    var r = rng(seed);
    var store = {};
    COLUMNS.forEach(function (col) {
      var list = [];
      if (col === 'voices') {
        var speakers = (world && world.speakers) || [];
        if (speakers.length) {
          speakers.forEach(function (sp) {
            list.push(makeCard(col, r, sp.name || 'speaker', firstSeed(sp, world, r)));
          });
        } else {
          for (var b = 0; b < 2; b++) list.push(fillerCard(col, world, r));
        }
      } else {
        for (var a = 0; a < 5; a++) list.push(fillerCard(col, world, r));
      }
      store[col] = list;
    });
    return store;
  }

  function firstSeed(speaker, world, r) {
    var seeds = (speaker && speaker.seeds) || {};
    var phases = (world && world.phases) || [];
    if (phases.length && seeds[phases[0]]) return seeds[phases[0]];
    for (var k in seeds) { if (seeds[k]) return seeds[k]; }
    return pick(r, NEUTRAL.voices);
  }

  function makeCard(col, r, name, content) {
    return {
      id: col + '-' + Math.floor(r() * 100000).toString(36),
      name: name,
      content: content,
      edited: null
    };
  }

  function fillerCard(col, world, r) {
    return makeCard(col, r,
      (world && world.title) || 'the world',
      pick(r, NEUTRAL[col]));
  }

  /* --- moves + persistence ------------------------------------------ */

  /* Re-home a card: find it by id in any column, move it to the end
     of toColumn, stamp it, persist, re-render. Returns true on a
     real move, false when the id or column is unknown. */
  function move(id, toCol) {
    if (!state.cards || COLUMNS.indexOf(toCol) === -1) return false;
    var card = null;
    var fromCol = null;
    COLUMNS.forEach(function (col) {
      var i = state.cards[col].findIndex(function (c) { return c.id === id; });
      if (i > -1) {
        card = state.cards[col].splice(i, 1)[0];
        fromCol = col;
      }
    });
    if (!card || fromCol === null) return false;
    card.edited = Date.now();
    state.cards[toCol].push(card);
    saveStore();
    render();
    return true;
  }

  /* --- render -------------------------------------------------------- */

  function cardEl(card) {
    var el = document.createElement('div');
    el.className = 'board-card';
    el.draggable = true;
    /* Keyboard-reachable like every other target in the chrome:
       focusable, button semantics, Enter/Space selects. */
    el.tabIndex = 0;
    el.setAttribute('role', 'button');
    el.dataset.id = card.id;
    el.textContent = card.name + ' \u2014 ' + card.content;
    var when = document.createElement('span');
    when.className = 'when';
    when.textContent = card.edited
      ? 'moved ' + new Date(card.edited).toLocaleString()
      : 'seeded';
    el.appendChild(when);
    el.addEventListener('dragstart', function (e) {
      e.dataTransfer.setData('text/plain', card.id);
    });
    el.addEventListener('click', function () { select(card, el); });
    el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        select(card, el);
      }
    });
    return el;
  }

  function render() {
    COLUMNS.forEach(function (col) {
      var holder = document.getElementById('board-' + col);
      if (!holder) return;
      holder.innerHTML = '';
      (state.cards[col] || []).forEach(function (card) {
        holder.appendChild(cardEl(card));
      });
    });
  }

  /* --- the right rail ------------------------------------------------ */

  function select(card, el) {
    if (state.selectedEl) {
      state.selectedEl.className = 'board-card';
      state.selectedEl.setAttribute('aria-pressed', 'false');
    }
    state.selected = card;
    state.selectedEl = el;
    el.setAttribute('aria-pressed', 'true');
    var col = columnOf(card.id);
    var rail = document.getElementById('board-rail');
    if (!rail) return;
    rail.hidden = false;
    /* Move focus with the disclosure, so keyboard users land in the
       rail instead of continuing to tab through hidden columns. */
    if (typeof rail.focus === 'function') rail.focus();
    var api = API[col] || API.whispers;
    setText('rail-name', card.name);
    setText('rail-meta', api.title + ' \u00b7 column: ' + col);
    setText('rail-request', api.method + ' ' + api.endpoint + '\n' + api.request);
    setText('rail-response', api.response);
    setText('rail-templates', 'the pack\u2019s own voice fragments - read-only until the wire-up');
    setText('rail-try-out', '');
    el.className = 'board-card board-card-selected';
  }

  function columnOf(id) {
    var found = 'whispers';
    COLUMNS.forEach(function (col) {
      if ((state.cards[col] || []).some(function (c) { return c.id === id; })) {
        found = col;
      }
    });
    return found;
  }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  /* Try it calls the column's endpoint exactly like the game's own
     buttons do. No answer is answered honestly - preview only. */
  function tryIt() {
    var card = state.selected;
    if (!card) return;
    var col = columnOf(card.id);
    var api = API[col] || API.whispers;
    var wrap = (window.VEFR_SESSION && window.VEFR_SESSION.wrap)
      || function (u) { return u; };
    var out = document.getElementById('rail-try-out');
    if (!out) return;
    out.textContent = 'asking\u2026';
    fetch(wrap(api.endpoint), {
      method: api.method,
      headers: { 'Content-Type': 'application/json' },
      body: api.method === 'POST' ? '{}' : undefined
    })
      .then(function (r) {
        if (!r.ok) throw new Error('bad answer');
        return r.json();
      })
      .then(function (body) {
        out.textContent = JSON.stringify(body, null, 2);
      })
      .catch(function () {
        out.textContent = 'no answer from the engine - preview only';
      });
  }

  /* --- boot ----------------------------------------------------------- */

  function getWorld() {
    if (window.OLD-STATE-GLOBAL && typeof window.OLD-STATE-GLOBAL.world === 'function') {
      return window.OLD-STATE-GLOBAL.world();
    }
    return fetch('/api/world').then(function (r) { return r.json(); });
  }

  var booted = false;

  function init() {
    /* One boot, ever - not "cards exist" (they arrive async, so a
       second boot path racing the first would double-fetch). */
    if (booted) return;
    booted = true;
    state.seed = readSeed();
    var stored = loadStore();
    if (stored) {
      state.cards = stored;
      render();
      getWorld().then(function (w) {
        state.world = w;
        render();
      }).catch(function () { /* no world - the stored cards still stand */ });
    } else {
      getWorld().then(function (w) {
        state.world = w;
        state.cards = generateStore(w, state.seed);
        saveStore();
        render();
      }).catch(function () { /* no world - the board stays bare */ });
    }
    wireDropTargets();
    var tryBtn = document.getElementById('rail-try');
    if (tryBtn) tryBtn.addEventListener('click', tryIt);
  }

  function wireDropTargets() {
    COLUMNS.forEach(function (col) {
      var holder = document.getElementById('board-' + col);
      if (!holder) return;
      holder.addEventListener('dragover', function (e) {
        e.preventDefault();
        holder.className = 'board-cards board-drag-over';
      });
      holder.addEventListener('dragleave', function () {
        holder.className = 'board-cards';
      });
      holder.addEventListener('drop', function (e) {
        e.preventDefault();
        holder.className = 'board-cards';
        var id = e.dataTransfer.getData('text/plain');
        if (id) move(id, col);
      });
    });
  }

  return {
    init: init,
    move: move,
    render: render,
    state: state,
    generateStore: generateStore,
    COLUMNS: COLUMNS,
    NEUTRAL: NEUTRAL
  };
})();

/* Lazy boot: the board lives in the Dev zone, so it asks for the
   world the first time its tab is shown - never on the Play path.
   Scripts load at the end of <body>, so the elements exist here. */
(function () {
  'use strict';
  if (typeof document === 'undefined' || !document.getElementById) return;
  var section = document.getElementById('view-board');
  if (!section || !window.VEFR_BOARD) return;
  var booted = false;
  window.addEventListener('old-name:board', function () {
    if (!booted) {
      booted = true;
      window.VEFR_BOARD.init();
    }
  });
  if (!section.hidden) window.VEFR_BOARD.init();
})();
