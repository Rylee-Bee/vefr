"""Spark tests - the resident brain's contract.

The benchmark proved the models; these tests prove the subsystem:
profiles are pinned, context is generated from the pack (not
hand-written), the thinking-mode invariant is explicit, the client
fails closed, and escalation judgment is scored against ground truth.
No live model needed except where marked.
"""

import json

import httpx
import pytest

from vefr import spark


@pytest.fixture
def sample_world_pack():
    """The tracked demo pack: context layers read real pack data."""
    from vefr import world as world_mod
    world_mod.load_world.cache_clear()
    yield
    world_mod.load_world.cache_clear()


# ----------------------------------------------------------- profiles

def test_quality_profile_is_phi():
    p = spark.profile('quality')
    assert p['file'] == 'Phi-4-mini-instruct-Q4_K_M.gguf'
    assert p['repo'] == 'unsloth/Phi-4-mini-instruct-GGUF'
    assert p['license'] == 'MIT'
    # Phi has no thinking mode: no enable_thinking kwarg to fake.
    assert 'enable_thinking' not in p['chat_template_kwargs']


def test_tiny_profile_forces_thinking_off():
    p = spark.profile('tiny')
    assert p['file'] == 'Qwen3.5-0.8B-Q8_0.gguf'
    # The invariant: Qwen3.5 ships thinking ON, which eats the whole
    # output budget. It must be explicitly disabled, never defaulted.
    assert p['chat_template_kwargs'].get('enable_thinking') is False


def test_unknown_profile_rejected():
    with pytest.raises(KeyError):
        spark.profile('q4-because-it-is-smaller')


def test_pinned_hashes_are_64_hex():
    for p in spark.PROFILES.values():
        assert len(p['sha256']) == 64
        int(p['sha256'], 16)  # hex or it isn't a hash


# ----------------------------------------------------- context builder

def test_core_contract_shipped_and_small():
    text = spark.core_contract()
    assert 'You are Spark' in text
    assert 'ESCALATE' in text
    assert 'fail closed' in text or 'fail-closed' in text
    # A core contract is a contract, not a world book: stable and small.
    assert len(text) < 4000


def test_build_messages_layers(sample_world_pack):
    # sample_world_pack points the loader at the tracked demo pack,
    # so the world layer is generated from real pack data.
    user = 'Scene: dusk, the candle-maker\'s stall. Create one NPC.'
    messages, meta = spark.build_messages('npc', user)
    system = messages[0]['content']
    assert messages[0]['role'] == 'system'
    assert 'You are Spark' in system
    assert '## World' in system
    assert 'Emberfield' in system  # generated from the pack, not copied
    assert meta['task'] == 'npc'
    assert meta['chat_template_kwargs'] == spark.profile('quality')['chat_template_kwargs']
    assert meta['approx_prompt_words'] > 50


def test_character_context_comes_from_pack(sample_world_pack):
    from vefr import world as world_mod
    w = world_mod.load_world()
    key = next(iter(w['voices']))
    ctx = spark.character_context(key)
    assert ctx.startswith('Voice rules for')
    # The voice rules text is the pack's own file content, not boilerplate.
    assert ctx.split('(absolute):\n', 1)[1].strip() != ''


def test_runtime_state_minimized(sample_world_pack):
    long = 'x' * 2000
    ctx = spark.runtime_context({'phase': 'dusk', 'note': long})
    assert 'dusk' in ctx and len(ctx) < 1600  # truncated, not dumped
    assert spark.runtime_context(None) == 'Current state: none supplied.'


def test_unknown_task_rejected(sample_world_pack):
    with pytest.raises(KeyError):
        spark.build_messages('reorganize_the_repository', 'do it')


# ------------------------------------------------- state edit contract

def test_state_edit_check_passes_exact_edit():
    original = {'gold': 12, 'npcs': [{'id': 'k', 'trust': 2}]}
    updated = {'gold': 12, 'npcs': [{'id': 'k', 'trust': 5}]}
    ok, detail = spark.state_edit_check(original, updated, allowed={'npcs'})
    assert ok and 'npcs' in detail


