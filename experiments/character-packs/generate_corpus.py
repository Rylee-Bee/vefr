#!/usr/bin/env python3
"""VEFR Character Pack & World Starter — Experimental Corpus Generator

Generates ~36-42 character packs and ~12-20 world-reference starters
using multiple template transformation families.

Uses Qwen2.5-1.5B through the production Hermod path.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

# Configuration
QWEN_URL = "http://127.0.0.1:8086"
MODEL_ALIAS = "qwen2.5-1.5b"
MAX_TOKENS = 2000
TEMP = 0.3

# Paths
WORK_DIR = Path(__file__).resolve().parent.parent
EXP_DIR = WORK_DIR / "experiments" / "character-packs"
RAW_DIR = EXP_DIR / "raw"
NORM_DIR = EXP_DIR / "normalized"
ACCEPTED_DIR = EXP_DIR / "accepted"
REJECTED_DIR = EXP_DIR / "rejected"
META_DIR = EXP_DIR / "metadata"

# Ensure dirs exist
for d in [RAW_DIR, NORM_DIR, ACCEPTED_DIR, REJECTED_DIR, META_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Transformation families
TRANSFORMATION_FAMILIES = {
    "A_structured": {
        "description": "Structured / factual — concrete facts, relationships, goals, boundaries, capabilities, possessions, locations, history, observable traits",
        "prompt_template": """Generate a VEFR character pack for a character described below.

Use ONLY the following structured format. Output ONLY the JSON object, no markdown.

CHARACTER_ID: {character_id}
SEED: {seed}

{character_brief}

OUTPUT FORMAT:
{{
  "id": "{character_id}",
  "name": "...",
  "role": "...",
  "location": "...",
  "observable_traits": ["..."],
  "capabilities": ["..."],
  "possessions": ["..."],
  "goals": ["..."],
  "boundaries": ["..."],
  "relationships": [
    {{"target": "...", "type": "...", "description": "..."}}
  ],
  "history_notes": ["..."],
  "current_state": "...",
  "facts_they_know": ["..."],
  "beliefs": ["..."],
  "factual_errors": ["..."]
}}

Rules:
- All fields must be present. Use empty arrays if none.
- beliefs: things they believe to be true. May or may not be factual.
- factual_errors: beliefs that are demonstrably wrong about the world.
- current_state: one sentence about what they're doing now.
- Do not make beliefs automatically true. At least one belief should be factually wrong.
- Keep each string under 50 words.""",
    },
    "B_narrative": {
        "description": "Narrative / literary — natural character/world reference for storytelling",
        "prompt_template": """Generate a VEFR character reference for storytelling purposes.

Write this as a prose character reference, not a data sheet. Think of it like a well-written RPG sourcebook entry that a game master could read and immediately use at the table.

CHARACTER_ID: {character_id}
SEED: {seed}

{character_brief}

OUTPUT FORMAT:
{{
  "id": "{character_id}",
  "name": "...",
  "reference": "3-5 paragraphs of literary character description. Capture their voice, mannerisms, what they want, what they fear, how they move through the world. At least one sentence should reveal a belief they hold that is factually incorrect.",
  "voice_notes": "2-3 sentences on how they speak",
  "story_hooks": ["...", "...", "..."]
}}

Rules:
- reference must be prose, not bullet points.
- Include at least one false belief the character holds.
- story_hooks: situations that would naturally pull this character into play.
- Keep total output under 400 words.""",
    },
    "C_behavioral": {
        "description": "Behavioral — how the character behaves under situations",
        "prompt_template": """Generate a VEFR behavioral character pack.

Describe this character primarily through how they behave in different situations, not through adjectives or backstory.

CHARACTER_ID: {character_id}
SEED: {seed}

{character_brief}

