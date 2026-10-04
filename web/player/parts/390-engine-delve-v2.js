// -- delve v2 start --
// The delve engine: the JavaScript twin of Python's `prng` and
// `generate_floor_v2` in src/vefr/delve.py. Pure logic only - no DOM,
// no clock, no Math.random, no storage - so the parity harness
// (tests/fixtures/floor_v2_parity_harness.mjs) can run this exact text
// in the real woven player and demand the same draws Python makes.
// `rng()` is one call of `prng(seed)`; a whole number in [lo, hi] is
// `lo + Math.floor(rng() * (hi - lo + 1))`, matching Python's
// `int(rng() * n)`. The draw order matches the numbered comment above
// `generate_floor_v2`: rooms (w, h, x, y per attempt), then one bend
// draw per corridor, then two draws per stair attempt.
window.VEFR_DELVE = (function () {
  // xmur3 hashes the seed by its UTF-16 code units (exactly what
  // `charCodeAt` reads, so an astral character is two units), and the
  // resulting 32-bit state feeds mulberry32. Only 32-bit integer maths
  // is used, so this returns the identical stream Python draws. The
  // returned closure is stateful: every call yields the next float.
  function prng(seed) {
    var str = String(seed);
    var h = 1779033703 ^ str.length;
    for (var i = 0; i < str.length; i++) {
      h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
      h = h << 13 | h >>> 19;
    }
    h = Math.imul(h ^ h >>> 16, 2246822507);
    h = Math.imul(h ^ h >>> 13, 3266489909);
    var state = (h ^ h >>> 16) >>> 0;
    return function next() {
      state = state + 0x6D2B79F5 | 0;
      var t = Math.imul(state ^ state >>> 15, 1 | state);
      t = (t + Math.imul(t ^ t >>> 7, 61 | t)) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  // A room's centre: integer floor division, as Python's `w // 2`.
  function center(room) {
    return [room[0] + Math.floor(room[2] / 2), room[1] + Math.floor(room[3] / 2)];
  }

  // True when two room rectangles touch or sit closer than `pad`.
  function overlaps(a, b, pad) {
    return ((a[0] - pad) < (b[0] + b[2]) && (b[0] - pad) < (a[0] + a[2])
      && (a[1] - pad) < (b[1] + b[3]) && (b[1] - pad) < (a[1] + a[3]));
  }

  function carveRoom(grid, room) {
    var x = room[0], y = room[1], w = room[2], h = room[3];
    for (var yy = y; yy < y + h; yy++) {
      for (var xx = x; xx < x + w; xx++) grid[yy][xx] = '.';
    }
  }

  function carveH(grid, x0, x1, y) {
    for (var x = Math.min(x0, x1); x <= Math.max(x0, x1); x++) grid[y][x] = '.';
  }

  function carveV(grid, x, y0, y1) {
    for (var y = Math.min(y0, y1); y <= Math.max(y0, y1); y++) grid[y][x] = '.';
  }

  // A whole number in [lo, hi] (both inclusive) from one `prng` draw.
  function randRange(rng, lo, hi) {
    return lo + Math.floor(rng() * (hi - lo + 1));
  }

  function placeRoomsV2(rng, grid, width, height, count) {
    var placed = [];
    var maxW = Math.max(3, Math.min(9, width - 2));
    var maxH = Math.max(3, Math.min(7, height - 2));
    for (var attempt = 0; attempt < count * 30; attempt++) {
      if (placed.length >= count) break;
      var w = randRange(rng, 3, maxW);
      var h = randRange(rng, 3, maxH);
      var x = randRange(rng, 1, width - 1 - w);
      var y = randRange(rng, 1, height - 1 - h);
      var room = [x, y, w, h];
      var hit = false;
      for (var p = 0; p < placed.length; p++) {
        if (overlaps(room, placed[p], 1)) { hit = true; break; }
      }
      if (hit) continue;
      carveRoom(grid, room);
      placed.push(room);
    }
    if (placed.length === 0) {
      carveRoom(grid, [1, 1, 3, 3]);
      placed.push([1, 1, 3, 3]);
    }
    return placed;
  }

  function carveCorridorV2(rng, grid, a, b) {
    var ax = a[0], ay = a[1], bx = b[0], by = b[1];
    if (rng() < 0.5) {
      carveH(grid, ax, bx, ay);
      carveV(grid, bx, ay, by);
    } else {
      carveV(grid, ax, ay, by);
      carveH(grid, ax, bx, by);
    }
  }

  var STAIR_ATTEMPTS = 500;
  var MIN_STAIR_DISTANCE = 10;

  function pickStairsV2(rng, floors) {
    if (floors.length < 2) {
      throw new Error("a floor needs at least two walkable tiles for stairs");
    }
    var n = floors.length;
    var best = null;
    var bestDist = -1;
    for (var attempt = 0; attempt < STAIR_ATTEMPTS; attempt++) {
      var i = Math.floor(rng() * n);
      var j = Math.floor(rng() * (n - 1));
      if (j >= i) j += 1;
      var a = floors[i], b = floors[j];
      var dist = Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]);
      if (dist > bestDist) { best = [a, b]; bestDist = dist; }
      if (dist >= MIN_STAIR_DISTANCE) return [a, b];
    }
    return best;
  }

  function generateFloorV2(seed, width, height, rooms) {
    if (width === undefined) width = 30;
    if (height === undefined) height = 20;
    if (rooms === undefined) rooms = 8;
    if (width < 5 || height < 5) {
      throw new Error("width and height must each be at least 5");
    }
    if (rooms < 1) {
      throw new Error("rooms must be at least 1");
    }

    var rng = prng(seed);
    var grid = [];
    for (var y = 0; y < height; y++) {
      var row = [];
      for (var x = 0; x < width; x++) row.push('#');
      grid.push(row);
    }
    var placed = placeRoomsV2(rng, grid, width, height, rooms);
    for (var k = 0; k + 1 < placed.length; k++) {
      carveCorridorV2(rng, grid, center(placed[k]), center(placed[k + 1]));
    }

    var floors = [];
    for (var fy = 0; fy < height; fy++) {
      for (var fx = 0; fx < width; fx++) {
        if (grid[fy][fx] === '.') floors.push([fx, fy]);
      }
    }
    var stairs = pickStairsV2(rng, floors);
    var up = stairs[0], down = stairs[1];
    grid[up[1]][up[0]] = 'u';
    grid[down[1]][down[0]] = 'd';
    var rows = [];
    for (var ry = 0; ry < height; ry++) rows.push(grid[ry].join(''));
    return rows;
  }

  return { prng: prng, generateFloorV2: generateFloorV2 };
})();
// -- delve v2 end --
