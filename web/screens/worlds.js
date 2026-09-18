/* vefr/web/screens/worlds.js — invitations to other places.
 *
 * World cards should feel like places you could sit down in.
 * Not database rows. Not app tiles. Invitations.
 */

(function () {
  'use strict';

  var shell = window.VEFR_SHELL;
  var el = null;
  var worlds = [];

  function render() {
    el = document.createElement('div');
    el.className = 'vefr-screen';
    el.id = 'screen-worlds';
    el.innerHTML = ''
      + '<div class="worlds">'
      + '  <div class="worlds__header">'
      + '    <h2 class="worlds__title">Your Worlds</h2>'
      + '    <div class="worlds__actions">'
      + '      <input type="search" class="worlds__search input" placeholder="Search worlds\u2026"'
      + '             aria-label="Search worlds" id="worlds-search">'
      + '    </div>'
      + '  </div>'
      + '  <div class="worlds__grid" id="worlds-grid">'
      + '    <div class="worlds__loading">Looking for worlds\u2026</div>'
      + '  </div>'
      + '</div>';

    wireEvents();
    return el;
  }

  function wireEvents() {
    var search = el.querySelector('#worlds-search');
    if (search) {
      search.addEventListener('input', function () {
        filterWorlds(search.value);
      });
    }
  }

  function loadWorlds() {
    return fetch('/api/builder/worlds')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        worlds = Array.isArray(data) ? data : (data.worlds || []);
        renderGrid();
      })
      .catch(function () {
        worlds = [];
        renderGrid();
      });
  }

  function renderGrid() {
    var grid = el.querySelector('#worlds-grid');
    if (!grid) return;

    if (!worlds.length) {
      grid.innerHTML = ''
        + '<div class="worlds__empty">'
        + '  <p class="worlds__empty-text">No worlds yet. Every world starts with a story.</p>'
        + '  <button class="btn btn--primary worlds__create">Begin a new world</button>'
        + '</div>';
      return;
    }

    grid.innerHTML = worlds.map(function (world) {
      var name = world.name || world.world_name || 'Untitled';
      var desc = world.description || world.summary || '';
      var sessions = world.sessions || world.session_count || 0;
      var active = world.active || world.current || false;
      var lastPlayed = world.last_played || world.lastPlayed || '';

      return ''
        + '<article class="world-card' + (active ? ' world-card--active' : '') + '"'
        + '         tabindex="0" role="button" aria-label="Open ' + escapeAttr(name) + '">'
        + '  <div class="world-card__visual">'
        + '    <span class="world-card__initial">' + escapeHtml(name.charAt(0).toUpperCase()) + '</span>'
        + '  </div>'
        + '  <div class="world-card__body">'
        + '    <h3 class="world-card__name">' + escapeHtml(name) + '</h3>'
        + (desc ? '    <p class="world-card__desc">' + escapeHtml(truncate(desc, 100)) + '</p>' : '')
        + '    <div class="world-card__meta">'
        + (sessions ? '      <span class="world-card__sessions">' + sessions + ' session' + (sessions !== 1 ? 's' : '') + '</span>' : '')
        + (lastPlayed ? '      <span class="world-card__time">' + escapeHtml(formatRelative(lastPlayed)) + '</span>' : '')
        + (active ? '      <span class="world-card__badge">Active</span>' : '')
        + '    </div>'
        + '  </div>'
        + '</article>';
    }).join('');

    // Wire card clicks
    grid.addEventListener('click', function (e) {
      var card = e.target.closest('.world-card');
      if (!card) return;
      var index = Array.from(grid.children).indexOf(card);
      if (index >= 0 && worlds[index]) {
        selectWorld(worlds[index]);
      }
    });
  }

  function selectWorld(world) {
    // Navigate to workshop with this world
    shell.navigate('workshop');
    // TODO: tell state which world to load
  }

  function filterWorlds(query) {
    var cards = el.querySelectorAll('.world-card');
    var q = query.toLowerCase();
    cards.forEach(function (card) {
      var name = card.querySelector('.world-card__name');
      var text = name ? name.textContent.toLowerCase() : '';
      card.style.display = text.indexOf(q) >= 0 ? '' : 'none';
    });
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function escapeAttr(s) {
    return s.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function truncate(s, n) {
    return s.length > n ? s.slice(0, n) + '\u2026' : s;
  }

  function formatRelative(t) {
    if (!t) return '';
    try {
      var d = new Date(t);
      if (isNaN(d.getTime())) return '';
      var now = Date.now();
      var diff = now - d.getTime();
      if (diff < 60000) return 'just now';
      if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
      if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
      return Math.floor(diff / 86400000) + 'd ago';
    } catch (e) {
      return '';
    }
  }

  function init() {
    render();
    document.querySelector('.vefr-main').appendChild(el);
  }

  function enter() {
    loadWorlds();
  }

  function leave() {}

  shell.register('worlds', {
    init: init,
    enter: enter,
    leave: leave,
    el: function () { return el; }
  });
})();
