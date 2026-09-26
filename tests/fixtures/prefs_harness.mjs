/* prefs.js harness: executes the REAL prefs.js inside a node vm
   sandbox with a stubbed localStorage and a stubbed document, then
   drives the full contract:

     1. defaults are the inclusive-forward floor (Atkinson, dark,
        contrast m, motion off, focus luminance)
     2. get() is a deep clone (mutating the result does not mutate
        the next call)
     3. set() persists to localStorage and writes the data-prefs
        attribute on <html>
     4. preview() applies to the DOM but does NOT persist
     5. on() subscribers fire on every persisted change and get
        re-fired with current state on attach (handled via apply()
        in the live wire-up - the test asserts the change-only path)
     6. shareLink() produces a URL that applyFromUrl() can decode
        back to identical state on a fresh "device" (fresh
        localStorage)
     7. reset() restores defaults and clears the persisted blob

   The spec file (argv[2]) is just a sentinel {path: 'web/prefs.js'}.
   The python test reads prefs.js itself and passes the JS body
   inline via a JSON spec, mirroring how the pool harness is
   driven. Here we accept the path and read the file in-harness
   for simplicity. Throws on any failed check; prints PASS on
   success. */
import fs from 'node:fs';
import vm from 'node:vm';

const path = process.argv[2];
const code = fs.readFileSync(path, 'utf8');

function makeSandbox(store) {
  const attrs = {};
  const sandbox = {
    JSON, Math, Date, URLSearchParams, URL,
    btoa: (s) => Buffer.from(s, 'binary').toString('base64'),
    atob: (s) => Buffer.from(s, 'base64').toString('binary'),
    history: { replaceState: () => {} },
    localStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
    },
    location: {
      origin: 'http://localhost',
      pathname: '/',
      href: 'http://localhost/',
      search: '',
    },
    document: {
      documentElement: {
        setAttribute(k, v) { attrs[k] = v; },
        getAttribute(k) { return attrs[k] || null; },
      },
    },
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  /* prefs.js writes `window.VEFR_PREFS = {...}` and the test reads
     the same object. window doesn't exist in a vm context, so we
     give it one that mirrors onto globalThis (which IS the scope
     the IIFE sees). */
  const winMirror = {};
  Object.defineProperty(winMirror, 'VEFR_PREFS', {
    get() { return sandbox.VEFR_PREFS; },
    set(v) { sandbox.VEFR_PREFS = v; },
  });
  sandbox.window = winMirror;
  vm.runInContext(code, sandbox, { timeout: 5000 });
  if (!sandbox.VEFR_PREFS) {
    throw new Error('prefs.js did not install window.VEFR_PREFS');
  }
  return { sandbox, attrs };
}

function expect(cond, msg) { if (!cond) throw new Error('FAIL: ' + msg); }

/* ---------- 1. defaults ---------- */
{
  const store = {};
  const { sandbox, attrs } = makeSandbox(store);
  const def = sandbox.window.VEFR_PREFS.defaults();
  expect(def.font === 'atkinson', 'default font is atkinson');
  expect(def.motion === 'off', 'default motion is off');
  expect(def.contrast === 'm', 'default contrast is m');
  expect(def.focus === 'luminance', 'default focus is luminance');
  expect(def.density === 'comfortable', 'default density is comfortable');
  expect(def.sound.pairWithVisual === true, 'sound pairs with visual by default');
  expect(def.sound.captions === true, 'captions on by default');
  expect(typeof attrs['data-prefs'] === 'string' && attrs['data-prefs'].startsWith('text='),
    'apply() wrote the data-prefs attribute on load');
  console.log('PASS defaults');
}

/* ---------- 2. deep clone ---------- */
{
  const store = {};
  const { sandbox } = makeSandbox(store);
  const a = sandbox.window.VEFR_PREFS.get();
  a.textSize = 'xl';
  const b = sandbox.window.VEFR_PREFS.get();
  expect(b.textSize !== 'xl', 'get() returned a deep clone (mutation does not leak)');
  console.log('PASS deep-clone');
}

