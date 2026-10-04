// ---- the fragment banks ----
// The composer's last resort before honest silence: when the pool
// is absent entirely, re-splice the speaker's own hand-written
// fragments (window.VEFR_FRAGMENTS). Every word is the author's.
// A bank needs at least two lines to splice; fewer stays silent.
function fragmentSpeakers() {
  const bank = window.VEFR_FRAGMENTS || {};
  return Object.keys(bank).filter(function (k) {
    return (bank[k] || []).length >= 2;
  });
}

function composeFromFragments(speaker, kind, seedOverride) {
  const lines = ((window.VEFR_FRAGMENTS || {})[speaker] || []).slice();
  if (lines.length < 2) return null;
  const rng = mulberry32(seedOverride || (saveSeed() + nextDraw()));
  let a = lines[Math.floor(rng() * lines.length)];
  let b = lines[Math.floor(rng() * lines.length)];
  for (let tries = 0; tries < 4 && String(a) === String(b); tries++) {
    b = lines[Math.floor(rng() * lines.length)];
  }
  const woven = spliceCloth(a, b, rng);
  if (!woven) return null;
  const speakers = (window.VEFR_WORLD && window.VEFR_WORLD.speakers) || {};
  const display = (speakers[speaker] && speakers[speaker].name) || speaker;
  const card = { speaker: display };
  if (kind === 'line') card.line = woven;
  else { card.whisper = woven; card.is_true = true; }
  return card;
}

function whisperFromFragments(seedOverride) {
  const keys = fragmentSpeakers();
  if (!keys.length) return null;
  const rng = mulberry32(seedOverride || (saveSeed() + nextDraw()));
  return composeFromFragments(keys[Math.floor(rng() * keys.length)], 'whisper', seedOverride);
}

