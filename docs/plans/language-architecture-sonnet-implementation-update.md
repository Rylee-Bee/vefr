# VEFR Blueprint: one family resolution and correct drop pointers (refined handoff)

This replaces `docs/plans/language-architecture-sonnet-implementation-update.md` in PR #231.
It keeps that handoff's intent and its hard boundaries.
It corrects the premises against live code and data, and it makes the scope exact.

> Universalize mechanisms and guarantees. Keep domain vocabulary local.

This pass does not authorize Format 2, a kernel, a resolver framework, a public API, a new feature or a cross-repo extraction.

Revisions inspected (2026-10-02):

- VEFR `origin/main` = `f88cdd4` (`git log --oneline -1 origin/main`). PR #231 branch is one commit, `d869dea`, on base `8ce399f`; it adds only this file (`git diff --stat origin/main...<branch>`: 1 file, 185 insertions).
- Cottage `origin/main` = `f02cd07`. The Blueprint trial is merged as `a999c5b` ("creature records come from a Blueprint (the VEFR trial) (#68)"), the last commit to touch `worlds/cottage-of-the-breeze/blueprint.json`. All Cottage evidence below comes from `git archive origin/main` into a scratch copy. Nothing was written in the Cottage repo.

## Decisions (Rylee, 2026-10-02, in chat, after this refine pass)

These override anything below that says otherwise.

1. **Orchestration:** tests first (merged), then **one offload code worker** (`offload agent -m code`, deepseek-flash) with no foreman, reviewed by the integrator, who takes over after one failed attempt. The architecture-records edit and the Cottage PR stay with the integrator.
2. **Unused broken families are rejected.** A family that no instance uses, with an unknown parent or a cycle, now fails like a used one (a tightening, decided). This moves "validating unused families" from out of scope to **in scope**: validate every family's parent chain once, before the regions, with the existing messages and pointers. Cottage's Blueprint is unaffected (every family is used; re-checked by the acceptance run). New tests T11 and T12 and two conformance cases (`unused-unknown-parent`, `unused-cycle`) are added to section 5; the guide and ADR 0008 get one sentence saying the check covers unused families.
3. **Cottage taxonomy:** Rylee asked for the best future shape. Recommendation, recorded: **flat (257 values, no abstract parents) now**; a parent family earns its place only when it expresses a real shared fact, as the rustle chain does. Add kind parents when a kind gets enough variants (the drafted monsters will probably do it). The Cottage change stays a separate follow-up PR for her review.
4. This document replaces the first version of PR #231 (kept in git history).


## 0. A hazard found while verifying (read first)

The shared VEFR checkout on the dev VM has a **stale bytecode cache**.
`src/vefr/__pycache__/blueprint.cpython-312.pyc` records the same source mtime (`1790983046`) and size (`25210`) as `src/vefr/blueprint.py`. But it was compiled from a different text, one with the same size and a reordered `FIELD_ORDER`.
Evidence:

- `PYTHONPATH=src .venv/bin/python -c "from vefr import blueprint as bp; print(bp.FIELD_ORDER)"` printed `('id', 'name', 'at', 'hp', 'atk', 'drops', 'sprite', 'xp', 'sight')`.
- The source at `src/vefr/blueprint.py:33` reads `("id", "name", "sprite", "at", "hp", "atk", "xp", "sight", "drops")`.
- With `PYTHONPYCACHEPREFIX=<fresh dir>`, the same command printed the source order.

Under the stale cache, `vefr normalize` wrote records in the wrong key order. The 64 Blueprint tests still pass under it (`PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_blueprint_*.py` printed `64 passed`, the same as with a clean cache). Parsed-JSON equality ignores key order, and no test pins the emitted key order on disk.
The likely cause is an edit and revert inside the same second by another session (UNVERIFIED).
Consequences for this plan:

- Every acceptance command below sets `PYTHONPYCACHEPREFIX` to a fresh directory, or runs in a throwaway clone (`bash tests/run.sh`).
- Deleting `src/vefr/__pycache__/` in the shared checkout is safe: it is gitignored and regenerated. This plan does not delete it. Rylee or the integrator should.
- One acceptance test (T9 below) pins the emitted key order. That is the existing documented contract (ADR 0008 line 31, guide "Generated records are written in this key order"), which is currently untested.