OUTPUT FORMAT:
{{
  "id": "{character_id}",
  "name": "...",
  "role": "...",
  "behavior_when_comfortable": "...",
  "behavior_when_frightened": "...",
  "behavior_when_challenged": "...",
  "behavior_when_attracted": "...",
  "behavior_when_angry": "...",
  "behavior_when_hiding_information": "...",
  "behavior_when_dealing_with_authority": "...",
  "behavior_when_helping_someone": "...",
  "behavior_when_betrayed": "...",
  "core_drive": "one sentence",
  "lie_they_tell_themselves": "...",
  "one_thing_they_never_do": "..."
}}

Rules:
- Each behavior field must show specific observable actions, not traits.
- "core_drive" is the single motivation that explains most of their behavior.
- "lie_they_tell_themselves" is a false belief they hold about themselves.
- All fields required. No empty strings.""",
    },
    "D_relationship": {
        "description": "Relationship-centered — characters through relationships, tensions, obligations",
        "prompt_template": """Generate a VEFR relationship-centered character pack.

Describe this character entirely through their relationships with others.

CHARACTER_ID: {character_id}
SEED: {seed}

{character_brief}

OUTPUT FORMAT:
{{
  "id": "{character_id}",
  "name": "...",
  "location": "...",
  "relationships": [
    {{
      "target": "another character name",
      "target_id": "char_xxx",
      "type": "friend|rival|family|romantic|professional|subordinate|superior|stranger|dependent|caretaker",
      "description": "2-3 sentences about this relationship",
      "tensions": ["..."],
      "obligations": ["..."],
      "history": "2-3 sentences of shared history",
      "trust_level": "high|medium|low|none",
      "secret_from_target": "...",
      "what_target_doesnt_know": "..."
    }}
  ],
  "isolated_from": ["names of people they avoid or are estranged from"],
  "social_position": "one sentence — where they stand in the community",
  "relationship_regret": "one sentence about a relationship they wish had gone differently"
}}

Rules:
- Minimum 3 relationships, maximum 6.
- Each relationship must have at least one tension or obligation.
- "what_target_doesnt_know" should be different from "secret_from_target".
- Include at least one relationship with a trust_level that doesn't match the outward description.""",
    },
    "E_sparse": {
        "description": "Sparse / emergent — minimum stable anchors, room for behavior to emerge",
        "prompt_template": """Generate a MINIMAL VEFR character pack.

Provide ONLY the minimum stable anchors required for VEFR. Leave room for behavior to emerge. Do not over-specify.

CHARACTER_ID: {character_id}
SEED: {seed}

{character_brief}

OUTPUT FORMAT:
{{
  "id": "{character_id}",
  "name": "...",
  "role": "...",
  "location": "...",
  "core_drive": "one sentence",
  "known_to_player": ["3-5 facts the player already knows"],
  "hidden_from_player": ["1-3 facts only the engine knows"],
  "entrance_line": "the first thing they say when the player meets them",
  "one_physical_detail": "...",
  "one_habit": "...",
  "unresolved_question": "something about this character that even the engine hasn't decided yet"
}}

Rules:
- Total output under 200 words.
- "unresolved_question" must be something genuinely uncertain, not a hidden fact.
- Do not include backstory. Do not include relationships array.
- The engine will discover the rest through play.""",
    },
    "F_layered": {
        "description": "Layered — separate immutable facts, current state, beliefs, desires, relationships, secrets, behavioral tendencies, hooks",
        "prompt_template": """Generate a VEFR layered character pack.

Separate the character into clearly distinct layers.

CHARACTER_ID: {character_id}
SEED: {seed}

{character_brief}

OUTPUT FORMAT:
{{
  "id": "{character_id}",
  "name": "...",
  "layer_1_immutable_facts": {{
    "birth_date": "...",
    "species": "human",
    "physical_traits": ["..."],
    "unchangeable_history": ["..."]
  }},
  "layer_2_current_state": {{
    "location": "...",
    "emotional_state": "...",
    "immediate_concern": "...",
    "current_activity": "..."
  }},
  "layer_3_beliefs": {{
    "about_self": ["..."],
    "about_world": ["..."],
    "about_others": ["..."],
    "factually_wrong": ["..."]
  }},
  "layer_4_desires": {{
    "immediate": ["..."],
    "long_term": ["..."],
    "secret": ["..."],
    "conflicting": ["describe two desires that conflict"]
  }},
  "layer_5_relationships": [
    {{"target": "...", "type": "...", "feeling_toward": "...", "feeling_assumed_from": "..."}}
  ],
  "layer_6_secrets": {{
    "known_only_to_self": ["..."],
    "shared_with": ["..."],
    "would_destroy_them_if_known": "..."
  }},
  "layer_7_behavioral_tendencies": {{
    "default": "...",
    "under_stress": "...",
    "when_safe": "..."
  }},
  "layer_8_story_hooks": ["...", "..."]
}}

Rules:
- All layers must be present.
- At least 2 beliefs in layer_3 must be factually wrong.
- layer_4 conflicting desires must be genuinely incompatible.
- layer_6 secrets must not appear in layer_5 relationships.""",
    },
    "G_compression": {
        "description": "Transformation / compression — rich source compressed to runtime pack",
        "prompt_template": """Transform the following rich character description into a minimal runtime-oriented VEFR pack.

Measure what important information survives or disappears.

CHARACTER_ID: {character_id}
SEED: {seed}

SOURCE DESCRIPTION:
{source_description}

OUTPUT FORMAT:
{{
  "id": "{character_id}",
  "name": "...",
  "compressed_pack": {{
    "role": "...",
    "location": "...",
    "core_drive": "...",
    "key_relationships": ["3-5 word summary each"],
    "behavioral_markers": ["3-5 word summary each"],
    "must_not_forget": ["..."],
    "hooks": ["..."]
  }},
  "compression_notes": {{
    "what_was_lost": ["..."],
    "what_survived": ["..."],
    "risk_areas": ["information that might be important but was compressed away"]
  }}
}}

Rules:
- compressed_pack must be under 100 words total.
- compression_notes must honestly assess what was lost.
- risk_areas should list anything that might cause problems during play.""",
    },
}

