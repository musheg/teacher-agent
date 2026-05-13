from app.learning.bkt import _bkt_step


def test_bkt_increases_on_correct() -> None:
    new = _bkt_step(0.3, correct=True, p_slip=0.1, p_guess=0.2, p_transit=0.2)
    assert new > 0.3


def test_bkt_decreases_or_holds_on_wrong() -> None:
    new = _bkt_step(0.7, correct=False, p_slip=0.1, p_guess=0.2, p_transit=0.2)
    assert new < 0.7