Also: the VEFR checkout's path differs between the dev VM and Bazzite, so use the checkout-relative form `<vefr checkout>/.venv/bin/python` and check that it exists on the machine you run on.

## 1. Premises: verified and corrected

All commands ran on the VM against the revisions above, with a fresh `PYTHONPYCACHEPREFIX` unless noted.
Scripts: `scratchpad/exp/probe.py`, `count.py`, `compare.py`, `make_candidate.py`.

| # | Handoff premise | Verdict | Evidence |
|---|---|---|---|
| P1 | `_family_record()` and `_family_chain()` duplicate the parent traversal | **Correct** | `blueprint.py:188-222` walks `extends` and validates (unknown parent, cycle) before merging. `blueprint.py:312-325` walks `extends` a second time, tolerantly (`current not in chain`). Callers: `_family_record` only at `:251` (in `expand`); `_family_chain` only at `:340` (in `_lock_data`). |
| P2 | `_family_record` validates unused families | **Wrong (the conditional resolves to "no")** | It runs only for an instance's family (`:247-251`). `read_v1` (`:95-108`) checks family keys and types, but not parents or cycles. Probe: adding an unused `{"extends": "nowhere"}` family, or an unused two-family cycle, to `STD_BLUEPRINT` expands with **no error**. |
| P3 | The drop check validates the merged record but always points at the instance | **Correct, and broader than stated** | `:269-276` always raises with `f"{ibase}/properties/drops"`. Probe results: a direct family default gives `/regions/act-1~1cave-2/enemies/0/properties/drops`; an ancestor default reached through `deep-beetle` gives `/regions/act-1~1cave-3/enemies/0/properties/drops`; a family named `a/b~c` gives the instance pointer. Each names an instance `properties` member that does not exist. |
| P4 | (not in handoff) the drop check is crash-free | **Wrong: a raw crash** | `drops: [{"a": 1}]` raises `TypeError: unhashable type: 'dict'` from `drop not in items` (`:272`). `check_errors` catches only `BlueprintError` (`:419-423`), so `vefr check` would print a traceback. The hardening suite's stated rule is "never a raw crash" (`tests/test_blueprint_hardening.py:1`). |
| P5 | A valid override replaces an invalid inherited drop | **Correct (current semantics)** | Probe: family `drops: ["nope"]`, every instance overriding with `["shell"]`: no error. The check runs on the merged record only. |
| P6 | "Include the offending list element where the convention supports it" | **The convention is the list, not the element** | The conformance fixture `tests/fixtures/blueprint/v1/invalid/unknown-drops-item/expected-error.txt:2` pins `/regions/act-1~1cave-2/enemies/0/properties/drops`. The message already names the item (`unknown item 'no-such-item' in drops`). Decision: keep list-level pointers, so the pinned fixture is unchanged. |
| P7 | 508 → 277 (45 family + 232 instance) | **Reproduced; method stated** | `count.py` on Cottage `f02cd07`: `families=10 defaults=39 extends=6 family_values=45`; `instances=69 top-level(id/family/at)=207 property_values=25 instance_values=232`; `total 277`; legacy `508`. |
| P8 | 258 (49 family + 209 instance) from the candidate taxonomy | **Reproduced** | Candidate built by `make_candidate.py`: `families=12 defaults=41 extends=8 family_values=49`; `property_values=2 instance_values=209`; `total 258`. |
| P9 | Drops: 9/9 fat cellar rats, 12/12 deep shades, 2/2 hollow shades, 1/7 cellar rats | **Correct** | Per-family property census: `fat-cellar-rat 9 → {"drops":["cloudy-potion"]}: 9`; `deep-shade 12 → 12`; `hollow-shade 2 → 2`; `cellar-rat 7 → drops 1, {} 6`; `damp-shade 9 → {"drops":["brass-ring"]}: 1, {} 8`. Those 25 property values are the only ones in the file. |
| P10 | Moths: HP 3 on floors 1-3, HP 4 on floors 4-6, same name/sprite/atk/xp | **Correct** | `nest-of-moths-3hp`: 6 instances (floor-1 1, floor-2 3, floor-3 2). `nest-of-moths`: 8 instances (floor-4 2, floor-5 3, floor-6 3). The 3hp family's only default is `hp: 3`, and it `extends: nest-of-moths`. |
| P11 | Keep `nest-of-moths-3hp` | **Correct, and also the cheaper option** | Folding it into 6 instance `hp` overrides removes 2 family values (`hp`, `extends`) and adds 6 instance values: net +4. |
| P12 | 207 instance values are explicit decisions (69 ids, 69 families, 69 positions) | **Correct** | `top-level(id/family/at)=207`. |
| P13 | Trial ref is PR #68, branch `feat/blueprint-creatures` | **Stale** | Merged to Cottage main as `a999c5b`; main is now `f02cd07`. Equivalence is measured against main. |
| P14 | ADR 0008 and closed key sets are unaffected | **Correct** | ADR 0008 line 31 says each failure has "a plain sentence and a JSON pointer"; it does not say which declaration the pointer names. No key set changes. |
| P15 | Lock / serialized provenance unchanged by the refactor | **Correct if the chain is root-first** | The lock's `families` is root-first (`tests/test_blueprint_out_dir.py:53-54` pins `["beetle", "deep-beetle"]`). Re-normalizing an unchanged Cottage copy reproduces `blueprint.lock.json` and all six `contract.json` byte for byte (fresh cache). |

