from app.services.risk import label_from_score, score_from_probability


def test_probability_extremes():
    assert score_from_probability(0.0) == 100
    assert score_from_probability(1.0) == 0


def test_probability_midpoint():
    assert score_from_probability(0.38) == 62


def test_label_boundaries():
    assert label_from_score(100) == "safe"
    assert label_from_score(70) == "safe"
    assert label_from_score(69) == "caution"
    assert label_from_score(40) == "caution"
    assert label_from_score(39) == "at_risk"
    assert label_from_score(0) == "at_risk"
