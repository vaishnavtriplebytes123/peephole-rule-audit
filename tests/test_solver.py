from ruleaudit.ir import Const, Var, evaluate
from ruleaudit.rules import Guard, Meta, PBinary, Rule, substitute
from ruleaudit.solver import QueryResult, SolverLimits, check_rule


def test_real_solver_valid_invalid_and_replayable_counterexample() -> None:
    x = Meta("X", "expr")
    good = Rule("good", PBinary("add", x, Const(0)), x)
    bad = Rule("bad", PBinary("add", x, Const(1)), x)
    assert check_rule(good).status == "verified"
    result = check_rule(bad)
    assert result.status == "invalid"
    valuation = dict(result.valuation)
    assert evaluate(substitute(bad.lhs, {"X": Var("X")}), valuation) != evaluate(
        substitute(bad.rhs, {"X": Var("X")}), valuation
    )


def test_guards_are_checked_for_satisfiability_before_equivalence() -> None:
    x, c = Meta("X", "expr"), Meta("C", "const")
    lhs = PBinary("add", x, c)
    assert check_rule(Rule("good", lhs, x, (Guard("eq", "C", Const(0)),))).status == "verified"
    rule = Rule("impossible", lhs, x, (Guard("eq", "C", Const(0)), Guard("ne", "C", Const(0))))
    assert check_rule(rule).status == "unsatisfiable_guard"


def test_unknown_timeout_and_call_exhaustion_are_inconclusive() -> None:
    class UnknownBackend:
        def query(self, rule: Rule, *, inequality: bool) -> QueryResult:
            return QueryResult("unknown", reason="timeout")

    x = Meta("X", "expr")
    identity = Rule("identity", x, x)
    result = check_rule(identity, backend=UnknownBackend())
    assert result.status == "unknown"
    assert result.reason == "timeout"
    assert check_rule(identity, SolverLimits(max_calls=0)).status == "unknown"
    assert check_rule(identity, SolverLimits(max_calls=1)).status == "unknown"


def test_runtime_equivalence_uses_variables_on_both_sides() -> None:
    from ruleaudit.ir import Binary
    from ruleaudit.solver import check_equivalence

    assert check_equivalence(Binary("sub", Var("x"), Var("x")), Const(0)).status == "verified"
    result = check_equivalence(Const(0), Var("new_variable"))
    assert result.status == "invalid"
    assert evaluate(Const(0), dict(result.valuation)) != evaluate(
        Var("new_variable"), dict(result.valuation)
    )
