"""Random floors, R1: the shared random number generator (design/random-floors.md).

`delve.prng(seed)` is xmur3 (string -> 32-bit hash) feeding mulberry32 (32-bit state ->
float in [0, 1)). Integer maths only, so JavaScript and Python give the same stream.
The expected numbers were computed by an independent reference implementation in
JavaScript (the standard public-domain xmur3 and mulberry32), NOT by this repo's code.
A string is hashed by its UTF-16 code units (what JavaScript's charCodeAt reads).
"""

from vefr import delve

KNOWN = {
    "cottage": [0.13393288478255272, 0.3199043916538358, 0.08566394122317433,
                0.4837643166538328, 0.31890994450077415, 0.979176236083731],
    "": [0.9757088038604707, 0.6221915907226503, 0.6578594758175313,
         0.23277555429376662, 0.09539095987565815, 0.21994475345127285],
    "a": [0.11000576918013394, 0.5356475834269077, 0.2972125029191375,
          0.47833533538505435, 0.609476268524304, 0.12825429462827742],
    "floor-4 run 7": [0.09258401091210544, 0.24910211516544223, 0.5866671686526388,
                      0.9571929608937353, 0.6610296063590795, 0.6412352914921939],
    "Ünïcode ☕": [0.23862227401696146, 0.8391314579639584, 0.09424700238741934,
                  0.9438501831609756, 0.7824371010065079, 0.34587301104329526],
}


def test_prng_matches_the_independent_reference():
    for seed, expected in KNOWN.items():
        rng = delve.prng(seed)
        assert [rng() for _ in expected] == expected, seed


def test_prng_streams_are_independent_and_in_range():
    a, b = delve.prng("one"), delve.prng("one")
    first = [a() for _ in range(50)]
    assert first == [b() for _ in range(50)]
    assert all(0.0 <= x < 1.0 for x in first)
    assert first != [delve.prng("two")() for _ in range(50)]
