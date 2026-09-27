/* vefr/web/js/achievements.js: Ratatoskr's sticker book, the reporting side.
 *
 * window.VEFR_ACHIEVE(event, data) tells the studio something happened (a room
 * opened, a square painted, a book finished). The server keeps the tally
 * (src/vefr/achievements.py) and says which stickers were just earned; each one
 * slaps down in the corner with a small "Sticker earned!" banner, then fades.
 * The full book lives in the Hall. Loaded before app.js, so every room can call it.
 *
 * Kind by design: never blocks anything, never throws, one polite line for screen
 * readers, no bounce when motion is off, the squeak only when sound is on.
 */
(function () {
  'use strict';
  var queue = Promise.resolve();
  var shown = [];
  var region = null;

  function local() {
    var d = new Date();
    var pad = function (n) { return (n < 10 ? '0' : '') + n; };
    return { date: d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()),
             hour: d.getHours(), minute: d.getMinutes(), weekday: (d.getDay() + 6) % 7 };
  }

  function post(event, data) {
    var wrap = (window.VEFR_SESSION && window.VEFR_SESSION.wrap) || function (u) { return u; };
    return fetch(wrap('/api/achievements/event'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event: event, data: data || {}, local: local() })
    }).then(function (r) { return r.ok ? r.json() : { earned: [] }; });
  }

  function ensureRegion() {
    if (region && document.body.contains(region)) return region;
    region = document.createElement('div');
    region.className = 'sticker-pops';
    document.body.appendChild(region);
    return region;
  }

  function announce(text) {
    var live = document.getElementById('sticker-live');
    if (!live) {
      live = document.createElement('p');
      live.id = 'sticker-live';
      live.className = 'sr-only';
      live.setAttribute('role', 'status');
      live.setAttribute('aria-live', 'polite');
      document.body.appendChild(live);
    }
    live.textContent = text;
  }

  function pop(a) {
    var box = document.createElement('div');
    box.className = 'sticker-pop';
    var img = document.createElement('img');
    img.className = 'sticker-pop__art';
    img.src = '/static/art/stickers/' + a.id + '.webp';
    img.alt = '';
    img.width = 72; img.height = 72;
    img.onerror = function () { img.src = '/static/art/icons/ui/star.webp'; img.onerror = null; };
    var text = document.createElement('div');
    text.className = 'sticker-pop__text';
    var kicker = document.createElement('span');
    kicker.className = 'sticker-pop__kicker';
    kicker.textContent = a.kind === 'secret' ? 'Secret sticker found!' : a.kind === 'riddle' ? 'Riddle solved!' : 'Sticker earned!';
    if (a.shine && a.shine !== 'paper') box.classList.add('sticker-pop--' + a.shine);
    var name = document.createElement('strong');
    name.textContent = a.name;
    var how = document.createElement('span');
    how.className = 'sticker-pop__how';
    how.textContent = a.how;
    text.appendChild(kicker); text.appendChild(name); text.appendChild(how);
    box.appendChild(img); box.appendChild(text);
    box.addEventListener('click', function () { location.hash = '#hall'; box.remove(); });
    ensureRegion().appendChild(box);
    announce('Sticker earned: ' + a.name + '.');
    try {
      var S = window.VEFR_STUDIO;
      var sound = window.VEFR_PREFS && window.VEFR_PREFS.get && window.VEFR_PREFS.get().sound;
      if (S && S.studioAudio && sound && sound.effects > 0) S.studioAudio.squeak();
    } catch (e) {}
    var stay = setTimeout(function () { box.classList.add('sticker-pop--leaving'); setTimeout(function () { box.remove(); }, 400); }, 6000);
    box.addEventListener('mouseenter', function () { clearTimeout(stay); });
  }

  window.VEFR_ACHIEVE = function (event, data) {
    queue = queue.then(function () {
      return post(event, data).then(function (res) {
        (res.earned || []).forEach(function (a, i) {
          if (shown.indexOf(a.id) !== -1) return;
          shown.push(a.id);
          setTimeout(function () { pop(a); }, i * 900);
        });
      });
    }).catch(function () {});
    return queue;
  };

  /* A couple of things only the whole page can see. */
  var CODE = ['arrowup', 'arrowup', 'arrowdown', 'arrowdown', 'arrowleft', 'arrowright', 'arrowleft', 'arrowright', 'b', 'a'];
  var typed = [];
  document.addEventListener('keydown', function (e) {
    typed.push(String(e.key || '').toLowerCase());
    typed = typed.slice(-CODE.length);
    if (typed.join(',') === CODE.join(',')) window.VEFR_ACHIEVE('konami');
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest) return;
    if (e.target.closest('.brand__tree')) window.VEFR_ACHIEVE('tree_click');
    if (e.target.closest('.foot-wave')) window.VEFR_ACHIEVE('squirrel_click');
    if (e.target.closest('.paddle')) window.VEFR_ACHIEVE('paddle_click');
  });
})();
