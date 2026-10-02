# 11 · Decisions for Rylee

## Decided (Rylee, 2026-10-02, in chat)

| # | Decision |
|---|---|
| 1 | **Source is edited, JSON is generated.** Generated contracts are read-only and carry a source hash; stale output is rejected (item 9 follows from this). |
| 2 | **JSON file inside the pack** holds the source. No YAML, no sibling directory. |
| 3 | **Name: "Blueprint".** Checked: no existing use of the word in `src`, `web` or `docs`. |
| 4 | **Rule saves are a per-pack setting.** The pack declares persist or reset; the default is reset, so old packs are unchanged. Cottage is expected to declare persist. Her reason: she wants many games on this engine. The field name and shape are for Plan 2. |
| 8 | **Bump Cottage's pin with the first normalizer.** Older runtimes are not promised. |

## Still open

1. **Editable side of truth:** is the source or the generated JSON what a human edits for migrated structures?
2. **Source location and format:** inside the pack dir (`source/`) or a sibling? JSON, YAML or the existing markdown style? Smallest fit for the creature-family slice.
3. **Naming:** what to call the source layer (not "grammar").
4. **Save-state:** persist rule flags and `once` markers across reloads, or declare reset intended? Decide before guardians and gates.
5. **Guardians and the ending:** how they are authored. The probe could not decide this; no real ending room exists.
6. **Disposition read:** this packet says GO WITH CONSTRAINTS. Nothing is authorized until Rylee has read it (the plan's Gate).
7. **Opus brief:** who sends the packet and plan to Opus, and the Foreman count and model, stated before launch.
8. **Supported-version policy:** Cottage CI pins an older VEFR than `main`; decide the supported matrix before any normalizer ships.
9. **Stale-output policy:** generated output carries the source hash and normalizer version, and a stale artifact is rejected (Codex recommendation; not implemented).
