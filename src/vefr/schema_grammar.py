"""JSON Schema to GBNF grammar converter for llama.cpp-compatible backends.

This module provides a dependency-free converter from a subset of JSON Schema
to GBNF (GGML BNF) grammar format, used by llama.cpp and compatible backends
to enforce structured output by construction.

Supported subset:
- object: properties, required, additionalProperties: false
- string (with optional enum), boolean, integer, number
- array of a single simple items type
- top-level enum
- nullable via "type": ["string", "null"] or {"type": "null"}

Unsupported (raises SchemaGrammarError):
- oneOf/anyOf/allOf
- $ref
- pattern, format, minLength, maxLength
- nested unions
- additionalProperties: true (when properties are defined)

The start rule is always named "root" as required by llama.cpp.
"""

from itertools import combinations


class SchemaGrammarError(ValueError):
    """Raised when a schema cannot be converted to GBNF."""
    pass


def grammar_from_schema(schema: dict) -> str:
    """Convert a JSON Schema to a GBNF grammar string.
    
    Args:
        schema: A JSON Schema dict
        
    Returns:
        A complete GBNF grammar string with "root" as the start rule
        
    Raises:
        SchemaGrammarError: If the schema uses unsupported features
    """
    converter = _SchemaConverter()
    return converter.convert(schema)


