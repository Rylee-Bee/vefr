/* vefr/web/js/rooms/floor.js: The Studio Floor.
 * Split out of app.js (2026-09-27); the shared studio helpers come from
 * window.VEFR_STUDIO, which app.js builds. Loaded after app.js, before boot.js. */
(function (S) {
  'use strict';

  var screens = S.screens, ART = S.ART, DEPARTMENTS = S.DEPARTMENTS, DOOR_NOTES = S.DOOR_NOTES,
      RESIDENTS = S.RESIDENTS, ROOM_BANNERS = S.ROOM_BANNERS, SCREEN_TITLES = S.SCREEN_TITLES,
      carved = S.carved, h = S.h, main = S.main;

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
})(window.VEFR_STUDIO);
