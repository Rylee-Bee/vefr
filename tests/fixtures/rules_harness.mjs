/* Rules-engine harness: executes the REAL window.VEFR_RULES_ENGINE
   block extracted from web/packaged.html between its own marker
   comments, inside a node vm sandbox with nothing but the built-ins
   (no npm packages, no jsdom). It then drives the engine over a JSON
   case file and prints one line per check:

       ok   <case name> / <step>
       all checks passed: <n>

   Usage: node rules_harness.mjs <path/to/packaged.html> <cases.json>

   Case file shape:
       { "cases": [ { "name": ..., "pack": {...}, "steps": [...] } ] }

   Steps run in order; each carries exactly one key:
       {"run": [<event>, <data>]}   engine.run(state, event, data)
       {"patch": {...}}             Object.assign into the state
       {"snapshot": true}           remember the state as JSON
       {"actions": [...]}           last run's actions, deep-equal
       {"fired_ids": [...]}         last run's fired ids, in order
       {"fired_count": n}           how many rules fired on last run
       {"why_contains": "<id>"}     that rule's why is one non-empty
                                    string containing the rule id
       {"flag": [<name>, <bool>]}
       {"belief": [<who>, <claim>, <bool>] or [..., "<source>"]}
       {"items": [[<item>, <bool>], ...]}
       {"state_unchanged": true}    state JSON equals the snapshot
       {"action_names": [...]}      each last action's single key
       {"same_objects": "<id>"}     the named rule fired, and every
                                    last action IS one of the fired
                                    rules' own `then` objects

   What runs here is exactly what ships, not a copy. The first failed
   check prints and exits non-zero. */
import fs from 'node:fs';
import vm from 'node:vm';

const htmlPath = process.argv[2];
const casePath = process.argv[3];
if (!htmlPath || !casePath) {
  console.error('usage: rules_harness.mjs <packaged.html> <cases.json>');
  process.exit(2);
}
const html = fs.readFileSync(htmlPath, 'utf8');

const start = html.indexOf('// -- rules start --');
const end = html.indexOf('// -- rules end --');
if (start === -1 || end === -1 || end <= start) {
  console.error('rules markers not found in ' + htmlPath);
  process.exit(1);
}
const code = html.slice(start, end);
if (!code.replace(/\/\/ -- rules (start|end) --/g, '').trim()) {
  console.error('the extracted rules block is empty');
  process.exit(1);
}

// Nothing but the built-ins: the sandbox gets a window pointing at
// itself and no document, no localStorage, no fetch, no network.
const ctx = {};
ctx.globalThis = ctx;
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(code, ctx, { timeout: 5000 });
const engine = ctx.window.VEFR_RULES_ENGINE;
if (!engine || typeof engine.newState !== 'function'
    || typeof engine.run !== 'function') {
  console.error('the extracted block did not define window.VEFR_RULES_ENGINE');
  process.exit(1);
}

const spec = JSON.parse(fs.readFileSync(casePath, 'utf8'));
const cases = Array.isArray(spec.cases) ? spec.cases : [];
let checked = 0;

function check(label, ok, detail) {
  checked += 1;
  if (!ok) {
    console.error('FAIL ' + label + (detail ? ' :: ' + detail : ''));
    process.exit(1);
  }
  console.log('ok   ' + label);
}

function deep(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

for (const c of cases) {
  const pack = c.pack && typeof c.pack === 'object' ? c.pack : {};
  const ruleById = {};
  for (const r of Array.isArray(pack.rules) ? pack.rules : []) {
    if (r && r.id) ruleById[r.id] = r;
  }
  let state = engine.newState(pack);
  let last = null;
  let snap = null;

  for (const step of Array.isArray(c.steps) ? c.steps : []) {
    const label = c.name + ' / ' + JSON.stringify(step);
    if (Object.prototype.hasOwnProperty.call(step, 'run')) {
      last = engine.run(state, step.run[0], step.run[1]);
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(step, 'patch')) {
      Object.assign(state, step.patch);
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(step, 'snapshot')) {
      snap = JSON.stringify(state);
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(step, 'actions')) {
      check(label, !!last && deep(last.actions, step.actions),
        'got ' + JSON.stringify(last && last.actions));
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(step, 'fired_ids')) {
      const ids = last ? last.fired.map((f) => f.id) : null;
      check(label, deep(ids, step.fired_ids), 'got ' + JSON.stringify(ids));
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(step, 'fired_count')) {
      const n = last ? last.fired.length : -1;
      check(label, n === step.fired_count, 'got ' + n);
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(step, 'why_contains')) {
      const id = step.why_contains;
      const entry = last ? last.fired.find((f) => f.id === id) : null;
      const why = entry ? entry.why : null;
      const ok = typeof why === 'string' && why.length > 0
        && why.indexOf('\n') === -1 && why.indexOf(id) !== -1;
      check(label, ok, 'why for ' + id + ' is ' + JSON.stringify(why));
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(step, 'flag')) {
      const [name, want] = step.flag;
      const got = state.flags[name];
      check(label, got === want, 'flag ' + name + ' is ' + got);
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(step, 'belief')) {
      const [who, claim, wantValue] = step.belief;
      const held = state.beliefs[who];
      const b = held && typeof held === 'object' ? held[claim] : null;
      let ok = !!b && b.value === wantValue;
      let detail = JSON.stringify(b);
      if (ok && step.belief.length > 3) {
        ok = b.source === step.belief[3];
        detail = JSON.stringify(b);
      }
      check(label, ok, 'belief ' + who + '/' + claim + ' is ' + detail);
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(step, 'items')) {
      let ok = true;
      for (const [item, want] of step.items) {
        if (state.items[item] !== want) ok = false;
      }
      check(label, ok, 'items are ' + JSON.stringify(state.items));
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(step, 'state_unchanged')) {
      check(label, snap !== null && JSON.stringify(state) === snap,
        'state moved: ' + JSON.stringify(state));
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(step, 'action_names')) {
      const names = last
        ? last.actions.map((a) => Object.keys(a)[0]) : null;
      check(label, deep(names, step.action_names),
        'got ' + JSON.stringify(names));
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(step, 'same_objects')) {
      // The actions must be the rules' own `then` objects - the same
      // references, in fired order, so the wiring never translates.
      const expected = [];
      let firedKnown = !!last;
      if (last) {
        for (const f of last.fired) {
          const r = ruleById[f.id];
          if (!r || !Array.isArray(r.then)) firedKnown = false;
          else expected.push(...r.then);
        }
      }
      const id = step.same_objects;
      const namedFired = !!last && last.fired.some((f) => f.id === id);
      const same = namedFired && firedKnown && !!last
        && last.actions.length === expected.length
        && last.actions.every((a, i) => a === expected[i]);
      check(label, same,
        'actions are not the rules\' own then objects: '
          + JSON.stringify(last && last.actions));
      continue;
    }
    check(label, false, 'unknown step key');
  }
}

console.log('all checks passed: ' + checked);
