from app.agents.translator import (
    _mask_math,
    _restore_math,
    needs_math_aware,
)


def test_needs_math_aware_detects_equation() -> None:
    assert needs_math_aware("Solve x + 2 = 5") is True


def test_needs_math_aware_skips_prose() -> None:
    assert needs_math_aware("Բարև, ինչպե՞ս ես") is False


def test_mask_and_restore_roundtrip() -> None:
    text = "Find x in: x + 2 = 5 please."
    masked, tokens = _mask_math(text)
    assert "〚M0〛" in masked or tokens, masked
    restored = _restore_math(masked, tokens)
    assert restored == text


def test_mask_preserves_latex() -> None:
    text = "Show $\\frac{1}{2} + \\frac{1}{4}$ on the line"
    masked, tokens = _mask_math(text)
    assert any("\\frac" in t for t in tokens)
    assert _restore_math(masked, tokens) == text
