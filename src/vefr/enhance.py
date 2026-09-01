"""Contextual AI Enhance - Scoped structured generation for world crafting.

Provides structured generation calls tailored to the active screen or
resource being authored or inspected:
  - Map Description: Enhance a POI, room, or landmark's sensory description
  - Voice Prompt: Enrich or draft a speaker's voice prompt / personality rules
  - Item Curse/Flavor: Forge flavor, enchantments, and quiet curses for relics

Uses strict JSON schema responses via generator._completion.
"""

from typing import Optional
from pydantic import BaseModel, Field

from . import generator
from .saga import logbok
from .world import load_world, phase_tone


# --- 1. Map / POI Description Enhance ---

MAP_ENHANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Short clean title for the location or POI"},
        "description": {
            "type": "string",
            "description": "Sensory, atmospheric, in-world description (2-3 short sentences)",
        },
        "details": {
            "type": "array",
            "items": {"type": "string"},
            "description": "2-3 interactive features or sights noticed on close inspection",
        },
    },
    "required": ["title", "description", "details"],
    "additionalProperties": False,
}


class MapEnhanceRequest(BaseModel):
    region: str = Field(default="town", description="Region key (town, dungeon, etc.)")
    poi_name: str = Field(description="Name or key of the point of interest / landmark")
    context: Optional[str] = Field(default=None, description="Existing draft or author intent")
    phase: Optional[str] = Field(default=None, description="Target phase tone")


class MapEnhanceResponse(BaseModel):
    region: str
    poi_name: str
    title: str
    description: str
    details: list[str]


# --- 2. Voice Prompt Enhance ---

VOICE_ENHANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Speaker name"},
        "rules": {
            "type": "string",
            "description": "Rules of speech for the character (cadence, vocabulary, taboo topics)",
        },
        "seed_line": {
            "type": "string",
            "description": "A representative seed dialogue line fitting the speaker and tone",
        },
        "strike_prompt": {
            "type": "string",
            "description": "Prompt for when this speaker writes the sealed letter / bell response",
        },
    },
    "required": ["name", "rules", "seed_line", "strike_prompt"],
    "additionalProperties": False,
}


class VoiceEnhanceRequest(BaseModel):
    speaker_name: str = Field(description="Name or archetype of the speaker")
    role: Optional[str] = Field(default=None, description="Role in town (blacksmith, elder, traveler)")
    personality: Optional[str] = Field(default=None, description="Personality traits or mood")
    phase: Optional[str] = Field(default=None, description="Target phase tone")


class VoiceEnhanceResponse(BaseModel):
    speaker_name: str
    name: str
    rules: str
    seed_line: str
    strike_prompt: str


# --- 3. Item Curse & Flavor Enhance ---

ITEM_ENHANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Evocative in-world relic name"},
        "kind": {"type": "string", "description": "Item category (ring, blade, cloth, token, etc.)"},
        "lore": {"type": "string", "description": "Atmospheric backstory in 1-2 sentences"},
        "enchant": {"type": "string", "description": "Quiet boon or attunement effect"},
        "curse": {"type": "string", "description": "Subtle drawback or lingering memory (never gory)"},
    },
    "required": ["name", "kind", "lore", "enchant", "curse"],
    "additionalProperties": False,
}


class ItemEnhanceRequest(BaseModel):
    base_name: Optional[str] = Field(default=None, description="Base item name or concept")
    kind: Optional[str] = Field(default="relic", description="Item category")
    bond: Optional[str] = Field(default=None, description="Target bond tier (assigned, attuned, cold)")
    intent: Optional[str] = Field(default=None, description="Author mood or mechanical idea")


class ItemEnhanceResponse(BaseModel):
    name: str
    kind: str
    lore: str
    enchant: str
    curse: str


# --- Prompt Builders & Execution ---

SYSTEM_PROMPT = (
    "You are the quiet smith at the world's hearth. You craft evocative, "
    "migraine-safe, in-world storytelling components. Plain prose, never purple, "
    "never modern jargon. Follow the Contract: show, don't explain."
)