# Character briefs for diversity
CHARACTER_BRIEFS = [
    # Ordinary people
    ("char_01", "A quiet librarian who knows everyone's reading habits and has opinions about what that says about them."),
    ("char_02", "A bus driver who's run the same route for 15 years and has seen the town change."),
    ("char_03", "A night-shift convenience store clerk working through college, perpetually tired but observant."),
    ("char_04", "A retired postwoman who still knows every house on her old route and visits when she shouldn't."),
    ("char_05", "A veterinary technician who's good with animals but awkward with people."),
    # Highly competent professionals
    ("char_06", "A forensic accountant who can smell fraud from three spreadsheets away. Works alone, prefers it."),
    ("char_07", "A trauma surgeon who's saved hundreds of lives but can't save her marriage."),
    ("char_08", "A structural engineer who inspected the bridge that collapsed — she warned them, nobody listened."),
    # Unreliable people
    ("char_09", "A charming grifter who actually believes his own lies half the time."),
    ("char_10", "A journalist who's fabricated sources before and tells herself this time is different."),
    ("char_11", "A self-proclaimed 'fixer' who creates half the problems she solves."),
    # Shy characters
    ("char_12", "A watchmaker who'd rather talk to gears than people. Sees everything, says little."),
    ("char_13", "A cartographer who maps places she's too anxious to visit in person."),
    # Abrasive characters
    ("char_14", "A municipal inspector who takes genuine pleasure in finding violations. Not corrupt, just harsh."),
    ("char_15", "A food critic whose reviews can close restaurants. She thinks she's protecting diners."),
    # Warm characters
    ("char_16", "A retired nurse who feeds every stray cat on the street and knows all their names."),
    ("char_17", "A high school teacher who stays late every day for students who need to talk."),
    # Morally complicated
    ("char_18", "A defense attorney who got a guilty client acquitted. Uses the money for good causes."),
    ("char_19", "A pharmacist who's been diverting opioids to her addicted sister for months."),
    ("char_20", "An environmental activist who sabotaged a construction site — someone was almost killed."),
    # Characters with secrets
    ("char_21", "A small-town banker who's been embezzling to pay for his wife's experimental treatment."),
    ("char_22", "A high school principal who was a gang member 20 years ago. Only one person knows."),
    ("char_23", "A children's book author who writes dark fiction under a pseudonym. Nobody knows it's her."),
    # Factually wrong beliefs
    ("char_24", "A conspiracy theorist who genuinely believes the town water supply is mind-control. (It isn't.)"),
    ("char_25", "A woman convinced her husband is having an affair. He isn't — he's planning a surprise party."),
    ("char_26", "A man who believes he's descended from the town's founder. Genealogy records disprove this."),
    # Characters in conflict
    ("char_27", "Two siblings fighting over their dead mother's house. (Generate the sister — she wants to sell.)"),
    ("char_28", "A shop owner whose landlord is tripling the rent. She thinks it's personal. (It isn't.)"),
    ("char_29", "A union steward and a plant manager who used to be friends. (Generate the steward.)"),
    # Family relationships
    ("char_30", "A single father whose teenage daughter has stopped speaking to him. He doesn't know why."),
    ("char_31", "A grandmother raising grandchildren because her own daughter is absent. She resents it."),
    ("char_32", "A middle child who's become the family mediator while her own life falls apart."),
    # Friendships
    ("char_33", "A woman whose best friend is dying. She's already grieving but her friend doesn't know it yet."),
    ("char_34", "Two old friends who slept together once and never spoke of it. (Generate one.)"),
    # Romantic tension
    ("char_35", "A bartender who's in love with a regular customer who's married to someone else."),
    ("char_36", "A wedding planner who's fallen for the bride. She'll never say anything."),
    # Rivals
    ("char_37", "Two chefs who trained together and now run competing restaurants across the street. (Generate one.)"),
    ("char_38", "A novelist whose former protégé has surpassed her. She's gracious in public, bitter in private."),
    # Authority/subordinate
    ("char_39", "A fire chief who knows her station house is structurally unsafe but can't get funding."),
    ("char_40", "A junior doctor who suspects his attending is making mistakes but needs the reference."),
    # Strangers
    ("char_41", "A traveler passing through town who doesn't plan to stay but keeps finding reasons to."),
    ("char_42", "A new neighbor who's friendly in a way that feels slightly calculated."),
]

