/* vefr/web/js/features.js: the studio's two shelves. Pure, no DOM.
 *
 * Data arrives from GET /api/features as { catalog, pack }:
 *
 *   catalog  the engine's own list of what it can do
 *            ({ id, name, what, status }, status built|partial|proposed)
 *   pack     when the caller named a world, that world's scan
 *            ({ name, uses: [{ id, used, detail }] }); null otherwise
 *
 * shelfHtml returns an HTML string: what this game uses (only the
 * `used === true` rows, with their detail), what VEFR can do (every
 * built and partial feature), and - when any are proposed - what is
 * on the way. Every word is data, so every word is escaped before it
 * lands in the string: a name is shown, never run.
 */
(function (root) {
  'use strict';

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  var LABELS = { built: 'Built', proposed: 'Proposed', partial: 'Partly built' };

  function statusLabel(status) {
    return Object.prototype.hasOwnProperty.call(LABELS, status) ? LABELS[status] : status;
  }

  function item(name, what, extra) {
    var li = '<li><span class="features-item__name">' + esc(name) + '</span>';
    if (what) li += ' <span class="features-item__what">' + esc(what) + '</span>';
    if (extra) li += ' <span class="features-item__status">' + esc(extra) + '</span>';
    return li + '</li>';
  }

  /* One headed group. The first group carries the id the studio's
     section points aria-labelledby at, so the mount keeps a name even
     after its innerHTML is replaced. */
  function group(title, note, items, empty, first) {
    var head = '<h2 class="features-group__title"'
      + (first ? ' id="features-shelf-title"' : '') + '>' + esc(title) + '</h2>';
    var body = items.length
      ? '<ul class="features-list">' + items.join('') + '</ul>'
      : '<p class="note">' + esc(empty || 'Nothing here yet.') + '</p>';
    return '<section class="features-group" aria-label="' + esc(title) + '">'
      + head
      + (note ? '<p class="note">' + esc(note) + '</p>' : '')
      + body
      + '</section>';
  }

  function shelfHtml(report) {
    report = report || {};
    var catalog = report.catalog || [];
    var pack = report.pack || null;
    if (!catalog.length) {
      return '<p class="note">No features are catalogued yet.</p>';
    }

    var out = [];
    var first = true;

    if (pack) {
      var byId = {};
      catalog.forEach(function (f) { byId[f.id] = f; });
      var uses = (pack.uses || [])
        .filter(function (u) { return u && u.used === true; })
        .map(function (u) {
          var f = byId[u.id] || u;
          return item(f.name || u.name || u.id, u.detail || f.what);
        });
      out.push(group('What this game uses', pack.name || '',
        uses, 'This game uses no catalogued features yet.', first));
      first = false;
    }

    var can = catalog
      .filter(function (f) { return f.status === 'built' || f.status === 'partial'; })
      .map(function (f) { return item(f.name, f.what, statusLabel(f.status)); });
    out.push(group('What VEFR can do', '', can, 'Nothing is built yet.', first));

    var proposed = catalog
      .filter(function (f) { return f.status === 'proposed'; })
      .map(function (f) { return item(f.name, f.what, 'Proposed'); });
    if (proposed.length) {
      out.push(group('On the way', '', proposed, '', false));
    }

    return out.join('');
  }

  root.VEFR_FEATURES = { statusLabel: statusLabel, shelfHtml: shelfHtml };
})(typeof window !== 'undefined' ? window : globalThis);