/* ---------- 3. set persists + writes attr ---------- */
{
  const store = {};
  const { sandbox, attrs } = makeSandbox(store);
  let called = 0;
  sandbox.window.VEFR_PREFS.on(() => { called += 1; });
  sandbox.window.VEFR_PREFS.set({ textSize: 'xl', font: 'opendyslexic' });
  expect(JSON.parse(store['vefr-prefs']).textSize === 'xl', 'set() persisted to localStorage');
  expect(attrs['data-prefs'].includes('text=xl'), 'data-prefs reflects text=xl');
  expect(attrs['data-prefs'].includes('font=opendyslexic'), 'data-prefs reflects font');
  // CSS matches with [data-prefs~="font=..."], which needs whitespace-separated tokens
  expect(attrs['data-prefs'].split(/\s+/).includes('font=opendyslexic'), 'data-prefs tokens are space-separated for ~= selectors');
  expect(attrs['data-prefs'].split(/\s+/).includes('text=xl'), 'text token matches as its own word');
  expect(called === 1, 'subscriber fired once on set()');
  console.log('PASS set-persists');
}

/* ---------- 4. preview does NOT persist ---------- */
{
  const store = {};
  const { sandbox, attrs } = makeSandbox(store);
  sandbox.window.VEFR_PREFS.set({ textSize: 'xl' });
  sandbox.window.VEFR_PREFS.preview({ textSize: '2xl' });
  expect(attrs['data-prefs'].includes('text=2xl'), 'preview applied to the DOM');
  expect(JSON.parse(store['vefr-prefs']).textSize === 'xl', 'preview did NOT persist');
  console.log('PASS preview-ephemeral');
}

/* ---------- 5. share-link round-trip ---------- */
{
  const store1 = {};
  const { sandbox: s1 } = makeSandbox(store1);
  s1.window.VEFR_PREFS.set({
    textSize: 'l', spacing: 'loose', font: 'opendyslexic',
    contrast: 'high', motion: 'off', focus: 'accent', density: 'compact'
  });
  const link = s1.window.VEFR_PREFS.shareLink();
  expect(link.indexOf('?prefs=') > -1, 'shareLink produced a ?prefs= URL');

  /* Simulate a fresh device receiving the link. */
  const store2 = {};
  const { sandbox: sandbox2, attrs: attrs2 } = makeSandbox(store2);
  /* Override location.search + href so applyFromUrl sees the pref. */
  const parsed = new URL(link);
  sandbox2.location.search = parsed.search;
  sandbox2.location.href = parsed.href;
  sandbox2.history.replaceState = () => {};
  const applied = sandbox2.window.VEFR_PREFS.applyFromUrl();
  expect(applied === true, 'applyFromUrl returned true on a fresh device');
  const imported = sandbox2.window.VEFR_PREFS.get();
  expect(imported.textSize === 'l', 'textSize round-tripped');
  expect(imported.font === 'opendyslexic', 'font round-tripped');
  expect(imported.contrast === 'high', 'contrast round-tripped');
  expect(imported.focus === 'accent', 'focus round-tripped');
  console.log('PASS shareLink-roundtrip');
}

/* ---------- 6. reset restores defaults ---------- */
{
  const store = {};
  const { sandbox, attrs } = makeSandbox(store);
  sandbox.window.VEFR_PREFS.set({ textSize: '2xl', font: 'opendyslexic', contrast: 'ultra' });
  sandbox.window.VEFR_PREFS.reset();
  const after = sandbox.window.VEFR_PREFS.get();
  expect(after.textSize === 'm', 'reset restored default textSize');
  expect(after.font === 'atkinson', 'reset restored default font');
  expect(after.contrast === 'm', 'reset restored default contrast');
  expect(JSON.parse(store['vefr-prefs']).font === 'atkinson', 'reset persisted the new state');
  expect(attrs['data-prefs'].startsWith('text=m'), 'reset rewrote the data-prefs attribute');
  console.log('PASS reset');
}

/* ---------- 7. partial merge preserves other keys ---------- */
{
  const store = {};
  const { sandbox } = makeSandbox(store);
  sandbox.window.VEFR_PREFS.set({ textSize: 'xl' });
  sandbox.window.VEFR_PREFS.set({ font: 'opendyslexic' });
  const after = sandbox.window.VEFR_PREFS.get();
  expect(after.textSize === 'xl', 'first set survived a second set on a different key');
  expect(after.font === 'opendyslexic', 'second set took effect');
  console.log('PASS partial-merge');
}

console.log('ALL PASS');
