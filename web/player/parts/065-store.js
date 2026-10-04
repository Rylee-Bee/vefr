// ---- store: the one place the player touches browser storage ----
// A sandboxed iframe, or a browser that blocks storage, can make
// browser storage throw. Every method here wraps the access, so a
// player never sees the failure: get returns null, getJSON returns
// its fallback, and set/setJSON give up quietly. `raw()` hands the
// real storage object to startover (which clears every vefr- save);
// nothing else may name the backing global.
var store = {
  get: function (key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  },
  set: function (key, value) {
    try { localStorage.setItem(key, String(value)); } catch (e) {}
  },
  getJSON: function (key, fallback) {
    try {
      var raw = store.get(key);
      if (raw === null) return fallback;
      return JSON.parse(raw);
    } catch (e) { return fallback; }
  },
  setJSON: function (key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
  },
  raw: function () {
    try { return localStorage; } catch (e) { return null; }
  }
};
