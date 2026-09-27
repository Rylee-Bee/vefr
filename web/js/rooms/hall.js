/* vefr/web/js/rooms/hall.js: The Hall.
 * Split out of app.js (2026-09-27); the shared studio helpers come from
 * window.VEFR_STUDIO, which app.js builds. Loaded after app.js, before boot.js. */
(function (S) {
  'use strict';

  var screens = S.screens, API = S.API, RESIDENTS = S.RESIDENTS, chronicleLine = S.chronicleLine,
      emptyState = S.emptyState, firstWalk = S.firstWalk, formatTime = S.formatTime, h = S.h,
      loadingState = S.loadingState, main = S.main, openFolio = S.openFolio, portrait = S.portrait,
      residentLine = S.residentLine, spot = S.spot, truncate = S.truncate, watch = S.watch;

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
      container.appendChild(loadingState('Loading what you’ve kept…'));

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
            'Just arrived',
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
            'Kept from the Chronicle',
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
            'Kept items',
            kept.map(function (k) { return { name: k.name || k.title || 'Something kept', note: k.lore || '' }; }),
            '\u2726'
          ));
        }

        if (!anyKept) {
          container.appendChild(emptyState(
            'Nothing kept yet.',
            'Press Keep in the Hall on anything you want to find again.',
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
        textContent: (w.title || 'the town') + ', where the story happens in play' }));
      return glass;
    }

    function watchStrip() {
      var sec = h('section', { className: 'watch-strip' });
      sec.appendChild(h('h3', { className: 'watch-strip__title', textContent: 'Engine activity' }));
      sec.appendChild(h('p', { className: 'watch-strip__hint',
        textContent: 'What the engine actually did, as it happened.' }));
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
          S.folioInput.value = 'Tell me about ' + item.name + '.';
          S.folioInput.focus();
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
})(window.VEFR_STUDIO);
