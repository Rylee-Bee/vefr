/* vefr/web/js/rooms/runes.js: The Casting Table.
 * Split out of app.js (2026-09-27); the shared studio helpers come from
 * window.VEFR_STUDIO, which app.js builds. Loaded after app.js, before boot.js. */
(function (S) {
  'use strict';

  var screens = S.screens, API = S.API, ART = S.ART, emptyState = S.emptyState,
      ferryNote = S.ferryNote, h = S.h, loadingState = S.loadingState, main = S.main,
      residentLine = S.residentLine, sectionHead = S.sectionHead, spot = S.spot,
      studioAudio = S.studioAudio;

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
          spread.appendChild(emptyState('Couldn’t cast the stones.', 'Try again in a moment.'));
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
            grid.appendChild(emptyState('No runes found.', 'Try again in a moment.'));
            return;
          }
          runes.forEach(function (rune) { grid.appendChild(stone(rune, false)); });
        })
        .catch(function () {
          grid.innerHTML = '';
          grid.appendChild(emptyState('Couldn’t load the runes.', 'Try again in a moment.'));
        });
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();
})(window.VEFR_STUDIO);
