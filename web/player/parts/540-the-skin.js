// ---- the skin: the player paints the pack's pictures (design/ui-skin.md) ----
// A woven game may carry window.VEFR_SKIN: one baked object whose parts
// are data URIs. When it is there, a single <style id="vefr-skin-css">
// paints the real panels, buttons, bars and cursor and body gains the
// has-skin class. No skin (null) means no element, no class, no change.
// The whole sheet sits behind a media guard, so high contrast and forced
// colours keep the plain flat player (rules 3 and 4).
//
// Two more optional things a skin may name, both from
// docs/plans/interface/PLAN.md: `backdrop`, the seamless picture the ground
// outside the drawn map takes (painted on the canvas, in 480, once the
// picture has decoded), and `fonts`, the display and body families the
// engine bundles. A skin with neither plays exactly as it did.
var SKIN_FONT_STACKS = {
  'Cinzel': "'Cinzel', Georgia, 'Times New Roman', serif",
  'Atkinson Hyperlegible Next': "'Atkinson Hyperlegible Next', system-ui, -apple-system, 'Segoe UI', sans-serif",
  'Crimson Pro': "'Crimson Pro', Georgia, 'Times New Roman', serif"
};

// Whether this person asked for the plain flat style instead of a skin's
// pictures (rule 4). Read when the ground is set, and again when the
// setting changes while the game is open.
function plainStyle() {
  if (!window.matchMedia) return false;
  return !!(window.matchMedia('(prefers-contrast: more)').matches
    || window.matchMedia('(forced-colors: active)').matches);
}
// The map repaints itself on the next step, but a picture that arrives late
// should not wait for one.
function redrawGround() {
  if (typeof window.VEFR_REDRAW === 'function') window.VEFR_REDRAW();
}
// The ground the skin asks for, or none: the picture only when the person
// has not asked for the plain flat style. The map is redrawn when it lands.
function loadBackdrop(skin) {
  var url = (skin && skin.backdrop && !plainStyle()) ? skin.backdrop : null;
  window.VEFR_BACKDROP_URL = url;
  if (!url) { window.VEFR_BACKDROP = null; return; }
  var probe = new Image();
  probe.onload = function () { window.VEFR_BACKDROP = probe; redrawGround(); };
  probe.onerror = function () { window.VEFR_BACKDROP = null; };   // the flat ground stays
  probe.src = url;
}
// The setting can change while the game is open; the ground follows it.
function watchPlainStyle(skin) {
  ['(prefers-contrast: more)', '(forced-colors: active)'].forEach(function (q) {
    var mq = window.matchMedia && window.matchMedia(q);
    if (mq && mq.addEventListener) {
      mq.addEventListener('change', function () { loadBackdrop(skin); redrawGround(); });
    }
  });
}
function skinFontStack(family) {
  return (typeof family === 'string'
    && Object.prototype.hasOwnProperty.call(SKIN_FONT_STACKS, family))
    ? SKIN_FONT_STACKS[family] : null;
}

