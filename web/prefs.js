/* vefr - the reading & sound preferences.
 *
 * The settings that decide HOW the story reads to you, not WHAT
 * the story says. Lives in localStorage under `vefr-prefs`, mirrors
 * itself to <html data-prefs="..."> so the stylesheet can branch on
 * it with plain CSS selectors, and exposes a tiny pub/sub for views
 * that want to react (the bottom-sheet panel, mostly).
 *
 * The Norse-coded naming tradition lives in the *panel*, not here -
 * this file is the engine's contract. Urd / Verdandi / Skuld are
 * three columns in the panel UI; here the keys are English.
 *
 * No model calls, no network reads. The packaged ratatoskr weave
 * file ships this code inline next to state.js - the single file is
 * the unit of sharing.
 */
(function () {
  var KEY = 'vefr-prefs';
  var URL_PARAM = 'prefs';

  /* Defaults are the inclusive-forward floor. They match the agent
     rules' matrix: dark default, Atkinson Hyperlegible (or the
     installed serif fallback when the woff2 isn't shipped yet),
     luminance-only focus, motion off, comfortable density. The user
     can move away from any of them. */
  var DEFAULTS = {
    textSize: 'm',           /* xs | s | m | l | xl | 2xl */
    spacing:  'm',           /* tight | m | loose */
    font:     'atkinson',    /* system | atkinson | opendyslexic | serif */
    contrast: 'm',           /* m | high | ultra */
    palette:  'standard',    /* standard | cb-safe */
    motion:   'off',         /* off | subtle | full */
    focus:    'luminance',   /* luminance | accent */
    density:  'comfortable', /* comfortable | compact */
    sound: {
      effects: 0.7, speech: 0.8, ambience: 0.5,
      pairWithVisual: true,
      captions: true
    }
  };

  var SUBS = [];
  var state = null;

  /* contrast pref -> Figma semantic theme (vefr-theme.css). */
  var THEME_BY_CONTRAST = {
    m: 'warm',           /* Warm & Easy (standard) */
    high: 'bright',      /* Bright & Clear (high contrast) */
    ultra: 'max-contrast' /* Nothing Hides (ultra outlines) */
  };

  function deepClone(o) {
    return JSON.parse(JSON.stringify(o));
  }

  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return deepClone(DEFAULTS);
      var parsed = JSON.parse(raw);
      /* New keys land by merge, not replace - the next release can
         add a setting without breaking old saves. */
      var merged = deepClone(DEFAULTS);
      for (var k in parsed) {
        if (parsed[k] && typeof parsed[k] === 'object' && !Array.isArray(parsed[k])
            && merged[k] && typeof merged[k] === 'object') {
          for (var sk in parsed[k]) merged[k][sk] = parsed[k][sk];
        } else if (typeof parsed[k] !== 'undefined') {
          merged[k] = parsed[k];
        }
      }
      return merged;
    } catch (err) { /* broken JSON or no storage - defaults */ }
    return deepClone(DEFAULTS);
  }

  function persist() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (err) {}
  }

  function toAttr(p) {
    /* The <html data-prefs="..."> token. Order-stable so a re-apply
       produces the same string and CSS attribute diffs stay small. */
    return [
      'text=' + p.textSize,
      'space=' + p.spacing,
      'font=' + p.font,
      'contrast=' + p.contrast,
      'palette=' + p.palette,
      'motion=' + p.motion,
      'focus=' + p.focus,
      'density=' + p.density
    ].join(';');
  }

  function apply(p) {
    var root = document.documentElement;
    if (!root) return;
    root.setAttribute('data-prefs', toAttr(p));
    /* The Figma design system's three contrast tiers live in CSS as
       [data-theme] blocks (web/vefr-theme.css). The contrast pref is
       the user-facing switch, so the theme attribute is derived from
       it here - one control, both vocabularies, no second pref key
       to migrate or round-trip. */
    root.setAttribute('data-theme', THEME_BY_CONTRAST[p.contrast] || 'warm');
  }

  function notify() {
    SUBS.slice().forEach(function (fn) {
      try { fn(state); } catch (err) { /* a view's own problem */ }
    });
  }

  function get() { return deepClone(state); }

  function set(patch) {
    var changed = false;
    function merge(target, src) {
      for (var k in src) {
        if (src[k] && typeof src[k] === 'object' && !Array.isArray(src[k])
            && target[k] && typeof target[k] === 'object') {
          if (merge(target[k], src[k])) changed = true;
        } else if (target[k] !== src[k]) {
          target[k] = src[k];
          changed = true;
        }
      }
    }
    merge(state, patch);
    if (!changed) return get();
    persist();
    apply(state);
    notify();
    return get();
  }

  function preview(patch) {
    /* Apply to the DOM only, never persist. The panel calls this on
       every slider drag and the commit button calls set() with the
       same patch. Skuld is the preview column. */
    var snap = deepClone(state);
    function merge(target, src) {
      for (var k in src) {
        if (src[k] && typeof src[k] === 'object' && !Array.isArray(src[k])
            && target[k] && typeof target[k] === 'object') {
          merge(target[k], src[k]);
        } else { target[k] = src[k]; }
      }
    }
    merge(snap, patch);
    apply(snap);
    return snap;
  }

  function reset() {
    state = deepClone(DEFAULTS);
    persist();
    apply(state);
    notify();
    return get();
  }

  function on(fn) {
    if (typeof fn === 'function') SUBS.push(fn);
    return function () {
      var i = SUBS.indexOf(fn);
      if (i > -1) SUBS.splice(i, 1);
    };
  }

  function shareLink() {
    var p = new URLSearchParams();
    p.set(URL_PARAM, btoa(unescape(encodeURIComponent(JSON.stringify(state)))));
    return location.origin + location.pathname + '?' + p.toString();
  }

  function applyFromUrl() {
    try {
      var raw = new URLSearchParams(location.search).get(URL_PARAM);
      if (!raw) return false;
      var decoded = JSON.parse(decodeURIComponent(escape(atob(raw))));
      set(decoded);
      /* Clean the URL so reloads don't re-apply. */
      var url = new URL(location.href);
      url.searchParams.delete(URL_PARAM);
      history.replaceState(null, '', url.toString());
      return true;
    } catch (err) { return false; }
  }

  state = load();

  /* Apply once on load, before the panel paints, so the very first
     render already honors saved settings. Subscribers that register
     later (the panel) get an immediate notify() via on() below. */
  apply(state);

  window.VEFR_PREFS = {
    get: get,
    set: set,
    preview: preview,
    reset: reset,
    on: on,
    shareLink: shareLink,
    applyFromUrl: applyFromUrl,
    defaults: function () { return deepClone(DEFAULTS); }
  };
})();
