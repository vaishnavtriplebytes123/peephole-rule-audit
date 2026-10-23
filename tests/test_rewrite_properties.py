"""Independent value checks for every step on generated bounded trees."""

from hypothesis import given, settings
from hypothesis import strategies as st

from ruleaudit.ir import Binary, BinaryOp, Const, Expr, Unary, Var, evaluate
from ruleaudit.rewrite import RunLimits, Schedule, run
from ruleaudit.rules import Meta, PBinary, PUnary, Rule

OPS: tuple[BinaryOp, ...] = ("add", "sub", "and", "or", "xor")


def binary(parts: tuple[BinaryOp, Expr, Expr]) -> Expr:
    return Binary(*parts)


TREES: st.SearchStrategy[Expr] = st.recursive(
    st.one_of(
        st.sampled_from((Var("x"), Var("y"), Var("z"))), st.integers(0, 2**32 - 1).map(Const)
    ),
    lambda inner: st.one_of(
        inner.map(lambda value: Unary("not", value)),
        st.tuples(st.sampled_from(OPS), inner, inner).map(binary),
    ),
    max_leaves=10,
)
X, Y = Meta("X", "expr"), Meta("Y", "expr")
RULES = (
    Rule("add_zero", PBinary("add", X, Const(0)), X),
    Rule("double_not", PUnary("not", PUnary("not", X)), X),
    Rule("xor_self", PBinary("xor", X, X), Const(0)),
    Rule(
        "de_morgan",
        PUnary("not", PBinary("and", X, Y)),
        PBinary("or", PUnary("not", X), PUnary("not", Y)),
    ),
)


@settings(max_examples=100, deadline=None)
@given(
    tree=TREES,
    form=st.integers(0, 3),
    values=st.tuples(*(st.integers(0, 2**32 - 1) for _ in range(3))),
    postorder=st.booleans(),
    reverse=st.booleans(),
    h=st.integers(1, 8),
)
def test_each_generated_rewrite_preserves_independently_evaluated_value(
    tree: Expr, form: int, values: tuple[int, int, int], postorder: bool, reverse: bool, h: int
) -> None:
    # Each form guarantees at least one applicable identity, avoiding vacuous passes.
    original = (
        Binary("add", tree, Const(0)),
        Unary("not", Unary("not", tree)),
        Binary("xor", tree, tree),
        Unary("not", Binary("and", tree, Var("y"))),
    )[form]
    bindings = dict(zip(("x", "y", "z"), values, strict=True))
    priority = tuple(rule.id for rule in RULES)
    result = run(
        original,
        RULES,
        Schedule("postorder" if postorder else "preorder", priority[::-1] if reverse else priority),
        RunLimits(h=h),
        now=lambda: 0.0,
    )
    assert result.completed and result.trace
    expected = evaluate(original, bindings)
    assert evaluate(result.output, bindings) == expected
    for step in result.trace:
        assert evaluate(step.before, bindings) == evaluate(step.after, bindings)


@given(tree=TREES, value=st.integers(0, 2**32 - 1))
def test_independent_value_oracle_detects_a_deliberately_invalid_rewrite(
    tree: Expr, value: int
) -> None:
    bad = Rule("bad", X, PBinary("add", X, Const(1)))
    result = run(tree, (bad,), Schedule("preorder", ("bad",)), RunLimits(h=1), now=lambda: 0.0)
    bindings = {name: value for name in ("x", "y", "z")}
    assert len(result.trace) == 1
    assert evaluate(result.output, bindings) == (evaluate(tree, bindings) + 1) % 2**32
    assert evaluate(result.output, bindings) != evaluate(tree, bindings)
