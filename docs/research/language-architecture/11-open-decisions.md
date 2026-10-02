# 11 · Decisions for Rylee

## Decided (Rylee, 2026-10-02, in chat)

| # | Decision |
|---|---|
| 1 | **Source is edited, JSON is generated.** Generated contracts are read-only and carry a source hash; stale output is rejected (this settles item 9, stale output). |
| 2 | **JSON file inside the pack** holds the source. No YAML, no sibling directory. |
| 3 | **Name: "Blueprint".** Checked: no existing use of the word in `src`, `web` or `docs`. |
| 4 | **Rule saves are a per-pack setting.** The pack declares persist or reset; the default is reset, so old packs are unchanged. Cottage is expected to declare persist. Her reason: she wants many games on this engine. The field name and shape are for Plan 2. |
| 8 | **Bump Cottage's pin with the first normalizer.** Older runtimes are not promised. |

| 4a | Rule saves go in a nested `saves` block: `saves.rules` = persist or reset, `saves.legacy` = fresh or from-log (old saves); persist covers flags, `once` markers, beliefs and items; `starts` fires once per save. |
| 5a | Plan 1 exit threshold: at least 25% fewer authored values, or one real error caught. Generated records are committed and read-only. End of life for hand-written records is set later. |

## Still open

5. **Guardians and the ending:** how they are authored. The probe could not decide this; no real ending room exists. Not needed for either plan.
6. **Disposition read:** this packet says GO WITH CONSTRAINTS. Nothing is authorized until Rylee has read it (the plan's Gate) and says go.
7. **Opus brief:** the Foreman count and model, stated before launch.