**Counting method (P7, P8), stated exactly.**
A "value" is one top-level key of an object. A list such as `at` or `drops` counts as one value.

- Family values = keys in each family's `defaults`, plus 1 for each `extends`.
- Instance values = an instance's `id`, `family` and `at`, plus the keys of its `properties`. The `properties` key itself is not counted.
- Legacy values = the top-level keys of each of the 69 committed records in `acts/act-1/floor-*/contract.json` `enemies`. This includes `id` and `at`.
- Not counted: the `"blueprint": 1` marker, region keys, `enemies` keys, and the `families`, `regions` and `defaults` wrappers.

This is a count of authored decisions, not of bytes, lines or JSON tokens.

| Representation | Family | Instance | Total | Reduction from 508 |
|---|---|---|---|---|
| Legacy records | n/a | n/a | 508 | n/a |
| Current Blueprint (Cottage `f02cd07`) | 45 | 232 | 277 | 45.47% |
| Candidate taxonomy (handoff table) | 49 | 209 | 258 | 49.21% |
| Flat alternative (no abstract parents; see §7) | 48 | 209 | 257 | 49.41% |

## 2. Final scope

In scope, VEFR only, all in `src/vefr/blueprint.py`:

1. Replace `_family_record` and `_family_chain` with one private operation, `_resolve_family` (§3). `expand` and `_lock_data` both consume it.
2. Track the winning declaration for each field through the existing merge, and point the unknown-drop error at it (§4).
3. Make a non-string drop element a `BlueprintError` instead of a `TypeError` (P4). It is the same check, and it adds no new rule.
4. **Reject broken unused families** (P2; decided above): validate every family's parent chain once, before the regions, with the existing messages and pointers.
5. Tests first (§5), one guide sentence, one ROADMAP entry, and a narrow records edit after the code merges (§6).

Out of scope, deferred, not built:

- Element-index pointers (P6).
- Memoization or caching of any kind. Resolution walks at most a few families per instance; Cottage has 69 instances and chains of 3 or fewer.
- Any change to `FIELD_ORDER`, the key sets, `NORMALIZER_VERSION`, the lock shape, `check_errors` sentence templates, the CLI, or ADR 0008.
- `vefr explain`, provenance fields, traits, mixins, multiple inheritance, Format 2, a kernel, or any generic read/validate/resolve/transform interface.
- Any Cottage change in the VEFR PRs. The Cottage cleanup is a separate follow-up (§7).

No `NORMALIZER_VERSION` bump: the version policy (ADR 0008, "bumps whenever the same input could produce different output") concerns output, and valid input produces identical records and lock bytes. Only error pointers change.

## 3. The single resolution operation

Private, module-level, not exported, and not named in ADR 0008's library contract:

