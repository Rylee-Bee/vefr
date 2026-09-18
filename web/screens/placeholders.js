/* Placeholder screen factory — makes a screen that shows real data or a graceful state. */
(function () {
  'use strict';

  var shell = window.VEFR_SHELL;

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function createPlaceholderScreen(id, title, apiEndpoint, renderItem) {
    var el = null;
    var data = null;

    function render() {
      el = document.createElement('div');
      el.className = 'vefr-screen';
      el.id = 'screen-' + id;
      el.innerHTML = ''
        + '<div class="placeholder-screen">'
        + '  <div class="placeholder-screen__header">'
        + '    <h2 class="placeholder-screen__title">' + escapeHtml(title) + '</h2>'
        + '  </div>'
        + '  <div class="placeholder-screen__body" id="' + id + '-content">'
        + '    <div class="placeholder-screen__loading">Loading\u2026</div>'
        + '  </div>'
        + '</div>';
      return el;
    }

    function loadData() {
      if (!apiEndpoint) {
        showEmpty();
        return;
      }
      var body = el.querySelector('#' + id + '-content');
      if (body) body.innerHTML = '<div class="placeholder-screen__loading">Loading\u2026</div>';

      fetch(apiEndpoint)
        .then(function (r) { return r.json(); })
        .then(function (d) {
          data = d;
          renderContent();
        })
        .catch(function () {
          showEmpty();
        });
    }

    function renderContent() {
      var body = el.querySelector('#' + id + '-content');
      if (!body) return;

      if (renderItem && data) {
        body.innerHTML = renderItem(data);
      } else {
        showEmpty();
      }
    }

    function showEmpty() {
      var body = el.querySelector('#' + id + '-content');
      if (body) {
        body.innerHTML = ''
          + '<div class="placeholder-screen__empty">'
          + '  <p>This room isn\u2019t finished yet.</p>'
          + '</div>';
      }
    }

    function init() {
      render();
      document.querySelector('.vefr-main').appendChild(el);
    }

    function enter() {
      loadData();
    }

    function leave() {}

    shell.register(id, {
      init: init,
      enter: enter,
      leave: leave,
      el: function () { return el; }
    });
  }

  /* ── Characters ──────────────────────────────────────── */
  createPlaceholderScreen('characters', 'Characters', '/api/wiki', function (data) {
    // Wiki entries are characters/lore
    var entries = Array.isArray(data) ? data : (data.entries || data.wiki || []);
    if (!entries.length) {
      return '<div class="placeholder-screen__empty"><p>No characters yet. They\u2019ll appear as the story grows.</p></div>';
    }
    return '<div class="character-list">'
      + entries.slice(0, 20).map(function (entry) {
        var name = entry.name || entry.title || entry.id || 'Unknown';
        var desc = entry.description || entry.summary || entry.text || '';
        return '<div class="character-card">'
          + '<h3 class="character-card__name">' + escapeHtml(name) + '</h3>'
          + (desc ? '<p class="character-card__desc">' + escapeHtml(desc.slice(0, 120)) + '</p>' : '')
          + '</div>';
      }).join('')
      + '</div>';
  });

  /* ── Map ──────────────────────────────────────────────── */
  createPlaceholderScreen('map', 'Map', '/api/world', function (data) {
    var regions = data.regions || {};
    var names = Object.keys(regions);
    if (!names.length) {
      return '<div class="placeholder-screen__empty"><p>The map is blank. Regions appear as you explore.</p></div>';
    }
    return '<div class="map-grid">'
      + names.map(function (name) {
        var region = regions[name];
        var mapText = region.map_text;
        return '<div class="map-region">'
          + '<h3 class="map-region__name">' + escapeHtml(name) + '</h3>'
          + (mapText ? '<pre class="map-region__grid">' + escapeHtml(mapText.join('\n')) + '</pre>' : '')
          + '</div>';
      }).join('')
      + '</div>';
  });

  /* ── Items ────────────────────────────────────────────── */
  createPlaceholderScreen('items', 'Items & Loot', '/api/vault', function (data) {
    var items = Array.isArray(data) ? data : (data.items || data.vault || []);
    if (!items.length) {
      return '<div class="placeholder-screen__empty"><p>Your vault is empty. Items appear through play.</p></div>';
    }
    return '<div class="item-list">'
      + items.map(function (item, i) {
        var name = item.name || item.title || 'Item ' + (i + 1);
        var desc = item.description || item.text || '';
        return '<div class="item-card">'
          + '<h3 class="item-card__name">' + escapeHtml(name) + '</h3>'
          + (desc ? '<p class="item-card__desc">' + escapeHtml(desc.slice(0, 120)) + '</p>' : '')
          + '</div>';
      }).join('')
      + '</div>';
  });

  /* ── Journal ──────────────────────────────────────────── */
  createPlaceholderScreen('journal', 'Journal', '/api/journal', function (data) {
    var entries = Array.isArray(data) ? data : (data.entries || data.journal || []);
    if (!entries.length) {
      return '<div class="placeholder-screen__empty"><p>The journal is empty. Entries accumulate as you play.</p></div>';
    }
    return '<div class="journal-entries">'
      + entries.slice(-20).reverse().map(function (entry, i) {
        var text = entry.text || entry.content || entry.summary || entry.event || '';
        var time = entry.timestamp || entry.time || entry.created || '';
        var starred = entry.starred || entry.star;
        return '<div class="journal-entry' + (starred ? ' journal-entry--starred' : '') + '">'
          + '<span class="journal-entry__time">' + escapeHtml(formatTime(time)) + '</span>'
          + '<span class="journal-entry__text">' + escapeHtml(text) + '</span>'
          + '</div>';
      }).join('')
      + '</div>';
  });

  /* ── Settings ─────────────────────────────────────────── */
  createPlaceholderScreen('settings', 'Settings', null, null);

  /* ── Helpers ──────────────────────────────────────────── */
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
})();
