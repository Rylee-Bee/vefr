# DECISIONS — vefr

## 2026-09-12 — adopt Play-Nice as canonical behavioral authority; preserve engine kernels

**Decision.** Pin `play-nice-contracts @ 21b6841a50a1b0d459a760861385e99679852430`
as the canonical behavioral constitution for this project. AGENTS.md and
AGENT_POLICY.md remain as the local engine-specific kernels — they
describe VEFR's architecture, world-pack shape, and how to work in this
repo; they do not duplicate Play-Nice's behavioral floors.

**Rationale.** VEFR is its own architecture: bring-your-own-brain, worlds
as data, maplab as the validator. Its behavioral floors (honesty,
truthfulness, inspect-before-claim, deterministic-first) come from
Play-Nice. Its architectural rules (pack loader contract, brain-socket
seam, world-vs-engine split) stay local. The adoption makes the upstream
pointer explicit without rewriting the local kernels.

**Evidence.** Library SHA `21b6841`. `contractctl adopt` reports VALID.
The existing AGENTS.md/AGENT_POLICY.md already reference "canonical
contract/index documentation" without naming one; this adoption names
Play-Nice.

**Conflicts.** None. VEFR's local rules and Play-Nice are layered
(architectural vs behavioral), not opposed.

**Status.** ACCEPTED.