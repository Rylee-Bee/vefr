/* The canonical FloorPlan JSON, and the canonical form the twin writes.

`tests/floor_v3_parity_cases.canonical` is Python's half:
`json.dumps(value, sort_keys=True, separators=(",", ":"))`. This file is the
twin's half, so the two parity paths - the node/jsdom harness
(`tests/fixtures/floor_v3_parity_harness.mjs`) and the Chromium test - compare
the same bytes instead of each having a private idea of canonical.

They are equal for every value a FloorPlan can hold because:

  - every key is ASCII, so Python's `sort_keys` and JavaScript's `sort` agree
    on the order (both order by code point / code unit, which agree below
    U+0100);
  - every number is a whole number Python and JavaScript print identically;
  - every string is ASCII, checked rather than assumed, because
    `json.dumps` escapes a non-ASCII character by default and `JSON.stringify`
    does not.

So the comparison is on bytes, which is what PLAN.md section 2 asks for, and a
floor that differs anywhere differs here.
*/

// The canonical form: sorted keys, no whitespace, ASCII only.
export function canon(value) {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') {
    if (!Number.isInteger(value)) {
      throw new Error('a FloorPlan number is not a whole number: ' + value);
    }
    return String(value);
  }
  if (typeof value === 'string') {
    // Python's json.dumps escapes every non-ASCII character by default and
    // JSON.stringify does not, so the two agree only while the floor is ASCII.
    // Checked here rather than assumed.
    if (/[^\x20-\x7e]/.test(value)) {
      throw new Error('a FloorPlan string is not ASCII: ' + JSON.stringify(value));
    }
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return '[' + value.map(canon).join(',') + ']';
  var keys = Object.keys(value).sort();
  var parts = [];
  for (var i = 0; i < keys.length; i++) {
    parts.push(JSON.stringify(keys[i]) + ':' + canon(value[keys[i]]));
  }
  return '{' + parts.join(',') + '}';
}