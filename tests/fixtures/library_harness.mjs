// Drives web/js/library.js in a node vm sandbox (shipped-JS pattern).
import fs from 'node:fs';
import vm from 'node:vm';
const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);
const L = sandbox.window.VEFR_LIBRARY;
let fails = 0;
const eq = (name, got, want) => {
  if (JSON.stringify(got) !== JSON.stringify(want)) { fails++; console.log(`FAIL ${name}: got ${JSON.stringify(got)} want ${JSON.stringify(want)}`); }
  else console.log(`ok   ${name}`);
};
eq('clamp low', L.clampPage(-3, 4), 0);
eq('clamp high', L.clampPage(9, 4), 3);
eq('clamp empty', L.clampPage(2, 0), 0);
eq('label', L.pageLabel(1, 3), 'Page 2 of 3');
eq('label empty', L.pageLabel(0, 0), 'No pages');
eq('paragraphs', L.renderPage('One.\n\nTwo.'), '<p>One.</p><p>Two.</p>');
eq('emphasis', L.renderPage('**Gate:** *soft*'), '<p><strong>Gate:</strong> <em>soft</em></p>');
eq('bullets', L.renderPage('- a\n- b'), '<ul><li>a</li><li>b</li></ul>');
eq('numbers', L.renderPage('1. a\n2. b'), '<ol><li>a</li><li>b</li></ol>');
// The author's words are shown, never run: markup is escaped.
eq('escapes html', L.renderPage('<img src=x onerror=alert(1)>'), '<p>&lt;img src=x onerror=alert(1)&gt;</p>');
eq('line breaks', L.renderPage('a\nb'), '<p>a<br>b</p>');
if (fails) { console.log(`${fails} FAILED`); process.exit(1); }
console.log('ALL PASS');