# World-reference starter briefs
WORLD_STARTERS = [
    ("world_01", "A small town where the main employer just closed. The diner is the only place still open late."),
    ("world_02", "A dense city neighborhood where everyone knows everyone's business except the truth."),
    ("world_03", "A restaurant kitchen during the dinner rush. Every character has a secret they're keeping from the others."),
    ("world_04", "A road trip that was supposed to be three hours but the GPS sent them somewhere else entirely."),
    ("world_05", "An isolated community that cut itself off from the internet five years ago. Now someone's phone is ringing."),
    ("world_06", "A historical-ish town where everyone's family has lived for 200 years. And they remember everything."),
    ("world_07", "A speculative near future where AI writes most of the news and people have started lying to be interesting."),
    ("world_08", "A fantasy village that has no giant lore dump — just people trying to make rent while dragons circle overhead."),
    ("world_09", "A single-location story: a waiting room where everyone has been waiting for something different."),
    ("world_10", "A socially complicated community where three families have been intermarrying for generations."),
    ("world_11", "A world with incomplete/uncertain information: an expedition journal with pages missing."),
    ("world_12", "A town where the boundary between the living and the dead is described differently by every resident."),
    ("world_13", "A workplace where the employees are convinced the building is haunted. Management insists it isn't."),
    ("world_14", "A neighborhood block party that's been going on for 30 years. Everyone performs happiness."),
]