```python
def _resolve_family(family: str, families: dict) -> tuple[list[str], dict[str, tuple[object, str]]]:
    """Walk `family`'s parent chain once.

    Returns (chain, fields):
      chain  - family names, root first (the lock's `families` order);
      fields - {field: (value, pointer)} after merging defaults root first,
               a later family replacing an earlier value whole. `pointer` is
               the JSON pointer of the declaration whose value won:
               /families/<escaped family>/defaults/<field>.
    `value` is the source object itself, not a copy: callers deep-copy.
    Unknown parents and cycles raise the existing BlueprintErrors,
    with the same messages and pointers as `_family_record` today.
    """
```

Rules for the implementer:

- **Traversal:** copy the loop in `_family_record` (`:195-216`) exactly. Keep `seen`, the self-cycle check `len(chain) == 1`, the pointer `/families/<esc>`, the longer-cycle pointer `/families`, and the unknown-parent pointer `/families/<esc>/extends`. Then reverse the list so it is root-first.
- **Source tracking mirrors `dict.update`:** for each name in the root-first chain, for each `key, value` in `families[name].get("defaults") or {}`, set `fields[key] = (value, f"/families/{_esc(name)}/defaults/{key}")`. Assigning per key is exactly `dict.update` semantics. A list is replaced whole, never merged, so the winning pointer names the whole list. Field keys come from the closed `FIELD_KEYS`, which have no `~` or `/`. Family names are unrestricted and must go through `_esc` (`:54-56`).
- **In `expand`**, at the same point as today's `_family_record` call (`:251`, so error precedence is unchanged: unknown family, then parent/cycle, then missing `at`, then duplicate id, then drops):
  ```python
  chain, fields = _resolve_family(family, families)
  for key, value in (instance.get("properties") or {}).items():
      fields[key] = (value, f"{ibase}/properties/{key}")
  record = {key: copy.deepcopy(value) for key, (value, _) in fields.items()}
  ```
  `fields` is a fresh dict for each call, so an instance override can never reach another instance. The deep copy keeps the existing "records never share objects" guarantee (`tests/test_blueprint_hardening.py:61-68`).
- **In `_lock_data`:** `"families": _resolve_family(instance.get("family"), families)[0]`. `_lock_data` runs only after `expand` succeeded (`:595` then `:625`), so the call cannot raise. Delete `_family_chain` and `_family_record`.
- No new public names. `vulture` (dead code) must stay clean.

## 4. Diagnostic changes (before / after)

Unknown-drop check, replacing `:269-276`:

```python
drops, where = fields.get("drops", (None, ""))
if isinstance(drops, list):
    for drop in drops:
        if not isinstance(drop, str) or drop not in items:
            raise BlueprintError(f"unknown item {drop!r} in drops", where)
```

| Case (synthetic `STD_BLUEPRINT` pack) | Before (`f88cdd4`, observed) | After |
|---|---|---|
| Direct family default: `beetle.defaults.drops = ["nope"]` | `/regions/act-1~1cave-2/enemies/0/properties/drops` | `/families/beetle/defaults/drops` |
| Ancestor default reached through `deep-beetle` (cave-2 emptied) | `/regions/act-1~1cave-3/enemies/0/properties/drops` | `/families/beetle/defaults/drops` |
| Descendant default overrides the ancestor: `deep-beetle.defaults.drops = ["nope"]` | `/regions/act-1~1cave-3/enemies/0/properties/drops` | `/families/deep-beetle/defaults/drops` |
| Instance `properties.drops = ["no-such-item"]` (conformance fixture) | `/regions/act-1~1cave-2/enemies/0/properties/drops` | unchanged |
| Family `a/b~c` with a bad default drop | instance pointer | `/families/a~1b~0c/defaults/drops` |
| Valid instance override over an invalid inherited drop | no error | no error (unchanged) |
| `drops: [{"a": 1}]` | raw `TypeError` | `BlueprintError("unknown item {'a': 1} in drops")` at the winning pointer |
| `drops` that is not a list | not checked here | unchanged (not checked here) |

User-visible text changes only inside the parentheses of `blueprint: <msg> (<pointer>)` (`:423`, `:597`), and only for inherited bad drops.
Nothing pins those strings (`grep -rn "properties/drops" tests` matches only the conformance fixture above).

## 5. Acceptance tests, written first

Land these in PR A. Mark each test that fails today `@pytest.mark.xfail(strict=True, reason="PR B")`, the repo's frozen-test convention, so that PR A is green. `--runxfail` runs them for real.

