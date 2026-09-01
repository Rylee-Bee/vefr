def _testSeed(seed):
    def RNG(s):
        def generate():
            nonlocal s
            s = (s * 9301 + 49297) % 233280
            return s / 233280
        return generate
    rng = RNG(seed)
    return rng() > 0

def _testDrag(card, column):
    return card.get('dataset', {}).get('name') and column.get('contains', lambda x: False)(card)

def test_board_seed():
    assert _testSeed(12345) is True

def test_board_drag():
    card = {'dataset': {'name': 'Asa'}}
    column = {'contains': lambda x: True}
    assert _testDrag(card, column) is True