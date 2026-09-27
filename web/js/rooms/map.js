/* vefr/web/js/rooms/map.js: The Map Room.
 * Split out of app.js (2026-09-27); the shared studio helpers come from
 * window.VEFR_STUDIO, which app.js builds. Loaded after app.js, before boot.js. */
(function (S) {
  'use strict';

  var screens = S.screens, API = S.API, ART = S.ART, emptyState = S.emptyState,
      ferryNote = S.ferryNote, firstWalk = S.firstWalk, h = S.h, loadingState = S.loadingState,
      main = S.main, openFolio = S.openFolio, residentLine = S.residentLine, spot = S.spot,
      studioAudio = S.studioAudio, truncate = S.truncate;

  /* ══════════════════════════════════════════════════════
     THE MAP ROOM — spatial, the world laid out
     ══════════════════════════════════════════════════════ */

  screens.map = (function () {
    var el_screen;
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-map' });
      main.appendChild(el_screen);
    }
    function enter() {
      el_screen.innerHTML = '<div class="wrap band map-room" id="map-content"></div>';
      var container = el_screen.querySelector('#map-content');
      container.appendChild(loadingState('Loading the map…'));

      Promise.all([
        API.world().catch(function () { return null; }),
        API.validate().catch(function () { return { ok: false, errors: ['The map file couldn’t be read'] }; })
      ]).then(function (results) {
        var data = results[0];
        var packCheck = results[1];
        container.innerHTML = '';
        if (!data) {
          container.appendChild(emptyState(
            'Couldn’t load the map.',
            'Try again in a moment.'
          ));
          return;
        }
        var rl = residentLine('map');
        if (rl) container.appendChild(rl);

        var regions = data.regions || {};
        var names = Object.keys(regions);
        if (!names.length) {
          container.appendChild(emptyState(
            'No map yet.',
            'Regions appear as you explore, or sketch some below.',
            true
          ));
          return;
        }

        container.appendChild(workingsControl());
        container.appendChild(mapPrimer());
        var bench = h('div', { className: 'map-bench' });
        var wrap = h('div', { className: 'map-regions' });
        names.forEach(function (name) { wrap.appendChild(regionCard(name, regions[name])); });
        bench.appendChild(wrap);
        bench.appendChild(packCheckRow(packCheck));
        container.appendChild(bench);
        container.appendChild(drawingTable(data));
      });
    }

    /* "Keep it simple / Show me how things work": one pref for the whole
       studio (prefs.js `workings`); here so the Map Room can flip it in place. */
    function workingsControl() {
      var P = window.VEFR_PREFS;
      var cur = (P && P.get && P.get().workings) || 'simple';
      var row = h('div', { className: 'workings', role: 'group', 'aria-label': 'How much of the workings to show' });
      [['simple', 'Keep it simple'], ['show', 'Show me how things work']].forEach(function (o) {
        var b = h('button', { className: 'workings__opt', type: 'button', textContent: o[1],
          'aria-pressed': String(cur === o[0]) });
        b.addEventListener('click', function () {
          if (P && P.set) P.set({ workings: o[0] });
          row.querySelectorAll('.workings__opt').forEach(function (x) {
            x.setAttribute('aria-pressed', String(x === b)); });
        });
        row.appendChild(b);
      });
      return row;
    }

    /* How maps work, in plain words, right where the map is made
       (Rylee: "it would be cool if something in the screen could explain it"). */
    function mapPrimer() {
      var d = h('details', { className: 'map-primer' });
      d.open = true;
      d.appendChild(h('summary', { className: 'map-primer__title', textContent: 'How maps work' }));
      var ul = h('ul', { className: 'map-primer__list' });
      [
        'A map is a grid of squares, like graph paper. Each square is one kind of ground.',
        'The player walks on open ground. Solid squares (walls, rock) block the way.',
        'Some squares do something: a safe square is a place nothing can hurt you.',
        'Some maps are drawn by hand here; others are built by the game from rules as you play.',
        'Pick a brush below and press the squares. The engine checks every sketch, and nothing is kept until you say so.'
      ].forEach(function (t) { ul.appendChild(h('li', { textContent: t })); });
      d.appendChild(ul);
      return d;
    }

    /* The survey — real numbers read off the map itself */
    function surveyOf(mapText) {
      var rows = mapText.length;
      var cols = 0;
      var census = {};
      mapText.forEach(function (ln) {
        if (ln.length > cols) cols = ln.length;
        ln.split('').forEach(function (ch) {
          if (ch === ' ' || ch === '\n' || ch === '\r') return;
          census[ch] = (census[ch] || 0) + 1;
        });
      });
      return { rows: rows, cols: cols, census: census };
    }

    function regionCard(name, region) {
      var mapText = (region && region.map_text) || [];
      var card = h('section', { className: 'map-region' });
      card.appendChild(h('h3', { className: 'map-region__name', textContent: name }));
      if (!mapText.length) return card;

      var survey = surveyOf(mapText);
      var kinds = Object.keys(survey.census).length;
      card.appendChild(h('p', { className: 'map-region__survey',
        textContent: 'a ' + survey.cols + '\u00d7' + survey.rows + ' stretch \u00b7 '
          + kinds + ' kind' + (kinds === 1 ? '' : 's') + ' of ground' }));
      /* The typed view is for the curious: the drawing table below shows
         the same map as squares. */
      var symbols = h('details', { className: 'map-symbols workings-only' });
      symbols.appendChild(h('summary', { className: 'map-symbols__toggle', textContent: 'Show the symbols' }));
      symbols.appendChild(h('pre', { className: 'map-region__grid', textContent: mapText.join('\n') }));
      card.appendChild(symbols);

      /* Each kind of ground is a door — press it and ask what lives there */
      var marks = h('div', { className: 'map-marks' });
      marks.appendChild(h('span', { className: 'map-marks__label',
        textContent: 'Press a map symbol to ask the Cartographer about it' }));
      Object.keys(survey.census).forEach(function (ch) {
        var chip = h('button', { className: 'map-mark', type: 'button',
          textContent: '\u201c' + ch + '\u201d \u00b7 ' + survey.census[ch] });
        chip.addEventListener('click', function () {
          openFolio('map', chip);
          S.folioInput.value = 'What is the mark \u201c' + ch + '\u201d in ' + name + '? What lives under it?';
          S.folioInput.focus();
        });
        marks.appendChild(chip);
      });
      symbols.appendChild(marks);

      card.appendChild(deepenTool(name));
      return card;
    }

    /* Deepen a landmark — the surveyor walks the ground (real enhance) */
    function deepenTool(name) {
      var div = h('div', { className: 'map-deepen' });
      div.appendChild(h('span', { className: 'map-deepen__label', textContent: 'deepen a landmark' }));
      var row = h('div', { className: 'map-deepen__row' });
      var inp = h('input', { className: 'map-deepen__input', type: 'text',
        placeholder: 'e.g. the old mill', 'aria-label': 'Landmark to describe in ' + name });
      var btn = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Deepen' });
      var out = h('div', { className: 'map-deepen__out' });
      function run() {
        var poi = inp.value.trim();
        if (!poi) { inp.focus(); return; }
        btn.disabled = true;
        out.innerHTML = '';
        out.appendChild(loadingState('The Cartographer is writing it up…'));
        API.enhanceMap({ region: name, poi_name: poi })
          .then(function (res) {
            out.innerHTML = '';
            var box = h('div', { className: 'map-enhance' });
            box.appendChild(h('div', { className: 'map-enhance__title', textContent: res.title || poi }));
            if (res.description) {
              box.appendChild(h('p', { className: 'map-enhance__desc', textContent: res.description }));
            }
            if (res.details && res.details.length) {
              var ul = h('ul', { className: 'map-enhance__details' });
              res.details.forEach(function (d) { ul.appendChild(h('li', { textContent: d })); });
              box.appendChild(ul);
            }
            out.appendChild(box);
          })
          .catch(function () {
            out.innerHTML = '';
            out.appendChild(h('p', { className: 'map-deepen__err',
              textContent: 'Couldn’t describe that landmark. Try again, or use a different name.' }));
          })
          .finally(function () { btn.disabled = false; });
      }
      btn.addEventListener('click', run);
      inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') run(); });
      row.appendChild(inp);
      row.appendChild(btn);
      div.appendChild(row);
      div.appendChild(out);
      return div;
    }

    /* The pack's own word — real validation, shown plainly */
    function packCheckRow(first) {
      var row = h('div', { className: 'map-check' });
      row.appendChild(h('span', { className: 'map-check__label', textContent: 'The world' }));
      var val = h('span', { className: 'map-check__value', role: 'status' });
      var btn = h('button', { className: 'btn btn--ghost', type: 'button', textContent: 'Check the world' });
      function paint(res) {
        if (!res) {
          val.textContent = 'Couldn’t check';
          val.className = 'map-check__value map-check__value--warn';
          return;
        }
        var ok = !!res.ok;
        val.textContent = ok
          ? 'All good: nothing to fix'
          : ((res.errors && res.errors.length) ? res.errors.join(' \u00b7 ') : 'Has things to fix');
        val.className = 'map-check__value' + (ok ? ' map-check__value--ok' : ' map-check__value--warn');
      }
      paint(first);
      btn.addEventListener('click', function () {
        btn.disabled = true;
        val.textContent = 'checking\u2026';
        API.validate().catch(function () { return null; }).then(paint)
          .finally(function () { btn.disabled = false; });
      });
      row.appendChild(val);
      row.appendChild(btn);
      return row;
    }

    /* ── The drawing table — a map maker with no markdown ── */
    function drawingTable(data) {
      var regions = data.regions || {};
      var names = Object.keys(regions);
      var useName = names.indexOf('town') !== -1 ? 'town' : (names[0] || 'town');
      var region = regions[useName] || {};
      var legend = data.legend || {};
      var sanctuary = data.sanctuary_tiles || [];
      var packLines = (region.map_text && region.map_text.length)
        ? region.map_text.slice()
        : (data.map || []).slice();
      var legendKeys = Object.keys(legend);

      var section = h('section', { className: 'map-draw' });
      section.appendChild(spot('cartographer-long-map', 'spot--right'));
      section.appendChild(h('h3', { className: 'map-draw__title', textContent: 'The drawing table' }));
      section.appendChild(h('p', { className: 'map-draw__hint',
        textContent: 'Pick a brush, then press or drag across the squares. Nothing is kept until you save it.' }));

      if (!legendKeys.length || !packLines.length) {
        section.appendChild(h('p', { className: 'map-draw__note',
          textContent: 'This world has no map file yet. Add map.md with a legend to start sketching.' }));
        return section;
      }

      var grid = packLines.map(function (ln) { return ln.split(''); });
      var rows = grid.length;
      var cols = grid[0] ? grid[0].length : 0;
      var brush = legendKeys.indexOf('.') !== -1 ? '.' : legendKeys[0];
      var dirty = false;
      var tool = 'brush';                // the hand at the table: brush | bucket
      var undoStack = [];
      var MAX_UNDO = 40;
      function snapshot() {
        undoStack.push(grid.map(function (r) { return r.slice().join(''); }));
        if (undoStack.length > MAX_UNDO) undoStack.shift();
        if (undoBtn) undoBtn.hidden = false;
      }
      function undo() {
        if (!undoStack.length) return;
        grid = undoStack.pop().map(function (ln) { return ln.split(''); });
        window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('map_undo');
        saveSketch();
        render();
        if (undoBtn) undoBtn.hidden = undoStack.length === 0;
      }
      var sketchKey = 'vefr.sketch.' + String(data.title || 'world')
        .replace(/[^a-z0-9]/gi, '-').toLowerCase() + '.' + useName;
      try {
        var saved = window.localStorage && localStorage.getItem(sketchKey);
        if (saved) {
          var parsed = JSON.parse(saved);
          if (parsed && Array.isArray(parsed.grid) && parsed.grid.length === rows &&
              parsed.grid.every(function (r) { return Array.isArray(r) && r.length === cols; })) {
            grid = parsed.grid.map(function (r) { return r.slice(); });
            if (parsed.brush && legend[parsed.brush]) brush = parsed.brush;
            dirty = true;
          }
        }
      } catch (e) {}

      var canvas = h('div', { className: 'map-canvas', role: 'grid', tabindex: '0',
        'aria-label': 'Map of ' + useName + '. Use the arrow keys to move and Enter to paint.' });
      var inkLine = h('p', { className: 'map-draw__ink', role: 'status' });
      var focusR = 0, focusC = 0, cells = [];

      /* Picture tiles: a pack's legend may name one (`"tile": "stone-wall"`);
         otherwise the kind of ground picks a sensible one. */
      var TILE_FOR_KIND = { 'solid': 'stone-wall', 'sanctuary': 'rug', 'marked': 'grass', 'open ground': 'grass' };
      var openKinds = legendKeys.filter(function (k) {
        var sp = legend[k] || {};
        return !sp.solid && sanctuary.indexOf(k) === -1 && !sp.deco;
      });
      function tileFor(ch) {
        var spec = legend[ch] || {};
        if (spec.tile) return spec.tile;
        if (spec.solid === true) return TILE_FOR_KIND.solid;
        if (sanctuary.indexOf(ch) !== -1) return TILE_FOR_KIND.sanctuary;
        if (spec.deco) return TILE_FOR_KIND.marked;
        return openKinds.indexOf(ch) > 0 ? 'path' : 'grass';
      }
      function tileUrl(ch) { return ART + 'tiles/' + tileFor(ch) + '.webp'; }
      function dressCell(cell, ch) {
        cell.style.background = cellColor(ch) || 'transparent';
        cell.style.backgroundImage = 'url(' + tileUrl(ch) + ')';
        cell.style.backgroundSize = 'cover';
        cell.innerHTML = '';
        cell.appendChild(h('span', { className: 'map-cell__glyph workings-only', textContent: ch }));
        cell.setAttribute('aria-label', potName(ch));
      }
      function cellColor(ch) {
        var spec = legend[ch];
        if (!spec || !spec.base || !spec.base.length) return '';
        return spec.base[0];
      }
      function cellSolid(ch) {
        var s = legend[ch];
        return !!(s && s.solid === true);
      }
      function saveSketch() {
        try {
          window.localStorage.setItem(sketchKey, JSON.stringify({
            grid: grid.map(function (r) { return r.slice(); }), brush: brush }));
        } catch (e) {}
      }
      function census() {
        var chr = {};
        for (var r = 0; r < rows; r++) {
          for (var c = 0; c < cols; c++) {
            var ch = grid[r][c];
            if (ch && ch !== ' ') chr[ch] = (chr[ch] || 0) + 1;
          }
        }
        var parts = Object.keys(chr).map(function (k) { return potName(k) + ' \u00d7 ' + chr[k]; });
        inkLine.textContent = rows + ' rows \u00d7 ' + cols + ' cols \u00b7 '
          + (parts.length ? parts.join(', ') : 'Nothing painted yet');
      }
      function paint(r, c) {
        if (r < 0 || r >= rows || c < 0 || c >= cols) return;
        var cell = cells[r] && cells[r][c];
        if (!cell) return;
        if (grid[r][c] === brush) return;
        snapshot();
        grid[r][c] = brush;
        window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('map_paint', { brush: brush });
        dressCell(cell, brush);
        cell.classList.toggle('map-cell--solid', cellSolid(brush));
        cell.classList.toggle('map-cell--marked', !!(legend[brush] && legend[brush].deco));
        cell.title = 'row ' + (r + 1) + ', column ' + (c + 1) + ' \u00b7 ' + potName(brush);
        dirty = true;
        saveSketch();
        census();
        cansBtn.hidden = false;
        btnKeep.disabled = false;
        btnUse.disabled = false;
        firstWalk.attempt('map');
      }
      function floodFill(r, c) {
        if (r < 0 || r >= rows || c < 0 || c >= cols) return;
        var target = grid[r][c];
        if (target === brush) return;
        snapshot();
        var open = [[r, c]];
        var seen = {};
        seen[r * cols + c] = true;
        while (open.length) {
          var cur = open.pop();
          var cr = cur[0], cc = cur[1];
          grid[cr][cc] = brush;
          window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('map_paint', { brush: brush });
          var cell = cells[cr] && cells[cr][cc];
          if (cell) {
            dressCell(cell, brush);
            cell.classList.toggle('map-cell--solid', cellSolid(brush));
            cell.classList.toggle('map-cell--marked', !!(legend[brush] && legend[brush].deco));
            cell.title = 'row ' + (cr + 1) + ', column ' + (cc + 1) + ' \u00B7 ' + potName(brush);
          }
          var dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
          for (var d = 0; d < 4; d++) {
            var nr = cr + dirs[d][0], nc = cc + dirs[d][1];
            if (nr >= 0 && nr < rows && nc >= 0 && nc < cols &&
                !seen[nr * cols + nc] && grid[nr][nc] === target) {
              seen[nr * cols + nc] = true;
              open.push([nr, nc]);
            }
          }
        }
        dirty = true;
        saveSketch();
        census();
        cansBtn.hidden = false;
        btnKeep.disabled = false;
        btnUse.disabled = false;
        firstWalk.attempt('map');
      }
      function focusCell(r, c) {
        var old = cells[focusR] && cells[focusR][focusC];
        if (old) old.tabIndex = -1;
        focusR = r; focusC = c;
        var cell = cells[r] && cells[r][c];
        if (cell) {
          cell.tabIndex = 0;
          cell.focus();
        }
      }
      function makeCell(r, c) {
        var ch = grid[r][c];
        var cell = h('div', { className: 'map-cell' + (cellSolid(ch) ? ' map-cell--solid' : ''),
          role: 'gridcell', tabindex: '-1',
          'data-xy': String(r * cols + c) });
        dressCell(cell, ch);
        if (legend[ch] && legend[ch].deco) cell.classList.add('map-cell--marked');
        cell.title = 'row ' + (r + 1) + ', column ' + (c + 1) + ' \u00b7 ' + potName(ch);
        cell.addEventListener('click', function () {
          var idx = Number(cell.getAttribute('data-xy'));
          var rr = Math.floor(idx / cols), cc = idx % cols;
          if (tool === 'bucket') floodFill(rr, cc); else paint(rr, cc);
          focusCell(rr, cc);
        });
        return cell;
      }
      function render() {
        var hadFocus = canvas.contains(document.activeElement);
        canvas.innerHTML = '';
        cells = [];
        focusR = Math.min(focusR, rows - 1);
        focusC = Math.min(focusC, cols - 1);
        for (var r = 0; r < rows; r++) {
          cells.push([]);
          var rowEl = h('div', { className: 'map-canvas__row', role: 'row' });
          for (var c = 0; c < cols; c++) {
            var cell = makeCell(r, c);
            if (r === focusR && c === focusC) cell.tabIndex = 0;
            cells[r].push(cell);
            rowEl.appendChild(cell);
          }
          canvas.appendChild(rowEl);
        }
        census();
        if (hadFocus) focusCell(focusR, focusC);
      }
      canvas.addEventListener('keydown', function (e) {
        var r = focusR, c = focusC;
        if (e.key === 'ArrowUp') r = Math.max(0, r - 1);
        else if (e.key === 'ArrowDown') r = Math.min(rows - 1, r + 1);
        else if (e.key === 'ArrowLeft') c = Math.max(0, c - 1);
        else if (e.key === 'ArrowRight') c = Math.min(cols - 1, c + 1);
        else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); paint(r, c); return; }
        else return;
        e.preventDefault();
        focusCell(r, c);
      });

      /* Drag to paint with the brush — press, sweep, lift */
      var dragging = false;
      canvas.addEventListener('pointerdown', function (e) {
        var cell = e.target.closest && e.target.closest('.map-cell');
        if (!cell) return;
        dragging = true;
        var idx = Number(cell.getAttribute('data-xy'));
        var rr = Math.floor(idx / cols), cc = idx % cols;
        if (tool === 'bucket') floodFill(rr, cc); else paint(rr, cc);
      });
      canvas.addEventListener('pointerover', function (e) {
        if (!dragging || tool !== 'brush') return;
        var cell = e.target.closest && e.target.closest('.map-cell');
        if (!cell) return;
        var idx = Number(cell.getAttribute('data-xy'));
        var rr = Math.floor(idx / cols), cc = idx % cols;
        paint(rr, cc);
      });
      document.addEventListener('pointerup', function () { dragging = false; });

      /* The ink pots — one brush per mark the pack really knows */
      var pots = h('div', { className: 'map-pots', role: 'group',
        'aria-label': 'Brushes: one per map symbol' });
      function potLabel(ch) {
        var spec = legend[ch] || {};
        if (spec.solid === true) return 'solid';
        if (sanctuary.indexOf(ch) !== -1) return 'sanctuary';
        if (spec.deco) return 'marked';
        return 'open ground';
      }
      var POT_MEANING = {
        'solid': 'blocks walking',
        'sanctuary': 'a safe square',
        'marked': 'walkable, with a mark',
        'open ground': 'walkable'
      };
      /* Two kinds can share a name (two looks of open ground); number them. */
      function potName(ch) {
        var base = potLabel(ch);
        var same = legendKeys.filter(function (k) { return potLabel(k) === base; });
        return same.length > 1 ? base + ' ' + (same.indexOf(ch) + 1) : base;
      }
      function paintPots() {
        pots.innerHTML = '';
        legendKeys.forEach(function (ch) {
          var b = h('button', { className: 'map-inked' + (brush === ch ? ' map-inked--active' : ''),
            type: 'button', 'aria-pressed': String(brush === ch) });
          b.appendChild(h('span', { className: 'map-inked__tile', 'aria-hidden': 'true',
            style: 'background-image:url(' + tileUrl(ch) + ')' }));
          b.appendChild(h('span', { className: 'map-inked__char workings-only', textContent: ch }));
          b.appendChild(h('span', { className: 'map-inked__label', textContent: potName(ch) }));
          b.appendChild(h('span', { className: 'map-inked__means', textContent: POT_MEANING[potLabel(ch)] }));
          var bg = cellColor(ch);
          if (bg) b.style.setProperty('--ink', bg);
          b.addEventListener('click', function () {
            brush = ch;
            paintPots();
            if (dirty) { cansBtn.hidden = false; btnKeep.disabled = false; btnUse.disabled = false; }
          });
          pots.appendChild(b);
        });
      }

      /* The tools — brush, bucket, undo */
      var tools = h('div', { className: 'map-draw__tools', role: 'group', 'aria-label': 'Table tools' });
      var brushTool = h('button', { className: 'map-tool map-tool--active', type: 'button',
        'aria-pressed': 'true', textContent: 'brush' });
      var bucketTool = h('button', { className: 'map-tool', type: 'button',
        'aria-pressed': 'false', textContent: 'fill' });
      var undoBtn = h('button', { className: 'map-tool map-tool--undo', type: 'button',
        textContent: 'undo', hidden: true });
      function setTool(t) {
        tool = t;
        brushTool.classList.toggle('map-tool--active', t === 'brush');
        bucketTool.classList.toggle('map-tool--active', t === 'bucket');
        brushTool.setAttribute('aria-pressed', String(t === 'brush'));
        bucketTool.setAttribute('aria-pressed', String(t === 'bucket'));
      }
      brushTool.addEventListener('click', function () { setTool('brush'); });
      bucketTool.addEventListener('click', function () { setTool('bucket'); });
      undoBtn.addEventListener('click', function () {
        undo();
        undoBtn.hidden = undoStack.length === 0;
      });
      tools.appendChild(brushTool);
      tools.appendChild(bucketTool);
      tools.appendChild(undoBtn);

      /* Sketches kept from this very table, pinned by the ferry */
      var pinned = h('div', { className: 'map-draw__pinned' });
      API.vault().catch(function () { return { items: [] }; }).then(function (v) {
        var sketches = ((v && v.items) || []).filter(function (i) { return i.kind === 'sketch'; });
        if (!sketches.length) return;
        pinned.appendChild(h('h4', { className: 'map-draw__pinned-title', textContent: 'Saved sketches' }));
        var shelf = h('div', { className: 'folks-shelf' });
        sketches.forEach(function (s) {
          var card = h('button', { className: 'pinned-card', type: 'button',
            'aria-label': 'Ask about ' + (s.name || 'a sketch') });
          card.appendChild(h('span', { className: 'pinned-card__name', textContent: s.name || 'a sketch' }));
          card.appendChild(h('span', { className: 'pinned-card__lore', textContent: truncate(s.lore || '', 90) }));
          card.addEventListener('click', function () {
            openFolio('map', card);
            S.folioInput.value = 'Tell me about \u201C' + (s.name || 'this sketch') + '”. What could be here?';
            S.folioInput.focus();
          });
          shelf.appendChild(card);
        });
        pinned.appendChild(shelf);
      });

      /* The actions — reset, sketch new land, keep, ask */
      var actions = h('div', { className: 'map-draw__row' });
      var cansBtn = h('button', { className: 'btn btn--ghost', type: 'button', textContent: 'Clear the sketch', hidden: true });
      var sketchBtn = h('button', { className: 'btn btn--ghost', type: 'button', textContent: 'Sketch new land' });
      var keepName = h('input', { className: 'map-draw__keep-name', type: 'text',
        value: 'map sketch of ' + useName + ' (hand-inked)',
        'aria-label': 'Name for the kept sketch' });
      var btnKeep = h('button', { className: 'btn btn--bell', type: 'button', textContent: 'Save this sketch', disabled: true });
      var keepWrap = h('div', { className: 'map-draw__keep' });
      keepWrap.appendChild(keepName);
      keepWrap.appendChild(btnKeep);
      var btnUse = h('button', { className: 'btn btn--warm', type: 'button',
        textContent: 'Use as this world’s map', disabled: true });
      actions.appendChild(cansBtn);
      actions.appendChild(sketchBtn);
      actions.appendChild(keepWrap);
      actions.appendChild(btnUse);

      /* Committing the drawing to the world — the one action that
         writes. A refusal (422) is the engine's own words; an
         existing map (409) is a question, never a silent clobber. */
      var useNote = h('p', { className: 'map-draw__check', role: 'status',
        'aria-live': 'polite', hidden: true });
      var replaceRow = h('div', { className: 'map-draw__replace', hidden: true });
      replaceRow.appendChild(h('p', { className: 'map-draw__replace-q',
        textContent: 'Replace the current map? A backup is kept.' }));
      var replaceYes = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Replace' });
      var replaceNo = h('button', { className: 'btn btn--ghost', type: 'button', textContent: 'Cancel' });
      replaceRow.appendChild(replaceYes);
      replaceRow.appendChild(replaceNo);

      function commitMap(force) {
        if (!dirty) return;
        btnUse.disabled = true;
        replaceRow.hidden = true;
        useNote.hidden = false;
        useNote.classList.remove('map-draw__check--good', 'map-draw__check--bad');
        useNote.textContent = 'Checking and saving your map…';
        API.mapBuild({
          grid: grid.map(function (r) { return r.join(''); }),
          force: !!force
        })
          .then(function (res) {
            dirty = false;
            /* The world's map is now the truth; the local sketch is redundant. */
            try { window.localStorage.removeItem(sketchKey); } catch (e) {}
            studioAudio.clank();
            window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('map_build');
            ferryNote('Your map is saved to this world'
              + (res && res.backup_rel ? '. The old map is kept as a backup.' : '') + '.');
            enter();
          })
          .catch(function (err) {
            if (err && err.status === 409) {
              useNote.hidden = true;
              replaceRow.hidden = false;
              replaceYes.focus();
              return;
            }
            useNote.textContent = (err && err.detail)
              ? String(err.detail)
              : 'The map didn’t pass its check. Fix what it reports and try again.';
            useNote.classList.add('map-draw__check--bad');
          })
          .finally(function () { btnUse.disabled = false; });
      }
      btnUse.addEventListener('click', function () { commitMap(false); });
      replaceYes.addEventListener('click', function () { commitMap(true); });
      replaceNo.addEventListener('click', function () {
        replaceRow.hidden = true;
        useNote.hidden = false;
        useNote.classList.remove('map-draw__check--good', 'map-draw__check--bad');
        useNote.textContent = 'Cancelled. This world’s map is unchanged.';
      });

      var askBtn = h('button', { className: 'btn btn--ghost', type: 'button',
        textContent: 'Ask the Cartographer about it' });
      actions.appendChild(askBtn);
      var checkBtn = h('button', { className: 'btn btn--ghost', type: 'button',
        textContent: 'Check the map' });
      actions.appendChild(checkBtn);
      var checkNote = h('p', { className: 'map-draw__check', role: 'status',
        'aria-live': 'polite', hidden: true });
      checkBtn.addEventListener('click', function () {
        checkBtn.disabled = true;
        checkNote.hidden = false;
        checkNote.textContent = 'Checking the map…';
        checkNote.classList.remove('map-draw__check--good', 'map-draw__check--bad');
        API.mapCheck({ grid: grid.map(function (r) { return r.join(''); }) })
          .then(function (res) {
            if (res && res.ok) {
              checkNote.textContent = 'The map checks out: every path connects and every door can be reached.';
              checkNote.classList.add('map-draw__check--good');
              studioAudio.squeak();
              window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('map_check_ok');
            } else {
              var errs = (res && res.errors && res.errors.length)
                ? res.errors.join(' \u00B7 ')
                : 'This sketch doesn’t pass the map check yet.';
              checkNote.textContent = errs;
              checkNote.classList.add('map-draw__check--bad');
              window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('map_check_fail');
            }
          })
          .catch(function () {
            checkNote.textContent = 'Couldn’t check the map. Try again.';
            checkNote.classList.add('map-draw__check--bad');
          })
          .finally(function () {
            checkBtn.disabled = false;
            checkNote.hidden = false;
          });
      });

      cansBtn.addEventListener('click', function () {
        grid = packLines.map(function (ln) { return ln.split(''); });
        dirty = false;
        saveSketch();
        render();
        cansBtn.hidden = true;
        btnKeep.disabled = true;
        btnUse.disabled = true;
      });

      btnKeep.addEventListener('click', function () {
        if (!dirty) return;
        btnKeep.disabled = true;
        var name = keepName.value.trim() || ('map sketch of ' + useName);
        var marks = {};
        for (var r = 0; r < rows; r++) {
          for (var c = 0; c < cols; c++) {
            var ch = grid[r][c];
            if (ch && ch !== ' ') marks[ch] = (marks[ch] || 0) + 1;
          }
        }
        var lore = 'A hand-painted map sketch of ' + useName + ' from the drawing table: '
          + (Object.keys(marks).map(function (k) { return '\u201c' + k + '\u201d \u00d7 ' + marks[k]; }).join(', ') || 'blank');
        API.vaultKeep({ name: name, kind: 'sketch', bond: 'assigned', lore: lore })
          .then(function () {
            studioAudio.clank();
            ferryNote('Ratatoskr is carrying \u201c' + truncate(name, 36) + '\u201d into the vault\u2026');
          })
          .catch(function () {
            btnKeep.disabled = false;
            ferryNote('Couldn’t save the sketch. Try again.');
          });
      });

      /* Sketch new land — the surveyor proposes, the engine checks */
      var sketchRow = h('div', { className: 'map-sketch', hidden: true });
      var sketchInp = h('input', { className: 'map-sketch__input', type: 'text',
        placeholder: 'What should the land feel like? For example: a hollow with one path and a standing stone',
        'aria-label': 'Describe the new land' });
      var sketchGo = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Sketch it' });
      var sketchErr = h('p', { className: 'map-sketch__err', role: 'status', hidden: true });
      sketchRow.appendChild(sketchInp);
      sketchRow.appendChild(sketchGo);
      sketchRow.appendChild(sketchErr);
      sketchBtn.addEventListener('click', function () {
        sketchRow.hidden = !sketchRow.hidden;
        if (!sketchRow.hidden) sketchInp.focus();
      });
      function runSketch() {
        var story = sketchInp.value.trim();
        if (!story) { sketchInp.focus(); return; }
        sketchGo.disabled = true;
        sketchErr.hidden = true;
        API.mapPropose({ story: story })
          .then(function (res) {
            if (!res || !res.ok || !res.grid || !res.grid.length) {
              sketchErr.textContent = (res && res.reason) || 'That sketch came back empty. Try again, or paint it yourself.';
              sketchErr.hidden = false;
              return;
            }
            grid = res.grid.map(function (ln) { return ln.split(''); });
            rows = grid.length;
            cols = grid[0] ? grid[0].length : 0;
            if (res.legend && Object.keys(res.legend).length) {
              legend = res.legend;
              legendKeys = Object.keys(legend);
              if (!legend[brush]) brush = legendKeys.indexOf('.') !== -1 ? '.' : legendKeys[0];
              paintPots();
            }
            dirty = true;
            saveSketch();
            render();
            cansBtn.hidden = false;
            btnKeep.disabled = false;
            btnUse.disabled = false;
            ferryNote('The Cartographer sketched “' + truncate(story, 42) + '”.');
          })
          .catch(function () {
            sketchErr.textContent = 'Couldn’t sketch that right now. Try again, or paint it yourself.';
            sketchErr.hidden = false;
          })
          .finally(function () { sketchGo.disabled = false; });
      }
      sketchGo.addEventListener('click', runSketch);
      sketchInp.addEventListener('keydown', function (e) { if (e.key === 'Enter') runSketch(); });

      askBtn.addEventListener('click', function () {
        openFolio('map', askBtn);
        S.folioInput.value = 'Tell me about the map I just sketched: '
          + (sketchInp.value.trim() || 'a place I painted by hand');
        S.folioInput.focus();
      });

      section.appendChild(pots);
      section.appendChild(inkLine);
      section.appendChild(tools);
      section.appendChild(canvas);
      section.appendChild(sketchRow);
      section.appendChild(actions);
      section.appendChild(useNote);
      section.appendChild(replaceRow);
      section.appendChild(checkNote);
      section.appendChild(pinned);
      paintPots();
      render();
      cansBtn.hidden = !dirty;
      btnKeep.disabled = !dirty;
      btnUse.disabled = !dirty;
      return section;
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();
})(window.VEFR_STUDIO);
