/* vefr/web/js/rooms/settings.js: Settings (the Boiler Room).
 * Split out of app.js (2026-09-27); the shared studio helpers come from
 * window.VEFR_STUDIO, which app.js builds. Loaded after app.js, before boot.js. */
(function (S) {
  'use strict';

  var screens = S.screens, API = S.API, ART = S.ART, firstWalk = S.firstWalk, h = S.h,
      main = S.main, portrait = S.portrait, residentLine = S.residentLine, spot = S.spot,
      studioAudio = S.studioAudio;

  /* ══════════════════════════════════════════════════════
     SETTINGS — the boiler room (plain is kindness)
     ══════════════════════════════════════════════════════ */

  screens.settings = (function () {
    // VEFR_PREFS is the one canonical voice for how the studio reads
    // and moves: it writes the data-prefs tokens the foundation and
    // theme branch on. The boiler room just points at it.
    var el_screen,
        P = window.VEFR_PREFS,
        current = (P && P.get) ? P.get() : { contrast: 'm', font: 'atkinson', motion: 'off' };
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-settings' });
      main.appendChild(el_screen);
    }
    function enter() {
      el_screen.innerHTML = '<div class="wrap band settings-room" id="settings-content"></div>';
      var container = el_screen.querySelector('#settings-content');

      var boilerRow = h('div', { className: 'spot-row' });
      boilerRow.appendChild(h('p', { className: 'archives-intro',
        textContent: 'Settings for how the studio looks, sounds and moves.' }));
      boilerRow.appendChild(spot('volundr-pipe-with-bolt', 'spot--inline'));
      container.appendChild(boilerRow);
      var rl = residentLine('settings');
      if (rl) container.appendChild(rl);

      // Spark, the little local brain, has a face: Bolt. The card says
      // in words whether Spark is running, and how he is doing.
      var bolt = h('section', { className: 'settings-card spark-card', 'aria-labelledby': 'spark-title' });
      bolt.appendChild(portrait('spark', { name: 'Bolt, the face of Spark' }, 'spark-card__face'));
      var boltImg = bolt.querySelector('.spark-card__face img');
      var boltText = h('div', { className: 'spark-card__text' });
      boltText.appendChild(h('h3', { className: 'settings-card__title', id: 'spark-title', textContent: 'Bolt \u00B7 Spark, the little local brain' }));
      var boltStatus = h('p', { className: 'spark-card__status', role: 'status', textContent: 'checking on Bolt\u2026' });
      if (boltImg) boltImg.src = ART + 'poses/bolt-thinking.webp';
      boltText.appendChild(boltStatus);
      boltText.appendChild(h('p', { className: 'settings-card__note',
        textContent: 'Spark is a small model that runs on this machine and helps every resident. Nothing leaves the house.' }));
      bolt.appendChild(boltText);
      container.appendChild(bolt);
      API.sparkHealth()
        .then(function (sp) {
          if (sp && sp.ok) {
            bolt.classList.add('spark-card--awake');
            if (boltImg) boltImg.src = ART + 'poses/bolt-awake-wave.webp';
            boltStatus.textContent = 'Awake. Spark is running' + (sp.profile ? ' (' + sp.profile + ' profile)' : '') + '.';
          } else {
            boltStatus.textContent = 'Napping. Spark isn’t set up on this machine yet.';
            if (boltImg) boltImg.src = ART + 'poses/bolt-boiler-nap.webp';
          }
        })
        .catch(function () {
          boltStatus.textContent = 'Unplugged. Couldn’t reach Spark.';
          if (boltImg) boltImg.src = ART + 'poses/bolt-unplugged.webp';
        });

      // Appearance — one voice for all of it: the prefs engine
      current = (P && P.get) ? P.get() : current;

      var themeCard = makeCard('How it feels');
      addOptionRow(themeCard, 'Mood', [
        { label: 'Warm & Easy', value: 'm' },
        { label: 'Bright & Clear', value: 'high' },
        { label: 'Nothing Hides', value: 'ultra' }
      ], 'contrast');
      container.appendChild(themeCard);

      // Reading
      var fontCard = makeCard('How it reads');
      addOptionRow(fontCard, 'Font', [
        { label: 'Atkinson', value: 'atkinson' },
        { label: 'OpenDyslexic', value: 'opendyslexic' },
        { label: 'Serif', value: 'serif' },
        { label: 'System', value: 'system' }
      ], 'font');
      container.appendChild(fontCard);

      // How much of the workings to show (studio-modules.md: the two sliders)
      var workCard = makeCard('How much to show');
      addOptionRow(workCard, 'The workings', [
        { label: 'Keep it simple', value: 'simple' },
        { label: 'Show me how things work', value: 'show' }
      ], 'workings');
      container.appendChild(workCard);

      // Learning as you build: Fróði names the idea you just used (teach.py)
      var teachCard = makeCard('Learning as you build');
      addOptionRow(teachCard, 'Fróði’s notes', [
        { label: 'Teach me as I build', value: 'build' },
        { label: 'Occasional tips', value: 'tips' },
        { label: 'Just plain words', value: 'off' }
      ], 'teach');
      addOptionRow(teachCard, 'Tell me when there’s a word', [
        { label: 'Stay quiet', value: 'off' },
        { label: 'Say it once, politely', value: 'on' }
      ], 'teachAnnounce');
      container.appendChild(teachCard);

      // Motion
      var motionCard = makeCard('How it moves');
      addOptionRow(motionCard, 'Motion', [
        { label: 'Off', value: 'off' },
        { label: 'Subtle', value: 'subtle' },
        { label: 'Full', value: 'full' }
      ], 'motion');
      container.appendChild(motionCard);

      // Sound — off by default; every sound pairs with a visible event
      var soundCard = makeCard('How it sounds');
      var soundOn = !!(current.sound && (current.sound.effects > 0 || current.sound.ambience > 0));
      var soundRow = h('div', { className: 'settings-row' });
      soundRow.appendChild(h('span', { className: 'settings-row__label', textContent: 'Hearth sound' }));
      var soundOpts = h('div', { className: 'settings-row__options' });
      [{ label: 'Off', on: false }, { label: 'On', on: true }].forEach(function (opt) {
        var btn = h('button', {
          className: 'settings-option' + (soundOn === opt.on ? ' settings-option--active' : ''),
          textContent: opt.label
        });
        btn.addEventListener('click', function () {
          if (P && P.set) {
            var s = opt.on ? { effects: 0.7, ambience: 0.5, speech: 0.8 } : { effects: 0, ambience: 0, speech: 0 };
            P.set({ sound: s });
            current = P.get();
          }
          soundOpts.querySelectorAll('.settings-option').forEach(function (b) { b.classList.remove('settings-option--active'); });
          btn.classList.add('settings-option--active');
          if (opt.on && studioAudio) { studioAudio.unlock(); studioAudio.ambient(true); }
          if (!opt.on && studioAudio) studioAudio.ambient(false);
        });
        soundOpts.appendChild(btn);
      });
      soundRow.appendChild(soundOpts);
      soundCard.appendChild(soundRow);
      soundCard.appendChild(h('p', { className: 'settings-card__note',
        textContent: 'Every sound has something to see with it, so nothing is sound-only. Off unless you turn it on.' }));
      container.appendChild(soundCard);

      // Learning — the walk and the sheet stay callable any time
      var learnCard = makeCard('Help');
      var learnA = h('div', { className: 'settings-row' });
      learnA.appendChild(h('span', { className: 'settings-row__label', textContent: 'The first walk' }));
      var learnAOpts = h('div', { className: 'settings-row__options' });
      var walkBtn = h('button', { className: 'btn btn--warm settings-row__btn', type: 'button',
        textContent: 'Take the tour again' });
      walkBtn.addEventListener('click', function () { if (firstWalk) firstWalk.reset(); });
      learnAOpts.appendChild(walkBtn);
      learnA.appendChild(learnAOpts);
      learnCard.appendChild(learnA);
      var learnB = h('div', { className: 'settings-row' });
      learnB.appendChild(h('span', { className: 'settings-row__label', textContent: 'How the studio works' }));
      var learnBOpts = h('div', { className: 'settings-row__options' });
      var sheetBtn = h('button', { className: 'btn btn--warm settings-row__btn', type: 'button',
        textContent: 'Open the guide' });
      sheetBtn.addEventListener('click', function () { if (firstWalk) firstWalk.openSheet(); });
      learnBOpts.appendChild(sheetBtn);
      learnB.appendChild(learnBOpts);
      learnCard.appendChild(learnB);
      container.appendChild(learnCard);

      // Engine
      var engineCard = makeCard('The engine');
      API.health()
        .then(function (data) {
          addInfoRow(engineCard, 'Status', data.ok ? 'Healthy' : 'Unavailable');
          if (data.purpose) addInfoRow(engineCard, 'Purpose', data.purpose);
        })
        .catch(function () { addInfoRow(engineCard, 'Status', 'Disconnected'); });
      API.sparkHealth()
        .then(function (data) {
          addInfoRow(engineCard, 'Spark', data.spark || 'unavailable');
          if (data.profile) addInfoRow(engineCard, 'Profile', data.profile);
        })
        .catch(function () { addInfoRow(engineCard, 'Spark', 'unavailable'); });
      container.appendChild(engineCard);
    }

    function makeCard(title) {
      var card = h('div', { className: 'settings-card' });
      card.appendChild(h('h3', { className: 'settings-card__title', textContent: title }));
      return card;
    }
    function addOptionRow(card, label, options, prefKey) {
      var row = h('div', { className: 'settings-row' });
      row.appendChild(h('span', { className: 'settings-row__label', textContent: label }));
      var opts = h('div', { className: 'settings-row__options' });
      options.forEach(function (opt) {
        var active = current[prefKey] === opt.value;
        var btn = h('button', {
          className: 'settings-option' + (active ? ' settings-option--active' : ''),
          textContent: opt.label
        });
        btn.addEventListener('click', function () {
          if (P && P.set) {
            var patch = {};
            patch[prefKey] = opt.value;
            P.set(patch);
            window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('setting_change', { key: prefKey, value: opt.value });
            current = P.get();
          }
          opts.querySelectorAll('.settings-option').forEach(function (b) { b.classList.remove('settings-option--active'); });
          btn.classList.add('settings-option--active');
        });
        opts.appendChild(btn);
      });
      row.appendChild(opts);
      card.appendChild(row);
    }
    function addInfoRow(card, label, value) {
      var row = h('div', { className: 'settings-row' });
      row.appendChild(h('span', { className: 'settings-row__label', textContent: label }));
      row.appendChild(h('span', { className: 'settings-row__value', textContent: value }));
      card.appendChild(row);
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();
})(window.VEFR_STUDIO);
