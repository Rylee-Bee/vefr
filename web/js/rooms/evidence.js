/* vefr/web/js/rooms/evidence.js: The Archives.
 * Split out of app.js (2026-09-27); the shared studio helpers come from
 * window.VEFR_STUDIO, which app.js builds. Loaded after app.js, before boot.js. */
(function (S) {
  'use strict';

  var screens = S.screens, API = S.API, esc = S.esc, h = S.h, loadingState = S.loadingState,
      main = S.main, residentLine = S.residentLine, spot = S.spot;

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
      container.appendChild(loadingState('Opening the Archives…'));

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
})(window.VEFR_STUDIO);