def call_model(system, user, max_tokens=MAX_TOKENS, temp=TEMP):
    """Call the model through the production path."""
    body = {
        "model": MODEL_ALIAS,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temp,
        "min_p": 0.1,
    }
    t0 = time.time()
    try:
        req = urllib.request.Request(
            f"{QWEN_URL}/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read().decode())
            t1 = time.time()
            content = resp["choices"][0]["message"].get("content", "")
            timings = resp.get("timings", {})
            ttft = timings.get("prompt_ms", 0)
            total_ms = (t1 - t0) * 1000
            return content, ttft, total_ms
    except Exception as e:
        return f"ERROR: {e}", 0, 0


def normalize_output(raw):
    """Normalize raw output: strip markdown fences, extract JSON."""
    if not raw:
        return None, "empty"
    
    # Try direct parse
    try:
        data = json.loads(raw)
        return data, "direct"
    except json.JSONDecodeError:
        pass
    
    # Strip markdown fences
    cleaned = re.sub(r'```(?:json)?\s*\n?', '', raw)
    cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
        return data, "stripped_fences"
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON object
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return data, "extracted"
        except json.JSONDecodeError:
            pass
    
    return None, "failed"


def validate_character_pack(data, family):
    """Validate a character pack. Returns (is_valid, issues_list)."""
    if data is None:
        return False, ["no_json"]
    
    issues = []
    
    # Check for required id field
    if "id" not in data:
        issues.append("missing_id")
    
    # Check for name
    if "name" not in data:
        issues.append("missing_name")
    
    # Family-specific checks
    if family == "A_structured":
        for field in ["observable_traits", "capabilities", "goals", "boundaries", "beliefs"]:
            if field not in data:
                issues.append(f"missing_{field}")
        # Check for factual_errors or false beliefs
        if "factual_errors" in data and len(data.get("factual_errors", [])) == 0:
            issues.append("no_false_beliefs")
    
    elif family == "B_narrative":
        if "reference" not in data:
            issues.append("missing_reference")
        if "story_hooks" not in data:
            issues.append("missing_hooks")
    
    elif family == "C_behavioral":
        for field in ["behavior_when_comfortable", "behavior_when_frightened", "behavior_when_challenged",
                      "behavior_when_attracted", "behavior_when_angry", "behavior_when_hiding_information",
                      "behavior_when_dealing_with_authority", "behavior_when_helping_someone"]:
            if field not in data:
                issues.append(f"missing_{field}")
    
    elif family == "D_relationship":
        if "relationships" not in data:
            issues.append("missing_relationships")
        elif len(data.get("relationships", [])) < 2:
            issues.append("too_few_relationships")
    
    elif family == "E_sparse":
        for field in ["core_drive", "known_to_player", "hidden_from_player", "entrance_line", "unresolved_question"]:
            if field not in data:
                issues.append(f"missing_{field}")
    
    elif family == "F_layered":
        for layer in ["layer_1_immutable_facts", "layer_2_current_state", "layer_3_beliefs", 
                      "layer_4_desires", "layer_5_relationships", "layer_6_secrets", 
                      "layer_7_behavioral_tendencies", "layer_8_story_hooks"]:
            if layer not in data:
                issues.append(f"missing_{layer}")
    
    elif family == "G_compression":
        if "compressed_pack" not in data:
            issues.append("missing_compressed_pack")
        if "compression_notes" not in data:
            issues.append("missing_compression_notes")
    
    # Check world-truth vs character-belief leakage
    # (rough heuristic: if beliefs array exists, at least one should sound like a belief not a fact)
    if "beliefs" in data and isinstance(data["beliefs"], list):
        for b in data["beliefs"]:
            if isinstance(b, str) and len(b) < 10:
                issues.append("suspicious_belief_format")
    
    is_valid = len([i for i in issues if i.startswith("missing_")]) == 0
    return is_valid, issues


def generate_character_pack(character_id, seed, brief, family, template):
    """Generate a single character pack."""
    prompt = template.format(
        character_id=character_id,
        seed=seed,
        character_brief=brief,
        source_description=brief,  # For compression family
    )
    
    system = "You are a character pack generator for the VEFR storytelling engine. Output ONLY the requested JSON object, no markdown fences, no extra prose."
    user = prompt
    
    return call_model(system, user)


def generate_world_starter(world_id, brief):
    """Generate a world-reference starter."""
    prompt = f"""Generate a VEFR world-reference starter for the following world concept.

Output ONLY the JSON object, no markdown.

WORLD_ID: {world_id}

{brief}

OUTPUT FORMAT:
{{
  "id": "{world_id}",
  "name": "...",
  "logbok_md": "2-3 paragraphs establishing the world's tone, rules, and what kind of story lives here",
  "ledger_md": "3-5 voice anchors — short lines that capture the world's mood",
  "phases": {{"phase_1": "name and tone description", "phase_2": "name and tone description"}},
  "surface": "combat|investigation|plain",
  "town_description": "2-3 paragraphs describing the central location",
  "three_notable_places": ["...", "...", "..."],
  "entry_hook": "one sentence that draws the player in"
}}

Rules:
- phases should have exactly 2 phases (beginning and end of journey)
- logbok_md should be prose, not bullet points
- surface should match the world's actual tone (not every world is combat)
- entry_hook must be a single sentence"""
    
    system = "You are a world starter generator for the VEFR storytelling engine. Output ONLY the requested JSON object."
    user = prompt
    
    return call_model(system, user)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="VEFR Experimental Corpus Generator")
    parser.add_argument("--quick", action="store_true", help="Quick mode: fewer generations")
    parser.add_argument("--family", help="Only run this transformation family")
    parser.add_argument("--worlds-only", action="store_true", help="Only generate world starters")
    parser.add_argument("--chars-only", action="store_true", help="Only generate character packs")
    args = parser.parse_args()
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    # Determine which families to run
    families = list(TRANSFORMATION_FAMILIES.keys())
    if args.family:
        families = [args.family]
    
    # Determine character set
    briefs = CHARACTER_BRIEFS
    if args.quick:
        briefs = CHARACTER_BRIEFS[:6]
    
    print("=" * 60)
    print("VEFR Experimental Corpus Generator")
    print(f"Families: {', '.join(families)}")
    print(f"Characters: {len(briefs)}")
    print(f"World starters: {len(WORLD_STARTERS)}")
    print("=" * 60)
    
    all_results = []
    metrics = {fam: {"total": 0, "schema_ok": 0, "normalized": 0, "retries": 0, "failures": 0} for fam in families}
    
    # Generate character packs
    if not args.worlds_only:
        for family in families:
            family_info = TRANSFORMATION_FAMILIES[family]
            print(f"\n{'='*60}")
            print(f"Family: {family} — {family_info['description']}")
            print(f"{'='*60}")
            
            for char_id, brief in briefs:
                metrics[family]["total"] += 1
                seed = f"{family}_{char_id}_{timestamp}"
                
                print(f"  Generating {char_id} ({family})...", end=" ", flush=True)
                
                # Generate
                raw, ttft, total_ms = generate_character_pack(
                    char_id, seed, brief, family, family_info["prompt_template"]
                )
                
                # Normalize
                data, norm_method = normalize_output(raw)
                
                # Validate
                is_valid, issues = validate_character_pack(data, family)
                
                # Save raw
                raw_path = RAW_DIR / f"{family}_{char_id}.json"
                raw_path.write_text(json.dumps({
                    "character_id": char_id,
                    "family": family,
                    "seed": seed,
                    "raw": raw,
                    "generated_at": timestamp,
                }, indent=2))
                
                # Save normalized
                if data:
                    norm_path = NORM_DIR / f"{family}_{char_id}.json"
                    norm_path.write_text(json.dumps(data, indent=2))
                
                # Track metrics
                if norm_method in ["stripped_fences", "extracted"]:
                    metrics[family]["normalized"] += 1
                if is_valid:
                    metrics[family]["schema_ok"]  += 1
                    # Copy to accepted
                    if data:
                        accept_path = ACCEPTED_DIR / f"{family}_{char_id}.json"
                        accept_path.write_text(json.dumps(data, indent=2))
                else:
                    reject_path = REJECTED_DIR / f"{family}_{char_id}.json"
                    reject_path.write_text(json.dumps({
                        "data": data,
                        "issues": issues,
                        "raw_excerpt": raw[:500] if raw else "",
                    }, indent=2))
                
                status = "PASS" if is_valid else "FAIL"
                print(f"{status} (norm: {norm_method}, issues: {len(issues)}, {total_ms:.0f}ms)")
                
                all_results.append({
                    "type": "character",
                    "id": char_id,
                    "family": family,
                    "valid": is_valid,
                    "normalization": norm_method,
                    "issues": issues,
                    "ttft_ms": round(ttft),
                    "total_ms": round(total_ms),
                })
    
    # Generate world starters
    if not args.chars_only:
        print(f"\n{'='*60}")
        print("World Starters")
        print(f"{'='*60}")
        
        world_metrics = {"total": 0, "schema_ok": 0, "failures": 0}
        
        for world_id, brief in WORLD_STARTERS:
            world_metrics["total"] += 1
            seed = f"world_{world_id}_{timestamp}"
            
            print(f"  Generating {world_id}...", end=" ", flush=True)
            
            raw, ttft, total_ms = generate_world_starter(world_id, brief)
            data, norm_method = normalize_output(raw)
            
            issues = []
            if data is None:
                issues.append("no_json")
            else:
                for field in ["id", "name", "logbok_md", "ledger_md", "phases", "surface", "town_description"]:
                    if field not in data:
                        issues.append(f"missing_{field}")
            
            is_valid = len([i for i in issues if i.startswith("missing_")]) == 0
            
            # Save
            raw_path = RAW_DIR / f"world_{world_id}.json"
            raw_path.write_text(json.dumps({"id": world_id, "raw": raw, "generated_at": timestamp}, indent=2))
            
            if data:
                norm_path = NORM_DIR / f"world_{world_id}.json"
                norm_path.write_text(json.dumps(data, indent=2))
            
            if is_valid:
                world_metrics["schema_ok"] += 1
                accept_path = ACCEPTED_DIR / f"world_{world_id}.json"
                accept_path.write_text(json.dumps(data, indent=2))
            else:
                world_metrics["failures"] += 1
            
            status = "PASS" if is_valid else "FAIL"
            print(f"{status} (norm: {norm_method}, {total_ms:.0f}ms)")
            
            all_results.append({
                "type": "world",
                "id": world_id,
                "family": "world",
                "valid": is_valid,
                "normalization": norm_method,
                "issues": issues,
                "ttft_ms": round(ttft),
                "total_ms": round(total_ms),
            })
        
        metrics["worlds"] = world_metrics
    
    # Save metadata
    meta = {
        "generated_at": timestamp,
        "model": "Granite 4.1 3B Q4_K_M",
        "model_alias": MODEL_ALIAS,
        "total_generations": len(all_results),
        "metrics_by_family": metrics,
        "all_results": all_results,
    }
    meta_path = META_DIR / f"corpus_run_{timestamp}.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    
    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total generations: {len(all_results)}")
    
    for fam, m in metrics.items():
        if isinstance(m, dict) and "total" in m:
            rate = m["schema_ok"] / m["total"] * 100 if m["total"] > 0 else 0
            print(f"  {fam:<25} {m['schema_ok']}/{m['total']} valid ({rate:.0f}%)")
    
    print(f"\nRaw outputs: {RAW_DIR}")
    print(f"Normalized: {NORM_DIR}")
    print(f"Accepted: {ACCEPTED_DIR}")
    print(f"Rejected: {REJECTED_DIR}")
    print(f"Metadata: {meta_path}")


if __name__ == "__main__":
    main()