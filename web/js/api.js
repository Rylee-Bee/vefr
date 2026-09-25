/* api.js — the engine underneath.
 *
 * Every function returns a promise.
 * Every function fails gracefully.
 * The UI never sees an unhandled rejection.
 */

(function () {
  'use strict';

  var BASE = '';

  function get(path) {
    return fetch(BASE + path)
      .then(function (r) {
        if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
        return r.json();
      });
  }

  function post(path, body) {
    return fetch(BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    }).then(function (r) {
      if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
      return r.json();
    });
  }

  window.VEFR_API = {
    // World
    world:        function ()     { return get('/api/world'); },
    health:       function ()     { return get('/api/health'); },
    builderWorlds:function ()     { return get('/api/builder/worlds'); },
    aspects:      function ()     { return get('/api/builder/aspects'); },
    resolved:     function ()     { return get('/api/builder/resolved'); },

    // Story
    rumor:        function ()     { return post('/api/rumor'); },
    forge:        function (item) { return post('/api/forge', item); },
    stefna:       function (dir)  { return post('/api/stefna', dir); },
    npc:          function (q)    { return post('/api/npc', q); },
    combat:       function (a)    { return post('/api/combat/action', a); },

    // Journal
    journal:      function ()     { return get('/api/journal'); },
    journalStar:  function (i)    { return post('/api/journal/star/' + i); },
    journalRemove:function (i)    { return post('/api/journal/remove/' + i); },
    journalUndo:  function ()     { return post('/api/journal/undo'); },
    journalClear: function ()     { return post('/api/journal/clear'); },
    journalRewind:function ()     { return post('/api/journal/rewind'); },
    journalFork:  function ()     { return post('/api/journal/fork'); },

    // Vault
    vault:        function ()     { return get('/api/vault'); },
    vaultKeep:    function (item) { return post('/api/vault', item); },
    vaultStar:    function (i)    { return post('/api/vault/star/' + i); },
    vaultRemove:  function (i)    { return post('/api/vault/remove/' + i); },
    vaultUndo:    function ()     { return post('/api/vault/undo'); },

    // Wiki / Characters
    wiki:         function ()     { return get('/api/wiki'); },

    // Runes
    runes:        function ()     { return get('/api/runes'); },
    castRune:     function ()     { return get('/api/runes/cast'); },

    // AI / Evidence
    starred:      function ()     { return get('/api/starred'); },
    trace:        function ()     { return get('/api/trace'); },
    weave:        function ()     { return get('/api/weave'); },
    weaveBuild:   function ()     { return post('/api/builder/weave'); },
    sparkHealth:  function ()     { return get('/api/spark/health'); },
    sparkTask:    function (q)    { return post('/api/spark/task', q); },
    sparkInspect: function ()     { return get('/api/spark/inspect'); },
    sparkEscalate:function (q)    { return post('/api/spark/escalate', q); },
    lore:         function (q)    { return post('/api/builder/lore', q); },
    loreList:     function ()     { return post('/api/builder/lore/list'); },
    chat:         function (q)    { return post('/api/builder/chat', q); },
    enhanceItem:  function (q)    { return post('/api/builder/enhance/item', q); },
    enhanceMap:   function (q)    { return post('/api/builder/enhance/map', q); },
    mapPropose:   function (q)    { return post('/api/builder/map/propose', q); },
    mapCheck:     function (q)    { return post('/api/builder/map/check', q); },
    faceRoll:     function (q)    { return post('/api/builder/face/roll', q); },
    validate:     function ()     { return post('/api/builder/validate'); },
    verify:       function ()     { return post('/api/builder/verify'); },
    handoff:      function ()     { return post('/api/handoff'); }
  };
})();
