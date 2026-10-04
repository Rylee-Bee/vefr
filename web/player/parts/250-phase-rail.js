// ---- phase rail ----
function buildPhaseRail() {
  var rail = document.getElementById('phase');
  rail.innerHTML = '';
  Object.keys(window.VEFR_WORLD.phases).forEach(function (k) {
    var b = document.createElement('button');
    b.type = 'button'; b.textContent = k; b.dataset.phase = k;
    b.setAttribute('aria-pressed', 'false');
    b.addEventListener('click', function () {
      STATE.set({ phase: k });
      rail.querySelectorAll('button').forEach(function (x) {
        x.setAttribute('aria-pressed', x.dataset.phase === k ? 'true' : 'false');
      });
      // A new tone moves the encounter prompt; the health line is
      // the hero's own and does not follow the phase.
      renderHp();
      renderEncounter();
      fireRule('phase-changes', { to: k });
    });
    rail.appendChild(b);
  });
  rail.querySelectorAll('button').forEach(function (b) {
    b.setAttribute('aria-pressed', b.dataset.phase === STATE.get().phase ? 'true' : 'false');
  });
}

