from app.agents.visualization import validate_spec


def test_validate_fraction_pie() -> None:
    spec = validate_spec({"kind": "fraction_pie", "numerator": 3, "denominator": 4})
    assert spec.kind == "fraction_pie"
    assert spec.numerator == 3


def test_validate_number_line() -> None:
    spec = validate_spec(
        {
            "kind": "number_line",
            "start": 0,
            "end": 10,
            "marks": [{"value": 3, "label": "3", "color": "#3b82f6"}],
        }
    )
    assert spec.kind == "number_line"
    assert len(spec.marks) == 1


def test_validate_geometry_with_frames() -> None:
    spec = validate_spec(
        {
            "kind": "geometry",
            "bounds": [-5, 5, 5, -5],
            "constructions": [{"op": "point", "id": "A", "args": [0, 0]}],
            "frames": [{"t_ms": 1000, "ops": [{"op": "highlight", "id": "A"}]}],
        }
    )
    assert spec.frames and spec.frames[0].t_ms == 1000
