/* vefr/web/js/library.js: how the Library reads a book. Pure, no DOM.
 *
 * Books arrive from /api/library as { title, pages: [text, ...], ... }.
 * The reader shows one page at a time. Page text is the author's words,
 * so it is escaped first and then given a tiny, safe subset of markdown:
 * paragraphs, **bold**, *italic*, and "- " / "1. " lists.
 */
(function (root) {
  'use strict';

  function clampPage(i, n) {
    if (!n) return 0;
    return Math.max(0, Math.min(n - 1, i | 0));
  }

  function pageLabel(i, n) {
    return n ? 'Page ' + (clampPage(i, n) + 1) + ' of ' + n : 'No pages';
  }

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function inline(s) {
    return esc(s)
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em>$1</em>');
  }

  function renderPage(text) {
    var blocks = String(text || '').split(/\n\s*\n/);
    return blocks.map(function (block) {
      var lines = block.split('\n').filter(function (l) { return l.trim(); });
      if (!lines.length) return '';
      if (lines.every(function (l) { return /^\s*-\s+/.test(l); })) {
        return '<ul>' + lines.map(function (l) { return '<li>' + inline(l.replace(/^\s*-\s+/, '')) + '</li>'; }).join('') + '</ul>';
      }
      if (lines.every(function (l) { return /^\s*\d+\.\s+/.test(l); })) {
        return '<ol>' + lines.map(function (l) { return '<li>' + inline(l.replace(/^\s*\d+\.\s+/, '')) + '</li>'; }).join('') + '</ol>';
      }
      return '<p>' + lines.map(inline).join('<br>') + '</p>';
    }).join('');
  }

  root.VEFR_LIBRARY = { clampPage: clampPage, pageLabel: pageLabel, renderPage: renderPage, esc: esc };
})(typeof window !== 'undefined' ? window : globalThis);
