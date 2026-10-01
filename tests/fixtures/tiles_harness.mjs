/* Tiles-variant harness: executes the REAL window.pickVariant helper
   extracted from web/packaged.html between its own marker comments,
   inside a node vm sandbox with no npm packages (jsdom is not needed
   and not installed). It then prints the 16x16 grid of picks for a few
   variant counts to stdout as JSON:

       {"1": [[...]], "2": [...], "3": [...], "5": [...]}

   Usage: node tiles_harness.mjs <path/to/packaged.html>

   What runs here is exactly what ships, not a copy. Throws on a missing
   block or a function that never lands on the sandbox. */
import fs from 'node:fs';
import vm from 'node:vm';

const htmlPath = process.argv[2];
if (!htmlPath) throw new Error('usage: tiles_harness.mjs <packaged.html>');
const html = fs.readFileSync(htmlPath, 'utf8');

const start = html.indexOf('// -- pickVariant start --');
const end = html.indexOf('// -- pickVariant end --');
if (start === -1 || end === -1 || end < start) {
  throw new Error('pickVariant markers not found in ' + htmlPath);
}
const code = html.slice(start, end);

const ctx = { Math };
ctx.globalThis = ctx;
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(code, ctx, { timeout: 5000 });
if (typeof ctx.pickVariant !== 'function') {
  throw new Error('the extracted block did not define pickVariant');
}

const counts = [1, 2, 3, 5];
const out = {};
for (const n of counts) {
  const grid = [];
  for (let y = 0; y < 16; y++) {
    const row = [];
    for (let x = 0; x < 16; x++) row.push(ctx.pickVariant(x, y, n));
    grid.push(row);
  }
  out[String(n)] = grid;
}
process.stdout.write(JSON.stringify(out));
