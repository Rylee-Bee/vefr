/* vefr/web/js/rooms/characters.js: The Folks.
 * Split out of app.js (2026-09-27); the shared studio helpers come from
 * window.VEFR_STUDIO, which app.js builds. Loaded after app.js, before boot.js. */
(function (S) {
  'use strict';

  var screens = S.screens, API = S.API, emptyState = S.emptyState, ferryNote = S.ferryNote,
      firstWalk = S.firstWalk, h = S.h, loadingState = S.loadingState, main = S.main,
      openFolio = S.openFolio, residentLine = S.residentLine, spot = S.spot,
      studioAudio = S.studioAudio, truncate = S.truncate;

  /* ══════════════════════════════════════════════════════
     THE FOLKS — people, not records
     ══════════════════════════════════════════════════════ */

  screens.characters = (function () {
    var el_screen;
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-characters' });
      main.appendChild(el_screen);
    }
    function enter() {
      el_screen.innerHTML = '<div class="wrap band folks-room" id="folks-content"></div>';
      var container = el_screen.querySelector('#folks-content');
      container.appendChild(loadingState('Looking for familiar faces\u2026'));

      Promise.all([
        API.wiki().catch(function () { return { characters: [] }; }),
        API.world().catch(function () { return { speakers: [], phases: [] }; }),
        API.vault().catch(function () { return { items: [] }; })
      ]).then(function (results) {
        container.innerHTML = '';
        var worldChars = (results[0] && results[0].characters) || [];
        var packSpeakers = (results[1] && results[1].speakers) || [];
        var phases = (results[1] && results[1].phases) || [];
        var keptFaces = ((results[2] && results[2].items) || []).filter(function (i) {
          return i.kind === 'face';
        });

        var rl = residentLine('characters');
        if (rl) container.appendChild(rl);

        /* The bench — a new face can join by hand */
        container.appendChild(inviteBench());

        /* The pack's voices, as living cards: where they stand,
           what they say, what they've already said */
        var byName = {};
        packSpeakers.forEach(function (s) { byName[s.name] = s; });
        worldChars.forEach(function (c) {
          var k = c.name || c.key;
          if (!k) return;
          if (!byName[k]) byName[k] = { name: k, key: c.key || k };
          byName[k].lines = c.lines;
          if (!byName[k].key) byName[k].key = c.key || k;
        });
        var voices = Object.keys(byName).map(function (k) { return byName[k]; });

        if (voices.length) {
          container.appendChild(h('h3', { className: 'folks-room__sub', textContent: 'The world’s characters' }));
          var grid = h('div', { className: 'folks-grid' });
          voices.forEach(function (v) {
            grid.appendChild(voiceCard(v, phases));
          });
          container.appendChild(grid);
        } else {
          container.appendChild(h('p', { className: 'folks-room__quiet',
            textContent: 'This world has no characters yet. Invite the first one above.' }));
        }

        /* Faces the storyteller kept — the household grew by hand */
        if (keptFaces.length) {
          container.appendChild(h('h3', { className: 'folks-room__sub', textContent: 'Characters you’ve invited' }));
          var shelf = h('div', { className: 'folks-shelf' });
          keptFaces.forEach(function (f) { shelf.appendChild(faceCard(f)); });
          container.appendChild(shelf);
        }
      })
      .catch(function () {
        container.innerHTML = '';
        container.appendChild(emptyState(
          'Couldn’t load the characters.',
          'Try again in a moment.'
        ));
      });
    }

    function voiceCard(v, phases) {
      var card = h('div', { className: 'folk-card', role: 'button', tabindex: '0',
        'aria-label': 'Ask about ' + v.name });
      var initial = v.name.charAt(0).toUpperCase();
      card.appendChild(h('div', { className: 'folk-card__portrait', textContent: initial }));
      var who = h('div', { className: 'folk-card__who' });
      who.appendChild(h('div', { className: 'folk-card__name', textContent: v.name }));
      var bits = [];
      if (v.at) bits.push('stands at ' + v.at[0] + ', ' + v.at[1]);
      if (v.near) bits.push('near ' + v.near);
      if (v.lines !== undefined) bits.push(v.lines + ' line' + (v.lines !== 1 ? 's' : ''));
      who.appendChild(h('div', { className: 'folk-card__bits', textContent: bits.join(' \u00B7 ') }));
      if (v.seeds && typeof v.seeds === 'object') {
        var keys = Object.keys(v.seeds);
        var seed = keys.length ? v.seeds[phases[0]] || v.seeds[keys[0]] : null;
        if (seed) who.appendChild(h('div', { className: 'folk-card__seed', textContent: '\u201C' + seed + '\u201D' }));
      }
      card.appendChild(who);
      card.addEventListener('click', function () {
        firstWalk.attempt('folks');
        openFolio('characters', card);
        S.folioInput.value = 'Tell me about ' + v.name + '. Who are they, and what do they want?';
        S.folioInput.focus();
      });
      card.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); card.click(); }
      });
      return card;
    }

    function faceCard(f) {
      var card = h('div', { className: 'folk-card folk-card--invited' });
      var initial = (f.name || '?').charAt(0).toUpperCase();
      card.appendChild(h('div', { className: 'folk-card__portrait', textContent: initial }));
      var who = h('div', { className: 'folk-card__who' });
      who.appendChild(h('div', { className: 'folk-card__name', textContent: f.name || 'New character' }));
      if (f.lore) who.appendChild(h('div', { className: 'folk-card__bits', textContent: truncate(f.lore, 140) }));
      var btn = h('button', { className: 'folk-card__ask', type: 'button', textContent: 'Ask about them' });
      btn.addEventListener('click', function () {
        firstWalk.attempt('folks');
        openFolio('characters', btn);
        S.folioInput.value = 'Meet ' + (f.name || 'the new character') + ': ' + truncate(f.lore || '', 180);
        S.folioInput.focus();
      });
      who.appendChild(btn);
      card.appendChild(who);
      return card;
    }

    function inviteBench() {
      var bench = h('section', { className: 'folk-invite' });
      bench.appendChild(spot('keeper-of-faces-show-sketch', 'spot--right'));
      bench.appendChild(h('h3', { className: 'map-draw__title', textContent: 'Invite a new character' }));
      bench.appendChild(h('p', { className: 'map-draw__hint',
        textContent: 'Ask the Keeper of Faces to suggest someone who belongs here. They’re placed somewhere reachable on the map, and they only join the world when you keep them.' }));
      var row = h('div', { className: 'forge__row' });
      var rollBtn = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Suggest a character' });
      var result = h('div', { className: 'folk-invite__result', role: 'status', 'aria-live': 'polite' });
      rollBtn.addEventListener('click', function () {
        rollBtn.disabled = true;
        rollBtn.textContent = 'The Keeper of Faces is thinking…';
        result.innerHTML = '';
        API.faceRoll({}).then(function (data) {
          rollBtn.disabled = false;
          rollBtn.textContent = 'Suggest a character';
          if (!data || !data.ok || !data.face) {
            result.appendChild(h('p', { className: 'folk-invite__cold',
              textContent: (data && data.reason) || 'That suggestion came back empty. Try again, or write the character yourself.' }));
            return;
          }
          result.appendChild(faceDraft(data.face));
        }).catch(function () {
          rollBtn.disabled = false;
          rollBtn.textContent = 'Suggest a character';
          result.appendChild(h('p', { className: 'folk-invite__cold',
            textContent: 'Couldn’t get a suggestion. Try again.' }));
        });
      });
      row.appendChild(rollBtn);
      bench.appendChild(row);
      bench.appendChild(result);
      return bench;
    }

    function faceDraft(f) {
      var panel = h('div', { className: 'face-draft', role: 'group', 'aria-label': 'Draft character' });
      var nameF = h('input', { className: 'draft__field', type: 'text', id: 'face-name', value: f.name || '', 'aria-label': 'Name' });
      var roleF = h('input', { className: 'draft__field', type: 'text', id: 'face-role', value: f.role || '', 'aria-label': 'What they do' });
      var seedF = h('input', { className: 'draft__field', type: 'text', id: 'face-seed', value: f.seed || '', 'aria-label': 'What they first say' });
      var err = h('p', { className: 'draft__error', role: 'status', hidden: true });
      var at = f.at ? ('at ' + f.at[0] + ', ' + f.at[1]) : 'somewhere reachable';
      var row = h('div', { className: 'forge__row' });
      var keepBtn = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Keep this character' });
      row.appendChild(keepBtn);

      function label(forId, text) {
        var l = h('label', { className: 'face-draft__label', textContent: text });
        l.setAttribute('for', forId);
        return l;
      }

      keepBtn.addEventListener('click', function () {
        var name = nameF.value.trim();
        var role = roleF.value.trim();
        var seed = seedF.value.trim();
        if (!name || !role || !seed) {
          err.textContent = 'A character needs a name, a role and a first line.';
          err.hidden = false;
          return;
        }
        keepBtn.disabled = true;
        API.vaultKeep({
          name: name,
          kind: 'face',
          bond: 'invited',
          lore: 'Role: ' + role + '. First words: \u201C' + seed + '”. They stand ' + at + '.'
        }).then(function () {
          studioAudio.clank();
          ferryNote('Ratatoskr is carrying \u201c' + truncate(name, 32) + '\u201D to the people\u2026');
          enter();
        }).catch(function () {
          err.textContent = 'Couldn’t save the character. Try again.';
          err.hidden = false;
          keepBtn.disabled = false;
        });
      });

      panel.appendChild(label('face-name', 'name'));
      panel.appendChild(nameF);
      panel.appendChild(label('face-role', 'What they do'));
      panel.appendChild(roleF);
      panel.appendChild(label('face-seed', 'What they first say'));
      panel.appendChild(seedF);
      panel.appendChild(h('p', { className: 'face-draft__at', textContent: 'They stand ' + at + '.' }));
      panel.appendChild(row);
      panel.appendChild(err);
      return panel;
    }

    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();
})(window.VEFR_STUDIO);
