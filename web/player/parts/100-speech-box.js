// ---- speech box: whoever is talking, in a box over the game ----
function showSpeech(speaker, line, note) {
  document.getElementById('npc-name').textContent = speaker || '';
  document.getElementById('npc-line').textContent = line || '';
  var n = document.getElementById('npc-note');
  n.textContent = note || ''; n.hidden = !note;
  document.getElementById('npc-box').hidden = false;
  document.getElementById('npc-close').focus();
}

