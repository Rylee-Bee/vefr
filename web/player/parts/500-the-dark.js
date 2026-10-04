  // ---- the dark, on the player's terms ----
  // The pack says whether a region is dark; the player can still turn it
  // off for themselves (remembered per world). `V`, or the Display switch.
  var fogToggle = document.getElementById('fog-toggle');
  var fogLive = document.getElementById('fog-live');
  function renderFogToggle() {
    if (!fogToggle) return;
    fogToggle.setAttribute('aria-pressed', fogOn ? 'true' : 'false');
    if (!town.fog) {
      fogToggle.textContent = 'No darkness here';
      fogToggle.disabled = true;
    } else {
      fogToggle.disabled = false;
      fogToggle.textContent = 'Darkness: ' + (fogOn ? 'on' : 'off');
    }
  }
  function toggleFog() {
    if (!town.fog) {
      if (fogLive) fogLive.textContent = 'This place has no darkness.';
      return;
    }
    setFogPref(!fogOn);
    fogOn = fogEnabled();
    if (!fogOn && exploring()) exploreStop('Stopped.');
    resize();
    draw();
    renderFogToggle();
    if (fogLive) fogLive.textContent = fogOn ? 'Darkness on.' : 'Darkness off.';
  }
  if (fogToggle) fogToggle.addEventListener('click', toggleFog);
  renderFogToggle();

