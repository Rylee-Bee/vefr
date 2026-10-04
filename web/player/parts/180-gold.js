// ---- gold: the hero's purse, persisted with the bag ----
// `vefr-gold-<world>` holds one number; the baked `VEFR_HERO.gold` is
// the starting purse (default 0). A world with no shop and no priced
// item shows no gold line, so an old world's HUD is untouched.
var GOLD_KEY = 'vefr-gold-' + ((window.VEFR_WORLD && window.VEFR_WORLD.name) || 'world');

function itemHasValue(def) {
  return !!(def && typeof def.value === 'number' && def.value > 0);
}

// Does this world trade at all? A shop, or anything a shop would pay
// for. When false the game is exactly the game it was before gold.
var REWARD_ON = (function () {
  if (Object.keys(window.VEFR_SHOPS || {}).length) return true;
  var cat = window.VEFR_ITEMS || {};
  return Object.keys(cat).some(function (id) { return itemHasValue(cat[id]); });
})();

function heroGold() {
  var n = NaN;
  try { n = parseInt(localStorage.getItem(GOLD_KEY), 10); } catch (e) {}
  if (isFinite(n) && n >= 0) return n;
  var baked = window.VEFR_HERO && window.VEFR_HERO.gold;
  return (typeof baked === 'number' && baked >= 0) ? baked : 0;
}
function saveGold(n) {
  n = Math.max(0, Math.floor(n));
  try { localStorage.setItem(GOLD_KEY, String(n)); } catch (e) {}
  return n;
}

function itemCatalog() {
  return (window.VEFR_ITEMS && typeof window.VEFR_ITEMS === 'object')
    ? window.VEFR_ITEMS : {};
}
function itemName(id) {
  var def = itemCatalog()[id];
  return (def && def.name) || id;
}
function itemSpriteSrc(id) {
  var def = itemCatalog()[id];
  var name = def && def.sprite;
  if (!name) return '';
  return (window.VEFR_SPRITES || {})[name] || '';
}
function bagItems() {
  try {
    var ids = JSON.parse(localStorage.getItem(BAG_KEY) || '[]');
    return Array.isArray(ids) ? ids.filter(function (id) {
      return typeof id === 'string' && itemCatalog()[id];
    }) : [];
  } catch (e) { return []; }
}
// Rebuild the harness-readable fight snapshot after bag/gold changes.
// setupTown installs the real builder; before that (or in a pack with no
// game surface) this is a no-op.
function syncCombat() {
  if (typeof window.refreshCombatSnapshot === 'function') {
    try { window.refreshCombatSnapshot(); } catch (e) {}
  }
}
function bagAdd(id) {
  if (!itemCatalog()[id]) return false;
  var ids = bagItems();
  ids.push(id);
  try { localStorage.setItem(BAG_KEY, JSON.stringify(ids)); } catch (e) {}
  renderBagPanel();
  renderBagStrip();
  syncCombat();
  return true;
}
// Take one copy of an id out of the bag. False when it was not carried.
function bagRemoveOne(id) {
  var ids = bagItems();
  var i = ids.indexOf(id);
  if (i === -1) return false;
  ids.splice(i, 1);
  try { localStorage.setItem(BAG_KEY, JSON.stringify(ids)); } catch (e) {}
  renderBagPanel();
  renderBagStrip();
  syncCombat();
  return true;
}

