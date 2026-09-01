/* vefr - the one client-side story state.
 *
 * The town renderer (town.js) and the tabs (the inline script in
 * index.html) are two separate script scopes. Each used to keep its
 * own copy of the same three facts - which phase the world is in,
 * what is in the vault, what the player is carrying - so the two
 * phase rails disagreed the moment you touched either one, and
 * keeping an item in the Vault tab did not reach the town's HUD
 * until you clicked the Town tab. One state, read and written by
 * every view.
 *
 * No framework: a plain object, a patch function, and a list of
 * subscribers. Loaded before every other script; every consumer
 * reaches it as `window.OLD-STATE-GLOBAL`.
 */
/* Per-session play state. ?session=<id> in the URL wins; the last
   minted id is remembered in localStorage; no id at all is the
   default playthrough the deployed quadlet has always kept. */
window.VEFR_SESSION = (function () {
  var sid = '';
  try {
    sid = new URLSearchParams(location.search).get('session')
      || localStorage.getItem('vefr-session')
      || '';
  } catch (err) { /* no storage - play the default session */ }
  return {
    id: sid,
    /* Append the session to any state-touching API URL. */
    wrap: function (url) {
      if (!sid) return url;
      return url + (url.indexOf('?') > -1 ? '&' : '?')
        + 'session=' + encodeURIComponent(sid);
    },
    /* New game: label a fresh playthrough and move to it. The old
       session is never deleted - forking back is a URL away. */
    mint: function () {
      var id = Math.random().toString(16).slice(2, 10);
      try { localStorage.setItem('vefr-session', id); } catch (err) {}
      location.href = location.pathname + '?session=' + id;
    }
  };
})();

window.OLD-STATE-GLOBAL = (function () {
  var subs = [];
  var worldReq = null;

  var state = {
    world: null,     /* the /api/world payload, once */
    phases: [],      /* the pack's phase names, in order */
    phase: null,     /* the one current phase, shared by both rails */
    vault: [],       /* everything kept, oldest first */
    carrying: null   /* the newest kept item - what the player holds */
  };

  function get() { return state; }

  /* Notify every view. One broken listener must not stop the rest -
     a throw in the town renderer should never take the tabs down. */
  function notify() {
    subs.slice().forEach(function (fn) {
      try { fn(state); } catch (err) { /* a view's own problem */ }
    });
  }

  function on(fn) {
    if (typeof fn === 'function') subs.push(fn);
    return fn;
  }

  function set(patch) {
    var changed = false;
    for (var k in patch) {
      if (state[k] !== patch[k]) {
        state[k] = patch[k];
        changed = true;
      }
    }
    if (changed) notify();
    return state;
  }

  /* The phase is the world's tone. Refuse a name the pack does not
     have: the rails are built from state.phases, but a stale click
     handler or a hand-typed call should not be able to put the world
     in a tone the pack cannot describe. */
  function setPhase(p) {
    if (!p) return state;
    if (state.phases.length && state.phases.indexOf(p) === -1) return state;
    return set({ phase: p });
  }

  /* One /api/world fetch for the whole page, shared as a promise so
     the second caller waits on the first instead of asking again. */
  function world() {
    if (!worldReq) {
      worldReq = fetch('/api/world')
        .then(function (r) {
          if (!r.ok) throw new Error('the world did not load');
          return r.json();
        })
        .then(function (data) {
          var phases = (data && data.phases) || [];
          state.world = data;
          state.phases = phases;
          /* Keep a phase already chosen by a click that landed before
             the payload did, as long as the pack knows it. */
          if (!state.phase || phases.indexOf(state.phase) === -1) {
            state.phase = phases.length ? phases[0] : null;
          }
          notify();
          return data;
        });
    }
    return worldReq;
  }

  /* The vault is the game's inventory: the list the Vault tab shows
     and the item the town's HUD draws are the same list. Never
     coalesced with an in-flight request - a refresh right after
     keeping an item must not be answered by an older one. */
  function refreshVault() {
    return fetch(VEFR_SESSION.wrap('/api/vault'))
      .then(function (r) {
        if (!r.ok) throw new Error('the vault did not answer');
        return r.json();
      })
      .then(function (body) {
        var list = Array.isArray(body) ? body : (body && body.items) || [];
        state.vault = list;
        state.carrying = list.length ? list[list.length - 1] : null;
        notify();
        return list;
      });
  }

  return {
    get: get,
    set: set,
    on: on,
    setPhase: setPhase,
    world: world,
    refreshVault: refreshVault
  };
})();
