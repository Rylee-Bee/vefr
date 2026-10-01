/* Hero-motion harness: EXECUTES the woven single-file player (jsdom,
   dev-only) and reads the hero's cosmetic step motion through the
   player's own window.VEFR_MOTION snapshot and its pure
   window.VEFR_STEP_MOTION helper. It runs the SAME short walk twice -
   once with motion on, once with prefers-reduced-motion: reduce - so
   the test can prove two things at once:

     1. facing: the hero turns to face each of the four directions, and
        a REFUSED move (a wall, the map edge) still turns the hero;
     2. the game is untouched by the hop: the VEFR_COMBAT snapshot after
        the walk is identical whether the hop ran or was reduced away.

   The pure maths is checked directly too: reduced motion is the
   identity for every progress and direction, and the offsets stay
   inside one tile of travel, a 6% hop, a 6-degree lean and a 0..0.12
   squash even for out-of-range progress.

   usage: node motion_harness.mjs <woven.html> */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const html = fs.readFileSync(process.argv[2], 'utf8');
const noop = () => {};

/* jsdom has no canvas; the player only needs a 2D context to exist so
   setupTown runs. Every drawing call is a no-op, including rotate, so
   the lean path is exercised without a real painter. */
function stubCanvas(window) {
  window.HTMLCanvasElement.prototype.getContext = function () {
    return {
      canvas: this, save: noop, restore: noop, translate: noop, rotate: noop,
      setTransform: noop, fillRect: noop, clearRect: noop, drawImage: noop,
      beginPath: noop, arc: noop, fill: noop, stroke: noop, closePath: noop,
      moveTo: noop, lineTo: noop, fillText: noop,
    };
  };
}

/* Run the player once and walk it. `reduced` decides what
   prefers-reduced-motion reports at move time. `withStep` also runs the
   pure-helper checks against the live player's own VEFR_STEP_MOTION. */
async function runPlayer(reduced, withStep) {
  const dom = new JSDOM(html, {
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    url: 'http://localhost/',
    beforeParse: (window) => {
      stubCanvas(window);
      window.matchMedia = (query) => ({
        matches: /prefers-reduced-motion:\s*reduce/.test(query) ? reduced : false,
        media: query,
        addListener: noop, removeListener: noop,
        addEventListener: noop, removeEventListener: noop,
      });
    },
  });
  const { window } = dom;
  const document = window.document;
  const wait = (ms) => new Promise((r) => window.setTimeout(r, ms));

  // Step through the title screen the way a player does.
  for (let i = 0; i < 200 && !document.getElementById('ts-enter'); i++) await wait(10);
  document.getElementById('ts-enter').click();
  for (let i = 0; i < 200 && !window.VEFR_COMBAT; i++) await wait(10);
  if (!window.VEFR_COMBAT) throw new Error('the woven player never reached play');
  if (typeof window.VEFR_MOTION !== 'function') {
    throw new Error('the player exposes no window.VEFR_MOTION snapshot');
  }

  const motion = () => window.VEFR_MOTION();
  const combat = () => window.VEFR_COMBAT;
  const press = (key) => document.dispatchEvent(
    new window.KeyboardEvent('keydown', { key, bubbles: true }));

  // Wait out any running hop so the next press starts from a settled
  // state and `animating` reads cleanly right after a move.
  const settle = async () => {
    for (let i = 0; i < 400; i++) {
      if (!motion().animating) return true;
      await wait(10);
    }
    throw new Error('a step never finished drawing');
  };

  const result = { reduced, startHero: combat().hero.at.slice(), moves: [],
                   drawn: null, animating: null, hero: null, combat: null,
                   motionProbe: null };

  // The pure helper, read from the live player (never a copy) while its
  // setupTown closure is still alive.
  if (withStep) {
    const stepFn = window.VEFR_STEP_MOTION;
    if (typeof stepFn !== 'function') {
      throw new Error('the player exposes no window.VEFR_STEP_MOTION helper');
    }
    result.step = checkStepMotion(stepFn);
  }

  // One walk, in an order that faces all four ways and hits a wall in
  // all four: north and west of the start are refused at once, then the
  // hero walks the room's edge to be refused by its east and south
  // walls. Facing is read straight after each press, before the hop
  // settles, so a refused move is caught turning the hero too.
  const walk = [
    'ArrowUp',    // refused by the north wall, facing up
    'ArrowLeft',  // refused by the west wall, facing left
    'ArrowDown',  // open, facing down
    'ArrowUp',    // open, facing up again
    'ArrowRight', // open, facing right - the probe move
    'ArrowRight', 'ArrowRight', 'ArrowRight', 'ArrowRight', 'ArrowRight',
    'ArrowRight', // refused by the east wall, facing right
    'ArrowDown', 'ArrowDown',
    'ArrowDown',  // refused by the south wall, facing down
  ];
  let probeTaken = false;
  for (const key of walk) {
    press(key);
    const m = motion();
    result.moves.push({
      key,
      facing: m.facing,
      hero: combat().hero.at.slice(),
      animating: m.animating,
    });
    // The first open eastward step: motion-on may be mid-hop here;
    // reduced motion must already be on the new tile.
    if (!probeTaken && key === 'ArrowRight') {
      result.motionProbe = m.drawn.slice();
      probeTaken = true;
    }
    await settle();
  }

  const final = motion();
  result.drawn = final.drawn.slice();
  result.animating = final.animating;
  result.hero = combat().hero.at.slice();
  result.combat = combat();
  window.close();
  return result;
}