function applySkin() {
  var skin = window.VEFR_SKIN;
  if (!skin || typeof skin !== 'object') return;
  var parts = skin.parts || {};
  var ink = skin.ink || {};
  loadBackdrop(skin);
  watchPlainStyle(skin);

  // The flat ground behind a panel's own centre: dark ink wants a light
  // ground, so the words stay readable if the picture does not cover it.
  function ground() {
    var m = /^#([0-9a-fA-F]{6})$/.exec(ink.on_panel || '');
    if (!m) return '#F4EEDD';
    var n = parseInt(m[1], 16);
    var lum = (0.2126 * ((n >> 16) & 255)
      + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)) / 255;
    return lum > 0.55 ? '#15181D' : '#F4EEDD';
  }
  // One border-image rule from a part's picture and slice (nine-slice).
  function nine(file, slice, noFill) {
    var s = (typeof slice === 'number' && slice > 0) ? slice : 0;
    return ' border-image: url(' + file + ') ' + s + (noFill ? '' : ' fill') + ' / ' + s
      + 'px / 0 round;';
  }
  // The middle of a panel picture is a small patch (often 32 px). border-image would TILE it
  // across a wide panel and show the seams as stripes behind the text, so a panel keeps only
  // its carved border from the picture and paints its middle one flat colour taken from the
  // picture's own centre (measured in the browser; ground() is the fallback).
  function sampleGround(file, slice) {
    var im = new Image();
    im.onload = function () {
      try {
        var c = document.createElement('canvas'); c.width = 1; c.height = 1;
        var w = im.naturalWidth, h = im.naturalHeight, sl = (slice | 0) || 0;
        var sw = Math.max(1, w - 2 * sl), sh = Math.max(1, h - 2 * sl);
        var x = c.getContext('2d'); x.drawImage(im, sl, sl, sw, sh, 0, 0, 1, 1);
        var d = x.getImageData(0, 0, 1, 1).data;
        document.documentElement.style.setProperty('--vefr-skin-ground',
          'rgb(' + d[0] + ',' + d[1] + ',' + d[2] + ')');
      } catch (e) { /* no canvas: the fallback colour stays */ }
    };
    im.src = file;
  }

  var css = '';
  // The type, when the skin chooses it: the player's own two variables, so
  // every rule already written reaches the new family. Only a family the
  // engine bundles has a stack here, and the same list is what the
  // validator accepts (maplab.SKIN_FONTS).
  var fonts = skin.fonts || {};
  var show = skinFontStack(fonts.display), read = skinFontStack(fonts.body);
  if (show) css += ':root { --display: ' + show + '; }\n';
  if (read) css += ':root { --read: ' + read + '; }\n';
  var panel = parts.panel;
  if (panel && panel.file) {
    css += '.glass, #npc-box, #reader .reader-card, #trade .reader-card, #menu .carved {'
      + nine(panel.file, panel.slice, true)
      + ' background: var(--vefr-skin-ground, ' + ground() + ');'
      + (ink.on_panel ? ' color: ' + ink.on_panel + ';' : '') + ' }\n';
  }
  // The plain player writes light-on-dark text colours on the HEADINGS, labels and lines
  // inside its panels; on a parchment panel those vanish (measured 1.2:1). So the ink the
  // skin declares reaches every piece of text inside a skinned panel, except buttons.
  if (panel && panel.file && /^#[0-9a-fA-F]{6}$/.test(ink.on_panel || '')) {
    var inPanel = ['.glass', '#npc-box', '#reader .reader-card', '#trade .reader-card', '#menu .carved'];
    css += inPanel.map(function (q) {
      return q + ' :not(button, button *, .cta, .cta *, .gbtn, .gbtn *, kbd)';
    }).join(',\n') + ' { color: ' + ink.on_panel + ' !important; }\n';
    // the menu's tab buttons sit on the panel too (the teal accent on parchment was 3.8:1)
    css += '#menu .pm button { color: ' + ink.on_panel + ' !important; }\n';
    sampleGround(panel.file, panel.slice);
  }
  var button = parts.button;
  if (button && button.file) {
    var b = '.gbtn, .cta, .verb-row button';
    // Light text with a dark shadow reads on the carved-wood face (>= 4.5:1 measured);
    // the plain player's gold and dark button labels did not.
    // A dark wood-brown base UNDER the picture: the plain player's gold Whisper button kept its
    // gold background-color beneath the wood, so with the picture missing (or to a checker that
    // cannot see images) the light text sat on gold at 3.2:1.
    css += b + ' { color: #F6F0E2 !important; background-color: #5F5043 !important;'
      + ' text-shadow: 0 1px 1px rgba(20, 12, 4, 0.7); }\n';
    css += b + ' {' + nine(button.file, button.slice) + ' min-height: 44px; }\n';
    if (button.hover) css += b + ':hover {' + nine(button.hover, button.slice) + ' }\n';
    if (button.pressed) css += b + ':active {' + nine(button.pressed, button.slice) + ' }\n';
    if (button.disabled) css += b + ':disabled {' + nine(button.disabled, button.slice) + ' }\n';
  }
  var bar = parts.bar;
  if (bar && bar.frame) {
    css += '.hud-hp-bar { background: url(' + bar.frame + ') center / 100% 100% no-repeat; }\n';
  }
  if (bar && bar.fill) {
    css += '.hud-hp-fill { background: url(' + bar.fill + ') center / 100% 100% no-repeat; }\n';
  }
  var cursor = parts.cursor;
  if (cursor && cursor.file) {
    var hs = (Array.isArray(cursor.hotspot) && cursor.hotspot.length >= 2)
      ? cursor.hotspot : [0, 0];
    css += 'body.has-skin { cursor: url(' + cursor.file + ') ' + hs[0]
      + ' ' + hs[1] + ', auto; }\n';
    if (cursor.hand) {
      css += 'body.has-skin a, body.has-skin button { cursor: url('
        + cursor.hand + ') ' + hs[0] + ' ' + hs[1] + ', auto; }\n';
    }
  }
  if (!css) return;

  var style = document.createElement('style');
  style.id = 'vefr-skin-css';
  style.textContent = '@media (prefers-contrast: no-preference) and'
    + ' (not (forced-colors: active)) {\n' + css + '}\n';
  document.head.appendChild(style);
  document.body.classList.add('has-skin');
}
applySkin();

