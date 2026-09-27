/* vefr/web/js/library.js: how the Library reads a book. Pure, no DOM.
 *
 * Books arrive from /api/library as { title, pages: [text, ...], ... }.
 * The reader shows one page at a time. Page text is the author's words,
 * so it is escaped first and then given a tiny, safe subset of markdown:
 * paragraphs, **bold**, *italic*, `code`, ``` fenced blocks, and "- " /
 * "1. " lists. Wrapped lines join into one paragraph (a line ending in two
 * spaces keeps its break, for poems). With a glossary, an italic word that
 * has an entry becomes a button the reader can tap for its meaning.
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

  function lookup(glossary, word) {
    if (!glossary) return null;
    var w = String(word).toLowerCase().replace(/\s+/g, ' ').trim();
    if (Object.prototype.hasOwnProperty.call(glossary, w)) return w;
    for (var k in glossary) {
      if (Object.prototype.hasOwnProperty.call(glossary, k) && (glossary[k].also || []).indexOf(w) !== -1) return k;
    }
    return null;
  }

  function inline(s, glossary) {
    return esc(s)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g, function (_, t) {
        var key = lookup(glossary, t.replace(/&#39;/g, "'"));
        if (!key) return '<em>' + t + '</em>';
        return '<button type="button" class="lib-term" data-term="' + esc(key) + '" aria-expanded="false"><em>' + t + '</em></button>';
      });
  }

  /* Wrapped lines are one paragraph; two trailing spaces keep a break. */
  function joinLines(lines, glossary) {
    var parts = [''];
    lines.forEach(function (l, i) {
      var cur = parts[parts.length - 1];
      parts[parts.length - 1] = cur ? cur + ' ' + l.trim() : l.trim();
      if (/\s{2,}$/.test(l) && i < lines.length - 1) parts.push('');
    });
    return parts.map(function (t) { return inline(t, glossary); }).join('<br>');
  }

  function renderPage(text, glossary) {
    var src = String(text || '');
    var out = [];
    /* Fenced blocks first: their inside is shown exactly, never styled. */
    var parts = src.split(/^```[^\n]*$/m);
    parts.forEach(function (chunk, n) {
      if (n % 2 === 1) {
        out.push('<pre><code>' + esc(chunk.replace(/^\n/, '').replace(/\n$/, '')) + '</code></pre>');
        return;
      }
      chunk.split(/\n\s*\n/).forEach(function (block) {
        var lines = block.split('\n').filter(function (l) { return l.trim(); });
        if (!lines.length) return;
        if (lines.every(function (l) { return /^\s*-\s+/.test(l); })) {
          out.push('<ul>' + lines.map(function (l) { return '<li>' + inline(l.replace(/^\s*-\s+/, ''), glossary) + '</li>'; }).join('') + '</ul>');
          return;
        }
        if (lines.every(function (l) { return /^\s*\d+\.\s+/.test(l); })) {
          out.push('<ol>' + lines.map(function (l) { return '<li>' + inline(l.replace(/^\s*\d+\.\s+/, ''), glossary) + '</li>'; }).join('') + '</ol>');
          return;
        }
        out.push('<p>' + joinLines(lines, glossary) + '</p>');
      });
    });
    return out.join('');
  }

  root.VEFR_LIBRARY = { clampPage: clampPage, pageLabel: pageLabel, renderPage: renderPage, esc: esc, lookup: lookup };
})(typeof window !== 'undefined' ? window : globalThis);
