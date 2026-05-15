"""
研究员团 — 看多/看空辩论。
逻辑分两层：
  • 快路径：分析师之间分歧标准差 < 20 时直接复用最高置信度方向，跳过 LLM
  • 慢路径：分歧时调用 LLM（复用 aggregator._bull_bear_debate 的工具调用）
"""
from __future__ import annotations
from dataclasses import dataclass
import statistics

from backend.agents.analyst import AnalystReport


@dataclass
class ResearcherConclusion:
    bull_points: list[str]
    bear_points: list[str]
    action_bias: str        # 偏多 / 中性 / 偏空
    rationale: str
    used_llm: bool


def quick_consensus(reports: list[AnalystReport]) -> ResearcherConclusion:
    """无分歧时的快速结论生成"""
    scores = [r.score for r in reports]
    avg = sum(scores) / len(scores) if scores else 0
    if avg > 15:
        bias = "偏多"
    elif avg < -15:
        bias = "偏空"
    else:
        bias = "中性"
    bull = [f.key_findings[0] for f in reports if f.score > 10 and f.key_findings]
    bear = [f.key_findings[0] for f in reports if f.score < -10 and f.key_findings]
    return ResearcherConclusion(
        bull_points=bull[:3],
        bear_points=bear[:3],
        action_bias=bias,
        rationale=f"四路均值 {avg:+.1f}，方向一致，跳过辩论。",
        used_llm=False,
    )


def has_divergence(reports: list[AnalystReport], threshold: float = 25.0) -> bool:
    """分析师分数标准差超过阈值视为分歧"""
    if len(reports) < 2:
        return False
    scores = [r.score for r in reports]
    return statistics.stdev(scores) > threshold


def debate(reports: list[AnalystReport], llm_arbitration: dict | None = None) -> ResearcherConclusion:
    """
    完整辩论：分歧时由 aggregator._bull_bear_debate 注入 llm_arbitration 后调用。
    llm_arbitration 为 None 时退回 quick_consensus。
    """
    if llm_arbitration:
        return ResearcherConclusion(
            bull_points=llm_arbitration.get("bull_points", [])[:3],
            bear_points=llm_arbitration.get("bear_points", [])[:3],
            action_bias=llm_arbitration.get("action_bias", "中性"),
            rationale=llm_arbitration.get("rationale", ""),
            used_llm=True,
        )
    return quick_consensus(reports)