New file `tests/test_blueprint_sources.py`. It is not part of the frozen A1-A12 set; its header says so, like `test_blueprint_hardening.py`. It uses `mk.STD_BLUEPRINT`, `mk.build` and `copy.deepcopy`.

| ID | Test name | Asserts | Today |
|---|---|---|---|
| T1 | `test_invalid_family_default_drop_points_at_the_family` | `beetle.defaults.drops=["nope"]` gives `err.pointer == "/families/beetle/defaults/drops"` and `"unknown item" in str(err)` | Fails: instance pointer (P3) |
| T2 | `test_invalid_ancestor_drop_points_at_the_ancestor` | Same default, cave-2 `enemies` emptied (only `deep-beetle` instances use it) gives `/families/beetle/defaults/drops` | Fails |
| T3 | `test_descendant_drop_points_at_the_descendant` | `beetle` drops `["shell"]`, `deep-beetle` drops `["nope"]`, cave-2 emptied, gives `/families/deep-beetle/defaults/drops` | Fails |
| T4 | `test_valid_override_hides_an_invalid_inherited_drop` | `beetle` drops `["nope"]`, every cave-2 instance overrides `drops: ["shell"]`, cave-3 emptied: `expand` succeeds | Passes (pins P5) |
| T5 | `test_family_names_are_escaped_in_the_pointer` | Family `"a/b~c"` with bad drops, used by one cave-3 instance, gives `/families/a~1b~0c/defaults/drops` | Fails |
| T6 | `test_a_non_string_drop_is_a_plain_error` | `beetle.defaults.drops=[{"a": 1}]` raises `BlueprintError` (not `TypeError`) with `/families/beetle/defaults/drops` | Fails (P4) |
| T7 | `test_check_names_the_family_declaration` | `mk.build(tmp_path, blueprint=<T1 source>)`, then `blueprint.check_errors(pack)` has one entry containing `(/families/beetle/defaults/drops)` | Fails |
| T8 | `test_three_level_chain_is_root_first_in_the_lock` | Add `"deeper": {"extends": "deep-beetle", "defaults": {"hp": 5}}` and one cave-3 instance; after `normalized_pack`, that lock record's `families == ["beetle", "deep-beetle", "deeper"]` and the record's `hp == 5` | Passes (guards the refactor) |
| T9 | `test_records_on_disk_follow_the_documented_key_order` | After `normalized_pack(tmp_path)`, every record in both caves' `contract.json`, read with `json.loads` (dicts keep file order), has `list(record) == [k for k in FIELD_ORDER if k in record]`, where `FIELD_ORDER` is written out literally in the test, not imported | Passes on a clean cache; fails under the stale cache found in §0 |
| T10 | `test_resolution_does_not_leak_between_instances_or_runs` | Deep-copy `STD_BLUEPRINT`; `expand` it twice; both results are equal; the source equals its pre-copy; `odd1.hp == 9` while `b1.hp == 3` | Passes (guards against future caching) |
| T11 | `test_an_unused_family_with_an_unknown_parent_is_rejected` | A family used by no instance with `extends: "nowhere"` makes `expand` raise `BlueprintError` ("unknown parent") at `/families/<name>/extends` | Fails: unused families are never checked (P2) |
| T12 | `test_an_unused_family_cycle_is_rejected` | Two unused families that extend each other make `expand` raise `BlueprintError` ("cycle") at `/families` | Fails |
| T13 | `test_cottage_shaped_blueprints_still_pass` | `STD_BLUEPRINT` and every `valid/` conformance case still expand (every family there is used or valid) | Passes (guards the tightening) |

Conformance cases, justified because the pointer is part of each case's recorded contract (`expected-error.txt` line 2) and the corpus is format 1's versioned behavior record:

- `tests/fixtures/blueprint/v1/invalid/inherited-drops-item/`: copy `unknown-drops-item/blueprint.json`, move `"drops": ["no-such-item"]` into family `b`'s `defaults`, and remove the instance's `properties`. `expected-error.txt`: `unknown item` / `/families/b/defaults/drops`. Fails today.
- `tests/fixtures/blueprint/v1/invalid/ancestor-drops-item/`: family `a` with `"drops": ["no-such-item"]`, family `b` `extends: a`, and the instance uses `b`. Expected: `unknown item` / `/families/a/defaults/drops`. Fails today.