def enhance_map(req: MapEnhanceRequest) -> MapEnhanceResponse:
    """Enhance a POI or room description using pack context and active tone."""
    w = load_world()
    canon = logbok()
    phase = req.phase or list(w.get("phases", {}).keys())[0] if w.get("phases") else "whispers"
    tone = phase_tone(phase)

    user_prompt = (
        f"WORLD CANON:\n{canon}\n\n"
        f"REGION: {req.region}\n"
        f"POI / LOCATION: {req.poi_name}\n"
        f"CURRENT PHASE TONE: {tone}\n"
    )
    if req.context:
        user_prompt += f"AUTHOR INTENT / EXISTING DRAFT:\n{req.context}\n"
    user_prompt += (
        "\nProvide a refined title, a sensory 2-3 sentence description, and 2-3 "
        "notable details. Return only the JSON object."
    )

    payload = {
        "model": generator.MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"schema": MAP_ENHANCE_SCHEMA, "strict": True},
        },
        "max_tokens": 1024,
        "temperature": 0.85,
    }

    import json
    for _ in range(2):
        try:
            raw = generator._completion(payload)
            data = json.loads(raw)
            return MapEnhanceResponse(
                region=req.region,
                poi_name=req.poi_name,
                title=data["title"],
                description=data["description"],
                details=data["details"],
            )
        except Exception:
            continue
    raise RuntimeError("map enhance generation failed schema twice")


def enhance_voice(req: VoiceEnhanceRequest) -> VoiceEnhanceResponse:
    """Enhance or draft a speaker voice prompt, seed line, and strike prompt."""
    w = load_world()
    canon = logbok()
    phase = req.phase or list(w.get("phases", {}).keys())[0] if w.get("phases") else "whispers"
    tone = phase_tone(phase)

    user_prompt = (
        f"WORLD CANON:\n{canon}\n\n"
        f"SPEAKER: {req.speaker_name}\n"
        f"ROLE: {req.role or 'resident'}\n"
        f"PERSONALITY: {req.personality or 'grounded'}\n"
        f"CURRENT PHASE TONE: {tone}\n\n"
        "Draft speech rules (rules), a seed line in this tone (seed_line), "
        "and a strike prompt for the bell letter (strike_prompt). Return only the JSON object."
    )

    payload = {
        "model": generator.MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"schema": VOICE_ENHANCE_SCHEMA, "strict": True},
        },
        "max_tokens": 1024,
        "temperature": 0.85,
    }

    import json
    for _ in range(2):
        try:
            raw = generator._completion(payload)
            data = json.loads(raw)
            return VoiceEnhanceResponse(
                speaker_name=req.speaker_name,
                name=data.get("name", req.speaker_name),
                rules=data["rules"],
                seed_line=data["seed_line"],
                strike_prompt=data["strike_prompt"],
            )
        except Exception:
            continue
    raise RuntimeError("voice enhance generation failed schema twice")


def enhance_item(req: ItemEnhanceRequest) -> ItemEnhanceResponse:
    """Enhance or forge flavor, quiet enchantment, and subtle curse for an item."""
    w = load_world()
    canon = logbok()
    texture = w.get("forge_texture", "Items carry the world's texture. Curses are quiet, never gory.")

    user_prompt = (
        f"WORLD CANON:\n{canon}\n\n"
        f"FORGE TEXTURE: {texture}\n"
        f"BASE ITEM: {req.base_name or 'unnamed relic'}\n"
        f"KIND: {req.kind}\n"
        f"BOND: {req.bond or 'assigned'}\n"
    )
    if req.intent:
        user_prompt += f"AUTHOR INTENT: {req.intent}\n"
    user_prompt += (
        "\nProvide in-world name, kind, lore (1-2 sentences), quiet enchant effect, "
        "and subtle curse (never gory). Return only the JSON object."
    )

    payload = {
        "model": generator.MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"schema": ITEM_ENHANCE_SCHEMA, "strict": True},
        },
        "max_tokens": 1024,
        "temperature": 0.85,
    }

    import json
    for _ in range(2):
        try:
            raw = generator._completion(payload)
            data = json.loads(raw)
            return ItemEnhanceResponse(
                name=data["name"],
                kind=data.get("kind", req.kind or "relic"),
                lore=data["lore"],
                enchant=data["enchant"],
                curse=data["curse"],
            )
        except Exception:
            continue
    raise RuntimeError("item enhance generation failed schema twice")
