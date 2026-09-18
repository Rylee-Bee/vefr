/* vefr/web/screens/workshop.js — the place where something is being made.
 *
 * The Workshop is the heart of VEFR. It holds:
 * - the current world's story/workspace
 * - AI collaboration context
 * - one obvious continuation action
 *
 * It should feel like sitting down at a writing desk
 * where the world is already in progress.
 */

(function () {
  'use strict';

  var shell = window.VEFR_SHELL;

  var el = null;
  var currentWorld = null;
  var journalEntries = [];

  /* ── Template ──────────────────────────────────────────── */

  function render() {
    el = document.createElement('div');
    el.className = 'vefr-screen';
    el.id = 'screen-workshop';
    el.innerHTML = ''
      + '<div class="workshop">'
      + '  <div class="workshop__story">'
      + '    <div class="workshop__story-header">'
      + '      <h2 class="workshop__chapter" id="ws-chapter"></h2>'
      + '      <span class="workshop__wordcount" id="ws-wordcount"></span>'
      + '    </div>'
      + '    <div class="workshop__story-body" id="ws-story">'
      + '      <div class="workshop__story-content" id="ws-content"></div>'
      + '    </div>'
      + '    <div class="workshop__story-footer">'
      + '      <button class="workshop__continue btn btn--primary" id="ws-continue">'
      + '        Continue the story'
      + '      </button>'
      + '      <button class="workshop__context-toggle btn btn--ghost" id="ws-toggle-ctx"'
      + '              aria-label="Toggle AI context" aria-expanded="true">'
      + '        AI Context'
      + '      </button>'
      + '    </div>'
      + '  </div>'
      + '  <aside class="workshop__context" id="ws-context" role="complementary" aria-label="AI Context">'
      + '    <div class="context__section">'
      + '      <h3 class="context__heading">What the world knows</h3>'
      + '      <div class="context__items" id="ws-ctx-items">'
      + '        <div class="context__empty">The world is quiet.</div>'
      + '      </div>'
      + '    </div>'
      + '    <div class="context__section">'
      + '      <h3 class="context__heading">Recent</h3>'
      + '      <div class="context__timeline" id="ws-ctx-recent"></div>'
      + '    </div>'
      + '    <div class="context__section">'
      + '      <button class="context__evidence-link btn btn--ghost" id="ws-evidence">'
      + '        Inspect evidence'
      + '      </button>'
      + '    </div>'
      + '  </aside>'
      + '</div>';

    wireEvents();
    return el;
  }

  /* ── Events ────────────────────────────────────────────── */

  function wireEvents() {
    var continueBtn = el.querySelector('#ws-continue');
    if (continueBtn) {
      continueBtn.addEventListener('click', generateRumor);
    }

    var toggleBtn = el.querySelector('#ws-toggle-ctx');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', toggleContext);
    }

    var evidenceBtn = el.querySelector('#ws-evidence');
    if (evidenceBtn) {
      evidenceBtn.addEventListener('click', function () {
        shell.navigate('ai-context');
      });
    }
  }

  function toggleContext() {
    var btn = el.querySelector('#ws-toggle-ctx');
    var contextEl = el.querySelector('#ws-context');
    var isOpen = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', String(!isOpen));
    if (contextEl) contextEl.style.display = isOpen ? 'none' : '';
    var workshop = el.querySelector('.workshop');
    if (workshop) workshop.classList.toggle('workshop--context-closed', isOpen);
  }

  /* ── Data ──────────────────────────────────────────────── */

  function loadWorld() {
    return fetch('/api/world')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        currentWorld = data;
        renderWorld();
      })
      .catch(function () {
        showStoryEmpty();
      });
  }

  function loadJournal() {
    return fetch('/api/journal')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        journalEntries = Array.isArray(data) ? data : (data.entries || data.journal || []);
        renderRecent();
      })
      .catch(function () {
        journalEntries = [];
        renderRecent();
      });
  }

  function generateRumor() {
    var btn = el.querySelector('#ws-continue');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'The storyteller is considering it\u2026';
    }

    fetch('/api/rumor', { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function () {
        if (btn) {
          btn.disabled = false;
          btn.textContent = 'Continue the story';
        }
        loadWorld();
        loadJournal();
      })
      .catch(function (err) {
        if (btn) {
          btn.disabled = false;
          btn.textContent = 'Continue the story';
        }
        console.error('[workshop] rumor failed:', err);
      });
  }

  /* ── Rendering ─────────────────────────────────────────── */

  function renderWorld() {
    if (!currentWorld) {
      showStoryEmpty();
      return;
    }

    // Handle actual VEFR API shape
    var title = currentWorld.title || currentWorld.name || '';
    var act = currentWorld.act;
    var actTitle = '';
    if (act && typeof act === 'object') {
      actTitle = act.title || act.name || '';
    } else if (typeof act === 'string') {
      actTitle = act;
    }
    var goldRule = currentWorld.gold_rule || '';
    var phase = currentWorld.surface || '';
    var regions = currentWorld.regions || {};

    // Chapter header
    var chapterEl = el.querySelector('#ws-chapter');
    if (chapterEl) {
      chapterEl.textContent = actTitle || title;
    }

    // Build story content from world state
    var contentEl = el.querySelector('#ws-content');
    if (contentEl) {
      var parts = [];

      // Gold rule as opening line
      if (goldRule) {
        parts.push('<p class="workshop__gold-rule">' + escapeHtml(goldRule) + '</p>');
      }

      // Region descriptions
      var regionNames = Object.keys(regions);
      if (regionNames.length) {
        parts.push('<div class="workshop__regions">');
        regionNames.forEach(function (name) {
          var region = regions[name];
          var mapText = region.map_text;
          if (mapText && Array.isArray(mapText)) {
            // Show the map as a visual element
            parts.push('<div class="workshop__region">');
            parts.push('<h3 class="workshop__region-name">' + escapeHtml(name) + '</h3>');
            parts.push('<pre class="workshop__region-map">' + escapeHtml(mapText.join('\n')) + '</pre>');
            parts.push('</div>');
          }
        });
        parts.push('</div>');
      }

      // Phase/HP info
      var hp = currentWorld.hp;
      if (hp) {
        parts.push('<div class="workshop__status">');
        parts.push('<span class="workshop__hp">HP: ' + hp.current + '/' + hp.max + '</span>');
        if (phase) parts.push('<span class="workshop__phase">Surface: ' + escapeHtml(phase) + '</span>');
        parts.push('</div>');
      }

      if (parts.length) {
        contentEl.innerHTML = parts.join('\n');
      } else {
        showStoryEmpty();
      }
    }

    // Context items
    renderContextItems();
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function showStoryEmpty() {
    var contentEl = el.querySelector('#ws-content');
    if (contentEl) {
      contentEl.innerHTML = ''
        + '<div class="workshop__empty">'
        + '  <p class="workshop__empty-text">The world is quiet. That\u2019s not the same as empty.</p>'
        + '  <p class="workshop__empty-hint">Continue the story to see what happens next.</p>'
        + '</div>';
    }
    var chapterEl = el.querySelector('#ws-chapter');
    if (chapterEl) chapterEl.textContent = '';
    var countEl = el.querySelector('#ws-wordcount');
    if (countEl) countEl.textContent = '';
  }

  function renderContextItems() {
    var container = el.querySelector('#ws-ctx-items');
    if (!container) return;

    var items = [];

    if (currentWorld) {
      var regions = currentWorld.regions || {};
      var regionNames = Object.keys(regions);
      if (regionNames.length) {
        items.push({ label: 'Regions', value: regionNames.join(', ') });
      }

      var phases = currentWorld.phases;
      if (phases && phases.length) {
        items.push({ label: 'Phases', value: phases.join(', ') });
      }

      var surface = currentWorld.surface;
      if (surface) {
        items.push({ label: 'Surface', value: surface });
      }

      var goldRule = currentWorld.gold_rule;
      if (goldRule) {
        items.push({ label: 'Gold Rule', value: goldRule });
      }
    }

    if (!items.length) {
      container.innerHTML = '<div class="context__empty">The world is quiet.</div>';
      return;
    }

    container.innerHTML = items.map(function (item) {
      return ''
        + '<div class="context__item">'
        + '  <span class="context__item-label">' + escapeHtml(item.label) + '</span>'
        + '  <span class="context__item-value">' + escapeHtml(item.value) + '</span>'
        + '</div>';
    }).join('');
  }

  function renderRecent() {
    var container = el.querySelector('#ws-ctx-recent');
    if (!container) return;

    if (!journalEntries.length) {
      container.innerHTML = '<div class="context__empty">Nothing yet.</div>';
      return;
    }

    var recent = journalEntries.slice(-5).reverse();
    container.innerHTML = recent.map(function (entry) {
      var text = entry.text || entry.content || entry.summary || entry.event || '';
      var time = entry.timestamp || entry.time || entry.created || '';
      return ''
        + '<div class="context__event">'
        + '  <span class="context__event-time">' + escapeHtml(formatTime(time)) + '</span>'
        + '  <span class="context__event-text">' + escapeHtml(truncate(text, 80)) + '</span>'
        + '</div>';
    }).join('');
  }

  function formatTime(t) {
    if (!t) return '';
    try {
      var d = new Date(t);
      if (isNaN(d.getTime())) return String(t);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return String(t);
    }
  }

  function truncate(s, n) {
    if (!s) return '';
    return s.length > n ? s.slice(0, n) + '\u2026' : s;
  }

  /* ── Lifecycle ─────────────────────────────────────────── */

  function init() {
    render();
    document.querySelector('.vefr-main').appendChild(el);
  }

  function enter() {
    loadWorld();
    loadJournal();
  }

  function leave() {}

  /* ── Register ──────────────────────────────────────────── */

  shell.register('workshop', {
    init: init,
    enter: enter,
    leave: leave,
    el: function () { return el; }
  });
})();
