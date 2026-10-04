// ---- the pack grammars ----
// The author's own sentence recipes, baked at weave time from
// world.json `grammars` (see window.VEFR_GRAMMARS above). A grammar
// maps a rule name to a list of strings and must carry `origin`,
// where expansion starts: `#rule#` inside a string expands to one
// drawn entry of that rule, and every other character is kept as it
// was written. Three laws keep it safe - `origin` is required, every
// `#rule#` must name a rule in the same grammar, and one expansion
// draws at most 200 entries, so a grammar that feeds itself stops
// instead of looping.
//
// Deterministic: the only randomness is the mulberry32 stream the
// caller hands in, seeded from this save. No model, no network, no
// clock. A reference that does not resolve, or a cap that trips,
// gives the empty string - the honest silence, never a half-built
// line. The engine's own copy of this algorithm is src/vefr/grammar.py.
const GRAMMAR_MAX_EXPANSIONS = 200;

function grammarDraw(entries, rng, budget) {
  // One entry of a rule, or null for a refusal: not a rule, not a
  // list, an empty list, or a spent budget. `budget` is a one-slot
  // counter shared by every nested reference in one expansion.
  if (!Array.isArray(entries) || !entries.length) return null;
  if (budget[0] <= 0) return null;
  budget[0] -= 1;
  const entry = entries[Math.floor(rng() * entries.length)];
  return typeof entry === 'string' ? entry : null;
}

function grammarFill(grammar, text, rng, budget) {
  // Every `#rule#` in `text` replaced by one drawn expansion. A fresh
  // regex per call: a global one is stateful, and the recursion here
  // re-enters this function.
  const re = /#([A-Za-z0-9_][A-Za-z0-9_.-]*)#/g;
  let out = '';
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    const piece = grammarRule(grammar, m[1], rng, budget);
    if (piece === null) return null;
    out += text.slice(last, m.index) + piece;
    last = m.index + m[0].length;
  }
  return out + text.slice(last);
}

function grammarRule(grammar, name, rng, budget) {
  const entry = grammarDraw(grammar[name], rng, budget);
  if (entry === null) return null;
  return grammarFill(grammar, entry, rng, budget);
}

function grammarExpand(grammar, rng) {
  // The whole expansion, or '' when the grammar is not an object, has
  // no `origin`, or refuses anywhere inside.
  if (!grammar || typeof grammar !== 'object' || Array.isArray(grammar)) return '';
  const out = grammarRule(grammar, 'origin', rng, [GRAMMAR_MAX_EXPANSIONS]);
  return out === null ? '' : out;
}

function grammarSeeded(grammar, seed) {
  // The caller's convenience: build the seeded stream from this save
  // (the save's own seed plus the draw number) and expand.
  return grammarExpand(grammar, mulberry32(seed));
}

function grammarFromPack(name) {
  // One named grammar from the baked block, or '' when the pack has
  // no such grammar. The seed is this save plus the draw counter, so
  // the same save says the same thing on the same draw.
  const all = window.VEFR_GRAMMARS || {};
  if (!all[name]) return '';
  return grammarSeeded(all[name], saveSeed() + nextDraw());
}

// The whisper the pack's own grammar speaks when there is no endpoint,
// no pool and no fragment bank: the line from `grammars.whisper`, the
// speaker from `grammars.name` (or plain "someone"), and the truth
// drawn from the same seeded stream. Returns null when the pack has
// no whisper grammar or the grammar refuses.
function whisperFromGrammar() {
  const grammars = window.VEFR_GRAMMARS || {};
  if (!grammars.whisper) return null;
  const rng = mulberry32(saveSeed() + nextDraw());
  const whisper = grammarExpand(grammars.whisper, rng);
  if (!whisper) return null;
  const speaker = grammars.name ? grammarExpand(grammars.name, rng) : '';
  return { speaker: speaker || 'someone', whisper: whisper, is_true: rng() < 0.5 };
}