// Use a carried thing. A thing the pack gave a `light` lights the dark
// (see setupTown); a thing with a `heal` raises health by `heal` (never
// above the max). Either way it takes one copy out of the bag and says
// so in the panel's live line. With neither, nothing happens.
function useItem(id) {
  var def = itemCatalog()[id];
  if (!def) return false;
  // A worn thing is not in the bag list, so its Use button does not
  // exist; if anything still reaches it, the line says take it off.
  if (isWorn(id)) {
    bagSay('Take it off first.');
    return false;
  }
  // The `use` verb fires with the item and the named place the hero is
  // standing on (the POI line's own text - the thing in reach); with
  // no named place it is '', which matches no rule and harms nothing.
  fireRule('uses-with', { item: id, with: (document.getElementById('poi') || {}).textContent || '' });
  // Usable is not the same as consumable: a `keep` thing is used and
  // stays; a bare `use` (no heal, no light) has nothing to spend and
  // is the natural shape of a quest tool.
  var keep = def.keep === true;
  if (def.light && typeof def.light === 'object'
      && typeof window.useLightItem === 'function') {
    return window.useLightItem(id, def);
  }
  var verb = def.use || 'use';
  if (!(typeof def.heal === 'number' && def.heal > 0)) {
    bagSay('You ' + verb + ' ' + itemName(id) + '.');
    return true;
  }
  // Whole already: say so and keep the thing. A potion is not spent on
  // nothing, so the player never loses a heal by mis-tapping.
  if (HERO_HP >= heroMax()) {
    bagSay('You ' + verb + ' ' + itemName(id) + '. You are already whole.');
    return true;
  }
  if (!keep && !bagRemoveOne(id)) return false;
  var before = HERO_HP;
  HERO_HP = Math.min(heroMax(), HERO_HP + def.heal);
  saveHeroHp();
  renderHp();
  var gained = HERO_HP - before;
  bagSay('You ' + verb + ' ' + itemName(id) + '. '
    + 'You recover ' + gained + ' health.');
  syncCombat();
  return true;
}

// The Bag panel's live line (kept in the panel, not the game's toasts).
function bagSay(msg) {
  var el = document.getElementById('bag-live');
  if (el) el.textContent = msg || '';
}

// Gold writes redraw both the HUD line and the Bag panel's line.
function renderGold() {
  var g = heroGold();
  var hud = document.getElementById('hud-gold');
  if (hud) { hud.hidden = !REWARD_ON; hud.textContent = g + ' gold'; }
  var panel = document.getElementById('bag-gold');
  if (panel) panel.textContent = REWARD_ON ? ('You carry ' + g + ' gold.') : '';
  syncCombat();
}
function addGold(n) {
  var g = saveGold(heroGold() + n);
  renderGold();
  return g;
}

// The top-of-screen strip: a small sprite per carried thing, beside the
// health bar. A thing with no ready sprite is a neutral dot. A worn
// thing is not in the bag list and is not shown here - it sits in its
// slot in the Bag panel instead.
function renderBagStrip() {
  var strip = document.getElementById('bag-strip');
  if (!strip) return;
  strip.textContent = '';
  var ids = bagItems().filter(function (id) { return !isWorn(id); });
  if (!ids.length) {
    strip.hidden = true;
    strip.setAttribute('aria-label', 'Nothing carried');
    return;
  }
  strip.hidden = false;
  ids.forEach(function (id) {
    var src = itemSpriteSrc(id);
    var node;
    if (src) {
      node = document.createElement('img');
      node.src = src;
      node.alt = '';
      node.className = 'bag-pip';
    } else {
      node = document.createElement('span');
      node.className = 'bag-pip bag-pip--dot';
      node.setAttribute('aria-hidden', 'true');
    }
    strip.appendChild(node);
  });
  strip.setAttribute('aria-label',
    'Carrying: ' + ids.map(itemName).join(', ') + '.');
}

