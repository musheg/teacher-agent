from app.services.cas import cas


def test_simplify() -> None:
    r = cas.simplify("2*x + 3*x")
    assert r.success
    assert r.result == "5*x"


def test_solve_equation() -> None:
    r = cas.solve("x + 2 = 5")
    assert r.success
    assert "3" in (r.result or "")


def test_verify_equivalence_true() -> None:
    r = cas.verify_equivalence("2*x + 2", "2*(x+1)")
    assert r.success
    assert r.result == "equivalent"


def test_verify_equivalence_false() -> None:
    r = cas.verify_equivalence("x + 1", "x + 2")
    assert r.success
    assert r.result == "different"


def test_step_by_step_simplify() -> None:
    r = cas.step_by_step("x*(x+2)")
    assert r.success
    assert len(r.steps) >= 2
