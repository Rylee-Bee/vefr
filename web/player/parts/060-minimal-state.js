// ---- minimal state ----
const STATE = (function () {
  var s = { phase: null, world: null };
  return {
    get: () => s,
    set: (patch) => { Object.assign(s, patch); },
    on: () => () => {},
  };
})();

