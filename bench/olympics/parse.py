"""Lenient decoder: parse leniently, judge strictly.

Every trial preserves:
  raw          - exactly what came back from the runtime
  parsed       - the artifact(s) we recognized (JSON objects, tool calls, prose)
  normalized   - bool/dict: did we have to transform anything to get there?
  semantic     - is the DECISION right? (scored by validators)
  protocol     - did it arrive in an acceptable shape?

A model that decides correctly in an unusual-but-valid dialect must NOT be
scored as a protocol failure. A model that only fakes format on a restraint
prompt must NOT be scored as a semantic pass. Both facts are recorded
separately.
"""

import json
import re

DIALECTS = ["canonical", "bracket", "xml", "bare-json", "openai-native"]


def _find_matching(txt, op, cl, i):
    depth = 0
    for j in range(i, len(txt)):
        if txt.startswith(op, j):
            depth += 1
        elif txt.startswith(cl, j):
            depth -= 1
            if depth == 0:
                return j + len(cl)
    return None


def _extract_json_objects(text):
    """Pull each JSON object/array out of the text, tracking spans."""
    objs = []
    for m in re.finditer(r"[{\[]", text):
        close = "}" if m.group(0) == "{" else "]"
        end = _find_matching(text, m.group(0), close, m.start())
        if end is None:
            continue
        try:
            val = json.loads(text[m.start():end])
        except Exception:
            continue
        objs.append((val, m.start(), end))
    return objs


def _top_level(objs):
    """Keep only outermost JSON constructs (drop anything nested inside
    another construct). A list that wraps answer dicts must not leak its
    contents as 'the answer'."""
    out = []
    for obj, s, e in objs:
        if any(s2 <= s and e <= e2 and (s2, e2) != (s, e)
               for o2, s2, e2 in objs):
            continue
        out.append((obj, s, e))
    return out


def _top_split(s):
    """Split on commas at top level, ignoring commas inside quotes."""
    out, buf, q = [], [], None
    for ch in s:
        if q:
            buf.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            buf.append(ch)
        else:
            if ch == ",":
                out.append("".join(buf))
                buf = []
            else:
                buf.append(ch)
    out.append("".join(buf))
    return out


def _split_bare_functions(text):
    """Recognize `name(k=v, k2=v2)` or `name(arg1, arg2)` calls anywhere."""
    calls = []
    pat = re.compile(r"(?<![\w\"'])([A-Za-z_][\w]*)\(([^(){}]*)\)")
    for m in pat.finditer(text):
        name, inner = m.group(1), m.group(2)
        if name in ("function", "tool") and inner.strip():
            continue
        args = {}
        for kv in _top_split(inner):
            kv = kv.strip()
            if not kv:
                continue
            if "=" in kv:
                k, _, v = kv.partition("=")
                v = v.strip().strip('"\'')
                args[k.strip()] = _coerce(v)
        calls.append((name, args, m.start(), m.end()))
    return calls


def _coerce(v):
    try:
        return json.loads(v)
    except Exception:
        return v


def _norm_args(args_obj):
    """Normalize arguments across dialects: dict, or JSON string (native)."""
    if isinstance(args_obj, str):
        try:
            args_obj = json.loads(args_obj)
        except Exception:
            return None
    return args_obj if isinstance(args_obj, dict) else None


