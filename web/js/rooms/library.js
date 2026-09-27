/* vefr/web/js/rooms/library.js: The Library.
 * Split out of app.js (2026-09-27); the shared studio helpers come from
 * window.VEFR_STUDIO, which app.js builds. Loaded after app.js, before boot.js. */
(function (S) {
  'use strict';

  var screens = S.screens, API = S.API, ART = S.ART, emptyState = S.emptyState, h = S.h,
      loadingState = S.loadingState, main = S.main, residentLine = S.residentLine, spot = S.spot;

  /* ══════════════════════════════════════════════════════
     THE LIBRARY — Fróði's shelves: the studio's books and the world's
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
      page.innerHTML = L.renderPage(b.pages[open.page], window.VEFR_GLOSSARY);
      reader.appendChild(page);
      /* Tap a real word for its meaning (Gee: explicit information on demand). */
      var card = h('div', { className: 'lib-term-card', role: 'status', 'aria-live': 'polite', hidden: true });
      reader.appendChild(card);
      page.addEventListener('click', function (e) {
        var btn = e.target.closest && e.target.closest('.lib-term');
        if (!btn) return;
        var was = btn.getAttribute('aria-expanded') === 'true';
        page.querySelectorAll('.lib-term').forEach(function (x) { x.setAttribute('aria-expanded', 'false'); });
        if (was) { card.hidden = true; return; }
        var key = btn.getAttribute('data-term');
        var g = (window.VEFR_GLOSSARY || {})[key];
        if (!g) return;
        btn.setAttribute('aria-expanded', 'true');
        card.innerHTML = '';
        card.appendChild(h('p', { className: 'lib-term-card__word', textContent: key }));
        card.appendChild(h('p', { className: 'lib-term-card__plain', textContent: g.plain }));
        if (g.vefr) card.appendChild(h('p', { className: 'lib-term-card__vefr', textContent: 'In VEFR: ' + g.vefr }));
        var close = h('button', { className: 'cta cta--line lib-term-card__close', type: 'button', textContent: 'Got it' });
        close.addEventListener('click', function () {
          card.hidden = true; btn.setAttribute('aria-expanded', 'false'); btn.focus();
        });
        card.appendChild(close);
        card.hidden = false;
      });
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
      /* books and the glossary arrive together, so the first page is already tappable */
      Promise.all([API.library(), window.VEFR_GLOSSARY_READY || Promise.resolve()])
        .then(function (both) { return both[0]; })
        .then(function (data) {
          shelves.innerHTML = '';
          var ladder = spot('frodi-library-ladder', 'spot--inline lib-ladder');
          var intro = h('div', { className: 'spot-row' });
          intro.appendChild(h('p', { className: 'archives-intro',
            textContent: 'Books are written by people, never by the model. A world keeps its own in its library folder.' }));
          intro.appendChild(ladder);
          shelves.appendChild(intro);
          var worldName = data.world || 'this world';
          var empty = h('p', { className: 'lib-empty',
            textContent: worldName + ' has no books yet. Write one as a markdown file in the pack’s library/ folder; it will appear here.' });
          shelves.appendChild(shelf('Found in ' + worldName, (data.books || []).length + ' written', data.books || [], empty));
          var studio = data.studio || [];
          var howVefr = studio.filter(function (b) { return b.shelf === 'how-vefr-works'; });
          var handbook = studio.filter(function (b) { return b.shelf !== 'how-vefr-works'; });
          shelves.appendChild(shelf('How games are made', 'the studio handbook', handbook, h('p', { className: 'lib-empty', textContent: 'The studio shelf is empty.' })));
          if (howVefr.length) shelves.appendChild(shelf('How VEFR works', 'real words for what\u2019s inside', howVefr, null));
        })
        .catch(function () {
          shelves.innerHTML = '';
          shelves.appendChild(emptyState('Couldn’t load the Library.', 'Try again in a moment.'));
        });
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();
})(window.VEFR_STUDIO);
