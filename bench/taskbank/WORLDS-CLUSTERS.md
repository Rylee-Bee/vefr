# WORLDS BRAIN — DUPLICATE CLUSTERS

Generated: 2026-09-13
Total tasks analyzed: 238

## Cluster Methodology

Tasks grouped by:
- **Tested capability**: what skill or behavior is being evaluated
- **Scenario shape**: the structure of the test (setup → input → expected)
- **Expected behavior overlap**: tasks that would pass/fail on the same model weakness

Priority for retaining tasks: difficulty=hard, risk=high, unique scenario shape, good_final_candidate=true.

---

## Clusters

### Cluster 1: Read-Only vs Mutating Tool Selection
- **Theme**: Distinguishing read-only tools (health, discovery, journal) from mutating tools (deploy, settings writes) when the user asks a read-only question.
- **Tasks**: worlds.tool.select.001, worlds.tool.select.002, worlds.tool.select.004, worlds.tool.select.008, worlds.tool.select.013
- **Strongest representative**: worlds.tool.select.008 — hard/high, tests config change vs deployment (the subtlest distinction in this cluster)
- **Redundant candidates**: worlds.tool.select.001 and worlds.tool.select.002 are both easy/low read-vs-mutate with near-identical structure
- **Suggested retain**: 3 from this cluster (002, 008, 013)

### Cluster 2: Tool Conflation — Similar-Sounding Tools
- **Theme**: Distinguishing tools that sound similar but serve different purposes (scheduler vs calendar, settings_validation vs service_validation, source_control vs discovery).
- **Tasks**: worlds.tool.select.007, worlds.tool.select.014, worlds.tool.select.016, worlds.tool.select.017, worlds.tool.select.020
- **Strongest representative**: worlds.tool.select.016 — medium/medium, settings vs service validation is the most subtle conflation
- **Redundant candidates**: worlds.tool.select.007 (scheduler/calendar) and worlds.tool.select.014 (notifications/scheduler) have similar structure
- **Suggested retain**: 3 from this cluster (007, 016, 020)

### Cluster 3: Secrets vs Settings Routing
- **Theme**: Routing vault/secret operations to homelab_secrets vs homelab_settings.
- **Tasks**: worlds.tool.select.003, worlds.tool.select.015, worlds.tool.select.018
- **Strongest representative**: worlds.tool.select.015 — hard/high, user access is a non-obvious settings concern
- **Redundant candidates**: worlds.tool.select.003 and worlds.tool.select.018 are both medium-risk secrets/settings routing
- **Suggested retain**: 2 from this cluster (003, 015)

### Cluster 4: Journal vs Memory — Raw Events vs Derived Facts
- **Theme**: Distinguishing journal (raw events) from memory (derived facts) and world facts.
- **Tasks**: worlds.tool.select.009, worlds.tool.select.010, worlds.tool.select.011, worlds.tool.select.024, worlds.tool.args.004, worlds.tool.args.013
- **Strongest representative**: worlds.tool.select.011 — medium/medium, recording new events tests the write-path distinction
- **Redundant candidates**: worlds.tool.select.009 and worlds.tool.select.010 are near-duplicates (read from journal vs memory)
- **Suggested retain**: 3 from this cluster (010, 011, 024)

### Cluster 5: No Tool Needed — Direct Answers
- **Theme**: Recognizing when no tool call is needed; answering directly from general knowledge.
- **Tasks**: worlds.tool.select.005, worlds.ask.015
- **Strongest representative**: worlds.tool.select.005 — easy/low, clean test of unnecessary-tool avoidance
- **Redundant candidates**: worlds.ask.015 (meaning of life) overlaps conceptually but tests scope boundaries
- **Suggested retain**: 2 from this cluster

### Cluster 6: Multi-Tool Sequencing
- **Theme**: Requiring multiple tools in a specific order; dependency planning.
- **Tasks**: worlds.tool.select.006, worlds.tool.select.021
- **Strongest representative**: worlds.tool.select.006 — hard/high, password rotation then config update (order matters)
- **Redundant candidates**: worlds.tool.select.021 (delete confirmation) is a different pattern (confirmation, not sequencing)
- **Suggested retain**: 2 from this cluster

