import pytest

from ruleaudit.ir import Binary, Const, Unary, Var
from ruleaudit.rules import Guard, Meta, PBinary, PUnary, Rule, match, substitute


def test_repeated_expression_bindings_are_structural() -> None:
    x = Meta("X", "expr")
    pattern = PBinary("sub", x, x)
    assert match(pattern, Binary("sub", Var("x"), Var("x"))) == {"X": Var("x")}
    assert match(pattern, Binary("sub", Var("x"), Var("y"))) is None
    assert match(pattern, Var("x")) is None
    assert match(Const(0), Const(1)) is None
    nested = PUnary("not", PBinary("add", x, Const(0)))
    bindings = match(nested, Unary("not", Binary("add", Var("x"), Const(0))))
    assert bindings == {"X": Var("x")}
    assert substitute(nested, bindings) == Unary("not", Binary("add", Var("x"), Const(0)))


def test_constant_metavariables_and_guards() -> None:
    c = Meta("C", "const")
    assert match(c, Const(0xFFFFFFFF)) == {"C": Const(0xFFFFFFFF)}
    assert match(c, Var("x")) is None
    assert match(c, Binary("add", Const(0), Const(1))) is None
    assert Guard("eq", "C", Const(0)).holds({"C": Const(0)})
    assert Guard("ne", "C", Const(0)).holds({"C": Const(0xFFFFFFFF)})
    assert Guard("eq", "C", "D").holds({"C": Const(1), "D": Const(1)})
    with pytest.raises(ValueError):
        Guard("eq", "C", Const(0)).holds({"C": Var("x")})
    with pytest.raises(ValueError):
        substitute(c, {"C": Var("x")})
    with pytest.raises(ValueError):
        substitute(c, {})


def test_unbound_or_inconsistent_metavariables_rejected() -> None:
    x, c = Meta("X", "expr"), Meta("C", "const")
    with pytest.raises(ValueError, match="unbound"):
        Rule("bad", x, c)
    with pytest.raises(ValueError, match="constant"):
        Rule("bad", x, x, (Guard("eq", "X", Const(0)),))
    with pytest.raises(ValueError, match="unbound"):
        Rule("bad", x, x, (Guard("eq", "C", Const(0)),))
    with pytest.raises(ValueError, match="kind"):
        Rule("bad", PBinary("add", x, Meta("X", "const")), x)
    with pytest.raises(ValueError):
        Rule("bad/id", x, x)


def test_no_commutative_or_constant_folding_shortcut() -> None:
    p = PBinary("add", Meta("X", "expr"), Const(0))
    assert match(p, Binary("add", Const(0), Var("x"))) is None
    assert substitute(PBinary("add", Const(1), Const(2)), {}) == Binary("add", Const(1), Const(2))
