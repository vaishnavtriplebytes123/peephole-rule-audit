import pytest

from ruleaudit.derive import DeriveLimits, derive
from ruleaudit.ir import Binary, Const, Var
from ruleaudit.rules import Guard, Meta, PBinary, Rule

X = Meta("X", "expr")
ONE = PBinary("add", X, Const(0))
TWO = PBinary("add", ONE, Const(0))
A = Rule("A", TWO, X)
B = Rule("B", TWO, ONE)
C = Rule("C", ONE, X)


def test_two_step_template_excludes_target_and_keeps_opaque_placeholders() -> None:
    result = derive(A, (A, B, C))
    assert result.status == "found"
    witness = result.witnesses[0]
    assert [step.rule_id for step in witness.steps] == ["B", "C"]
    assert [step.location for step in witness.steps] == [(), ()]
    assert witness.constant_bindings == ()
    assert witness.placeholders == (("X", "_s0"),)
    assert witness.start == Binary("add", Binary("add", Var("_s0"), Const(0)), Const(0))
    assert witness.endpoint == Var("_s0")
    assert witness.semantic_status == "verified"
    assert "template" in witness.scope


def test_direct_alternative_and_no_target_self_proof() -> None:
    duplicate = Rule("other", TWO, X)
    assert len(derive(A, (A, duplicate)).witnesses[0].steps) == 1
    miss = derive(A, (A,))
    assert miss.status == "not-found-within-bounds"
    assert not miss.witnesses


def test_no_silent_specialization_of_expression_placeholders() -> None:
    # Applying double-zero elimination inside an opaque X would require
    # specializing X into a compound expression, which this search cannot do.
    target = Rule("target", X, X)
    result = derive(target, (target, C))
    assert result.status == "not-found-within-bounds"


def test_constant_specialization_checks_every_guard_and_endpoint() -> None:
    k = Meta("K", "const")
    target = Rule("target", PBinary("add", X, k), X, (Guard("eq", "K", Const(0)),))
    replacement = Rule("replacement", PBinary("add", X, k), X, (Guard("eq", "K", Const(0)),))
    result = derive(target, (target, replacement), constants=(0, 1))
    assert result.status == "found"
    assert len(result.witnesses) == 1
    assert result.witnesses[0].constant_bindings == (("K", 0),)
    assert result.witnesses[0].steps[0].guards == (True,)
    assert result.guard_rejections == 1


def test_guard_unavailable_on_other_rule_does_not_count_as_a_path() -> None:
    k = Meta("K", "const")
    other = Rule(
        "guarded_identity",
        PBinary("add", X, k),
        PBinary("add", X, k),
        (Guard("ne", "K", Const(0)),),
    )
    result = derive(Rule("target", ONE, X), (Rule("target", ONE, X), other))
    assert result.status == "not-found-within-bounds"


def test_structural_endpoint_required_even_when_semantically_equal() -> None:
    other = Rule("commute", PBinary("add", X, Const(0)), PBinary("add", Const(0), X))
    result = derive(Rule("target", ONE, X), (Rule("target", ONE, X), other))
    assert result.status == "not-found-within-bounds"


def test_search_exhaustion_and_solver_unknown_are_inconclusive() -> None:
    from ruleaudit.solver import SolverLimits, Z3Backend

    limited = derive(A, (A, B, C), limits=DeriveLimits(max_match_attempts=0))
    assert limited.status == "partial"
    assert not limited.witnesses
    assert "limit" in limited.reason
    unknown = derive(A, (A, B, C), backend=Z3Backend(SolverLimits(max_calls=0)))
    assert unknown.status == "partial"
    assert unknown.solver_unknowns > 0


def test_invalid_rule_cannot_supply_evidence() -> None:
    invalid = Rule("bad", TWO, Const(42))
    with pytest.raises(ValueError, match="bad"):
        derive(A, (A, invalid))


def test_state_and_step_caps_count_endpoint_states() -> None:
    duplicate = Rule("other", TWO, X)
    assert derive(A, (A, duplicate), DeriveLimits(max_states=1)).status == "partial"
    direct = derive(A, (A, duplicate), DeriveLimits(max_states=2))
    assert direct.status == "found"
    assert direct.states == 2
    assert derive(A, (A, B, C), DeriveLimits(max_steps=1)).status == "not-found-within-bounds"


def test_unknown_during_instantiated_path_check_emits_no_witness() -> None:
    from ruleaudit.solver import SolverLimits, Z3Backend

    duplicate = Rule("other", TWO, X)
    # Four calls validate the two rules; no call remains for path obligations.
    result = derive(A, (A, duplicate), backend=Z3Backend(SolverLimits(max_calls=4)))
    assert result.status == "partial"
    assert result.solver_unknowns == 1
    assert not result.witnesses


def test_growth_exclusions_and_zero_time_are_explicit() -> None:
    from ruleaudit.rules import PUnary
    from ruleaudit.solver import Z3Backend

    identity = Rule("identity", X, X)
    expand = Rule("expand", X, PUnary("not", PUnary("not", X)))
    contract = Rule("contract", PUnary("not", PUnary("not", X)), X)
    miss = derive(identity, (identity, expand, contract), DeriveLimits(max_depth=2))
    assert miss.status == "not-found-within-bounds"
    assert miss.growth_exclusions == 1
    backend = Z3Backend()
    timed = derive(A, (A, B, C), DeriveLimits(seconds=0), backend=backend)
    assert timed.status == "partial"
    assert "time-limit" in timed.reason
    assert backend.calls == 0


@pytest.mark.parametrize(
    "settings",
    [
        {"max_steps": 0},
        {"max_steps": 3},
        {"max_states": 0},
        {"max_states": 10001},
        {"max_bindings": True},
        {"seconds": 10**1000},
        {"seconds": float("nan")},
    ],
)
def test_search_limits_are_validated(settings: dict[str, int | float]) -> None:
    with pytest.raises(ValueError):
        DeriveLimits(**settings)  # type: ignore[arg-type]


def test_alternative_can_rewrite_below_the_root() -> None:
    from ruleaudit.rules import PUnary

    nested = Rule("nested", PUnary("not", TWO), PUnary("not", X))
    result = derive(nested, (nested, C))
    assert result.status == "found"
    assert [step.location for step in result.witnesses[0].steps] == [(0,), (0,)]