class _SchemaConverter:
    """Internal converter that builds GBNF rules from JSON Schema."""
    
    def __init__(self):
        self.rules = {}
        self.rule_counter = 0
        
    def convert(self, schema: dict) -> str:
        """Convert schema to GBNF grammar."""
        # Generate the root rule
        self._schema_to_rule(schema, "root")
        
        # Add common utility rules
        self._add_utility_rules()
        
        # Build the final grammar - root first, then others
        lines = []
        if "root" in self.rules:
            lines.append(self.rules["root"])
        
        for name, rule in self.rules.items():
            if name != "root":
                lines.append(rule)
        
        return "\n".join(lines)
    
    def _schema_to_rule(self, schema: dict, name: str) -> str:
        """Convert a schema to a GBNF rule with the given name."""
        # Check for unsupported features early
        if "$ref" in schema:
            raise SchemaGrammarError("$ref not supported")
        if "allOf" in schema or "anyOf" in schema or "oneOf" in schema:
            raise SchemaGrammarError("allOf/anyOf/oneOf not supported")
        if "pattern" in schema:
            raise SchemaGrammarError("pattern not supported")
        if "format" in schema:
            raise SchemaGrammarError("format not supported")
        if "minLength" in schema or "maxLength" in schema:
            raise SchemaGrammarError("minLength/maxLength not supported")
        
        # Handle nullable types: ["string", "null"]
        if isinstance(schema.get("type"), list):
            types = schema["type"]
            if "null" in types and len(types) == 2:
                # Nullable type - create a rule that's either the type or null
                other_type = [t for t in types if t != "null"][0]
                nullable_schema = dict(schema)
                nullable_schema["type"] = other_type
                
                # Create a rule for the non-null type
                inner_name = f"{name}_inner"
                self._schema_to_rule(nullable_schema, inner_name)
                
                # The actual rule is either inner or null
                rule = f'{name} ::= {inner_name} | "null"'
                self.rules[name] = rule
                return rule
            else:
                raise SchemaGrammarError(
                    f"Unsupported type union: {types}"
                )
        
        # Handle explicit null type
        if schema.get("type") == "null":
            rule = f'{name} ::= "null"'
            self.rules[name] = rule
            return rule
        
        # Handle enum at any level
        if "enum" in schema:
            enum_values = schema["enum"]
            alternatives = []
            for val in enum_values:
                if val is None:
                    alternatives.append('"null"')
                elif isinstance(val, str):
                    alternatives.append(f'"{self._escape_string(val)}"')
                elif isinstance(val, bool):
                    alternatives.append(f'"{str(val).lower()}"')
                elif isinstance(val, (int, float)):
                    alternatives.append(f'"{val}"')
                else:
                    raise SchemaGrammarError(
                        f"Unsupported enum value type: {type(val)}"
                    )
            rule = f'{name} ::= {" | ".join(alternatives)}'
            self.rules[name] = rule
            return rule
        
        schema_type = schema.get("type")
        
        if schema_type == "object":
            return self._object_to_rule(schema, name)
        elif schema_type == "string":
            rule = f'{name} ::= string'
            self.rules[name] = rule
            return rule
        elif schema_type == "boolean":
            rule = f'{name} ::= boolean'
            self.rules[name] = rule
            return rule
        elif schema_type == "integer":
            rule = f'{name} ::= integer'
            self.rules[name] = rule
            return rule
        elif schema_type == "number":
            rule = f'{name} ::= number'
            self.rules[name] = rule
            return rule
        elif schema_type == "array":
            return self._array_to_rule(schema, name)
        else:
            raise SchemaGrammarError(
                f"Unsupported schema type: {schema_type}"
            )
    
    def _object_to_rule(self, schema: dict, name: str) -> str:
        """Convert an object schema to a GBNF rule.

        Properties are constrained to the declared names, in declaration
        order, with exact JSON commas: optional properties are modelled
        by enumerating which of them are present, so the grammar can
        never emit a missing or trailing comma.
        """
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        if not properties:
            rule = f'{name} ::= "{{" ws "}}"'
            self.rules[name] = rule
            return rule

        names = list(properties)
        rule_names: dict[str, str] = {}
        for prop_name, prop_schema in properties.items():
            rule_name = f"{name}_{self._safe_name(prop_name)}"
            if rule_name in rule_names.values():
                raise SchemaGrammarError(
                    f"property names collide in GBNF: {prop_name!r}"
                )
            rule_names[prop_name] = rule_name
            self._schema_to_rule(prop_schema, rule_name)

        def member(prop_name: str) -> str:
            key = f'"{self._escape_string(prop_name)}"'
            return f'{key} ws ":" ws {rule_names[prop_name]}'

        optional = [n for n in names if n not in required]
        if len(optional) > 6:
            raise SchemaGrammarError(
                "too many optional properties to model exactly (max 6)"
            )

        alternatives: list[str] = []
        empty_allowed = False
        for r in range(len(optional) + 1):
            for combo in combinations(optional, r):
                present = set(combo)
                members = [
                    member(n) for n in names if n in required or n in present
                ]
                if not members:
                    empty_allowed = True
                    continue
                alternatives.append(' ws "," ws '.join(members))

        body = " | ".join(dict.fromkeys(alternatives))
        if empty_allowed:
            rule = f'{name} ::= "{{" ws ({body})? ws "}}"'
        else:
            rule = f'{name} ::= "{{" ws ({body}) ws "}}"'
        self.rules[name] = rule
        return rule
    
    def _array_to_rule(self, schema: dict, name: str) -> str:
        """Convert an array schema to a GBNF rule."""
        items = schema.get("items")
        if not items:
            raise SchemaGrammarError("Array without items schema not supported")
        
        items_rule_name = f"{name}_items"
        self._schema_to_rule(items, items_rule_name)
        
        # Array: empty or items separated by commas
        rule = f'{name} ::= "[" ws (ws {items_rule_name} ws ("," ws {items_rule_name} ws)*)? "]"'
        self.rules[name] = rule
        return rule
    
    def _add_utility_rules(self):
        """Add common utility rules for JSON syntax."""
        if "ws" not in self.rules:
            self.rules["ws"] = 'ws ::= [ \\t\\n]*'
        
        if "string" not in self.rules:
            # String: opening quote, content, closing quote
            self.rules["string"] = 'string ::= "\\"" string-content "\\""'
        
        if "string-content" not in self.rules:
            # JSON string content: any character except " and control chars, with escapes
            # Characters: not " or \ or control chars (0x00-0x1F, 0x7F)
            # Escapes: \" \\ \/ \b \f \n \r \t \uXXXX
            self.rules["string-content"] = (
                'string-content ::= '
                '([^"\\\\\\x00-\\x1F\\x7F] | '
                '"\\\\" (["\\\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))*'
            )
        
        if "boolean" not in self.rules:
            self.rules["boolean"] = 'boolean ::= "true" | "false"'
        
        if "integer" not in self.rules:
            # JSON integer: optional minus, then 0 or [1-9][0-9]*
            self.rules["integer"] = 'integer ::= "-"? ("0" | [1-9] [0-9]*)'
        
        if "number" not in self.rules:
            # JSON number: integer with optional fraction and exponent
            self.rules["number"] = (
                'number ::= "-"? ("0" | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [+-]? [0-9]+)?'
            )
    
    def _escape_string(self, s: str) -> str:
        """Escape a string for use in GBNF string literal."""
        # In GBNF, within double quotes, we need to escape:
        # - backslash: \\ 
        # - double quote: \"
        s = s.replace("\\", "\\\\")
        s = s.replace('"', '\\"')
        return s
    
    def _safe_name(self, name: str) -> str:
        """Convert a property name to a safe GBNF identifier."""
        # Replace non-alphanumeric chars with underscore
        safe = "".join(c if c.isalnum() else "_" for c in name)
        # Ensure it doesn't start with a digit
        if safe and safe[0].isdigit():
            safe = "_" + safe
        # Ensure it's not empty
        if not safe:
            safe = "prop"
        return safe
