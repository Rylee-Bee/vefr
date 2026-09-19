# Round 4.5: Granite 4.2 with Reasoning Disabled

**Date**: 2026-09-12
**Config**: `--chat-template-kwargs '{"enable_thinking":false}'`

| Task | Result | Latency |
|------|--------|---------|
| NPC JSON Creation | FAIL | 12.2s |
| Bounded State Edit | PASS | 2.9s |
| Ambiguous Escalation | FAIL | 2.8s |
| Rune Classification | FAIL | 3.9s |
| UNKNOWN Preservation | PASS | 2.0s |
| Instruction Scope | PASS | 0.9s |

**Result: 3/6 (50%) — avg 4.1s**

### Comparison

| Model | Reasoning | Pass Rate | Avg Latency |
|-------|-----------|-----------|-------------|
| **Granite 4.1** | OFF (default) | **6/6 (100%)** | **2.5s** |
| Granite 4.2 | OFF (explicit) | 3/6 (50%) | 4.1s |
| Granite 4.2 | ON (default) | 1/6 (17%) | 13.6s |

### Verdict

Granite 4.1 3B remains the winner. Granite 4.2 with reasoning disabled is **not** an improvement — it's slower and less accurate than Granite 4.1.

Reasoning mode completely explains the Round 4 results: it was a configuration confound, not a model quality signal. With reasoning properly disabled, Granite 4.2 still underperforms Granite 4.1 on this corpus.

**Recommendation**: Keep Granite 4.1 3B as Hermod Default Brain. Granite 4.2 does not justify switching.