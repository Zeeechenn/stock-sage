"""
综合分 → 仓位映射（阶段B）

替换原"每笔固定 20%"的简单规则，根据综合分置信度动态给出仓位建议。
当前实现为线性映射，可在测试1/2 后根据实测胜率分段调参。
"""
from __future__ import annotations
from backend.config import settings, active_signal_weights


def suggest_position_pct(
    composite_score: float,
    confidence: str = "中",
    portfolio_drawdown_pct: float = 0.0,
) -> float:
    """
    返回建议仓位占总资金的比例 (0.0 ~ max_position_per_stock)。

    映射逻辑（阶段B 初版，所有阈值通过 settings 可调）：
      综合分 < 入场阈值 → 0%
      入场阈值 ≤ x < 30 → 试错仓
      30  ≤ x < 40    → max × 0.50
      40  ≤ x < 50    → max × 0.75
      ≥ 50            → max × 1.00
    置信度"高"时上浮 20%，"低"时下浮 30%（不超过上限）。
    组合累计回撤超过 4% 时一律 ×0.5（防止逆风加仓）。
    """
    if not settings.position_sizing_enabled:
        return settings.max_position_per_stock

    entry_threshold = active_signal_weights().entry_threshold
    if composite_score < entry_threshold:
        return 0.0

    if composite_score >= 50:
        base = 1.0
    elif composite_score >= 40:
        base = 0.75
    elif composite_score >= 30:
        base = 0.50
    else:
        return min(settings.new_signal_trial_pct, settings.max_position_per_stock)

    confidence_mult = {"高": 1.2, "中": 1.0, "低": 0.7}.get(confidence, 1.0)
    drawdown_mult = 0.5 if portfolio_drawdown_pct < -4.0 else 1.0

    pct = settings.max_position_per_stock * base * confidence_mult * drawdown_mult
    return min(pct, settings.max_position_per_stock)