// The Bag panel's "You" section: five slots in a fixed order, each
// row named by one sentence the eye and the screen reader share.
// An empty slot draws a plain inline-SVG outline so no new art file
// is needed. A worn slot gets a "Take off" button.
function emptySlotSvg(slot) {
  var head = '<svg class="equip-empty-svg" viewBox="0 0 32 32" aria-hidden="true" focusable="false">';
  switch (slot) {
    case 'hand':  return head + '<path d="M16 6v14M12 10l4-4 4 4M10 22h12"/></svg>';
    case 'body':  return head + '<path d="M10 8l6-2 6 2v10l-6 6-6-6z"/></svg>';
    case 'head':  return head + '<circle cx="16" cy="14" r="7"/><path d="M9 24h14"/></svg>';
    case 'feet':  return head + '<path d="M8 22h16l-2-6-6-2-6 2z"/></svg>';
    case 'charm': return head + '<circle cx="16" cy="16" r="6"/><circle cx="16" cy="16" r="2"/></svg>';
    default:      return head + '<rect x="6" y="6" width="20" height="20"/></svg>';
  }
}
function renderEquipSlots() {
  var host = document.getElementById('equip-slots');
  if (!host) return;
  host.textContent = '';
  var cat = itemCatalog();
  EQUIP_SLOTS.forEach(function (slot) {
    var row = document.createElement('div');
    row.className = 'equip-row';
    row.setAttribute('role', 'listitem');
    row.dataset.slot = slot;
    var id = (typeof EQUIP_STATE[slot] === 'string') ? EQUIP_STATE[slot] : null;
    var def = (id && cat[id]) ? cat[id] : null;
    var cap = slot.charAt(0).toUpperCase() + slot.slice(1);
    var sentence = def ? (cap + ': ' + (def.name || id)) : (cap + ': empty');
    // The art is decoration: the sentence carries the name. The empty
    // outline means "nothing worn here", so a worn slot must never draw
    // it - a worn thing with no ready sprite gets the same neutral dot
    // the bag list uses, so the two states never look alike.
    var art = document.createElement('span');
    art.className = 'equip-row-art';
    art.setAttribute('aria-hidden', 'true');
    if (def) {
      var src = itemSpriteSrc(id);
      if (src) {
        var im = document.createElement('img');
        im.src = src;
        im.alt = '';
        art.appendChild(im);
      } else {
        art.appendChild(document.createElement('span'));
        art.firstChild.className = 'bag-row-art--dot';
      }
    } else {
      art.innerHTML = emptySlotSvg(slot);
    }
    row.appendChild(art);
    var label = document.createElement('span');
    label.className = 'equip-row-name';
    label.textContent = sentence;
    row.appendChild(label);
    if (def) {
      var takeOff = document.createElement('button');
      takeOff.type = 'button';
      takeOff.className = 'cta';
      takeOff.textContent = 'Take off';
      takeOff.setAttribute('aria-label', 'Take off ' + (def.name || id));
      takeOff.dataset.slot = slot;
      takeOff.dataset.action = 'takeoff';
      takeOff.addEventListener('click', function () { takeOffSlot(slot); });
      row.appendChild(takeOff);
    }
    host.appendChild(row);
  });
}
// A one-line summary of what a worn item's mods do, for the live line.
// An item with no mods returns an empty string so the caller can skip.
function modsLine(def) {
  if (!def || !def.mods || typeof def.mods !== 'object') return '';
  var parts = [];
  if (typeof def.mods.hp === 'number' && def.mods.hp > 0) parts.push('Health up by ' + def.mods.hp);
  if (typeof def.mods.atk === 'number' && def.mods.atk > 0) parts.push('Attack up by ' + def.mods.atk);
  return parts.join('. ');
}
// The engine's refusal reasons in plain words the player can read.
function reasonToWords(reason) {
  switch (reason) {
    case 'not-an-item': return 'That is not something you can wear.';
    case 'no-slot':     return 'That cannot be worn.';
    case 'bad-slot':    return 'That does not fit there.';
    case 'wrong-slot':  return 'That does not fit there.';
    default:            return 'That did not work.';
  }
}
// Equip a carried thing into its own slot. The bag row is removed and
// the old wearer, if any, comes back to the bag.
function equipItem(id) {
  var def = itemCatalog()[id];
  if (!def) return;
  var engine = window.VEFR_EQUIP_ENGINE;
  if (!engine) {
    bagSay(reasonToWords('not-an-item'));
    return;
  }
  // An item with no slot cannot be worn. Say so in words rather than
  // asking the engine with a made-up slot.
  if (typeof def.slot !== 'string' || EQUIP_SLOTS.indexOf(def.slot) < 0) {
    bagSay(reasonToWords('no-slot'));
    return;
  }
  var result = engine.equip(EQUIP_STATE, itemCatalog(), def.slot, id);
  if (result.reason !== 'ok') {
    bagSay(reasonToWords(result.reason));
    return;
  }
  // Apply the change before the re-render so every read sees the new state.
  EQUIP_STATE = result.state;
  saveEquipped(EQUIP_STATE);
  bagRemoveOne(id);
  if (result.swapped) bagAdd(result.swapped);
  var line = 'You put on ' + (def.name || id) + '.';
  var ml = modsLine(def);
  if (ml) line += ' ' + ml + '.';
  // On a swap, name what came off so the player can see the change.
  if (result.swapped) {
    var oldDef = itemCatalog()[result.swapped];
    line += ' ' + (oldDef ? (oldDef.name || result.swapped) : result.swapped) + ' comes off.';
  }
  bagSay(line);
  renderHp();
  renderEquipSlots();
  syncCombat();
}
// Take a worn thing off: the slot empties, the thing returns to the
// bag, and current health is clamped to the new max if needed.
function takeOffSlot(slot) {
  var engine = window.VEFR_EQUIP_ENGINE;
  if (!engine) return;
  var id = (typeof EQUIP_STATE[slot] === 'string') ? EQUIP_STATE[slot] : null;
  var def = id ? itemCatalog()[id] : null;
  var result = engine.unequip(EQUIP_STATE, slot);
  if (!result.removed) {
    bagSay('Nothing to take off there.');
    return;
  }
  EQUIP_STATE = result.state;
  saveEquipped(EQUIP_STATE);
  bagAdd(result.removed);
  // If the new max is below current, clamp and save; never below 1.
  var newMax = heroMax();
  if (HERO_HP > newMax) {
    HERO_HP = engine.clampHealth(HERO_HP, newMax);
    saveHeroHp();
  }
  var line = 'You take off ' + (def ? (def.name || result.removed) : result.removed) + '.';
  bagSay(line);
  renderHp();
  renderEquipSlots();
  syncCombat();
}

