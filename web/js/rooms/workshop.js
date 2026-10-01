/* vefr/web/js/rooms/workshop.js: The Desk.
 * Split out of app.js (2026-09-27); the shared studio helpers come from
 * window.VEFR_STUDIO, which app.js builds. Loaded after app.js, before boot.js. */
(function (S) {
  'use strict';

  var screens = S.screens, AMBIENCE = S.AMBIENCE, API = S.API, actionsLine = S.actionsLine,
      chronicleLine = S.chronicleLine, emptyState = S.emptyState, esc = S.esc,
      firstWalk = S.firstWalk, foldChronicle = S.foldChronicle, formatTime = S.formatTime, h = S.h,
      inhabitWorld = S.inhabitWorld, loadingState = S.loadingState, main = S.main,
      navigate = S.navigate, openFolio = S.openFolio, setLantern = S.setLantern,
      truncate = S.truncate;

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
        + '        <button class="cta cta--line" id="ws-weave-play" type="button" aria-describedby="ws-weave-status">Play it here</button>'
        + '        <span class="weave-status" id="ws-weave-status" role="status" aria-live="polite"></span>'
        + '        <a class="cta cta--line weave-action" id="ws-weave-download" download hidden>Download</a>'
        + '        <button class="cta cta--line weave-action" id="ws-weave-share" type="button" hidden>Share</button>'
        + '      </div>'
        + '      <p class="desk-tools__hint">One file, plays offline, no install. Send it to a friend.</p>'
        + '      <section class="weave-pane" id="ws-play-pane" hidden aria-label="Your game, playing here">'
        + '        <div class="weave-pane__bar">'
        + '          <span class="label">Playing in this page</span>'
        + '          <a class="cta cta--line weave-action" id="ws-play-open" href="#" target="_blank" rel="noopener">Open in a new tab</a>'
        + '        </div>'
        // Sandbox: measured in chromium, the woven player starts and walks
        // with `allow-scripts` alone (sandboxed localStorage calls are
        // wrapped and no-op), so every world uses the strict sandbox - the
        // pane can never reach the studio page or its origin.
        + '        <iframe class="weave-pane__frame" id="ws-play-frame" title="Your game, playing here" sandbox="allow-scripts"></iframe>'
        + '      </section>'
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
        window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('bell');
        firstWalk.attempt('bell');
        openFolio('workshop', e.currentTarget);
      });
      el_screen.querySelector('#ws-continue').addEventListener('click', continueStory);
      el_screen.querySelector('#ws-toggle-ctx').addEventListener('click', toggleContext);
      el_screen.querySelector('#ws-weave').addEventListener('click', makeShareable);
      el_screen.querySelector('#ws-weave-play').addEventListener('click', playHere);
      el_screen.querySelector('#ws-weave-share').addEventListener('click', shareWoven);
      el_screen.querySelector('#ws-evidence').addEventListener('click', function () { navigate('evidence'); });
      main.appendChild(el_screen);
    }

    function enter() { load(); }
    function leave() {}

    function load() {
      setContent(loadingState('The Storyteller is writing…'));
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
          setLantern(false, 'Storyteller offline');
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
          'Nothing has happened in this world yet.',
          'Ring for the Storyteller to begin.',
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
      btn.textContent = 'The Storyteller is writing…';
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
          window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('weave');
          dl.href = info.download_url;
          dl.setAttribute('download', info.name);
          dl.hidden = false;
          share.hidden = !canShareFiles();
          setWeaveStatus('Ready · ' + sizeWords(info.size_bytes));
        })
        .catch(function (err) {
          lastWoven = null;
          setWeaveStatus('Couldn’t build the shareable file. ' + (err && err.message ? err.message : 'Try again.'));
        })
        .finally(function () {
          btn.disabled = false;
        });
    }

    /* ── Play it here — the current world in a pane, no download ── */
    function playHere() {
      var btn = el_screen.querySelector('#ws-weave-play');
      var pane = el_screen.querySelector('#ws-play-pane');
      var frame = el_screen.querySelector('#ws-play-frame');
      var open = el_screen.querySelector('#ws-play-open');
      btn.disabled = true;
      setWeaveStatus('Weaving…');
      API.weaveBuild()
        .then(function (info) {
          lastWoven = info;
          window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('weave');
          var playUrl = '/api/builder/weave/play/' + encodeURIComponent(info.name);
          open.href = playUrl;
          // The name is stable for a whole day, so a cache-busting query
          // forces the pane to re-load a fresh weave even at the same URL.
          frame.onload = function () { frame.focus(); };
          frame.src = playUrl + '?at=' + Date.now();
          pane.hidden = false;
          setWeaveStatus('Playing · ' + sizeWords(info.size_bytes));
          /* The pane is really up: one event for the sticker book, one
             tick for the first walk. Both wait for a successful weave. */
          window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('play_here');
          firstWalk.attempt('play_here');
        })
        .catch(function (err) {
          lastWoven = null;
          setWeaveStatus('Couldn’t play it here. ' + (err && err.message ? err.message : 'Try again.'));
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
          setWeaveStatus('Couldn’t open sharing, so the file downloaded instead.');
        })
        .finally(function () {
          share.disabled = false;
        });
    }

    return { init: init, enter: enter, leave: leave };
  })();
})(window.VEFR_STUDIO);
