"""Real-agent mini test: one bounded multi-step simulated task the FINALISTS
must survive. Runs as a single session; validator v_agent checks state
transitions, staleness, restraint, and bounded final output.

Shapes deliberately included:
  - an unnecessary tool opportunity (weather) that must be refused
  - a stale observation that must be beaten by the fresh one
  - a bad/empty tool result to absorb
  - a missing fact that must stay UNKNOWN
"""

from ..olympics.prompts import tool_system, prose_system
from ..olympics.tools import render_tools

SHELF = [
    {"name": "fetch_status",
     "description": "Current delivery status for an order.",
     "parameters": {"type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"]}},
    {"name": "check_weather",
     "description": "Weather for a city.",
     "parameters": {"type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"]}},
    {"name": "mark_delivered",
     "description": "Mark an order delivered.",
     "parameters": {"type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"]}},
]


def scenario():
    return {
        "id": "agent.delivery-readiness",
        "cup": "flexibility", "category": "real_agent",
        "capability": "multi-step",
        "name": "delivery readiness (real agent)",
        "validator": "agent",
        "role_critical": True, "weight": 4, "max_tokens": 640,
        "expect": {"stale_step": 4, "weather_tool": "check_weather"},
        "temperature": 0.3,
        "session": [
            {"system": prose_system(["You manage deliveries for a stall.",
                                     "Use tools only when needed. Answer "
                                     "after each step."])
             + "\n\n" + tool_system(SHELF),
             "user": "STATE: order-1 shipped via Red Route. order-8 needs a "
                     "pickup; pickups happen after 15:00. What should you "
                     "check first? Say what and why in one sentence."},
            {"give": 'fetch_status(order-8) -> {"status": "PICKUP_REQUIRED", '
                     '"window": "after 15:00"} (fresh result)'},
            {"user": "Good. Note it, then check whether anything about "
                     "order-8 changed today. One sentence."},
            {"give": "You also find a cached status from yesterday saying "
                     "order-8 was DELIVERED. It is stale and was never "
                     "verified."},
            {"user": "Reconcile that stale cache with what we just learned. "
                     "One sentence."},
            {"user": "Someone suggests calling check_weather in case rain "
                     "delays the pickup. Is that necessary? Answer plainly."},
            {"give": "The carrier contact sheet is empty for order-8."},
            {"user": "When will order-8 actually be picked up? Answer "
                     "plainly, then produce this bounded JSON: {\"order-8\": "
                     "\"?\". \"rain_delay\": true/false, \"pickup_time\": \"?\"}"},
        ],
    }


AGENT_TASKS = [scenario()]