// The pause-menu panel: a "You" section of five slots, then one row
// per carried (not worn) thing, sprite then name. A slotted thing in
// the bag gets an Equip button; anything with `use`, `heal` or `light`
// keeps its Use button. A worn thing is never in this list.
function renderBagPanel() {
  renderEquipSlots();
  var list = document.getElementById('bag-list');
  var count = document.getElementById('bag-count');
  if (!list) return;
  list.textContent = '';
  var ids = bagItems().filter(function (id) { return !isWorn(id); });
  if (!ids.length) {
    var p = document.createElement('p');
    p.className = 'empty';
    p.textContent = 'Nothing yet.';
    list.appendChild(p);
    if (count) count.textContent = '';
    renderGold();
    return;
  }
  ids.forEach(function (id) {
    var row = document.createElement('div');
    row.className = 'bag-row';
    var src = itemSpriteSrc(id);
    if (src) {
      var im = document.createElement('img');
      im.src = src;
      im.alt = '';
      im.className = 'bag-row-art';
      row.appendChild(im);
    } else {
      var dot = document.createElement('span');
      dot.className = 'bag-row-art bag-row-art--dot';
      dot.setAttribute('aria-hidden', 'true');
      row.appendChild(dot);
    }
    var label = document.createElement('span');
    label.className = 'bag-row-name';
    label.textContent = itemName(id);
    row.appendChild(label);
    var def = itemCatalog()[id];
    // A slotted thing can be equipped from here. The engine refuses
    // anything that does not fit; the live line says so in words.
    if (def && typeof def.slot === 'string' && EQUIP_SLOTS.indexOf(def.slot) >= 0) {
      var eb = document.createElement('button');
      eb.type = 'button';
      eb.className = 'cta';
      eb.textContent = 'Equip';
      eb.dataset.item = id;
      eb.dataset.action = 'equip';
      eb.setAttribute('aria-label', 'Equip ' + itemName(id));
      eb.addEventListener('click', function () { equipItem(id); });
      row.appendChild(eb);
    }
    // Anything the pack gave a `use`, a `heal` or a `light` can be
    // used from here. The words are the pack's own verb, so a potion
    // is drunk, bread is eaten, and a torch is lit. Usable is not
    // the same as consumable: a `keep` thing is used and stays.
    if (def && (def.use
        || (typeof def.heal === 'number' && def.heal > 0)
        || (def.light && typeof def.light === 'object'))) {
      var use = document.createElement('button');
      use.type = 'button';
      use.className = 'cta';
      use.textContent = def.use || 'Use';
      use.dataset.item = id;
      use.dataset.action = 'use';
      use.setAttribute('aria-label',
        (def.use || 'Use') + ' ' + itemName(id));
      use.addEventListener('click', function () { useItem(id); });
      row.appendChild(use);
    }
    list.appendChild(row);
  });
  if (count) {
    count.textContent = ids.length
      + (ids.length === 1 ? ' thing carried.' : ' things carried.');
  }
  renderGold();
}

