"""Deterministic AI chat response builders used by the HTTP route."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.agent.action_parser import symbol_from_text
from backend.api.schemas import AIChatResponse
from backend.data.database import Position, Stock


def _fmt_score(value) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"{n:+.1f}"


def _fmt_pct(value) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"{n * 100:.1f}%"


def _copilot_context_section(db: Session, symbol: str) -> tuple[str | None, bool]:
    try:
        from backend.decision.harness import get_research_state
        state = get_research_state(db, symbol)
    except Exception:
        return None, False
    copilot = state.get("copilot") if isinstance(state, dict) else None
    if not copilot:
        return None, False
    official = copilot.get("official") or {}
    lines = [
        "双轨影子副驾驶：",
        "官方规则：",
        f"- 建议：{official.get('recommendation', '-')}",
        f"- 综合分：{_fmt_score(official.get('composite_score'))}",
        f"- 技术：{_fmt_score(official.get('technical_score') or official.get('breakdown', {}).get('technical'))}",
        f"- 情绪：{_fmt_score(official.get('sentiment_score') or official.get('breakdown', {}).get('sentiment'))}",
        f"- 官方仓位：{_fmt_pct(official.get('position_pct'))}",
        "LLM 副驾驶：",
        f"- 立场：{copilot.get('stance', '-')}",
        f"- 影子仓位：{_fmt_pct(copilot.get('shadow_position_pct'))}",
        f"- 结论：{copilot.get('summary_opinion', '-')}",
    ]
    if copilot.get("risk_conflict"):
        lines.append("- 标记：逆风控影子建议")
    risks = (copilot.get("risks") or [])[:2]
    if risks:
        lines.append("- 风险：" + "、".join(risks))
    questions = (copilot.get("validation_questions") or [])[:2]
    if questions:
        lines.append("- 待验证：" + "、".join(questions))
    return "\n".join(lines), True


def context_answer(
    message: str,
    db: Session,
    session_id: str | None = None,
    *,
    chat_context_for_session,
) -> AIChatResponse:
    """Deterministic fallback answer using internal MingCang resources."""
    symbol = symbol_from_text(message)
    stocks = db.query(Stock).filter(Stock.active).limit(6).all()
    positions = db.query(Position).filter(Position.status == "open").limit(6).all()
    parts = ["我会在 MingCang 项目内回答：已读取自选股、持仓、信号、复盘和研究记忆。"]
    used_resources = ["stocks", "positions", "project_research"]
    if session_id:
        chat_context = chat_context_for_session(db, session_id)
        if chat_context:
            parts.append("本窗口上下文：\n" + chat_context)
    if symbol:
        try:
            from backend.memory.stock_memory import build_memory_context
            memory_context = build_memory_context(
                db,
                symbol=symbol,
                query=message,
                task_type="chat",
            )
        except Exception:
            memory_context = {"text": ""}
        if memory_context.get("text"):
            parts.append("项目长期记忆：\n" + memory_context["text"])
            used_resources.append("stock_memory")
        copilot_section, has_copilot = _copilot_context_section(db, symbol)
        if has_copilot and copilot_section:
            parts.append(copilot_section)
            used_resources.append("research_copilot")
    if stocks:
        parts.append("当前自选股包括：" + "、".join(f"{s.name or s.symbol}({s.symbol})" for s in stocks))
    if positions:
        parts.append("当前持仓包括：" + "、".join(f"{p.name or p.symbol}({p.symbol})" for p in positions))
    parts.append("需要联网调研时，我会优先走项目内新闻、行情、深度研究和长期研究团队链路。")
    return AIChatResponse(
        answer="\n".join(parts),
        used_resources=used_resources,
    )


def long_term_answer(message: str, db: Session) -> AIChatResponse:
    symbol = symbol_from_text(message)
    if not symbol:
        return AIChatResponse(
            answer="请告诉我要研究的股票代码，或说明要研究“自选股”还是“持仓”。",
            used_resources=["long_term_team"],
        )
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if stock is None:
        raise HTTPException(404, f"stock {symbol} not found")
    from backend.agents.long_term.storage import save_label
    from backend.agents.long_term.team import LongTermTeam

    label = LongTermTeam().run(stock.symbol, stock.name, db)
    save_label(label, db)
    findings = "；".join(label.key_findings[:3]) if label.key_findings else "暂无关键发现"
    try:
        from backend.memory.stock_memory import build_memory_context
        memory_context = build_memory_context(
            db,
            symbol=stock.symbol,
            query=message,
            task_type="long_term_team",
        )
    except Exception:
        memory_context = {"text": ""}
    memory_text = f"\n项目长期记忆：\n{memory_context['text']}" if memory_context.get("text") else ""
    quality_note = "可约束官方动作" if label.constraint_eligible else "仅展示，不约束官方动作"
    return AIChatResponse(
        answer=(
            f"{stock.name}({stock.symbol}) 长期研究团队结论：{label.label}，评分 {label.score:.1f}。"
            f"质量：{label.quality}（{quality_note}）。{findings}{memory_text}"
        ),
        citations=[f"long_term:{stock.symbol}:{label.date}"],
        used_resources=["long_term_team"] + (["stock_memory"] if memory_context.get("text") else []),
    )
