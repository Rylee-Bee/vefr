/* Old Name - the town of Private Canon, walkable. 32px tiles, Bog & Bell. */
(function () {
  var canvas = document.getElementById('town-canvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var TILE = 32;

  /* Legend: . grass  , reeds  ~ water  = road  P/p path
     # building  H bookshop  M mill  T tower  W well  S whisper-stone
     B bog  G grave */
  var MAP = [
    '..............=...............',
    '..............=...............',
    '..####........=......#####....',
    '..#MM#........=........T..##..',
    '..####........=.......#####...',
    '.....P........=...............',
    '....W.P.......=...............',
    '.....P..S.....=...............',
    '.....P........=...............',
    '.....P........=...............',
    '~~~~~~~~pp~~~~~~~~~~~~~~~~~~~~',
    '~~~~~~~~pp~~~~~~~~~~~~~~~~~~~~',
    ',,,,,,p,,,,,,,,,,,,,,,,,,.....',
    ',,BBB,,.....HHHH.,,,,,,,,.....',
    ',,BBB,,p,,,H..H.P,,,,,,,,.....',
    ',,BBB,,p,,,HHHH.P,,BBB........',
    ',,BBB,,p,,,,,,,P.BB...........',
    ',,BBB,,p,,,,,,,P..............',
    ',,,,,,,,.......P..............',
    ',,,,,,,,,,,,,,,,,,,,,,,,,,,,,,'
  ];
  var ROWS = MAP.length;
  var COLS = MAP[0].length;
  var TOWER = { x: 23, y: 3, r: 12 };

  var POIS = {
    '12,13': 'the bookshop - the back door',
    '13,15': 'the bookshop - the front',
    '14,6': 'the well',
    '15,7': 'the whisper-stone',
    '23,3': 'the church tower',
    '20,3': "the priest's house",
    '3,3': 'the mill',
    '7,17': "her mother's grave",
    '8,10': 'the reed crossing',
    '14,0': 'the road out'
  };

  var COLORS = {
    '.': ['#212a20', '#242d22'],
    ',': ['#26301f'],
    '~': ['#20272b'],
    '=': ['#3a352c'],
    'P': ['#332e26'],
    'p': ['#332e26'],
    '#': ['#2a2e33'],
    'H': ['#2b2721'],
    'M': ['#26221a'],
    'T': ['#2a2e33'],
    'W': ['#212a20'],
    'S': ['#212a20'],
    'B': ['#15180f'],
    'G': ['#212a20']
  };

  var the wanderer = { x: 12, y: 14 }; /* the bookshop's back room */

  function tileAt(x, y) {
    if (y < 0 || y >= ROWS || x < 0 || x >= COLS) return '#';
    return MAP[y][x];
  }

  function blocked(x, y) {
    var t = tileAt(x, y);
    return t === '~' || t === 'B' || t === '#' || t === 'T' || t === 'M';
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
    var d = Math.sqrt(Math.pow(x - TOWER.x, 2) + Math.pow(y - TOWER.y, 2));
    return d <= TOWER.r && !losBlocked(TOWER.x, TOWER.y, x, y);
  }

  function poiAt(x, y) {
    var best = null, bestD = 2.4;
    for (var key in POIS) {
      var p = key.split(',');
      var d = Math.sqrt(Math.pow(x - p[0], 2) + Math.pow(y - p[1], 2));
      if (d < bestD) { bestD = d; best = POIS[key]; }
    }
    return best || 'Private Canon';
  }

  function drawTile(x, y) {
    var t = tileAt(x, y);
    var px = x * TILE, py = y * TILE;
    var c = COLORS[t] || COLORS['.'];
    ctx.fillStyle = c[(x + y) % c.length];
    ctx.fillRect(px, py, TILE, TILE);
    if (t === '~') {
      ctx.fillStyle = '#2c353a';
      if ((x + y) % 3 === 0) ctx.fillRect(px + 4, py + 14, TILE - 8, 2);
    }
    if (t === ',') {
      ctx.fillStyle = '#31402c';
      ctx.fillRect(px + 6, py + 8, 2, 8);
      ctx.fillRect(px + 20, py + 16, 2, 10);
    }
    if (t === 'B') {
      ctx.fillStyle = '#1e2416';
      ctx.fillRect(px + 8, py + 10, 6, 3);
      ctx.fillRect(px + 18, py + 20, 8, 3);
    }
    if (t === 'W') {
      ctx.strokeStyle = '#6b6f66';
      ctx.beginPath();
      ctx.arc(px + 16, py + 18, 8, 0, Math.PI * 2);
      ctx.stroke();
    }
    if (t === 'S') {
      ctx.fillStyle = '#c9ad6b';
      ctx.fillRect(px + 14, py + 14, 4, 4);
    }
    if (t === 'T') {
      ctx.fillStyle = '#3d434a';
      ctx.fillRect(px + 4, py + 4, TILE - 8, 6);
    }
    if (t === 'G') {
      ctx.strokeStyle = '#e8e5df';
      ctx.beginPath();
      ctx.moveTo(px + 16, py + 10);
      ctx.lineTo(px + 16, py + 22);
      ctx.stroke();
    }
  }

  function draw() {
    ctx.fillStyle = '#131311';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (var y = 0; y < ROWS; y++) {
      for (var x = 0; x < COLS; x++) {
        drawTile(x, y);
        if (watched(x, y)) {
          ctx.fillStyle = 'rgba(42, 46, 51, 0.30)';
          ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
        }
      }
    }
    /* the wanderer - ink on the world */
    ctx.fillStyle = '#e8e5df';
    ctx.beginPath();
    ctx.arc(the wanderer.x * TILE + 16, the wanderer.y * TILE + 18, 7, 0, Math.PI * 2);
    ctx.fill();
  }

  function hud() {
    document.getElementById('poi').textContent = poiAt(the wanderer.x, the wanderer.y);
    document.getElementById('watched').textContent = watched(the wanderer.x, the wanderer.y)
      ? 'the tower watches.'
      : 'out of the tower\u2019s sight.';
  }

  function move(dx, dy) {
    var nx = the wanderer.x + dx, ny = the wanderer.y + dy;
    if (blocked(nx, ny)) return;
    the wanderer.x = nx;
    the wanderer.y = ny;
    draw();
    hud();
  }

  document.addEventListener('keydown', function (e) {
    var key = e.key.toLowerCase().replace('arrow', '');
    var dirs = {
      up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0],
      w: [0, -1], s: [0, 1], a: [-1, 0], d: [1, 0]
    };
    if (dirs[key]) {
      e.preventDefault();
      move(dirs[key][0], dirs[key][1]);
    }
  });

  var pad = document.getElementById('dpad');
  if (pad) {
    pad.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-dir]');
      if (!b) return;
      var d = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] }[b.dataset.dir];
      if (d) move(d[0], d[1]);
    });
  }

  draw();
  hud();
})();
