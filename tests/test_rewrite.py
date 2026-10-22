import pytest

from ruleaudit.ir import Binary, Const, Unary, Var
from ruleaudit.rewrite import RunLimits, Schedule, run
from ruleaudit.rules import Guard, Meta, PBinary, PUnary, Rule

X, Y = Meta("X", "expr"), Meta("Y", "expr")
DROP_ADD = Rule("drop_add", PBinary("add", X, Const(0)), X)
DROP_DOUBLE_NOT = Rule("double_not", PUnary("not", PUnary("not", X)), X)
SELF_SUB = Rule("self_sub", PBinary("sub", X, X), Const(0))


def test_traversal_locations_and_restart() -> None:
    x0 = Binary("add", Var("x"), Const(0))
    expression = Binary("sub", x0, x0)
    rules = (DROP_ADD, SELF_SUB)
    pre = run(expression, rules, Schedule("preorder", ("drop_add", "self_sub")), RunLimits(h=4))
    post = run(expression, rules, Schedule("postorder", ("drop_add", "self_sub")), RunLimits(h=4))
    assert pre.output == post.output == Const(0)
    assert [(s.rule_id, s.location) for s in pre.trace] == [("self_sub", ())]
    assert [(s.rule_id, s.location) for s in post.trace] == [
        ("drop_add", (0,)),
        ("drop_add", (1,)),
        ("self_sub", ()),
    ]
    assert pre.stop_reason == post.stop_reason == "no-match"


@pytest.mark.parametrize(
    "h,cost,reason",
    [
        (0, 2, "rewrite-budget"),
        (1, 1, "rewrite-budget"),
        (2, 0, "rewrite-budget"),
        (3, 0, "no-match"),
    ],
)
def test_successful_rewrite_budget(h: int, cost: int, reason: str) -> None:
    from ruleaudit.ir import measure

    expr = Binary("add", Binary("add", Var("x"), Const(0)), Const(0))
    result = run(expr, (DROP_ADD,), Schedule("preorder", ("drop_add",)), RunLimits(h=h))
    assert measure(result.output).operators == cost
    assert result.stop_reason == reason
    assert len(result.trace) == min(h, 2)


def test_priority_identity_and_cycles_are_counted() -> None:
    identity = Rule("identity", X, X)
    expr = Binary("add", Var("x"), Const(0))
    result = run(
        expr, (DROP_ADD, identity), Schedule("preorder", ("identity", "drop_add")), RunLimits(h=2)
    )
    assert result.output == expr
    assert [s.rule_id for s in result.trace] == ["identity", "identity"]
    swap = Rule("swap", PBinary("add", X, Y), PBinary("add", Y, X))
    result = run(expr, (swap,), Schedule("preorder", ("swap",)), RunLimits(h=3))
    assert result.output == Binary("add", Const(0), Var("x"))
    assert len(result.trace) == 3
    assert result.stop_reason == "rewrite-budget"


def test_growth_limit_stops_first_match_without_skipping() -> None:
    grow = Rule("grow", X, PUnary("not", PUnary("not", X)))
    identity = Rule("identity", X, X)
    for limits in (RunLimits(max_nodes=2), RunLimits(max_depth=2)):
        result = run(Var("x"), (grow, identity), Schedule("preorder", ("grow", "identity")), limits)
        assert result.output == Var("x")
        assert result.trace == ()
        assert result.stop_reason == "growth-limit"
        assert result.completed


def test_interruption_keeps_a_consistent_trace_prefix() -> None:
    ticks = 0

    def clock() -> float:
        nonlocal ticks
        ticks += 1
        if ticks == 5:
            raise KeyboardInterrupt
        return 0.0

    result = run(
        Binary("add", Var("x"), Const(0)),
        (DROP_ADD,),
        Schedule("preorder", ("drop_add",)),
        now=clock,
    )
    assert result.stop_reason == "interrupted"
    assert not result.completed
    assert result.output == Var("x")
    assert len(result.trace) == 1


def test_guard_rejection_and_determinism() -> None:
    c = Meta("C", "const")
    rule = Rule("guarded", PBinary("add", X, c), X, (Guard("eq", "C", Const(0)),))
    schedule = Schedule("postorder", ("guarded",))
    assert run(Binary("add", Var("x"), Const(1)), (rule,), schedule).stop_reason == "no-match"
    expr = Unary("not", Binary("add", Var("x"), Const(0)))
    results = [run(expr, (rule,), schedule) for _ in range(3)]
    assert all(r.output == Unary("not", Var("x")) for r in results)
    assert all(r.trace == results[0].trace for r in results)
    assert results[0].trace[0].location == (0,)


def test_deadline_is_partial() -> None:
    clock = iter([0.0, 0.0, 1.0, 1.0])
    result = run(
        Var("x"),
        (Rule("identity", X, X),),
        Schedule("preorder", ("identity",)),
        RunLimits(seconds=0.5),
        now=lambda: next(clock),
    )
    assert result.stop_reason == "time-limit"
    assert not result.completed


@pytest.mark.parametrize(
    "settings",
    [
        {"h": True},
        {"h": -1},
        {"h": 10001},
        {"max_nodes": 10001},
        {"max_depth": 129},
        {"seconds": float("nan")},
        {"seconds": float("inf")},
        {"seconds": -1},
    ],
)
def test_invalid_settings(settings: dict[str, int | float]) -> None:
    with pytest.raises(ValueError):
        RunLimits(**settings)  # type: ignore[arg-type]


def test_schedule_requires_exact_unique_priorities() -> None:
    for priority in ((), ("missing",), ("drop_add", "drop_add")):
        with pytest.raises(ValueError):
            run(Var("x"), (DROP_ADD,), Schedule("preorder", priority))


def test_huge_time_limit_is_a_validation_error() -> None:
    with pytest.raises(ValueError, match="seconds"):
        RunLimits(seconds=10**1000)
