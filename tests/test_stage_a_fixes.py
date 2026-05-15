import math
import pandas as pd


def test_calc_rsi_single_direction_and_flat_are_finite():
    from backend.analysis.factors import calc_rsi

    up = calc_rsi(pd.Series([1, 2, 3, 4, 5]))
    down = calc_rsi(pd.Series([5, 4, 3, 2, 1]))
    flat = calc_rsi(pd.Series([3, 3, 3, 3, 3]))

    assert up.iloc[-1] == 100.0
    assert down.iloc[-1] == 0.0
    assert flat.iloc[-1] == 50.0
    assert up.map(math.isfinite).all()
    assert down.map(math.isfinite).all()
    assert flat.map(math.isfinite).all()


def test_aggregate_non_finite_composite_falls_back_to_neutral(monkeypatch):
    from backend.decision import aggregator

    monkeypatch.setattr(aggregator.settings, "paper_trading_profile", "new_framework")
    monkeypatch.setattr(aggregator.settings, "weight_quant", float("nan"))
    result = aggregator.aggregate(
        quant_score=10,
        technical_result={"score": 20, "limit": {}},
        sentiment_score=0.1,
        close=10,
        atr=1,
    )

    assert result["composite_score"] == 0.0
    assert result["recommendation"] == "观望"


def test_position_sizer_preserves_caps_for_small_candidate_sets():
    from backend.portfolio.combo_weights import equal_weight, size_positions

    assert equal_weight(1, max_per=0.2) == [0.2]
    assert equal_weight(2, max_per=0.2) == [0.2, 0.2]
    sized = size_positions([{"sym": "a"}, {"sym": "b"}, {"sym": "c"}], max_per=0.15)
    assert [x["weight"] for x in sized] == [0.15, 0.15, 0.15]


def test_risk_manager_downgrades_strong_buy_without_long_term_label():
    from backend.agents.risk_manager import review
    from backend.agents.trader import TraderProposal

    proposal = TraderProposal(
        composite_score=70,
        recommendation="强买",
        confidence="高",
        stop_loss=9,
        take_profit=12,
        position_pct=0.2,
        breakdown={},
        reasoning="test",
    )

    decision = review(proposal, regime=None, long_term_label=None)
    assert decision.final_recommendation == "可关注"
    assert any("长期标签缺失" in note for note in decision.risk_notes)
