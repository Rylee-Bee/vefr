// Drives web/js/chronicle.js in a node vm sandbox (shipped-JS pattern).
import fs from 'node:fs';
import vm from 'node:vm';

const src = fs.readFileSync(process.argv[2], 'utf8');
const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(src, sandbox);
const C = sandbox.window.VEFR_CHRONICLE;
let fails = 0;
const eq = (name, got, want) => {
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    fails++; console.log(`FAIL ${name}: got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
  } else console.log(`ok   ${name}`);
};

// Every kind keeps its words in its own field; none may read as blank.
eq('rumor', C.line({ kind: 'rumor', speaker: 'Maren', whisper: 'The tower hums.' }),
   { kind: 'A whisper', who: 'Maren', text: 'The tower hums.' });
eq('npc line', C.line({ kind: 'npc_line', speaker: 'The Keeper', line: 'Rest a while.' }),
   { kind: 'A line', who: 'The Keeper', text: 'Rest a while.' });
eq('letter', C.line({ kind: 'stefna_letter', letter: 'To the one who tends.' }).text, 'To the one who tends.');
eq('action', C.line({ kind: 'combat_action', verb: 'plate' }).text, 'You chose to plate.');
eq('unknown kind falls back', C.line({ kind: 'new_thing', text: 'hello' }).text, 'hello');

// A run of actions in one phase folds into one line; a phase change or
// another kind starts a new run; each run remembers its first index.
const runs = C.fold([
  { kind: 'rumor', whisper: 'a', at: 't0' },
  { kind: 'combat_action', verb: 'plate', phase: 'dusk', at: 't1' },
  { kind: 'combat_action', verb: 'plate', phase: 'dusk', at: 't2' },
  { kind: 'combat_action', verb: 'attack', phase: 'dusk', at: 't3' },
  { kind: 'combat_action', verb: 'attack', phase: 'dawn', at: 't4' },
]);
eq('fold count', runs.length, 3);
eq('fold run size', runs[1].count, 3);
eq('fold keeps last time', runs[1].at, 't3');
eq('fold index', runs.map(r => r.index), [0, 1, 4]);
eq('actions text', C.actions(runs[1]).text, 'At dusk: plate ×2, attack.');
eq('actions kind', C.actions(runs[1]).kind, '3 actions');

if (fails) { console.log(`${fails} FAILED`); process.exit(1); }
console.log('ALL PASS');
