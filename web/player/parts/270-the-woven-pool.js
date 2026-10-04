// ---- the woven pool ----
// When no live endpoint answers, draw a real, pre-generated line
// from the pool. Used entries are remembered per combo; when a
// combo is spent, unused lines from any other combo keep the world
// speaking; when the whole pool is spent, say so plainly.
const POOL_USED = store.getJSON('vefr-pool-used', {});

function poolDraw(key) {
  const pool = window.VEFR_POOL || {};
  const combos = [key].concat(Object.keys(pool).filter(function (k) { return k !== key; }));
  for (let c = 0; c < combos.length; c++) {
    const k = combos[c];
    const entries = pool[k] || [];
    const used = POOL_USED[k] || [];
    const fresh = [];
    for (let i = 0; i < entries.length; i++) {
      if (used.indexOf(i) === -1) fresh.push(i);
    }
    if (!fresh.length) continue;
    const idx = fresh[Math.floor(Math.random() * fresh.length)];
    POOL_USED[k] = used.concat(idx);
    store.setJSON('vefr-pool-used', POOL_USED);
    return entries[idx];
  }
  return null;
}

