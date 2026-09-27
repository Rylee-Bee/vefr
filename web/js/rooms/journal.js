/* vefr/web/js/rooms/journal.js: The Chronicle.
 * Split out of app.js (2026-09-27); the shared studio helpers come from
 * window.VEFR_STUDIO, which app.js builds. Loaded after app.js, before boot.js. */
(function (S) {
  'use strict';

  var screens = S.screens, API = S.API, KIND_MARKS = S.KIND_MARKS, actionsLine = S.actionsLine,
      chronicleLine = S.chronicleLine, emptyState = S.emptyState, ferryNote = S.ferryNote,
      firstWalk = S.firstWalk, foldChronicle = S.foldChronicle, formatTime = S.formatTime, h = S.h,
      loadingState = S.loadingState, main = S.main, residentLine = S.residentLine,
      studioAudio = S.studioAudio, truncate = S.truncate;

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
      container.appendChild(loadingState('Opening the Chronicle…'));
      API.journal()
        .then(function (data) {
          container.innerHTML = '';
          var entries = Array.isArray(data) ? data : ((data && data.entries) || []);
          if (!entries.length) {
            container.appendChild(emptyState(
              'The Chronicle is empty.',
              'What happens in play will show up here.',
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
                  ferryNote('Already kept in the Hall.');
                } else {
                  studioAudio.squeak();
                  firstWalk.attempt('chronicle');
                  ferryNote('Ratatoskr is carrying “' + truncate(text || 'this moment', 36) + '” to the Hall…');
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
            'Couldn’t load the Chronicle.',
            'Try again in a moment.'
          ));
        });
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();
})(window.VEFR_STUDIO);
