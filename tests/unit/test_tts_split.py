from app.services.tts import split_into_clauses


def test_split_simple() -> None:
    out = split_into_clauses("Hi there. Let's count to ten. Ready?")
    assert out == ["Hi there.", "Let's count to ten.", "Ready?"]


def test_split_armenian_full_stop() -> None:
    out = split_into_clauses("Բարև։ Ինչպե՞ս ես։")
    assert len(out) == 2


def test_split_long_clause_falls_back_to_comma() -> None:
    long = ("a very, long, sentence that, just keeps, going, on and on, and on without, end") * 5
    out = split_into_clauses(long, max_chars=80)
    assert all(len(c) <= 90 for c in out)