def parse(raw):
    """Parse a raw response. Returns a ParseResult."""
    text = (raw or "").strip()
    result = {"raw": raw or "", "objects": [], "tool_calls": [],
              "prose": text, "dialects": [], "norm": {}}

    # 1. markdown fences
    norm = {}
    if "```" in text:
        norm["fenced"] = True
        text = re.sub(r"```(?:json|tool|function)?\s*", "", text).strip()

    # 2. scan for known tool-call wrappers
    calls_found = []

    for opener, closer, dialect in (("<|tool_call|>", "<|/tool_call|>", "canonical"),
                                    ("<tool_call>", "</tool_call>", "canonical"),
                                    ("<functioncall>", "</functioncall>", "xml"),
                                    ("<|tool_call|", "<|/tool_call|>", "canonical"),
                                    ("<tool_call>", "<|/tool_call|>", "canonical")):
        pat = re.compile(re.escape(opener) + r"(.*?)" + re.escape(closer), re.DOTALL)
        for m in pat.finditer(text):
            inner = m.group(1).strip()
            obj = None
            try:
                obj = json.loads(inner)
            except Exception:
                pass
            if isinstance(obj, dict) and "name" in obj:
                calls_found.append((obj, dialect, m.start(), m.end()))
            elif isinstance(obj, dict) and "function" in obj:
                calls_found.append((obj, "openai-native", m.start(), m.end()))
            elif obj is None:
                # XML-ish <name>...</name>
                nm = re.search(r"<name>(.*?)</name>", inner, re.DOTALL)
                if nm:
                    try:
                        args = _norm_args(re.search(r"<arguments?>(.*?)</arguments?>",
                                                    inner, re.DOTALL).group(1))
                    except Exception:
                        args = {}
                    d = {"name": nm.group(1).strip(), "arguments": args}
                    calls_found.append((d, "xml", m.start(), m.end()))

    # 3. JSON objects anywhere (could be a tool call or just the answer)
    for obj, s, e in _top_level(_extract_json_objects(text)):
        if isinstance(obj, dict):
            if "name" in obj and isinstance(obj.get("name"), str) and "arguments" in obj:
                args = _norm_args(obj.get("arguments"))
                if args is not None:
                    calls_found.append((obj, "bare-json", s, e))
                    continue
            if "function" in obj and isinstance(obj.get("function"), dict):
                fn = obj["function"]
                if isinstance(fn.get("name"), str):
                    d = {"name": fn["name"],
                         "arguments": _norm_args(fn.get("arguments")) or {}}
                    calls_found.append((d, "openai-native", s, e))
                    continue
            if "tool_calls" in obj and isinstance(obj.get("tool_calls"), list):
                for tc in obj["tool_calls"]:
                    if not isinstance(tc, dict):
                        continue
                    fn = tc.get("function")
                    if isinstance(fn, dict) and isinstance(fn.get("name"), str):
                        calls_found.append(
                            ({"name": fn["name"],
                              "arguments": _norm_args(fn.get("arguments")) or {}},
                             "openai-native", s, e))
                result["objects"].append((obj, s, e))
                continue
        result["objects"].append((obj, s, e))

    # 4. bracket / bare function notation late in text (community favorite)
    if not calls_found:
        bare = _split_bare_functions(text)
        for name, args, s, e in bare:
            calls_found.append(({"name": name, "arguments": args}, "bracket", s, e))
            # only treat as in-regime if wrapped in brackets or clearly a call line
        if bare:
            result["norm"]["bracket"] = True

    # 5. residual prose after removing tool segments
    rest = text
    for _, _, s, e in calls_found:
        rest = rest[:s] + " " + rest[e:]
    rest = rest.strip()

    for obj, dialect, s, e in calls_found:
        result["tool_calls"].append({"name": obj["name"],
                                     "arguments": obj.get("arguments") or {},
                                     "dialect": dialect})
        if dialect not in result["dialects"]:
            result["dialects"].append(dialect)

    result["prose"] = rest
    seen_json_chars = "{" in text or "[" in text
    if result["objects"] and not calls_found:
        result["norm"]["embedded_json"] = True
    elif result["objects"]:
        result["norm"]["objects_suppressed"] = True
    elif seen_json_chars and not calls_found:
        result["norm"]["embedded_json"] = True
    else:
        result["norm"]["objects_suppressed"] = True
    if norm:
        result["norm"].update(norm)
    return result


def first_json(pr):
    """The first JSON object that is not a tool call (the 'answer').
    Only dict-shaped objects count; a top-level array (native tool_calls
    lists, lists of items) is NOT the answer."""
    if not pr.get("objects"):
        return None
    for obj, _, _ in pr["objects"]:
        if isinstance(obj, dict):
            return obj
    return None


def all_jsons(pr):
    return [o for o, _, _ in pr.get("objects", [])]


def tool_names(pr):
    return [c["name"] for c in pr.get("tool_calls", [])]


def has_tool_call(pr):
    return bool(pr.get("tool_calls"))


def latest_tool(pr):
    return pr["tool_calls"][-1] if pr.get("tool_calls") else None