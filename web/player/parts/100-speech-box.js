// ---- speech box: whoever is talking, in a box over the game ----
function showSpeech(speaker, line, note) {
  // A skin's portrait hangs off this hook (540-the-skin.js draws it). The
  // hook is read here, when the box is shown, and never when the skin loads,
  // so it does not matter which of the two parts the page loads first: a
  // speech box declared after the skin still gets its portrait. A player
  // with no skin has no hook, and this is one read and nothing more.
  if (typeof window.VEFR_SPEECH_BOX === 'function') window.VEFR_SPEECH_BOX(speaker);
  document.getElementById('npc-name').textContent = speaker || '';
  document.getElementById('npc-line').textContent = line || '';
  var n = document.getElementById('npc-note');
  n.textContent = note || ''; n.hidden = !note;
  document.getElementById('npc-box').hidden = false;
  document.getElementById('npc-close').focus();
}

