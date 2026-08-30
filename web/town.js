/* Old Name - the town. The renderer is engine; the world comes from /api/world. */
(function () {
  var canvas = document.getElementById('town-canvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');

  var W = null; /* world payload */
  var TILE = 32;
  var the wanderer = null;
  var phase = '';
  var phases = [];
  var watchR = 0;
  var BLOCKED = ['~', 'B', '#', 'T', 'M'];
  var SANCT = [];
  var openSpeaker = null;
  var busy = false;

  fetch('/api/world')
    .then(function (r) { return r.json(); })
    .then(init)
    .catch(function () {
      var note = document.getElementById('near-note');
      if (note) {
        note.hidden = false;
        note.textContent = 'the world did not load. refresh.';
      }
    });

  function init(data) {
    W = data;
    TILE = W.tile || 32;
    phases = W.phases;
    phase = phases[0];
    watchR = W.watch.r_by_phase[phase] || W.watch.tower[2] || 12;
    SANCT = W.sanctuary_tiles || [];
    the wanderer = { x: W.willow_start[0], y: W.willow_start[1] };
    canvas.width = W.map[0].length * TILE;
    canvas.height = W.map.length * TILE;
    buildRail();
    draw();
    hud();
  }

  function rows() { return W.map.length; }
  function cols() { return W.map[0].length; }

  function tileAt(x, y) {
    if (y < 0 || y >= rows() || x < 0 || x >= cols()) return '#';
    return W.map[y][x];
  }

  function blocked(x, y) {
    var t = tileAt(x, y);
    var e = W.legend[t];
    if (e && typeof e.solid === 'boolean') return e.solid;
    return BLOCKED.indexOf(t) !== -1;
  }

  function losBlocked(x0, y0, x1, y1) {
    var dx = x1 - x0, dy = y1 - y0;
    var steps = Math.max(Math.abs(dx), Math.abs(dy)) * 3;
    for (var i = 1; i < steps; i++) {
      var fx = x0 + dx * i / steps, fy = y0 + dy * i / steps;
      var t = tileAt(Math.round(fx), Math.round(fy));
      if (t === '#' || t === 'T' || t === 'H' || t === 'M') return true;
    }
    return false;
  }

  function watched(x, y) {
    var t = W.watch.tower;
    var d = Math.sqrt(Math.pow(x - t[0], 2) + Math.pow(y - t[1], 2));
    return d <= watchR && !losBlocked(t[0], t[1], x, y);
  }

  function poiAt(x, y) {
    var best = null, bestD = 2.4;
    for (var key in W.pois) {
      var p = key.split(',');
      var d = Math.sqrt(Math.pow(x - p[0], 2) + Math.pow(y - p[1], 2));
      if (d < bestD) { bestD = d; best = W.pois[key]; }
    }
    return best || W.title;
  }

  function speakerNear() {
    var found = null;
    W.speakers.forEach(function (s) {
      var d = Math.abs(the wanderer.x - s.at[0]) + Math.abs(the wanderer.y - s.at[1]);
      if (d <= 1) found = s;
    });
    return found;
  }

  function drawTile(x, y) {
    var t = tileAt(x, y);
    var e = W.legend[t] || W.legend['.'];
    var px = x * TILE, py = y * TILE;
    ctx.fillStyle = e.base[(x + y) % e.base.length];
    ctx.fillRect(px, py, TILE, TILE);
    var c = e.deco_color;
    if (e.deco === 'waves' && (x + y) % 3 === 0) {
      ctx.fillStyle = c;
      ctx.fillRect(px + 4, py + 14, TILE - 8, 2);
    }
    if (e.deco === 'reeds') {
      ctx.fillStyle = c;
      ctx.fillRect(px + 6, py + 8, 2, 8);
      ctx.fillRect(px + 20, py + 16, 2, 10);
    }
    if (e.deco === 'bog') {
      ctx.fillStyle = c;
      ctx.fillRect(px + 8, py + 10, 6, 3);
      ctx.fillRect(px + 18, py + 20, 8, 3);
    }
    if (e.deco === 'ring') {
      ctx.strokeStyle = c;
      ctx.beginPath();
      ctx.arc(px + 16, py + 18, 8, 0, Math.PI * 2);
      ctx.stroke();
    }
    if (e.deco === 'gold') {
      ctx.fillStyle = c;
      ctx.fillRect(px + 14, py + 14, 4, 4);
    }
    if (e.deco === 'garden') {
      ctx.fillStyle = c;
      ctx.fillRect(px + 6, py + 10, 2, 9);
      ctx.fillRect(px + 18, py + 16, 2, 9);
      ctx.fillRect(px + 25, py + 6, 2, 7);
    }
    if (e.deco === 'cap') {
      ctx.fillStyle = c;
      ctx.fillRect(px + 4, py + 4, TILE - 8, 6);
    }
    if (e.deco === 'cross') {
      ctx.strokeStyle = c;
      ctx.beginPath();
      ctx.moveTo(px + 16, py + 10);
      ctx.lineTo(px + 16, py + 22);
      ctx.stroke();
    }
  }

  function drawFigure(px, py, bodyColor, headColor) {
    ctx.fillStyle = bodyColor;
    ctx.beginPath();
    ctx.arc(px + 16, py + 21, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = headColor;
    ctx.beginPath();
    ctx.arc(px + 16, py + 11, 4, 0, Math.PI * 2);
    ctx.fill();
  }

  function draw() {
    ctx.fillStyle = W.bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (var y = 0; y < rows(); y++) {
      for (var x = 0; x < cols(); x++) {
        var t = tileAt(x, y);
        drawTile(x, y);
        if (watched(x, y) && SANCT.indexOf(t) === -1) {
          ctx.fillStyle = W.watch.overlay;
          ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
        }
      }
    }
    W.speakers.forEach(function (s) {
      drawFigure(s.at[0] * TILE, s.at[1] * TILE, W.speaker_color, W.speaker_head);
    });
    /* the wanderer - ink on the world */
    ctx.fillStyle = W.willow_color;
    ctx.beginPath();
    ctx.arc(the wanderer.x * TILE + 16, the wanderer.y * TILE + 18, 7, 0, Math.PI * 2);
    ctx.fill();
  }

  function hud() {
    document.getElementById('poi').textContent = poiAt(the wanderer.x, the wanderer.y);
    var onSanct = SANCT.indexOf(tileAt(the wanderer.x, the wanderer.y)) !== -1;
    document.getElementById('watched').textContent = onSanct
      ? 'safe here.'
      : watched(the wanderer.x, the wanderer.y)
        ? 'the tower watches.'
        : 'out of the tower\u2019s sight.';
    var near = speakerNear();
    var note = document.getElementById('near-note');
    if (near && !openSpeaker) {
      note.hidden = false;
      note.textContent = near.name + ' is here. press E, or tap.';
    } else if (!openSpeaker) {
      note.hidden = true;
    }
  }

  function buildRail() {
    var rail = document.getElementById('town-phase');
    if (!rail) return;
    phases.forEach(function (p, i) {
      var b = document.createElement('button');
      b.type = 'button';
      b.dataset.phase = p;
      b.textContent = p;
      b.setAttribute('aria-pressed', i === 0 ? 'true' : 'false');
      b.addEventListener('click', function () { setPhase(p); });
      rail.appendChild(b);
    });
  }

  function setPhase(p) {
    phase = p;
    watchR = W.watch.r_by_phase[p] || watchR;
    var rail = document.getElementById('town-phase');
    if (rail) {
      rail.querySelectorAll('button').forEach(function (b) {
        b.setAttribute('aria-pressed', b.dataset.phase === p ? 'true' : 'false');
      });
    }
    draw();
    hud();
  }

  function move(dx, dy) {
    var nx = the wanderer.x + dx, ny = the wanderer.y + dy;
    if (blocked(nx, ny)) return;
    the wanderer.x = nx;
    the wanderer.y = ny;
    if (openSpeaker) closeNpc();
    draw();
    hud();
  }

  function talk() {
    var near = speakerNear();
    if (!near) return;
    if (openSpeaker && openSpeaker.key === near.key) { closeNpc(); return; }
    if (busy) return;
    openSpeaker = near;
    document.getElementById('npc-box').hidden = false;
    document.getElementById('npc-name').textContent = near.name;
    document.getElementById('npc-line').textContent = '\u2026';
    document.getElementById('near-note').hidden = true;
    busy = true;
    fetch('/api/npc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phase: phase, speaker: near.key })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (openSpeaker && openSpeaker.key === near.key) {
          document.getElementById('npc-line').textContent =
            data.line || 'she says nothing, and stays.';
        }
      })
      .catch(function () {
        if (openSpeaker && openSpeaker.key === near.key) {
          document.getElementById('npc-line').textContent =
            'she says nothing, and stays.';
        }
      })
      .finally(function () { busy = false; });
  }

  function closeNpc() {
    openSpeaker = null;
    var box = document.getElementById('npc-box');
    if (box) box.hidden = true;
    hud();
  }

  document.addEventListener('keydown', function (e) {
    var key = e.key.toLowerCase().replace('arrow', '');
    var dirs = {
      up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0],
      w: [0, -1], s: [0, 1], a: [-1, 0], d: [1, 0]
    };
    if (key === 'e' || key === 'enter') { talk(); return; }
    if (dirs[key]) {
      e.preventDefault();
      move(dirs[key][0], dirs[key][1]);
    }
  });

  canvas.addEventListener('click', talk);

  var pad = document.getElementById('dpad');
  if (pad) {
    pad.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-dir]');
      if (!b) return;
      var d = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] }[b.dataset.dir];
      if (d) move(d[0], d[1]);
    });
  }

  var closeBtn = document.getElementById('npc-close');
  if (closeBtn) closeBtn.addEventListener('click', closeNpc);
})();
