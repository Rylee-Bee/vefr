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
    var el_screen, placeNote = null;
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

        /* A just-placed face says so once, plainly, after the refresh */
        if (placeNote) {
          container.appendChild(h('p', { className: 'folk-invite__cold', role: 'status',
            'aria-live': 'polite', textContent: placeNote }));
          placeNote = null;
        }

        /* The bench — a new face can join by hand */
        container.appendChild(inviteBench(phases));

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
        window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('folk_open');
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

    function inviteBench(phases) {
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
          result.appendChild(faceDraft(data.face, phases));
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

    /* A path-safe id from a display name: lowercase, digits and dashes,
       starting with a letter, capped at the route's 32. */
    function faceSlug(name) {
      var s = String(name || '').toLowerCase().replace(/[^a-z0-9]+/g, '-');
      s = s.replace(/^-+/, '').replace(/-+$/, '');
      if (!s) s = 'face';
      if (!/^[a-z]/.test(s)) s = 'face-' + s;
      return s.slice(0, 32).replace(/-+$/, '');
    }

    function firstSeed(seeds, phase) {
      if (!seeds || typeof seeds !== 'object') return '';
      if (phase && seeds[phase]) return seeds[phase];
      var keys = Object.keys(seeds);
      return keys.length ? seeds[keys[0]] : '';
    }

    function faceDraft(f, phases) {
      var panel = h('div', { className: 'face-draft', role: 'group', 'aria-label': 'Draft character' });
      var nameF = h('input', { className: 'draft__field', type: 'text', id: 'face-name', value: f.name || '', 'aria-label': 'Name' });
      var roleF = h('input', { className: 'draft__field', type: 'text', id: 'face-role', value: f.role || '', 'aria-label': 'What they do' });
      var seedF = h('input', { className: 'draft__field', type: 'text', id: 'face-seed', value: f.seed || '', 'aria-label': 'What they first say' });
      var err = h('p', { className: 'draft__error', role: 'status', 'aria-live': 'polite', hidden: true });
      var atNote = f.at ? ('at ' + f.at[0] + ', ' + f.at[1]) : 'somewhere reachable';
      var row = h('div', { className: 'forge__row' });
      var keepBtn = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Keep this character' });
      var vaultBtn = h('button', { className: 'btn btn--ghost', type: 'button', textContent: 'Keep in the vault' });
      var previewSlot = h('div', { className: 'folk-invite__result' });
      row.appendChild(keepBtn);
      row.appendChild(vaultBtn);

      function label(forId, text) {
        var l = h('label', { className: 'face-draft__label', textContent: text });
        l.setAttribute('for', forId);
        return l;
      }

      function values() {
        return { name: nameF.value.trim(), role: roleF.value.trim(), seed: seedF.value.trim() };
      }

      function buildRequest(v, preview, force) {
        var seeds = {};
        seeds[(phases && phases.length) ? phases[0] : 'dusk'] = v.seed;
        var req = {
          name: null,
          id: faceSlug(v.name),
          display_name: v.name,
          role: v.role,
          seeds: seeds,
          voice: 'You are ' + v.name + ', ' + v.role + '. You first say: \u201C' + v.seed + '\u201D',
          region: 'town',
          preview: preview === true,
          force: force === true
        };
        if (f.at) req.at = f.at;
        return req;
      }

      function showError(text) {
        err.textContent = text;
        err.hidden = false;
      }

      function showPreview(v, body, force) {
        previewSlot.innerHTML = '';
        err.hidden = true;
        var sp = (body && body.speaker) || {};
        var name = sp.name || v.name;
        var at = (body && body.at) || sp.at || [0, 0];
        var near = sp.near;
        var seed = firstSeed(sp.seeds, phases && phases[0]);
        var card = h('div', { className: 'folk-card folk-card--invited', role: 'group',
          'aria-label': 'Preview: ' + name });
        card.appendChild(h('div', { className: 'folk-card__portrait', textContent: name.charAt(0).toUpperCase() }));
        var who = h('div', { className: 'folk-card__who' });
        who.appendChild(h('div', { className: 'folk-card__name', textContent: name }));
        if (v.role) who.appendChild(h('div', { className: 'folk-card__bits', textContent: v.role }));
        who.appendChild(h('div', { className: 'folk-card__bits', textContent: 'Stands at '
          + at[0] + ', ' + at[1] + (near && near !== 'nearby' ? ', near ' + near : '') + '.' }));
        if (seed) who.appendChild(h('div', { className: 'folk-card__seed', textContent: '\u201C' + seed + '\u201D' }));
        var actions = h('div', { className: 'forge__row' });
        var put = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Put in the game' });
        var cancel = h('button', { className: 'btn btn--ghost', type: 'button', textContent: 'Cancel' });
        put.addEventListener('click', function () { putInGame(v, force, put); });
        cancel.addEventListener('click', function () { previewSlot.innerHTML = ''; err.hidden = true; });
        actions.appendChild(put);
        actions.appendChild(cancel);
        who.appendChild(actions);
        card.appendChild(who);
        previewSlot.appendChild(card);
      }

      function whereWords(body) {
        var sp = (body && body.speaker) || {};
        var at = (body && body.at) || sp.at;
        if (sp.near && sp.near !== 'nearby') return 'near ' + sp.near;
        if (at) return 'at ' + at[0] + ', ' + at[1];
        return 'somewhere in the world';
      }

      function putInGame(v, force, put) {
        put.disabled = true;
        err.hidden = true;
        API.placeCharacter(buildRequest(v, false, force)).then(function (data) {
          if (!data || !data.written) {
            put.disabled = false;
            showError('That placement came back empty. Try again.');
            return;
          }
          studioAudio.clank();
          /* A real write, not the preview: tell the sticker book and tick
             the first walk. previewPlacement never reaches here. */
          window.VEFR_ACHIEVE && window.VEFR_ACHIEVE('character_placed');
          firstWalk.attempt('character_placed');
          placeNote = v.name + ' is in the game, ' + whereWords(data.preview) + '.';
          ferryNote('Ratatoskr is walking \u201C' + truncate(v.name, 32) + '\u201D into the world\u2026');
          enter();
        }).catch(function (e) {
          put.disabled = false;
          if (e && e.status === 409) { showReplace(v); return; }
          showError((e && e.message) || 'Couldn\u2019t put them in the game. Try again.');
        });
      }

      function showReplace(v) {
        previewSlot.innerHTML = '';
        err.hidden = true;
        previewSlot.appendChild(h('p', { className: 'folk-invite__cold', role: 'status',
          'aria-live': 'polite', textContent: v.name + ' is already in the game. Replace them?' }));
        var replaceRow = h('div', { className: 'forge__row' });
        var replace = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Replace' });
        var cancel = h('button', { className: 'btn btn--ghost', type: 'button', textContent: 'Cancel' });
        replace.addEventListener('click', function () { previewPlacement(v, true); });
        cancel.addEventListener('click', function () { previewSlot.innerHTML = ''; err.hidden = true; });
        replaceRow.appendChild(replace);
        replaceRow.appendChild(cancel);
        previewSlot.appendChild(replaceRow);
      }

      function previewPlacement(v, force) {
        previewSlot.innerHTML = '';
        err.hidden = true;
        keepBtn.disabled = true;
        API.placeCharacter(buildRequest(v, true, force)).then(function (data) {
          keepBtn.disabled = false;
          if (!data || !data.preview) {
            showError('That preview came back empty. Try again.');
            return;
          }
          showPreview(v, data.preview, force);
        }).catch(function (e) {
          keepBtn.disabled = false;
          if (e && e.status === 409) { showReplace(v); return; }
          showError((e && e.message) || 'Couldn\u2019t preview the character. Try again.');
        });
      }

      // Keep is a look before the leap: the route writes nothing,
      // the card shows who they'd be and where they'd stand.
      keepBtn.addEventListener('click', function () {
        var v = values();
        if (!v.name || !v.role || !v.seed) {
          showError('A character needs a name, a role and a first line.');
          return;
        }
        previewPlacement(v, false);
      });

      // The vault shelf still works: keep a face as "I like this
      // person" without putting them in the world.
      vaultBtn.addEventListener('click', function () {
        var v = values();
        if (!v.name || !v.role || !v.seed) {
          showError('A character needs a name, a role and a first line.');
          return;
        }
        vaultBtn.disabled = true;
        API.vaultKeep({
          name: v.name,
          kind: 'face',
          bond: 'invited',
          lore: 'Role: ' + v.role + '. First words: \u201C' + v.seed + '\u201D. They stand ' + atNote + '.'
        }).then(function () {
          studioAudio.clank();
          ferryNote('Ratatoskr is carrying \u201C' + truncate(v.name, 32) + '\u201D to the people\u2026');
          enter();
        }).catch(function () {
          showError('Couldn\u2019t save the character. Try again.');
          vaultBtn.disabled = false;
        });
      });

      panel.appendChild(label('face-name', 'name'));
      panel.appendChild(nameF);
      panel.appendChild(label('face-role', 'What they do'));
      panel.appendChild(roleF);
      panel.appendChild(label('face-seed', 'What they first say'));
      panel.appendChild(seedF);
      panel.appendChild(h('p', { className: 'face-draft__at', textContent: 'They stand ' + atNote + '.' }));
      panel.appendChild(row);
      panel.appendChild(previewSlot);
      panel.appendChild(err);
      return panel;
    }

    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();
})(window.VEFR_STUDIO);
