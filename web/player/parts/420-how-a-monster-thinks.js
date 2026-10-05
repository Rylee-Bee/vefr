  // ---- how a monster thinks ----
  // A monster walks the floor the way the hero does: over walkable
  // tiles, around corners and walls, never through them. Each turn the
  // walkable tiles are flooded once from wherever the thinking starts -
  // the hero, or a monster a lost one is drifting toward - and the
  // monster steps to the neighbour that is closest to (or furthest
  // from) that flood. Breadth-first, one cost per tile, so a tile four
  // paces the long way round is four, not zero. The neighbour order is
  // fixed - up, down, left, right - so a tie always breaks the same
  // way and a floor always plays out the same way. No randomness
  // anywhere in here.
  var DIRS = [[0, -1], [0, 1], [-1, 0], [1, 0]];
  // A tile the flood may cross: on the map and not solid. Monsters and
  // the hero stand on walkable tiles too, so they are in the map - what
  // a single step may land on is `tileOpenForEnemy`'s business.
  function floorOpen(x, y) {
    if (x < 0 || y < 0 || y >= town.map.length || x >= town.map[0].length) return false;
    return !((town.legend[town.map[y][x]] || {}).solid);
  }
  // Steps from (x, y) to every walkable tile. `dist` has the source at
  // 0 and no entry at all for a tile the flood never reached. The flood
  // stops `floodLimit` tiles (Manhattan) from its own source: the
  // monster turn sets that once, before any monster acts, to a little
  // past the farthest wake, so a turn never floods the far end of the
  // floor. It rides in a variable rather than an argument so the
  // signature stays `distMap(x, y)`; 0 (no monster turn has set it)
  // means unbounded. The turn's harness counter is fed from here too -
  // enemyTurn resets it per turn, so it always shows the last turn.
  var floodLimit = 0;
  function distMap(x, y) {
    var dist = {};
    var start = x + ',' + y;
    dist[start] = 0;
    var queue = [[x, y]];
    var stats = window.VEFR_FLOOD_STATS;
    if (stats) { stats.floods++; stats.tiles++; }
    for (var qi = 0; qi < queue.length; qi++) {
      var cx = queue[qi][0], cy = queue[qi][1];
      for (var i = 0; i < DIRS.length; i++) {
        var nx = cx + DIRS[i][0], ny = cy + DIRS[i][1];
        var away = manhattan(nx, ny, x, y);
        if (floodLimit && away > floodLimit) continue;
        var nk = nx + ',' + ny;
        if (dist[nk] !== undefined) continue;
        if (!floorOpen(nx, ny)) continue;
        dist[nk] = dist[cx + ',' + cy] + 1;
        queue.push([nx, ny]);
        if (stats) {
          stats.tiles++;
          if (away > stats.maxSpan) stats.maxSpan = away;
        }
      }
    }
    return dist;
  }
  // The turn's shared floods, one per source tile, each built the first
  // time something needs it and kept for the rest of the turn. The
  // floors are small and a flood is cheap, so a turn that never moves a
  // monster never pays for one.
  function turnMaps() { return { from: {} }; }
  function distances(maps, x, y) {
    var key = x + ',' + y;
    if (!maps.from[key]) maps.from[key] = distMap(x, y);
    return maps.from[key];
  }
  // One step along `dist`: the neighbour with the lowest count (dir 1),
  // or the highest (-1, for a monster running for its life). A tile
  // with no count is one the source cannot reach, and is never chosen.
  // A tie keeps the earlier neighbour in the fixed order, so the same
  // floor always plays out the same way. If the best tile is already
  // taken the monster holds rather than shuffling sideways, so two of
  // them nose to nose stay nose to nose. True means the step was onto
  // the hero, and the hero was hit.
  function stepAlong(e, dist, dir) {
    var best = null, bestVal = (dir > 0 ? Infinity : -Infinity);
    for (var i = 0; i < DIRS.length; i++) {
      var nx = e.at[0] + DIRS[i][0], ny = e.at[1] + DIRS[i][1];
      var d = dist[nx + ',' + ny];
      if (d === undefined) continue;
      if (dir > 0 ? (d >= bestVal) : (d <= bestVal)) continue;
      bestVal = d; best = [nx, ny];
    }
    if (!best) return false;
    if (best[0] === hero[0] && best[1] === hero[1]) return enemyAttack(e);
    if (!tileOpenForEnemy(best[0], best[1])) return false;
    e.at = best;
    return false;
  }
  // The nearest other living monster, by walking distance rather than
  // straight-line: a wall between two of them is a long way round. Ties
  // go to the first in the roster. Null when this one is alone.
  function nearestAlly(e, maps) {
    var from = distances(maps, e.at[0], e.at[1]);
    var best = null, bestDist = Infinity;
    for (var i = 0; i < enemies.length; i++) {
      var other = enemies[i];
      if (!other || !other.alive || other === e) continue;
      var d = from[other.at[0] + ',' + other.at[1]];
      if (d === undefined || d >= bestDist) continue;
      bestDist = d; best = other;
    }
    return best;
  }
  // Badly hurt: down to a third of the health it walked into the region
  // with. A monster that has never been touched is not.
  function badlyHurt(e) { return e.hp <= e.hp0 / 3; }