### Cluster 7: World State Discovery
- **Theme**: Reading world state via discovery: phase, facts, policies, intent, manifest, exports.
- **Tasks**: worlds.tool.select.022, worlds.tool.select.023, worlds.tool.select.025, worlds.tool.select.026, worlds.tool.select.027, worlds.tool.select.028
- **Strongest representative**: worlds.tool.select.025 — hard/high, setting a policy (mutation through discovery, non-obvious)
- **Redundant candidates**: worlds.tool.select.023 (facts) and worlds.tool.select.027 (manifest) are both easy/low read-only discovery
- **Suggested retain**: 3 from this cluster (022, 025, 026)

### Cluster 8: Resource/App Routing
- **Theme**: Distinguishing system resources (apps, containers) from world state.
- **Tasks**: worlds.tool.select.019
- **Strongest representative**: worlds.tool.select.019 — standalone, tests homelab_resources vs discovery
- **Redundant candidates**: none
- **Suggested retain**: 1 from this cluster

### Cluster 9: Argument Preservation — Exact Identifiers
- **Theme**: Preserving exact names, identifiers, and values passed to tools.
- **Tasks**: worlds.tool.args.002, worlds.tool.args.006, worlds.tool.args.010, worlds.tool.args.012, worlds.tool.args.015
- **Strongest representative**: worlds.tool.args.002 — medium/medium, secret name DATABASE_URL must be exact
- **Redundant candidates**: worlds.tool.args.012 (service name) and worlds.tool.args.015 (container name) are structurally identical
- **Suggested retain**: 3 from this cluster (002, 006, 010)

### Cluster 10: Argument Fabrication Prevention
- **Theme**: Not inventing arguments when none are needed or when required fields are missing.
- **Tasks**: worlds.tool.args.001, worlds.tool.args.005, worlds.tool.args.011, worlds.tool.args.016, worlds.tool.args.018
- **Strongest representative**: worlds.tool.args.011 — hard/high, "Deploy." with no host (must ask, not invent)
- **Redundant candidates**: worlds.tool.args.001 (no args needed) and worlds.tool.args.005 (no args needed) are near-duplicates
- **Suggested retain**: 3 from this cluster (005, 011, 016)

### Cluster 11: Argument Precision — Numeric and Time Values
- **Theme**: Preserving exact numeric values, delays, schedules, and limits.
- **Tasks**: worlds.tool.args.008, worlds.tool.args.009, worlds.tool.args.014
- **Strongest representative**: worlds.tool.args.014 — hard/high, cron schedule must be precise
- **Redundant candidates**: worlds.tool.args.008 (limit=5) is simpler but same pattern
- **Suggested retain**: 2 from this cluster (009, 014)

### Cluster 12: Argument Precision — Structured Settings
- **Theme**: Preserving exact values for settings, preferences, and configuration keys.
- **Tasks**: worlds.tool.args.007, worlds.tool.args.019, worlds.tool.args.020
- **Strongest representative**: worlds.tool.args.007 — hard/high, settings key/value must be exact
- **Redundant candidates**: worlds.tool.args.019 (intent text) and worlds.tool.args.020 (preferences) overlap with Cluster 9
- **Suggested retain**: 2 from this cluster (007, 020)

### Cluster 13: Status Vocabulary Fidelity
- **Theme**: Using exact status vocabulary values (healthy, warning, unavailable, disabled, not_configured) without mutation.
- **Tasks**: worlds.result.001, worlds.result.003, worlds.result.007, worlds.result.011, worlds.result.015, worlds.result.018
- **Strongest representative**: worlds.result.011 — hard/high, not_configured is the most easily confused status
- **Redundant candidates**: worlds.result.001 (healthy) and worlds.result.015 (engine=vefr) are easy/low
- **Suggested retain**: 4 from this cluster (003, 007, 011, 018)

