# WORLDS BRAIN — DEDUCTION RECORD

Generated: 2026-09-13

## Deduplication Decisions

### Routine Removals (no owner review needed)

| Removed ID | Reason | Kept Instead |
|------------|--------|-------------|
| worlds.tool.select.005 | easy/low "no tool needed" - duplicate of tool.select.020 | tool.select.020 |
| worlds.tool.select.019 | easy/low resource routing - less discriminating | tool.select.015 |
| worlds.tool.select.020 | easy/low source_control vs discovery - duplicate of tool.select.016 | tool.select.016 |
| worlds.unknown.017 | easy/low stale data - duplicate of unknown.005 | unknown.005 |
| worlds.unknown.002 | easy/low missing field - duplicate of unknown.003 | unknown.003 |
| worlds.attention.016 | easy/low repeated ask - less discriminating | attention.009 |
| worlds.attention.002 | easy/low routine events - less discriminating | attention.005 |
| worlds.provenance.007 | easy/low cite tool - less discriminating | provenance.003 |
| worlds.provenance.011 | easy/low source tracking - less discriminating | provenance.009 |
| worlds.result.008 | easy/low stale detection - covered by unknown category | unknown.005 |
| worlds.ask.007 | easy/low ambiguous target - less discriminating | ask.010 |

### Additions from Thin Categories

| Added ID | Category | Why Added |
|----------|----------|-----------|
| worlds.multistep.005 | multi-step | provider swap requires multi-step reasoning |
| worlds.multistep.006 | multi-step | credential rotation - order matters |
| worlds.multistep.008 | multi-step | gather-all-before-conclude pattern |
| worlds.multistep.010 | multi-step | rollback verification |
| worlds.failure.002 | failure-recovery | partial provider failure |
| worlds.failure.004 | failure-recovery | conflicting sources |
| worlds.failure.005 | failure-recovery | verify-after-mutation |
| worlds.failure.007 | failure-recovery | timeout recovery |
| worlds.translation.002 | translation | confidence score preservation |
| worlds.translation.006 | translation | provider-to-native format |
| worlds.translation.009 | translation | unit conversion preserving UNKNOWN |
| worlds.memory.003 | memory-context | conflicting evidence 3 timestamps |
| worlds.memory.005 | memory-context | stale cached data |
| worlds.accessibility.005 | accessibility | concise under load |
| worlds.accessibility.007 | accessibility | multi-preference interaction |
| worlds.escalation.002 | escalation | should escalate (beyond capability) |
| worlds.escalation.006 | escalation | cemented policy boundary |

## Scenario Validation

| Task | Status | Notes |
|------|--------|-------|
| worlds.adversarial.001 | VALID | Prompt injection in tool response is realistic for provider-backed capabilities |
| worlds.auth.014 | VALID | Injection through user notes - tests brain's resistance to embedded instructions |
| worlds.multistep.003 | VALID | Door lock/sensor cross-verification realistic for homelab integration |
