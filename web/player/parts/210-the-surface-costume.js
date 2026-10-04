// ---- the surface costume (hp bar, encounter prompt, verbs) ----
// The hero's health is real now: `VEFR_HERO.hp` is the max, the
// current value is carried per world in browser storage
// (`vefr-hp-<world>`), and the bar shows it honestly. Deterministic:
// fixed numbers, no randomness, no clock. A drop to zero is Cozy
// (see setupTown).
var DEATH_LINE = 'You wake in the temple. You lost nothing that mattered.';

