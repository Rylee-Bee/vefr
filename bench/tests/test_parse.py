"""Parser unit tests. The rig must not mis-score a model's valid-but-different
dialect, which is exactly the failure the community documented (lfm2.5 bracket
notation scored as 0.640 until a fallback parser fixed it -> 0.880).

Run: python3 bench/cli.py parsertest
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bench.olympics.parse import parse  # noqa: E402

FIXTURES = [
    # (label, raw, expect_name, expect_args_subset, dialect, norm_flag)
    ("canonical", '<|tool_call|> {"name": "get_weather", "arguments": '
                  '{"city": "State College"}} <|/tool_call|>',
     "get_weather", {"city": "State College"}, "canonical", None),
    ("famous-bracket", '[get_weather(city="State College")]',
     "get_weather", {"city": "State College"}, "bracket", "bracket"),
    ("bare-func", 'get_weather(city="Port", units="c") I mean.',
     "get_weather", {"city": "Port", "units": "c"}, "bracket", "bracket"),
    ("xml-tags", "<tool_call>\n{\"name\": \"get_refund_status\", "
                 "\"arguments\": {\"order_id\": \"3\"}}\n</tool_call>",
     "get_refund_status", {"order_id": "3"}, "canonical", None),
    ("xml-name-args", "<tool_call><name>restart_service</name>"
                      "<arguments>{\"service\": \"mail\"}</arguments></tool_call>",
     "restart_service", {"service": "mail"}, "xml", None),
    ("prose-plus-call", 'Sure thing! Let me check that.\n<|tool_call|> '
                        '{"name": "get_store_hours", "arguments": '
                        '{"store": "Harbormaster"}} <|/tool_call|>\nHere you go.',
     "get_store_hours", {"store": "Harbormaster"}, "canonical", None),
    ("fenced-json", '```json\n{"status": "ok", "total": 3}\n```',
     None, None, None, "fenced"),
    ("openai-native", '{"role": "assistant", "content": null, '
                      '"tool_calls": [{"id": "x", "type": "function", '
                      '"function": {"name": "fetch_invoice", "arguments": '
                      '"{\\"order_id\\": \\"7\\"}"}}]}',
     "fetch_invoice", {"order_id": "7"}, "openai-native", None),
    ("garbage", "Well, uh, I do not think I have that information.",
     None, None, None, None),
    ("malformed-json", '{"name": "Kira", "role": }',
     None, None, None, "embedded_json"),
    ("top-list-answer", '[{"name": "Kira", "age": 40}, {"name": "Tova"}]',
     None, None, None, None),
]


def run():
    failures = []
    for label, raw, exp_name, exp_args, exp_dialect, exp_norm in FIXTURES:
        pr = parse(raw)
        calls = pr.get("tool_calls", [])
        got_name = calls[0]["name"] if calls else None
        got_args = calls[0]["arguments"] if calls else {}
        ok = True
        why = []
        if exp_name is not None and got_name != exp_name:
            ok, why = False, [f"name {got_name!r} != {exp_name!r}"]
        if exp_args:
            for k, v in exp_args.items():
                if got_args.get(k) != v:
                    ok, why = False, [f"arg {k}={got_args.get(k)!r} != {v!r}"]
        if exp_dialect and (not calls or calls[0]["dialect"] != exp_dialect):
            ok, why = False, [f"dialect {calls[0]['dialect'] if calls else None}"
                              f" != {exp_dialect}"]
        if exp_norm and not pr.get("norm", {}).get(exp_norm):
            ok, why = False, [f"norm flag {exp_norm} not set"]
        status = "PASS" if ok else "FAIL"
        print(f"{status:4s} {label:22s} calls={calls} prose={pr['prose'][:30]!r} "
              f"norm={pr.get('norm')}" + (f"  [{', '.join(why)}]" if why else ""))
        if not ok:
            failures.append(label)
    # the famous case, explicitly
    pr = parse('[get_weather(city="State College")]')
    assert pr["tool_calls"][0]["name"] == "get_weather"
    assert pr["tool_calls"][0]["arguments"]["city"] == "State College"
    print("\nfamous-lfm-case: bracket recovered ->",
          pr["tool_calls"][0]["name"], pr["tool_calls"][0]["arguments"])
    # regression: hermes-style top-level array is NOT 'the answer' -
    # first_json must not hand a list to the validators (AttributeError).
    from bench.olympics.parse import first_json
    pr = parse('[{"name": "get_weather", "arguments": {"city": "X"}}]')
    assert first_json(pr) is None, "top-level list must not be an answer dict"
    assert pr["tool_calls"] == [], "top-level list must not become a call"
    print("\ntop-list-regression: first_json=None, tool_calls=[] OK")
    print("\nparser: {} fixtures, {} failed".format(len(FIXTURES), len(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())