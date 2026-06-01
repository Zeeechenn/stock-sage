from backend.config import SignalWeights
from backend.decision import aggregator


def test_aggregate_uses_event_override_for_scoring(monkeypatch):
    monkeypatch.setattr(
        aggregator,
        "active_signal_weights",
        lambda: SignalWeights(
            quant=0.0,
            technical=0.0,
            sentiment=1.0,
            entry_threshold=25.0,
            profile="unit_event_override",
            use_multi_agent=False,
        ),
    )
    monkeypatch.setattr(aggregator, "_bull_bear_debate", lambda *args, **kwargs: {})

    result = aggregator.aggregate(
        quant_score=95.0,
        technical_result={"score": 95.0},
        sentiment_score=0.9,
        sentiment_result={
            "sentiment": 0.9,
            "event_score_mode": "event_override",
            "event_score": -0.8,
            "event_types": ["penalty"],
        },
        close=10.0,
        atr=1.0,
    )

    assert result["composite_score"] == -80.0
    assert result["recommendation"] == "规避"
    assert result["breakdown"]["sentiment"] == -80.0
    assert result["event_signal"] == {
        "event_score": -0.8,
        "raw_sentiment": 90.0,
        "event_types": ["penalty"],
    }
    assert result["rule_version"] == "aggregate_v1:unit_event_override"


def test_blend_quant_clamps_kronos_score_and_ignores_bad_values(monkeypatch):
    monkeypatch.setattr(aggregator.settings, "kronos_enabled", True)
    monkeypatch.setattr(aggregator.settings, "kronos_weight_in_quant", 1.5)

    blended, info = aggregator._blend_quant(
        -20.0,
        {
            "score": 150.0,
            "volatility_adj": 1.7,
            "predicted_high": 12.5,
            "predicted_low": 8.5,
        },
    )

    assert blended == 100.0
    assert info == {
        "kronos_score": 100.0,
        "kronos_volatility_adj": 1.7,
        "kronos_predicted_high": 12.5,
        "kronos_predicted_low": 8.5,
    }

    ignored, reason = aggregator._blend_quant(25.0, {"score": float("nan")})

    assert ignored == 25.0
    assert reason == {"kronos_ignored": "non_finite_score"}
