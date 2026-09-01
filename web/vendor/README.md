# web/vendor - vendored browser libraries

Kept as plain files so the engine keeps its no-build rule and the
packaged single-file play output stays self-contained. Every entry
records what it is, where it came from, and why it earned a place.

| file | what | source | version | license | why it is here |
| --- | --- | --- | --- | --- | --- |
| `Sortable.min.js` | reorderable drag-and-drop lists | github.com/SortableJS/Sortable | 1.15.7 | MIT | the dev board's drag layer: native HTML5 DnD has no touch support |

Rules for this directory:

- One file per library, pinned version, provenance recorded here.
- Classic-script compatible (UMD/IIFE). ESM-only packages need an
  import map or a bundler - that is a toolchain decision, made in
  the open, not a drive-by.
- Loaded before the script that uses it; every consumer must
  degrade honestly when the vendor file is absent (the tests run
  in a sandbox that loads none of these).
