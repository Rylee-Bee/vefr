/* Sprite-scale harness: runs the REAL window.spriteScale from web/packaged.html (between its own marker
   comments) in a node vm sandbox and prints a table of inputs and outputs as JSON.
   Usage: node sprite_scale_harness.mjs <packaged.html> */
import fs from 'node:fs';
import vm from 'node:vm';

const htmlPath = process.argv[2];
if (!htmlPath) throw new Error('usage: sprite_scale_harness.mjs <packaged.html>');
const html = fs.readFileSync(htmlPath, 'utf8');
const start = html.indexOf('// -- spriteScale start --');
const end = html.indexOf('// -- spriteScale end --');
if (start === -1 || end === -1 || end < start) throw new Error('spriteScale markers not found');
const ctx = { Math };
ctx.globalThis = ctx;
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(html.slice(start, end), ctx, { timeout: 5000 });
const f = ctx.spriteScale;
if (typeof f !== 'function') throw new Error('the block did not define spriteScale');
const s = { cat: 0.5, big: 1.5, tiny: 0.1, huge: 3, nan: NaN, inf: Infinity, str: '0.5', nul: null, neg: -1 };
const out = {};
for (const k of ['cat', 'big', 'tiny', 'huge', 'nan', 'inf', 'str', 'nul', 'neg', 'absent']) out[k] = f(s, k);
out.noScales = f(undefined, 'cat');
out.nullScales = f(null, 'cat');
console.log(JSON.stringify(out));