- `tests/fixtures/blueprint/v1/invalid/unused-unknown-parent/`: a family `ghost` that extends `nowhere`, used by no instance (the instance uses a valid family). Expected: `unknown parent` / `/families/ghost/extends`. Fails today.
- `tests/fixtures/blueprint/v1/invalid/unused-cycle/`: unused families `x` extends `y` and `y` extends `x`. Expected: `cycle` / `/families`. Fails today.

Conformance cases are parametrized from the directory (`tests/test_blueprint_conformance.py:16-17`). To keep PR A green, add them to an explicit `xfail` set by case name inside that test file, and remove the set in PR B. Do not change the existing `unknown-drops-item` case.

## 6. Architecture records (a narrow edit after PR B merges)

No new manifesto, and no ADR 0008 change.

- `docs/guides/blueprint.md`, after the sentence ending "an unknown `drops` item all fail." (around line 154): add "The error's pointer names the declaration whose value won: a family's `defaults` entry when the value is inherited, or the instance's `properties` entry when it is overridden." Ships in PR B with the code.
- `ROADMAP.md`: one `[x]` line under the Blueprint entry (repo rule: one entry per landed change). Ships in PR B.
- `.project/DECISIONS.md`: one dated entry, "Blueprint stays local; the second-consumer rule" (PR C), which says:
  1. Implemented: family resolution is one private operation in `blueprint.py`, and validation errors name the declaration that supplied the value.
  2. Rule: extract shared machinery only when two actual consumers independently need the same operation and invariants. Two helpers inside one module justify local consolidation only. A local bug fix needs no second consumer.
  3. Subtraction test for a new abstraction: name the duplicated fact or missing invariant; show what it deletes or makes enforceable; count the concepts, configuration and migration it adds; prefer the smallest change that pays. A change that only shortens syntax, or only serves hypothetical consumers, is deferred.
  4. Working boundaries, checked against existing seams:
     - **Definition** is the Blueprint families/defaults and the pack's `world.json` items (exists).
     - **Generator** is `src/vefr/delve.py` `generate_floor` (exists; note that `src/vefr/generator.py` is the storyteller model client, not this).
     - **Runtime** is the engine and player under host authority (exists).
     - **Recipe** has no artifact or seam today: it is a hypothesis.
     - "Theme owns vocabulary; generator owns arrangement" stands unchanged.
  5. Deferred: the kernel / dialect / pack horizon. It is not proven, and Blueprint gives no evidence for it.
- `docs/plans/language-architecture-campaign.md`, under "Kernel and dialects (the longer horizon)" (line 202): one status line pointing to that DECISIONS entry (PR C).

## 7. Cottage taxonomy cleanup: a separate follow-up (Cottage repo)

Proven on an isolated copy. The method:

1. `git archive origin/main worlds/cottage-of-the-breeze` into the scratchpad.
2. `make_candidate.py` rewrites `blueprint.json`.
3. From the VEFR checkout with a fresh `PYTHONPYCACHEPREFIX`: `.venv/bin/vefr normalize --pack <copy> --out <out>`, which returned rc 0.
4. `compare.py`: parsed-JSON equality of every `enemies` list, plus equality of every other contract key.
5. `cmp` of the bytes.
6. `vefr check --pack <out>`.

| Variant | Records equal | Regions differing | `contract.json` bytes | `vefr check` | Lock |
|---|---|---|---|---|---|
| Baseline re-normalize | 69/69 | 0 | 6/6 identical | n/a | byte-identical |
| Candidate (handoff table) | 69/69 | 0 | 6/6 identical | `ok: … geometry, reachability, voices all pass` | `source_sha256` `764bc714…` → `dfc0d3dc…`; 55 of 69 lock records change (chains gain `rat-kind`/`shade-kind`/`rustle`; 23 `overrides: ["drops"]` become `[]`) |
| Flat alternative | 69/69 | 0 | 6/6 identical | ok | changes (not itemized) |

Reparenting check, property by property: each family's resolved defaults were compared before and after (`_family_record` on old vs. candidate):

