# Art pipeline lessons from the Cottage soft-wood skin (2026-10-04)

Observed while drawing and picking the interface skin. Each lesson names the tool that would remove it; the slices are A3 to A5 in `docs/plans/tighten-shapes/PLAN.md`.

1. **The batch drawer's count means "variations of one brief".** `art/tools/codex_batch.sh OUTDIR NAME COUNT BRIEF` asks for COUNT variations. Asking it for "four separate pieces" returned one piece per image, each a different idea, so the picker held single pieces and the groups looked unrelated. Fix: `vefr art draw <piece>` (A4) takes one piece from the kit and refuses a multi-piece brief.
2. **No list of what a complete skin needs.** The 19 pieces lived in the geometry table inside `art/tools/build_skin.py`; the gap showed only after Rylee had chosen. Fix: a kit manifest as data (A3) and a completeness line in `vefr art check`.
3. **Picker and picks were hand-made.** Fix: `vefr art picker` (A5) builds the page from the kit and writes the picks back to the ledger.
4. **The style block was pasted into each prompt.** Fix: palette, references and the shared style text live in one style file read by every draw job (A4).
5. **Derived states were drawn, not derived.** Hover, pressed, disabled and toggle-off are recipes applied to the chosen piece (A3).
6. **Concurrent draws steal each other's images.** The script finds new images by diffing `~/.codex/generated_images`; two jobs at once mix results. Fix: a private output folder per job (A4). Until then, run draw jobs one at a time.
7. **Credits files say "draft" by hand.** Fix: `draft` and `approved` are ledger fields, set by the picker (A5).
