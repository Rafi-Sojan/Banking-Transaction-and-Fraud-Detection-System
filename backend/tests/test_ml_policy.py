from app.services.ml_service import combine_risk_scores


def test_rule_only_score_preserves_cpp_risk_when_ml_is_disabled() -> None:
    score, level = combine_risk_scores(0.80, None)
    assert score == 0.80
    assert level == "high"

