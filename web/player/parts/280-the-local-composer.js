// ---- the local composer ----
// When the pool is spent, the world need not fall silent mid-play:
// a small seeded generator re-weaves the pool's own cloth. Every
// word is real model output in the pack's voice, cut into sentences
// and re-sewn under a seed drawn from this save - the same few
// threads, new cloth each play. Nothing is invented here: whispers
// may cross combos (a rumor travels), but an npc line only ever
// splices that speaker's own words, and when there is no pool at
// all the world stays honestly silent.
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function saveSeed() {
  try {
    let s = store.get('vefr-save-seed');
    if (!s) {
      s = String(Math.floor(Math.random() * 0x7fffffff));
      store.set('vefr-save-seed', s);
    }
    return parseInt(s, 10) || 1;
  } catch (e) { return 1; }
}

function nextDraw() {
  try {
    const n = (parseInt(store.get('vefr-localgen-draws') || '0', 10) || 0) + 1;
    store.set('vefr-localgen-draws', String(n));
    return n;
  } catch (e) { return 1; }
}

function spliceCloth(aText, bText, rng) {
  const sa = String(aText).match(/[^.!?]+[.!?]*/g) || [String(aText)];
  const sb = String(bText).match(/[^.!?]+[.!?]*/g) || [String(bText)];
  const head = sa[0].trim();
  const tail = (sb.length > 1 ? sb.slice(1).join(' ') : sb[0]).trim();
  if (head === tail || !head || !tail) return head || null;
  return head + ' ' + tail;
}

function _compose(key, crossKind, seedOverride) {
  const pool = window.VEFR_POOL || {};
  let entries = (pool[key] || []).slice();
  if (crossKind && entries.length < 2) {
    const kind = key.split(':')[0];
    for (const k in pool) {
      if (k !== key && k.split(':')[0] === kind) entries = entries.concat(pool[k]);
    }
  }
  if (entries.length < 2) return null;
  const rng = mulberry32(seedOverride || (saveSeed() + nextDraw()));
  const textOf = (e) => (e.whisper !== undefined ? e.whisper : e.line);
  let a = entries[Math.floor(rng() * entries.length)];
  let b = entries[Math.floor(rng() * entries.length)];
  for (let tries = 0; tries < 4 && String(textOf(a)) === String(textOf(b)); tries++) {
    b = entries[Math.floor(rng() * entries.length)];
  }
  const woven = spliceCloth(textOf(a), textOf(b), rng);
  if (!woven) return null;
  const card = {};
  for (const f in a) card[f] = a[f];
  if (a.whisper !== undefined) card.whisper = woven; else card.line = woven;
  return card;
}

function composeWhisper(key, seedOverride) {
  return _compose(key, true, seedOverride);
}

function composeLine(key, seedOverride) {
  return _compose(key, false, seedOverride);
}

