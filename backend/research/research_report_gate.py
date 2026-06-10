"""ResearchReportGate — M50 Phase 1.

Checks every DeepResearchReport before write_text / _persist_report.
Returns GateVerdict(status, reasons, warnings).

Import shared constants from research_evidence_defs (never from
ai_supply_chain_template, those are input-field checks).

Hard constraints (per spec §3):
- blocked  → caller must NOT write_text, NOT _persist_report
- warning  → caller annotates text and persists with gate=verdict
- pass     → original behavior unchanged

This module has ZERO imports from:
  backend.agents, backend.decision, backend.scheduler,
  LongTermTeam, aggregate, aggregate_v2, run_pipeline,
  apply_research_constraints, _aggregate_score.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING

from backend.data.news_audit import WEAK_SOURCE_KEYWORDS
from backend.research.research_evidence_defs import ResearchPriorityBand, scan_forbidden_wording

if TYPE_CHECKING:
    from backend.data.news_audit import NewsAudit
    from backend.research.deep_research import DeepResearchReport
    from backend.research.serenity_chokepoint import SerenityChokepointReport

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GateVerdict:
    """Result of run_research_report_gate.

    status: 'pass' | 'warning' | 'blocked'
    reasons: human-readable descriptions of BLOCKED conditions
    warnings: human-readable descriptions of WARNING conditions
    """

    status: str                        # 'pass' | 'warning' | 'blocked'
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_research_report_gate(
    report: DeepResearchReport,
    audits: list[NewsAudit],
    rendered_text: str,
    *,
    llm_text: str | None = None,
    weak_source_count: int = 0,
    prices: list[dict] | None = None,
    financials: list[dict] | None = None,
    serenity: SerenityChokepointReport | None = None,
) -> GateVerdict:
    """Run all gate checks and return a single GateVerdict.

    Checks (from spec §2):
    1. Source integrity
    2. Timeline / lookahead
    3. Data coverage (prices / financials)
    4. Narrative evidence quality
    5. LLM out-of-bounds wording
    6. Serenity strictness layer (only if serenity is not None)

    ``rendered_text`` is the full rendered Markdown (used for non-wording checks
    that may need it in future).  ``llm_text`` is the LLM-generated content only
    (sections / summary / catalysts / risks) — the forbidden-wording scan runs
    against ``llm_text`` so that news titles embedded in the source-audit section
    do NOT cause false positives.  When ``llm_text`` is None the gate falls back
    to ``rendered_text`` for backward compatibility.
    """
    blocked: list[str] = []
    warnings: list[str] = []

    _check_source_integrity(report, audits, blocked, warnings)
    _check_timeline(report, audits, blocked, warnings)
    _check_data_coverage(report, prices, financials, blocked, warnings)
    _check_narrative_evidence(report, audits, weak_source_count, blocked, warnings)
    # F1: scan only LLM-generated text, never the full rendered output that
    # contains raw news titles from the source-audit section.
    wording_target = llm_text if llm_text is not None else rendered_text
    _check_forbidden_wording(wording_target, blocked, warnings)

    if serenity is not None:
        _check_serenity_layer(serenity, blocked, warnings)

    if blocked:
        return GateVerdict(status="blocked", reasons=blocked, warnings=warnings)
    if warnings:
        return GateVerdict(status="warning", reasons=[], warnings=warnings)
    return GateVerdict(status="pass", reasons=[], warnings=[])


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_source_integrity(
    report: DeepResearchReport,
    audits: list[NewsAudit],
    blocked: list[str],
    warnings: list[str],
) -> None:
    """Check 1: Source integrity.

    F5: source_count == 0 (no news found) is a *warning*, not a hard block.
    A pure-framework / offline report with no recent news is legitimate; the
    caller renders it with "本地数据库暂无近 14 日新闻" and that is fine.
    Hard-blocking only happens when there ARE audit records but none is usable.
    """
    if report.source_count == 0:
        # F5: downgrade to warning — pure-framework report is allowed through.
        warnings.append(
            "来源完整性：source_count == 0，无近期新闻；报告仅保留结构化研究框架"
        )
        return

    has_usable = any(a.usable for a in audits)
    if not has_usable and audits:
        # There ARE audit records, but all failed quality checks → hard block.
        blocked.append("来源完整性：所有审计来源均不可用（usable=False）")
        return

    # Warning: all usable sources carry the weak_source risk flag (F9: use only
    # the structured flag emitted by news_audit, not a hand-rolled keyword list).
    all_rumour = all(
        "weak_source" in a.risk_flags
        for a in audits
        if a.usable
    )
    if all_rumour and any(a.usable for a in audits):
        warnings.append("来源完整性：所有可用来源均含网传/传闻风险标记，建议补充直接来源")


def _check_timeline(
    report: DeepResearchReport,
    audits: list[NewsAudit],
    blocked: list[str],
    warnings: list[str],
) -> None:
    """Check 2: Timeline / lookahead guard."""
    try:
        as_of_date = datetime.strptime(report.as_of, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        warnings.append(f"时间线：as_of 格式无法解析 ({report.as_of!r})，跳过 lookahead 检查")
        return

    future_titles: list[str] = []
    for audit in audits:
        if not audit.usable:
            continue
        pub = audit.news.published_at
        if pub is None:
            continue
        # Normalize to date
        if isinstance(pub, datetime):
            pub_date = pub.date()
        elif isinstance(pub, date):
            pub_date = pub
        else:
            continue
        if pub_date > as_of_date:
            future_titles.append(audit.title[:60])
    # F8: Removed unreliable day==1 month-granularity heuristic.
    # RawNews / NewsAudit have no granularity field, and day==1 is a false
    # positive for legitimate news published on the first of any month.

    if future_titles:
        blocked.append(
            f"时间线 lookahead：{len(future_titles)} 条关键证据日期晚于 as_of ({report.as_of})："
            f" {future_titles[:3]}"
        )


def _check_data_coverage(
    report: DeepResearchReport,
    prices: list[dict] | None,
    financials: list[dict] | None,
    blocked: list[str],
    warnings: list[str],
) -> None:
    """Check 3: Data coverage — prices and financials.

    Design decision (M50 Phase 1 收尾): this check emits **warning only, never
    blocked**.  Rationale: an evidence-empty report is already hard-blocked by
    check 1 (source_count == 0); the absence of price/financial rows does NOT
    make a qualitative supply-chain thesis untrustworthy when it has good
    sources (a pure-theme report legitimately has symbols=[] and no prices).
    See docs/dev/m50_research_report_gate_spec.md §2.

    When prices/financials are passed (from the deep_research hook) we use real
    availability; otherwise we fall back to the sections proxy for direct
    callers that don't thread the raw context.
    """
    # Only meaningful when the report claims to research specific symbols.
    if not report.symbols:
        return

    if prices is not None or financials is not None:
        prices = prices or []
        financials = financials or []
        any_price = any(p.get("available") for p in prices)
        any_financial = any(f.get("available") for f in financials)
        if not any_price and not any_financial:
            warnings.append(
                "数据覆盖：所研标的均无价格/财务数据，结论缺量化支撑，建议补充"
            )
        return

    # Fallback: sections proxy (no raw prices/financials threaded in).
    if report.source_count == 0:
        return
    sections = report.sections or ()
    has_data = any(
        s.get("catalysts") or s.get("evidence_snippets")
        for s in sections
        if isinstance(s, dict)
    )
    if not has_data and sections:
        warnings.append("数据覆盖：sections 中未检测到价格/财务证据片段，建议补充结构化数据")


def _check_narrative_evidence(
    report: DeepResearchReport,
    audits: list[NewsAudit],
    weak_source_count: int,
    blocked: list[str],
    warnings: list[str],
) -> None:
    """Check 4: Narrative-only evidence check."""
    usable_audits = [a for a in audits if a.usable]
    if not usable_audits:
        # Already handled in source integrity; skip here.
        return

    # Determine source URL/source field to classify tier.
    # F9: prefer structured 'weak_source' risk flag; fall back to imported
    # WEAK_SOURCE_KEYWORDS from news_audit (single source of truth, no fork).
    def _is_narrative_only(audit: NewsAudit) -> bool:
        if "weak_source" in audit.risk_flags:
            return True
        src = (audit.news.source or "").lower()
        url = (audit.news.url or "").lower()
        return any(kw in src or kw in url for kw in WEAK_SOURCE_KEYWORDS)

    narrative_count = sum(1 for a in usable_audits if _is_narrative_only(a))
    total_usable = len(usable_audits)

    if total_usable > 0 and narrative_count == total_usable:
        blocked.append(
            "叙事证据：所有可用来源均为媒体叙事/社媒，无公告/财报/订单等一手证据"
        )
        return

    if weak_source_count > 0 and total_usable > 0:
        ratio = weak_source_count / (total_usable + weak_source_count)
        if ratio > 0.5:
            warnings.append(
                f"叙事证据：弱证据来源占比 {ratio:.0%}（weak_source_count={weak_source_count}），"
                f"建议补充更高等级证据"
            )


def _check_forbidden_wording(
    rendered_text: str,
    blocked: list[str],
    warnings: list[str],
) -> None:
    """Check 5: LLM out-of-bounds wording in rendered text."""
    hits = scan_forbidden_wording(rendered_text)
    strong_hits = [h for h in hits if h.endswith(":strong")]
    soft_hits = [h for h in hits if h.endswith(":warning")]

    if strong_hits:
        patterns = [h.rsplit(":", 1)[0] for h in strong_hits]
        blocked.append(
            f"LLM 越界措辞：检测到荐股式断言 {patterns}，报告不应包含买卖指令"
        )
    if soft_hits:
        patterns = [h.rsplit(":", 1)[0] for h in soft_hits]
        warnings.append(f"LLM 语气偏强：检测到措辞 {patterns}，建议改为中性表述")


def _check_serenity_layer(
    serenity: SerenityChokepointReport,
    blocked: list[str],
    warnings: list[str],
) -> None:
    """Check 6: Serenity strictness layer (only called when serenity is not None)."""
    # quick_filter_pass == False → warning
    if not serenity.quick_filter_pass:
        warnings.append(
            f"Serenity 加严：quick_filter_pass=False（层位：{serenity.scarce_layer}），"
            f"主题未通过快速筛选"
        )

    # research_priority_band == ResearchPriorityBand.insufficient → blocked (when
    # heading to promotion). Phase 1: pure report path — treat as warning, not
    # blocked (blocked only when memory promotion is triggered; that's Phase 2).
    if serenity.research_priority_band == ResearchPriorityBand.insufficient:
        warnings.append(
            "Serenity 加严：research_priority_band=证据不足，不建议将此报告升级为 memory candidate"
        )

    # falsification_questions empty → warning
    if not serenity.falsification_questions:
        warnings.append("Serenity 加严：falsification_questions 为空，反方先行未完成")


# ---------------------------------------------------------------------------
# Text annotation helper
# ---------------------------------------------------------------------------

def _annotate_warnings(text: str, verdict: GateVerdict) -> str:
    """Append gate warnings block to the rendered report text."""
    if not verdict.warnings:
        return text
    lines = [
        "",
        "---",
        "",
        "## ⚠️ Gate 检查警告",
        "",
        "本报告通过 ResearchReportGate 基线检查，但存在以下警告项，请研究时注意：",
        "",
    ]
    for i, w in enumerate(verdict.warnings, 1):
        lines.append(f"{i}. {w}")
    lines.append("")
    lines.append("*警告由 M50 ResearchReportGate 自动生成，不影响 official 信号。*")
    lines.append("")
    return text + "\n".join(lines)
