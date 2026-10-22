from dataclasses import FrozenInstanceError

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ruleaudit.ir import Binary, Const, Unary, Var, evaluate, measure


def test_modular_boundaries_and_cost() -> None:
    overflow = Binary("add", Const(0xFFFFFFFF), Const(1))
    underflow = Binary("sub", Const(0), Const(1))
    assert evaluate(overflow, {}) == 0
    assert evaluate(underflow, {}) == 0xFFFFFFFF
    assert measure(overflow) == (3, 2, 1)
    assert measure(Const(0)) == (1, 1, 0)
    assert measure(Var("x")) == (1, 1, 0)


@pytest.mark.parametrize("op,expected", [("and", 0xA0), ("or", 0xFA), ("xor", 0x5A)])
def test_bitwise(op: str, expected: int) -> None:
    assert evaluate(Binary(op, Const(0xAA), Const(0xF0)), {}) == expected  # type: ignore[arg-type]
    assert evaluate(Unary("not", Const(0xAA)), {}) == 0xFFFFFF55


def test_repeated_variables_and_nested_operations() -> None:
    x = Var("x")
    expression = Binary("xor", Binary("add", x, Const(1)), Unary("not", x))
    assert evaluate(expression, {"x": 0xFFFFFFFF}) == 0
    assert measure(expression) == (6, 3, 3)
    assert Binary("sub", x, x) == Binary("sub", Var("x"), Var("x"))
    assert Binary("add", x, Const(1)) != Binary("add", Const(1), x)


@given(
    st.integers(min_value=0, max_value=0xFFFFFFFF), st.integers(min_value=0, max_value=0xFFFFFFFF)
)
def test_add_sub_against_integer_arithmetic(x: int, y: int) -> None:
    assert evaluate(Binary("add", Var("x"), Var("y")), {"x": x, "y": y}) == (x + y) % 2**32
    assert evaluate(Binary("sub", Var("x"), Var("y")), {"x": x, "y": y}) == (x - y) % 2**32


@pytest.mark.parametrize("value", [True, False, -1, 2**32, 1.0, "1"])
def test_invalid_constant(value: object) -> None:
    with pytest.raises(ValueError):
        Const(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("name", ["", "a-b", "x;import", "é", "x" * 65, "1x"])
def test_invalid_variable(name: str) -> None:
    with pytest.raises(ValueError):
        Var(name)


def test_immutable_and_invalid_bindings() -> None:
    x = Var("x")
    with pytest.raises(FrozenInstanceError):
        x.name = "y"  # type: ignore[misc]
    with pytest.raises(ValueError, match="x"):
        evaluate(x, {})
    with pytest.raises(ValueError):
        evaluate(x, {"x": True})
    with pytest.raises(ValueError):
        Unary("neg", x)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Binary("mul", x, x)  # type: ignore[arg-type]