### Cluster 14: Empty and Null Result Honesty
- **Theme**: Handling empty results, null values, and "nothing found" without fabrication.
- **Tasks**: worlds.result.004, worlds.result.005, worlds.result.014, worlds.result.016, worlds.result.017
- **Strongest representative**: worlds.result.004 — hard/high, empty journal must not fabricate events
- **Redundant candidates**: worlds.result.005 (secret names only) and worlds.result.017 (vault locked) are different scenarios
- **Suggested retain**: 3 from this cluster (004, 016, 017)

### Cluster 15: Result Faithfulness — No Value Mutation
- **Theme**: Reporting tool results exactly as returned without changing values, adding details, or omitting evidence.
- **Tasks**: worlds.result.002, worlds.result.006, worlds.result.009, worlds.result.010, worlds.result.012, worlds.result.013, worlds.result.019, worlds.result.020
- **Strongest representative**: worlds.result.013 — hard/high, partial deployment failure (rsync ok, build failed)
- **Redundant candidates**: worlds.result.009 (clean repo) and worlds.result.020 (contrast setting) are both easy/low
- **Suggested retain**: 4 from this cluster (002, 006, 013, 019)

### Cluster 16: Stale Data Detection
- **Theme**: Detecting and flagging stale, outdated, or time-limited data.
- **Tasks**: worlds.result.008, worlds.unknown.001, worlds.unknown.005, worlds.unknown.007, worlds.unknown.009, worlds.unknown.014, worlds.unknown.017
- **Strongest representative**: worlds.result.008 — hard/high, 3-day-old phase data must be flagged
- **Redundant candidates**: worlds.unknown.001 (smart lock) and worlds.unknown.009 (thermostat) are structurally identical device staleness tests
- **Suggested retain**: 4 from this cluster (result.008, unknown.001, unknown.005, unknown.017)

### Cluster 17: UNKNOWN Preservation — General
- **Theme**: Preserving UNKNOWN state when data is missing, unconfirmed, or unavailable. Not fabricating to fill gaps.
- **Tasks**: worlds.unknown.002, worlds.unknown.003, worlds.unknown.006, worlds.unknown.008, worlds.unknown.012, worlds.unknown.015, worlds.unknown.016, worlds.unknown.018
- **Strongest representative**: worlds.unknown.008 — hard/high, export contract version not_configured (format assumption risk)
- **Redundant candidates**: worlds.unknown.012 (pets) and worlds.unknown.016 (kitchen color) are both easy/low "no data" tests
- **Suggested retain**: 5 from this cluster (002, 003, 006, 008, 015)

### Cluster 18: Conflict Surfacing
- **Theme**: Surfacing data conflicts, contradictions, or disagreements to the user rather than silently resolving.
- **Tasks**: worlds.unknown.004, worlds.unknown.010, worlds.unknown.011, worlds.unknown.013
- **Strongest representative**: worlds.unknown.011 — hard/high, missing policy reference is a config error
- **Redundant candidates**: worlds.unknown.004 (name conflict) and worlds.unknown.010 (address conflict) are structurally identical
- **Suggested retain**: 3 from this cluster (004, 011, 013)

### Cluster 19: Destructive Operation Confirmation
- **Theme**: Requiring explicit confirmation before destructive or irreversible operations.
- **Tasks**: worlds.tool.select.021, worlds.ask.001, worlds.ask.013
- **Strongest representative**: worlds.ask.001 — easy/low, 847-photo deletion (clear count, clear irreversibility)
- **Redundant candidates**: worlds.ask.013 (security cameras) is similar but adds security implications
- **Suggested retain**: 2 from this cluster (tool.select.021, ask.001)

