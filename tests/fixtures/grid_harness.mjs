/* Grid-tile harness: runs the REAL window.pickCell from web/packaged.html (between its own marker
   comments) in a node vm sandbox and prints the picks for a 3x3 grid over a 7x7 map, plus a few
   negative coordinates, as JSON.   Usage: node grid_harness.mjs <packaged.html> */
import fs from 'node:fs';
import vm from 'node:vm';

const htmlPath = process.argv[2];
if (!htmlPath) throw new Error('usage: grid_harness.mjs <packaged.html>');
const html = fs.readFileSync(htmlPath, 'utf8');
const start = html.indexOf('// -- pickCell start --');
const end = html.indexOf('// -- pickCell end --');
if (start === -1 || end === -1 || end < start) throw new Error('pickCell markers not found');

const ctx = { Math };
ctx.globalThis = ctx;
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(html.slice(start, end), ctx, { timeout: 5000 });
if (typeof ctx.pickCell !== 'function') throw new Error('the block did not define pickCell');

const grid = [];
for (let y = 0; y < 7; y++) {
  const row = [];
  for (let x = 0; x < 7; x++) row.push(ctx.pickCell(x, y, 3, 3));
  grid.push(row);
}
const negatives = [[-1, -1], [-3, -4], [-4, 2]].map(([x, y]) => ctx.pickCell(x, y, 3, 3));
const wide = [[0, 0], [5, 1], [2, 3]].map(([x, y]) => ctx.pickCell(x, y, 4, 2));
console.log(JSON.stringify({ grid, negatives, wide }));