- `name`, `hp`, `atk`, `xp` and `sprite` are identical for all 10 concrete families.
- The only difference: `drops: ["cloudy-potion"]` now resolves from the defaults of `fat-cellar-rat`, `deep-shade` and `hollow-shade` (via `deep-shade`). This replaces exactly the 23 instance properties removed.
- `cellar-rat` and `damp-shade` **had** to leave their old parents (`fat-cellar-rat`, `deep-shade`). Otherwise they would inherit the drop that 6 of 7 and 8 of 9 of them do not have. That is the real reason for the reparenting.
- The `rustle` reversal (`rustle` becomes the root, `loud-rustle extends rustle`) is count-neutral (14 family values before and after). It changes meaning only.

**The patch.** Two parts:

1. Families. The block becomes (`name` values are kept from the current file and elided here; key order follows the file's style, with `extends` before `defaults`):
   - `nest-of-moths`: unchanged
   - `nest-of-moths-3hp`: unchanged
   - `rat-kind` (new): `{"defaults": {"sprite": "rat", "atk": 1}}`
   - `cellar-rat`: `{"extends": "rat-kind", "defaults": {"name": <unchanged>, "hp": 4, "xp": 2}}`
   - `fat-cellar-rat`: `{"extends": "rat-kind", "defaults": {"name": <unchanged>, "hp": 6, "xp": 3, "drops": ["cloudy-potion"]}}`
   - `rustle`: `{"defaults": {"name": <unchanged>, "sprite": "rustle", "hp": 3, "atk": 1, "xp": 2}}` (no `extends`)
   - `loud-rustle`: `{"extends": "rustle", "defaults": {"name": <unchanged>, "hp": 5, "atk": 2, "xp": 5}}`
   - `howling-rustle`: unchanged (`extends: loud-rustle`)
   - `shade-kind` (new): `{"defaults": {"sprite": "shade"}}`
   - `damp-shade`: `{"extends": "shade-kind", "defaults": {"name": <unchanged>, "hp": 5, "atk": 1, "xp": 3}}`
   - `deep-shade`: `{"extends": "shade-kind", "defaults": {"name": <unchanged>, "hp": 8, "atk": 2, "xp": 8, "drops": ["cloudy-potion"]}}`
   - `hollow-shade`: unchanged (`extends: deep-shade`)
2. Instances: delete `"properties": {"drops": ["cloudy-potion"]}` from all 9 `fat-cellar-rat`, 12 `deep-shade` and 2 `hollow-shade` instances. The script asserts that each one carried exactly that. Keep the one `cellar-rat` drop and the one `damp-shade` `brass-ring` drop.

The exact transform is `make_candidate.py <in> <out> candidate`, which reads the names from the file. The full unified diff (223 changed lines: 162 `-`, 63 `+`) is kept privately at `scratchpad/cottage-taxonomy-candidate.diff`. It contains display names, so it belongs only in the private Cottage PR, never in this public file. Resulting `blueprint.json` sha256: `8aefc030…`. Canonical `source_sha256`: `dfc0d3dc49b2…`.

Cottage PR steps:

1. Apply the transform on a branch.
2. Run `uv run vefr normalize --pack worlds/cottage-of-the-breeze --out worlds/cottage-of-the-breeze` from a VEFR checkout with a clean cache.
3. Expect `git diff --stat` to list only `blueprint.json` and `blueprint.lock.json`. All six `contract.json` must be byte-unchanged.
4. Run `vefr check`.
5. Update the Cottage note that quotes 277.

This works against VEFR `f88cdd4` as it is today. It does not depend on PR B.

**Rylee's call (Q1):** the abstract parents `rat-kind` and `shade-kind` save **zero** values compared with the flat alternative (rats: 11 either way; shades: 17 with `shade-kind` vs 16 flat). They are justified only by meaning ("rats share a sprite and attack"). That is weak under this handoff's own subtraction test. Recommendation: the **flat** variant (257). It moves the repeated drops to their source and fixes the two wrong parent edges, without adding families that have no instances. In the flat variant, `cellar-rat` and `damp-shade` stand alone (they carry their own `sprite` and `atk`), `fat-cellar-rat` and `deep-shade` gain the drop, and the rustle reversal stays.

## 8. Orchestration

**Recommendation: no foreman.** The implementation is about 30 changed lines in one function pair, with ten tests that prove it. A foreman's setup, budget and review cost more than the work.
Use Sonnet as author, integrator and reviewer, with at most one `offload agent -m code` worker for PR B.
I did not run `offload route` (plan-only pass); its verdict is UNVERIFIED.

| PR | Repo | Content | Keep / offload | Who | Acceptance |
|---|---|---|---|---|---|
| #231 (existing) | vefr | Replace the handoff with this refined file (public-safe: counts, family ids, stat structure) | **keep** | Sonnet | `python3 scripts/check_public_surface.py`; docs-only |
| A | vefr | T1-T10 and the two conformance cases, failing ones as strict xfail | **keep** (frozen tests) | Sonnet | `PYTHONPYCACHEPREFIX=$(mktemp -d) PYTHONPATH=src <repo>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_blueprint_*.py` is green; with `--runxfail`, exactly T1, T2, T3, T5, T6, T7 and the two new conformance cases fail, for the stated reason |
| B | vefr | §3 and §4 in `blueprint.py`; remove the xfail markers; guide sentence; ROADMAP line | **offloadable** | 1 × `offload agent -m code` (deepseek-flash), no foreman. Sonnet reviews the diff against §3 line by line. After one failed attempt, Sonnet does it directly. | `PYTHONPYCACHEPREFIX=$(mktemp -d) PYTHONPATH=src <vefr checkout>/.venv/bin/python -m pytest -q --runxfail -p no:cacheprovider tests/test_blueprint_*.py` all pass (or `bash tests/run.sh tests/test_blueprint_sources.py tests/test_blueprint_conformance.py` in the worker's clone); then the full gate: `uv run --group test ruff check src tests scripts`, `uv run --group test pytest -q`, `uv tool run vulture`, `python3 scripts/check_public_surface.py`; then the Cottage regression in the next row |
| B (regression, integrator) | none | Re-normalize a scratch copy of Cottage `origin/main` with the PR B code | **keep** | Sonnet | All 6 `contract.json` and `blueprint.lock.json` byte-identical to committed (`cmp`) |
| C | vefr | §6 DECISIONS entry and campaign status line | **keep** (architecture records) | Sonnet, after B merges | `python3 scripts/check_public_surface.py`; docs-lint warn-only |
| D | cottage-of-the-breeze (private) | §7 cleanup, variant per Q1 | **keep** (owner content) | Sonnet; Rylee reviews | §7 steps: only `blueprint.json` and `blueprint.lock.json` change; `vefr check` passes |

The PR B worker must not touch:

- `tests/` or `tests/fixtures/`, except deleting the xfail markers and the conformance xfail set
- `FIELD_ORDER`, the five key sets, `NORMALIZER_VERSION`, `READERS`
- the `_lock_data` output keys and the `check_errors`, `normalize` and CLI message templates
- ADR 0008, any other module, any Cottage path

It must add no cache, no public name and no element-index pointer.

Risks:

1. The stale-bytecode trap (§0) gives false greens or false reds in the shared checkout. Always set a fresh pycache prefix, or use a throwaway clone.
2. A worker "fixes" a frozen test. Review the diff of `tests/` first: it must show only marker removals. A foreman that stops on a test is presumed right (DECISIONS 2026-10-02), and the test gets checked.
3. Moving the resolution call changes error precedence for sources with several faults. §3 pins the position.
4. Dropping a deep copy shares objects between records. The existing hardening test and T10 guard this.
5. The `/var/home` path fails on the VM.

PRs merge only on green CI (the full check list).

## 9. What Rylee must decide (all answered; see Decisions at the top)

- **Q1 (changes the Cottage PR).** Taxonomy: **(a) flat variant, 257 values, no abstract families (recommended)**; (b) the handoff's candidate with `rat-kind`/`shade-kind`, 258; (c) leave the Cottage Blueprint as it is.
- **Q2 (changes VEFR behavior).** Unused families with an unknown parent or a cycle pass today (P2). Options: **(a) leave them unchecked and note it in the guide's error paragraph (recommended: out of scope, and no pack is harmed today)**; (b) reject them in `read_v1`, with a new conformance case. That is a tightening that can refuse a currently-valid pack.

Everything else above is decided, with reasons. No other owner gate applies: no deploy, no secrets, no force-push.