def test_state_edit_check_fails_on_collateral():
    original = {'gold': 12, 'npcs': [{'id': 'k', 'trust': 2}]}
    updated = {'gold': 99, 'npcs': [{'id': 'k', 'trust': 5}]}
    ok, detail = spark.state_edit_check(original, updated, allowed={'npcs'})
    assert not ok and 'gold' in detail


def test_state_edit_check_fails_on_invented_keys():
    original = {'gold': 12}
    updated = {'gold': 12, 'curse': 'sudden'}
    ok, detail = spark.state_edit_check(original, updated, allowed={'gold'})
    assert not ok and 'curse' in detail


# ------------------------------------------------ fail-closed client

class _Resp:
    def __init__(self, payload=None, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError('bad', request=None, response=None)

    @property
    def text(self):
        return json.dumps(self._payload)

    def json(self):
        return self._payload


def _ok_body(content: str):
    return {'choices': [{'message': {'content': content}}]}


def test_spark_call_validates_schema(sample_world_pack, monkeypatch):
    calls = []

    def fake_post(url, json=None, timeout=None):
        calls.append(url)
        return _Resp(_ok_body('{"text": "a line"}'))

    monkeypatch.setattr(spark.httpx, 'post', fake_post)
    result, meta = spark.spark_call('dialogue', 'say a line', speaker='keeper')
    assert result.text == 'a line'
    assert meta['validation'] == 'ok'
    assert calls[0].endswith('/v1/chat/completions')


def test_spark_call_fails_closed_on_malformed(sample_world_pack, monkeypatch):
    monkeypatch.setattr(spark.httpx, 'post',
                        lambda *a, **k: _Resp(_ok_body('{"text": ')))
    with pytest.raises(spark.SparkMalformed):
        spark.spark_call('dialogue', 'say a line')


def test_spark_call_raises_unavailable_on_transport(sample_world_pack, monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError('refused')
    monkeypatch.setattr(spark.httpx, 'post', boom)
    with pytest.raises(spark.SparkUnavailable):
        spark.spark_call('dialogue', 'say a line')


def test_chat_template_kwargs_flow_to_request(sample_world_pack, monkeypatch):
    """The thinking-mode invariant, at the wire: a tiny-profile request
    carries enable_thinking:false in chat_template_kwargs - never the
    model's default."""
    seen = {}
    real_tiny = {**spark.profile('tiny'), 'key': 'tiny'}

    def fake_post(url, json=None, timeout=None, **kw):
        seen.update(json or {})
        return _Resp(_ok_body('{"text": "hi"}'))

    monkeypatch.setattr(spark.httpx, 'post', fake_post)
    monkeypatch.setattr(spark, 'profile', lambda name=None: real_tiny)
    spark.spark_call('dialogue', 'say a line')
    assert seen['chat_template_kwargs'] == {'enable_thinking': False}


# -------------------------------------------------------- escalation

def test_needs_escalation_deterministic_gate():
    assert spark.needs_escalation('design a save-state migration system')
    assert spark.needs_escalation('debug the async race in the journal')
    assert not spark.needs_escalation('write a haiku about a lamp')
    assert not spark.needs_escalation('set Kestrel\'s trust to 5')


def test_escalation_verdict_scoring():
    good = [spark.EscalationDecision(task_id=k, choice=v, reason='')
            for k, v in spark.ESCALATION_EXPECT.items()]
    ok, detail = spark.escalation_verdict(good)
    assert ok and 'all' in detail
    # Flip one non-negotiable probe (migrate must be ESCALATE) and the
    # verdict must fail loudly - escalation judgment is load-bearing.
    bad = [d for d in good if d.task_id != 'migrate'] + [
        spark.EscalationDecision(task_id='migrate', choice='LOCAL', reason='')]
    ok, detail = spark.escalation_verdict(bad)
    assert not ok and 'migrate' in detail


def test_escalate_route_payload_contract():
    """The classify task's schema is enum-locked: LOCAL or ESCALATE."""
    schema = spark.TASK_CONTRACTS['classify']['schema']
    choice = schema['properties']['decisions']['items']['properties']['choice']
    assert choice['enum'] == ['LOCAL', 'ESCALATE']
    assert schema['required'] == ['decisions']
