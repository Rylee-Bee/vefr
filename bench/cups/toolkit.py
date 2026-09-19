"""Shared tool shelves (synthetic, engine-neutral) for tool events."""

WEATHER = [{
    "name": "get_weather",
    "description": "Current weather conditions for a city.",
    "parameters": {"type": "object",
                   "properties": {"city": {"type": "string"}},
                   "required": ["city"]}}]

HOURS = [{
    "name": "get_store_hours",
    "description": "Opening hours for a named store.",
    "parameters": {"type": "object",
                   "properties": {"store": {"type": "string"}},
                   "required": ["store"]}}]

ORDERS = [
    {"name": "fetch_orders", "description": "List orders for a customer id.",
     "parameters": {"type": "object",
                    "properties": {"customer_id": {"type": "string"}},
                    "required": ["customer_id"]}},
    {"name": "fetch_invoice", "description": "Fetch the invoice document for an order.",
     "parameters": {"type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"]}},
    {"name": "fetch_customer", "description": "Fetch the customer record for a customer id.",
     "parameters": {"type": "object",
                    "properties": {"customer_id": {"type": "string"}},
                    "required": ["customer_id"]}}]

MEETING = [{
    "name": "book_meeting",
    "description": "Schedule a meeting with a named person.",
    "parameters": {"type": "object",
                   "properties": {"who": {"type": "string"},
                                  "when": {"type": "string"},
                                  "topic": {"type": "string"},
                                  "duration_min": {"type": "integer"}},
                   "required": ["who", "when"]}}]

SERVICE = [{
    "name": "restart_service",
    "description": "Restart a named service.",
    "parameters": {"type": "object",
                   "properties": {"service": {"type": "string"}},
                   "required": ["service"]}},
    {"name": "get_service_status",
     "description": "Current status of a named service.",
     "parameters": {"type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"]}}]

SHELVES = {"weather": WEATHER, "hours": HOURS, "orders": ORDERS,
           "meeting": MEETING, "service": SERVICE}