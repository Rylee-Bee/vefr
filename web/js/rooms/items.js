/* vefr/web/js/rooms/items.js: The Vault.
 * Split out of app.js (2026-09-27); the shared studio helpers come from
 * window.VEFR_STUDIO, which app.js builds. Loaded after app.js, before boot.js. */
(function (S) {
  'use strict';

  var screens = S.screens, API = S.API, emptyState = S.emptyState, ferryNote = S.ferryNote,
      h = S.h, loadingState = S.loadingState, main = S.main, residentLine = S.residentLine,
      spot = S.spot, studioAudio = S.studioAudio, truncate = S.truncate;

  /* ══════════════════════════════════════════════════════
     THE VAULT — kept objects on a tray
     ══════════════════════════════════════════════════════ */

  screens.items = (function () {
    var el_screen;
    function init() {
      el_screen = h('div', { className: 'screen', id: 'screen-items' });
      main.appendChild(el_screen);
    }
    function enter() {
      el_screen.innerHTML = '<div class="wrap band vault-room" id="vault-content"></div>';
      var container = el_screen.querySelector('#vault-content');
      container.appendChild(loadingState('Checking the vault\u2026'));

      /* The anvil — one shared place to shape a keepsake */
      var draft = draftArea(refresh);

      function askForge() {
        API.forge({}).catch(function () { return null; }).then(function (card) {
          if (!card || !card.name) {
            draft.show({}, true, 'No model is running, so there’s no draft. Fill in the card yourself and keep it.');
            return;
          }
          ferryNote('Drafting an item…');
          draft.show(card, true);
        });
      }
      draft.setReroll(askForge);

      API.vault()
        .then(function (data) {
          container.innerHTML = '';
          var items = (data && data.items) || [];
          var rl = residentLine('items');
          if (rl) container.appendChild(rl);

          /* The forge — the fire has a draft for you; shape it, keep it */
          var forgeWrap = h('div', { className: 'forge' });
          forgeWrap.appendChild(spot('hoard-keeper-inspect-gem', 'spot--right'));
          forgeWrap.appendChild(h('div', { className: 'forge__title', textContent: 'The forge' }));
          forgeWrap.appendChild(h('p', { className: 'forge__hint',
            textContent: 'Ask for an item this world might offer, edit it, and keep it. The Vault keeps everything you save.' }));
          var askRow = h('div', { className: 'forge__row' });
          var askBtn = h('button', { className: 'btn btn--warm', type: 'button', textContent: 'Draft an item' });
          askBtn.addEventListener('click', function () {
            askBtn.disabled = true;
            askBtn.textContent = 'Drafting…';
            askForge().finally(function () {
              askBtn.disabled = false;
              askBtn.textContent = 'Draft an item';
            });
          });
          askRow.appendChild(askBtn);
          forgeWrap.appendChild(askRow);
          container.appendChild(forgeWrap);
          container.appendChild(draft.panel);

          if (!items.length) {
            container.appendChild(emptyState(
              'The Vault is empty.',
              'Draft an item above, edit it, and keep it.',
              true
            ));
            return;
          }
          var tray = h('div', { className: 'vault-tray' });
          items.forEach(function (item, i) { tray.appendChild(vaultObject(item, i, draft)); });
          container.appendChild(tray);
        })
        .catch(function () {
          container.innerHTML = '';
          container.appendChild(emptyState(
            'Couldn’t load the Vault.',
            'Try again in a moment.'
          ));
        });
    }

    function refresh() { enter(); }

    /* The anvil itself — editable fields, one obeyable action */
    function draftArea(refresh) {
      var panel = h('div', { className: 'draft', hidden: true });
      panel.appendChild(h('div', { className: 'draft__title', textContent: 'The draft' }));

      function field(cls, label, type) {
        return h('input', { className: cls, type: type || 'text', placeholder: label, 'aria-label': label });
      }
      var nameF = field('draft__name', 'Name', 'text');
      var kindF = field('draft__kind', 'Kind', 'text');
      var bondF = field('draft__bond', 'Bond', 'text');
      var loreF = h('textarea', { className: 'draft__lore', rows: '3',
        placeholder: 'Why it matters', 'aria-label': 'Lore' });
      var enF = field('draft__enchant', 'Enchant (optional)', 'text');
      var cuF = field('draft__curse', 'Curse (optional)', 'text');

      var err = h('p', { className: 'draft__err', role: 'status', hidden: true });
      var row = h('div', { className: 'draft__row' });
      var keepBtn = h('button', { className: 'btn btn--bell', type: 'button', textContent: 'Keep it' });
      var againBtn = h('button', { className: 'btn btn--ghost', type: 'button',
        textContent: 'Try another draft', hidden: true });
      row.appendChild(keepBtn);
      row.appendChild(againBtn);

      function show(card, rerollable, note) {
        var c = card || {};
        nameF.value = c.name || '';
        kindF.value = c.kind || 'relic';
        bondF.value = c.bond || 'assigned';
        loreF.value = c.lore || '';
        enF.value = c.enchant || '';
        cuF.value = c.curse || '';
        againBtn.hidden = !rerollable;
        if (note) { err.textContent = note; err.hidden = false; }
        else { err.hidden = true; }
        panel.hidden = false;
        panel.scrollIntoView({ block: 'nearest' });
        nameF.focus();
      }

      function keep() {
        var name = nameF.value.trim();
        var lore = loreF.value.trim();
        if (!name || !lore) {
          err.textContent = 'An item needs a name and a reason it matters.';
          err.hidden = false;
          return;
        }
        keepBtn.disabled = true;
        var card = {
          name: name,
          kind: kindF.value.trim() || 'relic',
          bond: bondF.value.trim() || 'assigned',
          lore: lore
        };
        if (enF.value.trim()) card.enchant = enF.value.trim();
        if (cuF.value.trim()) card.curse = cuF.value.trim();
        API.vaultKeep(card)
          .then(function () {
            studioAudio.clank();
            ferryNote('Ratatoskr is carrying \u201c' + truncate(name, 32) + '\u201d into the vault\u2026');
            refresh();
          })
          .catch(function () {
            err.textContent = 'Couldn’t save the item. Check the fields and try again.';
            err.hidden = false;
            keepBtn.disabled = false;
          });
      }
      keepBtn.addEventListener('click', keep);
      [nameF, kindF, bondF, enF, cuF].forEach(function (f) {
        f.addEventListener('keydown', function (e) { if (e.key === 'Enter') keep(); });
      });

      panel.appendChild(nameF);
      var slim = h('div', { className: 'draft__slim' });
      slim.appendChild(kindF);
      slim.appendChild(bondF);
      panel.appendChild(slim);
      panel.appendChild(loreF);
      panel.appendChild(enF);
      panel.appendChild(cuF);
      panel.appendChild(row);
      panel.appendChild(err);

      return {
        panel: panel,
        show: show,
        setReroll: function (fn) { againBtn.addEventListener('click', fn); }
      };
    }

    function vaultObject(item, i, draft) {
      var starred = item.starred || item.star;
      var obj = h('div', { className: 'vault-object' + (starred ? ' vault-object--starred' : '') });
      obj.appendChild(h('span', { className: 'vault-object__icon', textContent: '\u{1F4E6}' }));
      obj.appendChild(h('span', { className: 'vault-object__name',
        textContent: item.name || item.title || 'Something treasured' }));
      obj.appendChild(h('span', { className: 'vault-object__kind',
        textContent: item.kind || 'relic' }));
      var starBtn = h('button', { className: 'vault-object__star',
        'aria-label': starred ? 'Unstar' : 'Star',
        textContent: starred ? '\u2B50' : '\u2606' });
      starBtn.addEventListener('click', function () {
        if (starred) {
          ferryNote('Already kept in the Hall.');
        } else {
          var name = item.name || item.title || 'that';
          studioAudio.squeak();
          ferryNote('Ratatoskr is carrying \u201c' + truncate(name, 36) + '\u201d to the hall\u2026');
        }
        API.vaultStar(i).then(function () { enter(); });
      });
      obj.appendChild(starBtn);
      var deepenBtn = h('button', { className: 'vault-deepen', type: 'button', textContent: 'deepen' });
      deepenBtn.addEventListener('click', function () {
        deepenBtn.disabled = true;
        deepenBtn.textContent = 'Asking the Hoard-Keeper…';
        API.enhanceItem({
          base_name: item.name || item.title,
          kind: item.kind || 'relic',
          intent: 'Grow its story (and any curse it carries)'
        }).catch(function () { return null; }).then(function (res) {
          deepenBtn.disabled = false;
          deepenBtn.textContent = 'deepen';
          if (!res || !res.name) {
            draft.show({}, false, 'Couldn’t grow this item’s story. Try again later.');
            return;
          }
          ferryNote('The Hoard-Keeper wrote more of its story.');
          draft.show(res, false);
        });
      });
      obj.appendChild(deepenBtn);
      return obj;
    }
    function leave() {}
    return { init: init, enter: enter, leave: leave };
  })();
})(window.VEFR_STUDIO);