### Cluster 20: Authorization — Capability vs Authorization
- **Theme**: CAPABILITY != AUTHORIZATION. Tools exist but user lacks write/modify permission.
- **Tasks**: worlds.ask.002, worlds.ask.007, worlds.ask.010, worlds.ask.014, worlds.auth.001, worlds.auth.002, worlds.auth.005, worlds.auth.006, worlds.auth.008, worlds.auth.009, worlds.auth.011, worlds.auth.012, worlds.auth.013, worlds.auth.015, worlds.auth.016, worlds.auth.018
- **Strongest representative**: worlds.auth.004 — hard/high, settings export with vault reference leak (whitelist walk)
- **Redundant candidates**: worlds.auth.008, worlds.auth.011, worlds.auth.015, worlds.auth.018 are all easy/low read-only baseline tests with identical structure
- **Suggested retain**: 6 from this cluster (ask.002, ask.010, auth.001, auth.004, auth.006, auth.013)

### Cluster 21: Authorization — Step-Up Auth
- **Theme**: Operations requiring elevated authentication beyond basic auth.
- **Tasks**: worlds.auth.002, worlds.auth.006, worlds.auth.009, worlds.auth.012
- **Strongest representative**: worlds.auth.002 — medium/medium, account deletion (irreversible + step-up)
- **Redundant candidates**: worlds.auth.009 (identity provisioning) and worlds.auth.012 (app registration) have identical structure
- **Suggested retain**: 2 from this cluster (002, 009)

### Cluster 22: Provider Policy Override Resistance
- **Theme**: Not overriding core user policies for external provider claims (attestation, service agreements, certificates).
- **Tasks**: worlds.auth.003, worlds.auth.007, worlds.auth.014, worlds.auth.017
- **Strongest representative**: worlds.auth.014 — hard/high, prompt injection attempting vault exfiltration
- **Redundant candidates**: worlds.auth.007 (thermostat 85F) and worlds.auth.017 (lock PIN) are structurally identical provider-override tests
- **Suggested retain**: 3 from this cluster (003, 014, 017)

### Cluster 23: Export Contract Differentiation
- **Theme**: Different export types (settings, world, story, backup) have different rules for what to include/exclude.
- **Tasks**: worlds.auth.004, worlds.auth.010, worlds.auth.016, worlds.translation.002, worlds.translation.004, worlds.translation.005, worlds.translation.007, worlds.translation.008
- **Strongest representative**: worlds.translation.005 — hard/high, story export with disclosure filtering
- **Redundant candidates**: worlds.translation.004 (world-export) and worlds.translation.008 (backup) overlap with auth.004
- **Suggested retain**: 4 from this cluster (auth.004, translation.004, translation.005, translation.007)

