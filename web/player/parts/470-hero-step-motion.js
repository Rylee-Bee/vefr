  // ---- the hero's step motion ----
  var STEP_MS = 110;       // one step's drawn tween, in milliseconds
  var STEP_HOP = 0.02;     // the hop's height, as a fraction of a tile
  var STEP_LEAN = 2;       // the lean into travel, in degrees
  var STEP_SQUASH = 0.04;  // the landing squash, as a fraction
  // `hop` lets a walk sheet ride without the Phase A bob (0); it defaults
  // to the standard hop, so every existing caller is unchanged.
  function stepMotion(p, fx, fy, t, dir, reduced, hop) {
    // `reduced` is the identity: no offset, no lean, no squash.
    if (reduced) return { dx: 0, dy: 0, lean: 0, squash: 0 };
    if (p < 0) p = 0; else if (p > 1) p = 1;
    var ease = 1 - (1 - p) * (1 - p);   // ease-out, travel slows at the end
    var arc = Math.sin(Math.PI * p);    // 0 at both ends, 1 mid-step
    var lean = 0;
    if (dir === 'right') lean = STEP_LEAN * arc;
    else if (dir === 'left') lean = -STEP_LEAN * arc;
    var land = p > 0.7 ? (p - 0.7) / 0.3 : 0;   // squash as the hero lands
    var bob = (typeof hop === 'number') ? hop : STEP_HOP;
    return { dx: fx * t * ease,
             dy: fy * t * ease - arc * t * bob,   // negative y is up
             lean: lean, squash: land * STEP_SQUASH };
  }
