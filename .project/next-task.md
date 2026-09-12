# Task: Classify Storyteller Packs

**STATUS**: Ready for delegation

**ROUTING REASONING**: Smallest available candidate selected for bounded, deterministic work.

## GOAL

Produce a structured classification of every storyteller pack in the VEFR repository's `storyteller_packs/` directory.

## SUPPLIED INPUT

The worker should enumerate all directories under `storyteller_packs/` in the VEFR repository. For each directory:

1. Read `storyteller.toml`
2. Extract: id, name, version, model, provider, capabilities, tier, license
3. List all files in the pack directory

## OUTPUT SCHEMA

Strict JSON. No extra text outside the JSON object.

```json
{
  "task": "classify_storyteller_packs",
  "packs": [
    {
      "id": "pack-name",
      "name": "Display Name",
      "version": "0.1.0",
      "model": "model-name",
      "provider": "openai-compatible|ollama",
      "capabilities": {
        "text": true,
        "structured_output": false,
        "tools": false,
        "vision": false
      },
      "tier": "STORYTELLER|STRUCTURED|AGENTIC",
      "tier_reason": "derived from capabilities per storyteller.py logic",
      "files": ["file1.md", "file2.toml"],
      "license": {
        "spdx": "Apache-2.0|MIT|unknown",
        "commercial_use": "allowed|no|restricted|unknown",
        "redistribution": "allowed|derivatives-only|no|unknown"
      }
    }
  ],
  "errors": []
}
```

## ALLOWED CLAIMS

- Pack exists (verified by directory presence)
- Field value (verified by reading storyteller.toml)
- Tier (derived from capabilities: tools→AGENTIC, structured_output→STRUCTURED, else→STORYTELLER)
- File existence (verified by filesystem)

## UNKNOWN POLICY

UNKNOWN is valid. Use it when:

- A field is missing from the manifest
- License metadata is empty or "unknown"
- A file's purpose cannot be determined from its name

Do NOT return UNKNOWN for required fields that exist in the manifest.

Escalate ONLY if:
- The unresolved fact is required to complete the task
- Another participant has a reasonable chance of resolving it
- The cost of escalation is justified

## ACCEPTANCE CRITERIA

1. JSON schema validates (exact fields, no extras)
2. All packs in `storyteller_packs/` are represented
3. Each pack has: id, name, version, model, provider, capabilities, tier, files
4. Tier derivation matches the logic in `storyteller.py`:
   - capabilities.tools == true → AGENTIC
   - capabilities.structured_output == true → STRUCTURED
   - else → STORYTELLER
5. License metadata extracted from `[license]` block
6. All file paths are relative to `storyteller_packs/<id>/`
7. `errors[]` documents any packs that could not be fully classified

## VERIFICATION METHOD

Hermes will:

1. Independently enumerate `storyteller_packs/*/storyteller.toml`
2. Parse each TOML file
3. Compare worker output against source manifests
4. Validate JSON schema (exact fields)
5. Verify tier derivation against `storyteller.py` logic
6. Verify every reported file exists on disk
7. Cross-check license metadata against `[license]` blocks
8. Document UNKNOWN where metadata is genuinely absent

## STOP CONDITIONS

Stop and return NEEDS_HELP if:
- storyteller.toml is malformed
- Required fields are missing
- Cannot determine pack id

Stop and return PARTIAL if:
- Some packs succeeded, others failed
- Document which packs failed in errors[]