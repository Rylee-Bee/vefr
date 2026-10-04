// ---- title screen ----
var titleScreen = document.getElementById('title-screen');
var tsEnter = document.getElementById('ts-enter');
tsEnter.addEventListener('click', function () {
  titleScreen.setAttribute('aria-hidden', 'true');
  // After fade completes, remove from flow and show the game
  setTimeout(function () {
    // Now reveal config or play surface. configured:true (saved even
    // when both fields were left blank) means "setup decided - play",
    // so offline players don't get re-prompted on every load. The
    // llmUrl && llmModel check keeps pre-flag saves working.
    // Begin goes straight into the game; a model is only ever an
    // optional extra, offered from the pause menu.
    enterGame();
    // The one `starts` event: Begin has been pressed, the world is up
    // (setupTown has run, so the engine exists for any pack that has
    // rules - and fireRule is a no-op for every pack that does not).
    // In persist mode a reload skips it: the save already saw it.
    if (rulesStartsNow()) fireRule('starts', {});
  }, 0);
});
// Focus the enter button after paint
requestAnimationFrame(function () { tsEnter.focus(); });
