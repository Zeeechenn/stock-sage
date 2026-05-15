"""
多 Agent 决策流水线编排器

调用顺序：
  Analysts (并行 4 路) → Researcher (分歧时辩论) → Trader → RiskManager
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

from backend.agents.analyst import (
    technical_analyst,
    quant_analyst,
    sentiment_analyst,
    news_analyst,
    AnalystReport,
)
from backend.agents.researcher import debate, has_divergence, quick_consensus
from backend.agents.trader import propose, TraderProposal
from backend.agents.risk_manager import review, RiskDecision
from backend.analysis.timing.regime import RegimeReport
from backend.config import settings


@dataclass
class AgentDecision:
    composite_score: float
    recommendation: str
    confidence: str
    stop_loss: float
    take_profit: float
    position_pct: float
    breakdown: dict
    analysts: dict           # role → AnalystReport.to_dict()
    researcher: dict         # ResearcherConclusion fields
    risk: dict               # RiskDecision fields
    regime: dict | None
    reasoning: str

    def to_signal_dict(self) -> dict:
        """转回 aggregator 兼容格式（用于写 Signal 表）"""
        return {
            "composite_score": self.composite_score,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "breakdown": self.breakdown,
            "position_pct": self.position_pct,
            "limit_status": self.risk.get("limit_status", "normal"),
            "llm_arbitration": {
                "bull_points": self.researcher.get("bull_points", []),
                "bear_points": self.researcher.get("bear_points", []),
                "action_bias": self.researcher.get("action_bias", "中性"),
                "rationale": self.researcher.get("rationale", ""),
            },
            "risk_notes": self.risk.get("risk_notes", []),
            "veto_reason": self.risk.get("veto_reason"),
            "regime": self.regime,
            "stop_loss_executable": self.risk.get("stop_loss_executable", True),
        }


def run_pipeline(
    technical_result: dict,
    qlib_result: dict,
    sentiment_result: dict,
    close: float,
    atr: float,
    regime: RegimeReport | None = None,
    llm_arbitration: dict | None = None,
    portfolio_drawdown_pct: float = 0.0,
    limit_status: dict | None = None,
    long_term_label=None,                 # LongTermLabel | None
) -> AgentDecision:
    """
    主入口。调用方（aggregator）需准备：
      • technical_result: technical_score() 返回值
      • qlib_result:      qlib_score() 返回值
      • sentiment_result: analyze_news() 返回值
      • regime:           market_regime() 返回值（可选，None 则跳过 RM 的 regime 检查）
      • llm_arbitration:  分歧时 _bull_bear_debate() 返回值（可选）
    """
    # 1. Analysts
    reports: dict[str, AnalystReport] = {
        "technical": technical_analyst(technical_result),
        "quant": quant_analyst(qlib_result),
        "sentiment": sentiment_analyst(sentiment_result),
        "news": news_analyst(sentiment_result),
    }

    # 2. Researcher
    report_list = list(reports.values())
    if has_divergence(report_list):
        researcher = debate(report_list, llm_arbitration)
    else:
        researcher = quick_consensus(report_list)

    # 3. Trader
    proposal: TraderProposal = propose(
        reports, researcher,
        close=close, atr=atr,
        portfolio_drawdown_pct=portfolio_drawdown_pct,
    )

    # 3.5 长期"观望"标签 → 综合分硬截断到 watch_score_cap
    from backend.agents.trader import _score_to_recommendation
    if long_term_label is not None and long_term_label.label == "观望" \
            and settings.long_term_team_enabled:
        cap = settings.long_term_watch_score_cap
        if proposal.composite_score > cap:
            proposal.breakdown["long_term_cap"] = cap
            proposal.composite_score = cap
            proposal.recommendation = _score_to_recommendation(cap)

    # 4. Risk Manager
    risk: RiskDecision = review(
        proposal, regime, limit_status, portfolio_drawdown_pct,
        long_term_label=long_term_label,
    )

    final_pos = risk.adjusted_position_pct
    final_rec = risk.final_recommendation

    reasoning = proposal.reasoning
    if risk.veto_reason:
        reasoning += f" 风控否决: {risk.veto_reason}。"
    if risk.risk_notes:
        reasoning += " 风控提示: " + "; ".join(risk.risk_notes)

    return AgentDecision(
        composite_score=proposal.composite_score,
        recommendation=final_rec,
        confidence=proposal.confidence,
        stop_loss=proposal.stop_loss,
        take_profit=proposal.take_profit,
        position_pct=final_pos,
        breakdown=proposal.breakdown,
        analysts={k: v.to_dict() for k, v in reports.items()},
        researcher={
            "bull_points": researcher.bull_points,
            "bear_points": researcher.bear_points,
            "action_bias": researcher.action_bias,
            "rationale": researcher.rationale,
            "used_llm": researcher.used_llm,
        },
        risk={
            "approved": risk.approved,
            "veto_reason": risk.veto_reason,
            "risk_notes": risk.risk_notes,
            "limit_status": (limit_status or {}).get("status", "normal"),
            "stop_loss_executable": (limit_status or {}).get("stop_loss_executable", True),
            "long_term": long_term_label.to_dict() if long_term_label else None,
        },
        regime=regime.to_dict() if regime else None,
        reasoning=reasoning,
    )
