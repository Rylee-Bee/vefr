// -- startover start --
// Start over: remove every save this site keeps for a vefr game, so an
// old save left by another game cannot surprise the player. Pure: it
// takes any object with `length`, `key(i)` and `removeItem(k)` - a
// real localStorage or a fake - and returns the keys it removed, in
// the order it found them. Keys not starting with `vefr-` are left
// alone, and a storage that refuses one remove is skipped, never an
// error. No DOM, no location, no clock: a node vm whose only global
// is Math can run it.
globalThis.startoverKeys = function (storage) {
  var removed = [];
  if (!storage || typeof storage.length !== 'number') return removed;
  var keys = [];
  for (var i = 0; i < storage.length; i++) {
    var k = storage.key(i);
    if (typeof k === 'string' && k.indexOf('vefr-') === 0) keys.push(k);
  }
  for (var j = 0; j < keys.length; j++) {
    try { storage.removeItem(keys[j]); removed.push(keys[j]); }
    catch (e) { /* a storage that refuses; leave it and keep going */ }
  }
  return removed;
};
// -- startover end --
