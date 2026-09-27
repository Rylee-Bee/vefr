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
// Wrapped lines are one paragraph; two trailing spaces keep a break (poems).
eq('soft wrap joins', L.renderPage('a\nb'), '<p>a b</p>');
eq('hard break', L.renderPage('a  \nb'), '<p>a<br>b</p>');
eq('italic across a wrap', L.renderPage('a *random number\ngenerator* here'), '<p>a <em>random number generator</em> here</p>');
eq('inline code', L.renderPage('`#` is a wall'), '<p><code>#</code> is a wall</p>');
eq('fenced block shown exactly', L.renderPage('Map:\n\n```\n#..#\n*a* <b>\n```\n\nDone.'),
  '<p>Map:</p><pre><code>#..#\n*a* &lt;b&gt;</code></pre><p>Done.</p>');
// The glossary: an italic word with an entry becomes a tappable button.
const G = { commit: { plain: 'Saving for good.' }, 'draw order': { plain: 'x', also: ['z-order'] } };
eq('glossary term', L.renderPage('a *commit*', G),
  '<p>a <button type="button" class="lib-term" data-term="commit" aria-expanded="false"><em>commit</em></button></p>');
eq('glossary alias', L.lookup(G, 'Z-Order'), 'draw order');
eq('unknown word stays italic', L.renderPage('*nope*', G), '<p><em>nope</em></p>');
eq('no glossary, no buttons', L.renderPage('*commit*'), '<p><em>commit</em></p>');
eq('glossary cannot inject', L.renderPage('*<x>*', { '<x>': { plain: 'x' } }).includes('<x>'), false);
if (fails) { console.log(`${fails} FAILED`); process.exit(1); }
console.log('ALL PASS');
