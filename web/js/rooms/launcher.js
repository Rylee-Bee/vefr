/* vefr/web/js/rooms/launcher.js: The Studio (home).
 * Split out of app.js (2026-09-27); the shared studio helpers come from
 * window.VEFR_STUDIO, which app.js builds. Loaded after app.js, before boot.js. */
(function (S) {
  'use strict';

  var screens = S.screens, API = S.API, ART = S.ART, HERO_ART = S.HERO_ART,
      RESIDENTS = S.RESIDENTS, SCREEN_DEPTS = S.SCREEN_DEPTS, SCREEN_TITLES = S.SCREEN_TITLES,
      actionsLine = S.actionsLine, carved = S.carved, chronicleLine = S.chronicleLine,
      door = S.door, emptyState = S.emptyState, ferryNote = S.ferryNote, firstWalk = S.firstWalk,
      foldChronicle = S.foldChronicle, formatTime = S.formatTime, h = S.h,
      inhabitWorld = S.inhabitWorld, loadingState = S.loadingState, main = S.main,
      navigate = S.navigate, portrait = S.portrait, posterSvg = S.posterSvg,
      sectionHead = S.sectionHead, studioAudio = S.studioAudio, truncate = S.truncate;

  /* ══════════════════════════════════════════════════════
     THE DESK — the writing desk where worlds are made
     ══════════════════════════════════════════════════════ */

  screens.launcher = (function () {
    // The foyer — the first room you step into. A launcher like a
    // game's: the project on the table, every other pack in the
    // pantry, what the house remembers, and the quick options at
    // the mantel. Everything is real — packs from /api/builder/worlds,
    // keepsakes from the vault, stars from the journal, threads the
    // house has already heard. Nothing is invented.
    var el_screen;
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-launcher' });
      main.appendChild(el_screen);
    }
    function enter() {
      // The studio's front page: what is on the table, every world on
      // the walls, how the studio works, the latest from the Chronicle,
      // and the residents. Everything is real data; nothing is invented.
      el_screen.innerHTML = '<div class="studio-home" id="foyer-content"></div>';
      var c = el_screen.querySelector('#foyer-content');

      var hearth = h('div', { className: 'foyer-hearth' });
      hearth.appendChild(h('div', { className: 'foyer-holder' }));
      c.appendChild(hearth);

      var games = h('div', { className: 'wrap band' });
      var pantry = h('section', { className: 'foyer-pantry', 'aria-labelledby': 'home-games' });
      pantry.appendChild(sectionHead('Our worlds', 'On the walls', 'home-games', door('floor', 'Walk the floor')));
      var holder = h('div', { className: 'foyer-holder' });
      holder.appendChild(loadingState('Loading your worlds…'));
      pantry.appendChild(holder);
      games.appendChild(pantry);
      c.appendChild(games);

      var creed = h('section', { className: 'creed-band', 'aria-label': 'How the studio works', id: 'home-creed' });
      c.appendChild(creed);

      var two = h('div', { className: 'wrap band home-two' });
      var news = h('section', { 'aria-labelledby': 'home-news' });
      news.appendChild(sectionHead('From the Chronicle', 'Latest from the studio', 'home-news', door('journal', 'All news')));
      var newsList = h('div', { className: 'news-list' });
      newsList.appendChild(loadingState('Urðr is turning the pages\u2026'));
      news.appendChild(newsList);
      var begin = h('section', { 'aria-labelledby': 'home-begin' });
      begin.appendChild(sectionHead('New project', 'Begin a new world', 'home-begin'));
      var beginCard = carved('div', 'begin-card');
      beginCard.appendChild(beginWorldForm(hearth, pantry));
      begin.appendChild(beginCard);
      two.appendChild(news);
      two.appendChild(begin);
      c.appendChild(two);

      var team = h('section', { className: 'wrap band', 'aria-labelledby': 'home-team' });
      team.appendChild(sectionHead('The team', 'Meet the residents', 'home-team', door('floor', 'Every department')));
      team.appendChild(h('img', { className: 'team-photo', src: ART + 'illustrations/team-photo.webp', width: 1600, height: 1000, loading: 'lazy',
        alt: 'All ten residents together on a branch of the World Tree, smiling for a group photo.' }));
      team.appendChild(teamGrid());
      c.appendChild(team);

      var mantel = h('div', { className: 'wrap band band--last' });
      mantel.appendChild(optionsPanel());
      c.appendChild(mantel);

      loadProjects(hearth, pantry);
      API.journal()
        .then(function (data) { renderNews(newsList, (data && data.entries) || []); })
        .catch(function () {
          newsList.innerHTML = '';
          newsList.appendChild(emptyState('Couldn’t load the Chronicle.', 'Try again in a moment.'));
        });
    }

    function renderNews(list, entries) {
      list.innerHTML = '';
      var folded = foldChronicle(entries).reverse().slice(0, 3);
      if (!folded.length) {
        list.appendChild(emptyState('Nothing has happened yet.', 'What happens in play will show up here.'));
        return;
      }
      folded.forEach(function (f, i) {
        var line = f.kind === 'combat_action' ? actionsLine(f) : chronicleLine(f.entry);
        var post = carved('a', 'post go' + (i === 0 ? ' post--lead' : ''), { href: '#journal', 'data-screen': 'journal' });
        post.appendChild(h('span', { className: 'post__date', textContent: formatTime(f.at) + ' \u00B7 ' + line.kind }));
        post.appendChild(h('p', { className: 'post__text', textContent: truncate(line.text || '', 180) }));
        if (line.who) post.appendChild(h('span', { className: 'post__who', textContent: '\u2014 ' + line.who }));
        list.appendChild(post);
      });
    }

    function teamGrid() {
      var grid = h('div', { className: 'team-grid' });
      ['hall', 'workshop', 'journal', 'map', 'characters', 'items', 'runes', 'evidence', 'settings'].forEach(function (id) {
        var r = RESIDENTS[id];
        if (!r) return;
        var card = carved('a', 'member go', { href: '#' + id, 'data-screen': id });
        card.appendChild(portrait(id, r, 'member__portrait'));
        card.appendChild(h('h3', { className: 'member__name', textContent: r.name }));
        card.appendChild(h('span', { className: 'member__role', textContent: (SCREEN_DEPTS[id] || '') + ' \u00B7 ' + (SCREEN_TITLES[id] || '') }));
        card.appendChild(h('p', { className: 'member__craft', textContent: r.craft }));
        grid.appendChild(card);
      });
      return grid;
    }

    function loadProjects(hearth, pantry) {
      Promise.all([API.world(), API.builderWorlds()])
        .then(function (rs) { renderProjects(hearth, pantry, rs[0], (rs[1] && rs[1].worlds) || []); })
        .catch(function () {
          setSection(hearth, emptyState('Couldn’t load this world.', 'Check that the studio server is running.'));
          setSection(pantry, emptyState('Couldn’t load the world’s contents.', 'Try again in a moment.'));
        });
    }

    /* The launcher's front door for a phone with no terminal: name,
       title, one-line premise, and the engine does the rest. This is
       the page's twin of `norns chat` - the same scaffold copy, the
       same world.json fields. The name is the folder id; the server
       owns the path and refuses anything that isn't a bare pack name. */
    function beginWorldForm(hearth, pantry) {
      var form = h('form', { className: 'world-begin', id: 'begin-world-form' });
      form.setAttribute('novalidate', 'novalidate');
      form.appendChild(field('begin-world-name', 'Name',
        'A short folder name: letters, numbers, dashes and underscores',
        'quiet-town', '^[A-Za-z0-9][A-Za-z0-9_-]*$'));
      form.appendChild(field('begin-world-title', 'Title',
        'The name players see', 'The name of your world', null));
      form.appendChild(field('begin-world-premise', 'Premise',
        'One line that sums up the world', 'A town keeps a quiet secret', null));

      var create = h('button', { className: 'btn btn--primary world-begin__submit',
        type: 'submit', textContent: 'Create' });
      form.appendChild(create);

      var status = h('p', { className: 'world-begin__status', id: 'begin-world-status',
        role: 'status', 'aria-live': 'polite' });
      form.appendChild(status);

      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var nameEl = form.querySelector('#begin-world-name');
        var name = nameEl.value.trim();
        var title = form.querySelector('#begin-world-title').value.trim();
        var premise = form.querySelector('#begin-world-premise').value.trim();
        if (!name) {
          status.textContent = 'Give the world a name first.';
          nameEl.focus();
          return;
        }
        create.disabled = true;
        status.textContent = 'Creating “' + name + '”…';
        API.createWorld({ name: name, title: title || null, premise: premise || null })
          .then(function (created) {
            status.textContent = '“' + (created.title || name) + '” is ready.';
            navigate('workshop');
          })
          .catch(function (err) {
            var code = String((err && err.message) || '');
            if (code.indexOf('409') === 0) {
              status.textContent = 'A world with that folder name already exists. Try another.';
            } else if (code.indexOf('400') === 0) {
              status.textContent = 'Use only letters, numbers, dashes and underscores (no spaces or slashes).';
            } else {
              status.textContent = 'Couldn’t create the world. Try again.';
            }
            create.disabled = false;
            nameEl.focus();
          });
      });
      return form;
    }

    function field(id, label, hint, placeholder, pattern) {
      var wrap = h('div', { className: 'world-begin__field' });
      var hintId = id + '-hint';
      wrap.appendChild(h('label', { className: 'world-begin__label', 'for': id, textContent: label }));
      var input = h('input', { className: 'world-begin__input', id: id, name: id, type: 'text',
        placeholder: placeholder, 'aria-describedby': hintId, autocomplete: 'off' });
      if (pattern) input.setAttribute('pattern', pattern);
      wrap.appendChild(input);
      wrap.appendChild(h('span', { className: 'world-begin__hint', id: hintId, textContent: hint }));
      return wrap;
    }

    /* Put an existing pack on the table: the web twin of setting
       VEFR_WORLD, no restart. Keeps the current room steady while
       the house re-reads the world it now serves. */
    function makeActive(name, btn, hearth, pantry) {
      var label = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Opening…';
      API.setActiveWorld({ name: name })
        .then(function () { return API.world(); })
        .then(function (w) {
          inhabitWorld(w);
          ferryNote('Now working on “' + ((w && w.title) || name) + '”.');
          loadProjects(hearth, pantry);
        })
        .catch(function (err) {
          btn.disabled = false;
          btn.textContent = label;
          /* 409 = the server pins a world: say so, don't invite a retry. */
          ferryNote(err && err.status === 409 && err.message
            ? err.message : 'Couldn’t open that world. Try again.');
        });
    }

    function section(c, cls, title) {
      var id = 'foyer-' + cls.replace('foyer-', '');
      var s = h('section', { className: cls, 'aria-labelledby': id });
      s.appendChild(h('h2', { className: 'foyer-h2', id: id, textContent: title }));
      var holder = h('div', { className: 'foyer-holder' });
      holder.appendChild(loadingState('Loading…'));
      s.appendChild(holder);
      c.appendChild(s);
      return s;
    }
    function setSection(s, node) {
      var holder = s.querySelector('.foyer-holder');
      if (!holder) return;
      holder.innerHTML = '';
      holder.appendChild(node);
    }

    function renderProjects(hearth, pantry, w, packs) {
      var currentName = null;
      if (w && w.title) {
        packs.forEach(function (p) {
          if (currentName === null && p.title === w.title) currentName = p.name;
        });
      }
      setSection(hearth, projectTable(w));
      setSection(pantry, pantryGrid(packs, currentName, hearth, pantry));
    }
    function projectTable(w) {
      if (!w || !w.title) return emptyState('No world is open yet.', 'Begin a world, or start the studio with one.');
      var hero = h('section', { className: 'hero', 'aria-labelledby': 'hero-title' });
      hero.innerHTML = HERO_ART;
      var copy = h('div', { className: 'wrap hero__copy' });
      copy.appendChild(h('span', { className: 'hero__kicker', textContent: 'On the table \u00B7 in development' }));
      copy.appendChild(h('h2', { className: 'hero__title', id: 'hero-title', textContent: w.title }));
      if (w.creed) copy.appendChild(h('p', { className: 'hero__creed', textContent: w.creed }));
      var facts = h('div', { className: 'hero__facts' });
      var bits = [];
      if (w.act && w.act.title && w.act.title !== w.title) bits.push(w.act.title);
      if (w.phases && w.phases.length) bits.push(w.phases.join(' \u00B7 '));
      if (w.act && w.act.ruleset) bits.push(w.act.ruleset);
      bits.forEach(function (b) { facts.appendChild(h('span', { className: 'hero__fact', textContent: b })); });
      copy.appendChild(facts);
      var actions = h('div', { className: 'hero__actions' });
      actions.appendChild(door('workshop', 'Open the Desk', 'cta--gold'));
      actions.appendChild(door('floor', 'Walk the floor', 'cta--ghost'));
      copy.appendChild(actions);
      hero.appendChild(copy);
      var band = document.getElementById('home-creed');
      if (band) {
        band.innerHTML = '';
        var inner = h('div', { className: 'wrap creed-band__row' });
        [[w.creed || 'Walk gently.', 'carved above the door'],
         ['Every sitting ends with something alive.', 'how the studio works'],
         ['You write the stories. The studio builds the halls.', 'who does what']].forEach(function (l) {
          var d = h('div', { className: 'creed-band__line' });
          d.appendChild(h('b', { textContent: l[0] }));
          d.appendChild(h('small', { textContent: l[1] }));
          inner.appendChild(d);
        });
        band.appendChild(inner);
      }
      return hero;
    }
    function pantryGrid(packs, currentName, hearth, pantry) {
      if (!packs.length) return emptyState('No worlds yet.', 'Begin one below.');
      var wrap = h('div', { className: 'poster-grid' });
      packs.forEach(function (p, i) {
        var current = p.name === currentName;
        var card = carved('article', 'poster');
        var key = h('div', { className: 'poster__key' });
        key.innerHTML = posterSvg(p, i);
        key.appendChild(h('h3', { className: 'poster__title', textContent: p.title || p.name }));
        if (current) {
          var seal = h('span', { className: 'wax-seal', 'aria-hidden': 'true' });
          seal.innerHTML = '<img src="' + ART + 'wax-seal.webp" alt="" width="64" height="64">';
          key.appendChild(seal);
        }
        card.appendChild(key);
        var body = h('div', { className: 'poster__body' });
        body.appendChild(h('span', { className: 'status' + (current ? ' status--now' : ''), textContent: current ? 'On the table' : 'On the wall' }));
        var bits = [];
        if (p.phases && p.phases.length) bits.push(p.phases.join(' \u00B7 '));
        if (p.speakers) bits.push(p.speakers.length + ' speaker' + (p.speakers.length !== 1 ? 's' : ''));
        if (bits.length) body.appendChild(h('p', { className: 'poster__meta', textContent: bits.join(' \u00B7 ') }));
        if (current) {
          body.appendChild(door('workshop', 'Open the Desk', 'cta--line'));
        } else {
          var put = h('button', { className: 'cta cta--line', type: 'button', textContent: 'Work on this world' });
          put.addEventListener('click', function () { makeActive(p.name, put, hearth, pantry); });
          body.appendChild(put);
        }
        card.appendChild(body);
        wrap.appendChild(card);
      });
      return wrap;
    }

    function optionsPanel() {
      // Quick options at the mantel — the same contracts the boiler
      // room owns: sound and motion via VEFR_PREFS, the walk and the
      // sheet via the first walk, the rest by walking through doors.
      var P = window.VEFR_PREFS;
      var current = (P && P.get) ? P.get() : {};
      var panel = h('section', { className: 'foyer-options', 'aria-labelledby': 'foyer-options-title' });
      panel.appendChild(h('h2', { className: 'foyer-h2', id: 'foyer-options-title', textContent: 'At the mantel' }));
      var optCard = h('div', { className: 'settings-card' });

      var soundRow = h('div', { className: 'settings-row' });
      soundRow.appendChild(h('span', { className: 'settings-row__label', textContent: 'Hearth sound' }));
      var soundOpts = h('div', { className: 'settings-row__options' });
      var snd = current.sound || {};
      var soundOn = (snd.effects || 0) > 0 || (snd.ambience || 0) > 0;
      [{ label: 'Off', on: false }, { label: 'On', on: true }].forEach(function (o) {
        var b = h('button', { className: 'settings-option' + (soundOn === o.on ? ' settings-option--active' : ''), textContent: o.label });
        b.addEventListener('click', function () {
          if (P && P.set) {
            P.set({ sound: o.on ? { effects: 0.7, ambience: 0.5, speech: 0.8 } : { effects: 0, ambience: 0, speech: 0 } });
          }
          soundOpts.querySelectorAll('.settings-option').forEach(function (x) { x.classList.remove('settings-option--active'); });
          b.classList.add('settings-option--active');
          if (o.on && studioAudio) { studioAudio.unlock(); studioAudio.ambient(true); }
          if (!o.on && studioAudio) studioAudio.ambient(false);
        });
        soundOpts.appendChild(b);
      });
      soundRow.appendChild(soundOpts);
      optCard.appendChild(soundRow);

      var motRow = h('div', { className: 'settings-row' });
      motRow.appendChild(h('span', { className: 'settings-row__label', textContent: 'Motion' }));
      var motOpts = h('div', { className: 'settings-row__options' });
      [{ label: 'Off', value: 'off' }, { label: 'Subtle', value: 'subtle' }, { label: 'Full', value: 'full' }].forEach(function (o) {
        var b = h('button', { className: 'settings-option' + ((current.motion || 'off') === o.value ? ' settings-option--active' : ''), textContent: o.label });
        b.addEventListener('click', function () {
          if (P && P.set) P.set({ motion: o.value });
          motOpts.querySelectorAll('.settings-option').forEach(function (x) { x.classList.remove('settings-option--active'); });
          b.classList.add('settings-option--active');
        });
        motOpts.appendChild(b);
      });
      motRow.appendChild(motOpts);
      optCard.appendChild(motRow);

      var doorsRow = h('div', { className: 'settings-row' });
      doorsRow.appendChild(h('span', { className: 'settings-row__label', textContent: 'Doorways' }));
      var doorOpts = h('div', { className: 'settings-row__options' });
      var walkBtn = h('button', { className: 'btn btn--warm settings-row__btn', type: 'button', textContent: 'Take the tour again' });
      walkBtn.addEventListener('click', function () { if (firstWalk) firstWalk.reset(); });
      var sheetBtn = h('button', { className: 'btn btn--warm settings-row__btn', type: 'button', textContent: 'How the studio works' });
      sheetBtn.addEventListener('click', function () { if (firstWalk) firstWalk.openSheet(); });
      var boilerBtn = h('button', { className: 'btn btn--ghost settings-row__btn', type: 'button', textContent: 'the boiler room \u2192' });
      boilerBtn.addEventListener('click', function () { navigate('settings'); });
      doorOpts.appendChild(walkBtn);
      doorOpts.appendChild(sheetBtn);
      doorOpts.appendChild(boilerBtn);
      doorsRow.appendChild(doorOpts);
      optCard.appendChild(doorsRow);

      panel.appendChild(optCard);
      return panel;
    }

    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();
})(window.VEFR_STUDIO);