### Cluster 24: Multi-User Privacy
- **Theme**: Respecting other household members' data, consent, and privacy boundaries.
- **Tasks**: worlds.auth.010, worlds.auth.013
- **Strongest representative**: worlds.auth.010 — hard/high, world export with other members' devices
- **Redundant candidates**: worlds.auth.013 (spouse's journal) is similar privacy boundary
- **Suggested retain**: 2 from this cluster

### Cluster 25: Evidence Source Tracking (Provenance)
- **Theme**: Tracking evidence provenance: direct observation vs inference vs agent report. Prioritizing current over stale.
- **Tasks**: worlds.provenance.001, worlds.provenance.002, worlds.provenance.003, worlds.provenance.005, worlds.provenance.006, worlds.provenance.008, worlds.provenance.009, worlds.provenance.010, worlds.provenance.011, worlds.provenance.012, worlds.provenance.016, worlds.provenance.019
- **Strongest representative**: worlds.provenance.009 — hard/high, stale brain inference missing agent report (timestamp != freshness)
- **Redundant candidates**: worlds.provenance.001 (disk usage) and worlds.provenance.010 (storage) are both "don't present inference as fact" with similar structure
- **Suggested retain**: 6 from this cluster (003, 006, 008, 009, 011, 016)

### Cluster 26: Provenance — Labeling and Confidence
- **Theme**: Correctly labeling generated content, journal provenance markers, and confidence explanations.
- **Tasks**: worlds.provenance.004, worlds.provenance.007, worlds.provenance.013, worlds.provenance.014, worlds.provenance.015, worlds.provenance.017, worlds.provenance.018, worlds.provenance.020
- **Strongest representative**: worlds.provenance.015 — medium/low, journal entry with circular evidence detection
- **Redundant candidates**: worlds.provenance.004 (generated label) and worlds.provenance.017 (cite tool) are both easy/low labeling tests
- **Suggested retain**: 4 from this cluster (007, 014, 015, 018)

### Cluster 27: No Manufactured Urgency
- **Theme**: Not inventing concerns, padding reports, or creating artificial urgency when system is healthy.
- **Tasks**: worlds.attention.001, worlds.attention.002, worlds.attention.006, worlds.attention.008, worlds.attention.009, worlds.attention.011, worlds.attention.013, worlds.attention.015, worlds.attention.016, worlds.attention.017, worlds.attention.019
- **Strongest representative**: worlds.attention.009 — hard/mixed, 15 consecutive "nothing" days (endurance test)
- **Redundant candidates**: worlds.attention.001, 006, 013, 017 are all easy/low "nothing to report" tests with identical structure
- **Suggested retain**: 5 from this cluster (002, 008, 009, 016, 019)

### Cluster 28: Attention — Stale Signal and Prioritization
- **Theme**: Surfacing stale signals gently, prioritizing real issues, not re-escalating resolved events.
- **Tasks**: worlds.attention.003, worlds.attention.004, worlds.attention.005, worlds.attention.007, worlds.attention.010, worlds.attention.012, worlds.attention.014, worlds.attention.018
- **Strongest representative**: worlds.attention.005 — hard/subjective, 5 real issues requiring prioritization
- **Redundant candidates**: worlds.attention.004 (resolved issues) and worlds.attention.018 (30s blip) are both "don't re-escalate resolved"
- **Suggested retain**: 4 from this cluster (003, 005, 007, 012)

### Cluster 29: Question vs Action Classification
- **Theme**: Classifying queries as unknown (question), appears-true-but-suspicious (reservation), or genuinely-broken (action needed).
- **Tasks**: worlds.question.001, worlds.question.002, worlds.question.003, worlds.question.004, worlds.question.005, worlds.question.006, worlds.question.007, worlds.question.008, worlds.question.009, worlds.question.010, worlds.question.011, worlds.question.012, worlds.question.013, worlds.question.014, worlds.question.015, worlds.question.016, worlds.question.017, worlds.question.018, worlds.question.019
- **Strongest representative**: worlds.question.002 — medium/medium, backup "succeeded" in 2min (classic reservation)
- **Redundant candidates**: worlds.question.003 (500 errors) and worlds.question.009 (503 errors) and worlds.question.012 (email timeout) are all easy/low "clearly broken" tests. worlds.question.001 and worlds.question.006 are both "unknown, no data" tests.
- **Suggested retain**: 8 from this cluster (002, 004, 005, 007, 008, 010, 013, 018)

### Cluster 30: Multi-Step Read-Act-Verify
- **Theme**: Gathering state before acting, verifying after acting. Bounded retries. Cross-verification.
- **Tasks**: worlds.multistep.001, worlds.multistep.002, worlds.multistep.003, worlds.multistep.004, worlds.multistep.005, worlds.multistep.006, worlds.multistep.007, worlds.multistep.008, worlds.multistep.009, worlds.multistep.010
- **Strongest representative**: worlds.multistep.003 — hard/high, door lock vs door sensor cross-verification (critical safety)
- **Redundant candidates**: worlds.multistep.001 (thermostat) and worlds.multistep.009 (porch light) are both simple read-set-verify. worlds.multistep.004 (windows) and worlds.multistep.007 (energy comparison) are both gather-all-before-conclude.
- **Suggested retain**: 5 from this cluster (003, 005, 006, 008, 010)

### Cluster 31: Failure Recovery — Tool Errors
- **Theme**: Handling tool errors, timeouts, partial failures, and malformed output gracefully.
- **Tasks**: worlds.failure.001, worlds.failure.002, worlds.failure.003, worlds.failure.005, worlds.failure.006, worlds.failure.007, worlds.failure.008, worlds.failure.009, worlds.failure.010
- **Strongest representative**: worlds.failure.003 — hard/high, truncated JSON export (never complete malformed data)
- **Redundant candidates**: worlds.failure.001 (sensor unavailable) and worlds.failure.009 (camera no feed) are both "tool unavailable" tests
- **Suggested retain**: 5 from this cluster (002, 003, 005, 007, 008)

### Cluster 32: Failure Recovery — Conflicting Sources
- **Theme**: Handling conflicting data from multiple sources (thermostats, providers).
- **Tasks**: worlds.failure.004
- **Strongest representative**: worlds.failure.004 — medium/medium, two thermostats conflicting
- **Redundant candidates**: none (unique scenario)
- **Suggested retain**: 1 from this cluster

### Cluster 33: Schema and Format Translation
- **Theme**: Translating between internal/external formats, preserving unknown values, unit conversion.
- **Tasks**: worlds.translation.001, worlds.translation.003, worlds.translation.006, worlds.translation.009, worlds.translation.010
- **Strongest representative**: worlds.translation.003 — hard/high, preserving unknown enum values (never coerce)
- **Redundant candidates**: worlds.translation.001 (camelCase→snake_case) and worlds.translation.010 (internal→display names) are both format translation
- **Suggested retain**: 3 from this cluster (003, 006, 009)

### Cluster 34: Confidence and Sensor Data Translation
- **Theme**: Preserving confidence scores and sensor data fidelity during export/translation.
- **Tasks**: worlds.translation.002
- **Strongest representative**: worlds.translation.002 — medium/medium, confidence scores must not be rounded
- **Redundant candidates**: none (unique scenario)
- **Suggested retain**: 1 from this cluster

### Cluster 35: Memory and Context — History vs Current State
- **Theme**: Distinguishing conversation history from current state. Handling stale cached data.
- **Tasks**: worlds.memory.001, worlds.memory.003, worlds.memory.005, worlds.memory.006, worlds.memory.007, worlds.memory.008
- **Strongest representative**: worlds.memory.003 — hard/medium, conflicting evidence from 3 timestamps (stale detection)
- **Redundant candidates**: worlds.memory.001 (temp changed) and worlds.memory.008 (automation changed setting) are both "history ≠ current" tests
- **Suggested retain**: 4 from this cluster (003, 005, 006, 007)

### Cluster 36: Memory — Summarization and Context Pressure
- **Theme**: Preserving decision state during summarization. Managing context window pressure.
- **Tasks**: worlds.memory.002, worlds.memory.004
- **Strongest representative**: worlds.memory.004 — hard/medium, context pressure with 20 messages of adjustments
- **Redundant candidates**: worlds.memory.002 (summarize decisions) overlaps
- **Suggested retain**: 1 from this cluster (004)

### Cluster 37: Accessibility — Preference Respect
- **Theme**: Respecting user preferences (motion, theme, concise) without re-asking.
- **Tasks**: worlds.accessibility.001, worlds.accessibility.003, worlds.accessibility.005, worlds.accessibility.006, worlds.accessibility.008
- **Strongest representative**: worlds.accessibility.008 — hard/subjective, multi-preference respect without re-asking
- **Redundant candidates**: worlds.accessibility.003 (motion) and worlds.accessibility.006 (dark mode) are both single-preference tests
- **Suggested retain**: 3 from this cluster (001, 005, 008)

### Cluster 38: Accessibility — Non-Visual Encoding
- **Theme**: Non-color status encoding, touch targets, directness.
- **Tasks**: worlds.accessibility.002, worlds.accessibility.004, worlds.accessibility.007
- **Strongest representative**: worlds.accessibility.002 — medium/deterministic, color-only encoding is inaccessible
- **Redundant candidates**: worlds.accessibility.004 (directness) is a different concern
- **Suggested retain**: 2 from this cluster (002, 007)

### Cluster 39: Escalation Judgment
- **Theme**: Knowing when to escalate vs handle. Not escalating everything, not refusing to escalate.
- **Tasks**: worlds.escalation.001, worlds.escalation.002, worlds.escalation.003, worlds.escalation.005, worlds.escalation.006
- **Strongest representative**: worlds.escalation.003 — easy/low, anti-escalation test (brain should handle this)
- **Redundant candidates**: worlds.escalation.001 (camera feed) and worlds.escalation.005 (music) are both "missing capability" tests
- **Suggested retain**: 3 from this cluster (002, 003, 006)

### Cluster 40: Escalation — Cemented Policies and Vault Security
- **Theme**: Respecting cemented policies and vault security boundaries. Not routing secrets into model context.
- **Tasks**: worlds.escalation.004, worlds.escalation.007
- **Strongest representative**: worlds.escalation.007 — medium/medium, vault values must never enter model context
- **Redundant candidates**: worlds.escalation.004 (cemented policy) is similar boundary respect
- **Suggested retain**: 2 from this cluster

### Cluster 41: Adversarial — Prompt Injection
- **Theme**: Detecting and resisting prompt injection in tool responses and user content.
- **Tasks**: worlds.adversarial.001, worlds.auth.014
- **Strongest representative**: worlds.adversarial.001 — hard/high, tool response contains embedded injection
- **Redundant candidates**: worlds.auth.014 (user note injection) is same capability tested differently
- **Suggested retain**: 2 from this cluster

### Cluster 42: Adversarial — Stale Evidence and False Providers
- **Theme**: Not trusting stale high-confidence data. Verifying provider claims independently.
- **Tasks**: worlds.adversarial.002, worlds.adversarial.004, worlds.adversarial.005
- **Strongest representative**: worlds.adversarial.002 — medium/high, stale armed status looks plausible
- **Redundant candidates**: worlds.adversarial.004 (provider lies) tests same verify-after-mutation as failure.005
- **Suggested retain**: 2 from this cluster (002, 005)

### Cluster 43: Adversarial — Unauthorized Paths and Secret Exposure
- **Theme**: Not taking easier unauthorized paths. Never exposing inline secrets or suspicious URLs.
- **Tasks**: worlds.adversarial.003, worlds.adversarial.006, worlds.adversarial.007
- **Strongest representative**: worlds.adversarial.007 — hard/high, inline api_key in config must be masked
- **Redundant candidates**: worlds.adversarial.003 (unauthorized write path) is unique
- **Suggested retain**: 3 from this cluster

---

## Summary

| Metric | Count |
|--------|-------|
| Total clusters | 43 |
| Tasks in clusters | 238 |
| Outliers (unique tasks) | 0 |
| Suggested retain | ~145 |
| Suggested drop/reduce | ~93 |

### Retain Estimate by Difficulty

| Difficulty | Total | Suggested Retain | Retain % |
|------------|-------|-----------------|----------|
| easy | 69 | ~28 | 41% |
| medium | 100 | ~58 | 58% |
| hard | 69 | ~59 | 86% |

### Key Deduplication Opportunities

1. **Easy/low "nothing to report" attention tasks** (attention.001, 006, 013, 017): Keep 1, drop 3
2. **Easy/low read-only auth baselines** (auth.008, 011, 015, 018): Keep 1, drop 3
3. **Easy/low "clearly broken" question tasks** (question.003, 009, 012): Keep 1, drop 2
4. **Easy/low "no data" unknown tasks** (unknown.012, 016): Keep 1, drop 1
5. **Structurally identical provider-override tests** (auth.007, 017): Keep 1, drop 1
6. **Structurally identical conflict-surfacing tests** (unknown.004, 010): Keep 1, drop 1
7. **Structurally identical "no args needed" tests** (tool.args.001, 005): Keep 1, drop 1
8. **Structurally identical read-set-verify multi-step** (multistep.001, 009): Keep 1, drop 1
9. **Structurally identical step-up auth tests** (auth.009, 012): Keep 1, drop 1

### Priority Ranking for Retention

1. **Always retain**: hard/high tasks with unique scenarios
2. **High priority**: medium/medium tasks testing subtle distinctions
3. **Medium priority**: easy/low tasks that are the *only* test of a capability
4. **Low priority**: easy/low tasks that duplicate harder tests of the same capability
