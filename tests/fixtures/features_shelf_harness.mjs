// Drives web/js/features.js (pure, no DOM) in a node vm sandbox, like library_harness.mjs.
import fs from 'node:fs';
import vm from 'node:vm';
const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);
const F = sandbox.window.VEFR_FEATURES;
const cat = [
  { id: 'growth', name: 'Levels, or learning by doing', what: 'The hero grows.', status: 'built' },
  { id: 'rules', name: 'Reactions', what: 'The world answers.', status: 'built' },
  { id: 'album', name: 'The <b>album</b>', what: 'Stickers.', status: 'proposed' },
  { id: 'skin', name: 'Skin', what: 'Pictures.', status: 'partial' },
];
const pack = { name: 'cottage-of-the-breeze', uses: [
  { id: 'growth', used: true, detail: 'levels, 8 levels' },
  { id: 'rules', used: false, detail: '' },
  { id: 'album', used: false, detail: '' },
  { id: 'skin', used: null, detail: '' } ] };
const out = {
  hasApi: !!(F && F.shelfHtml && F.statusLabel),
  labels: ['built', 'proposed', 'partial', 'weird'].map((s) => F.statusLabel(s)),
  withPack: F.shelfHtml({ catalog: cat, pack }),
  noPack: F.shelfHtml({ catalog: cat, pack: null }),
  empty: F.shelfHtml({ catalog: [], pack: null }),
};
console.log(JSON.stringify(out));