/* The pure helper: reduced motion is the identity, and an un-reduced
   step stays inside its generous bounds, even for progress outside
   0..1 (which must clamp, not run away). */
function checkStepMotion(stepFn) {
  const deltas = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
  const t = 32;
  const ps = [];
  for (let p = -0.5; p <= 1.5001; p += 0.05) ps.push(Math.round(p * 1000) / 1000);

  const identityViolations = [];
  const boundViolations = [];
  let maxDx = 0, maxDy = 0, maxBob = 0, maxLean = 0, maxSquash = 0;

  for (const dir of Object.keys(deltas)) {
    const [fx, fy] = deltas[dir];
    for (const p of ps) {
      const r = stepFn(p, fx, fy, t, dir, true);
      if (r.dx !== 0 || r.dy !== 0 || r.lean !== 0 || r.squash !== 0) {
        identityViolations.push({ p, dir, r });
      }
      const m = stepFn(p, fx, fy, t, dir, false);
      const pc = Math.max(0, Math.min(1, p));
      const ease = 1 - (1 - pc) * (1 - pc);
      // The vertical bob is whatever is left after the travel term.
      const bob = Math.abs(m.dy - fy * t * ease);
      maxDx = Math.max(maxDx, Math.abs(m.dx));
      maxDy = Math.max(maxDy, Math.abs(m.dy));
      maxBob = Math.max(maxBob, bob);
      maxLean = Math.max(maxLean, Math.abs(m.lean));
      maxSquash = Math.max(maxSquash, m.squash);
      const eps = 1e-9;
      // Travel along the axis is at most one tile. The hop itself is a
      // separate additive term (an upward step rises while it travels),
      // so the whole vertical offset is one tile plus at most the hop.
      if (Math.abs(m.dx) > t + eps) boundViolations.push({ p, dir, what: 'dx', v: m.dx });
      if (Math.abs(m.dy) > t * (1 + 0.06) + eps) {
        boundViolations.push({ p, dir, what: 'dy', v: m.dy });
      }
      if (bob > t * 0.06 + eps) boundViolations.push({ p, dir, what: 'bob', v: bob });
      if (Math.abs(m.lean) > 6 + eps) {
        boundViolations.push({ p, dir, what: 'lean', v: m.lean });
      }
      if (m.squash < -eps || m.squash > 0.12 + eps) {
        boundViolations.push({ p, dir, what: 'squash', v: m.squash });
      }
    }
  }
  return {
    samples: ps.length * Object.keys(deltas).length,
    maxDx, maxDy, maxBob, maxLean, maxSquash,
    identityViolations, boundViolations,
    tile: t, hop: 0.06, leanLimit: 6, squashLimit: 0.12,
  };
}

try {
  const active = await runPlayer(false, true);
  const reduced = await runPlayer(true, false);

  process.stdout.write(JSON.stringify({ active, reduced }, null, 1));
} catch (err) {
  console.error(String((err && err.stack) || err));
  process.exit(1);
}
