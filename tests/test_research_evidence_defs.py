"""Tests for backend/research/research_evidence_defs.py."""
from backend.research.research_evidence_defs import (
    SOURCE_TIER,
    SourceTier,
    scan_forbidden_wording,
    stronger_than,
    tier_rank,
)


class TestSourceTier:
    def test_enum_values_exist(self):
        assert SourceTier.primary.value == "primary"
        assert SourceTier.social_lead.value == "social_lead"

    def test_strength_order(self):
        # primary > official > filing > ir > industry > social_lead
        order = [
            SourceTier.primary,
            SourceTier.official,
            SourceTier.filing,
            SourceTier.ir,
            SourceTier.industry,
            SourceTier.social_lead,
        ]
        for i in range(len(order) - 1):
            assert tier_rank(order[i]) > tier_rank(order[i + 1]), (
                f"{order[i]} should rank higher than {order[i+1]}"
            )

    def test_stronger_than(self):
        assert stronger_than(SourceTier.primary, SourceTier.social_lead)
        assert stronger_than(SourceTier.filing, SourceTier.industry)
        assert not stronger_than(SourceTier.social_lead, SourceTier.primary)
        assert not stronger_than(SourceTier.primary, SourceTier.primary)

    def test_source_tier_alias(self):
        assert SOURCE_TIER is SourceTier


class TestScanForbiddenWording:
    def test_clean_text_no_hits(self):
        text = "本报告仅供参考，不构成投资建议。数据来源：东方财富。"
        assert scan_forbidden_wording(text) == []

    def test_strong_hit_mandarin(self):
        text = "综合分析，建议强烈买入该标的，预期收益显著。"
        hits = scan_forbidden_wording(text)
        strong = [h for h in hits if h.endswith(":strong")]
        assert strong, f"Expected strong hit, got: {hits}"

    def test_strong_hit_must_rise(self):
        text = "This stock must rise given current conditions."
        hits = scan_forbidden_wording(text)
        strong = [h for h in hits if h.endswith(":strong")]
        assert strong

    def test_warning_hit_bare_目标价(self):
        """Bare '目标价' without a number should be warning, not blocked."""
        text = "分析师在报告中提到了目标价的概念，但未给出具体数字。"
        hits = scan_forbidden_wording(text)
        # Should have a warning hit
        warning_hits = [h for h in hits if h.endswith(":warning")]
        strong_hits = [h for h in hits if h.endswith(":strong")]
        assert warning_hits, f"Expected warning hit for bare '目标价', got: {hits}"
        assert not strong_hits, f"Should not be strong hit for bare '目标价'"

    def test_strong_hit_目标价_with_number(self):
        """目标价 followed by a number should be a strong hit."""
        text = "分析师给出目标价120元，建议配置。"
        hits = scan_forbidden_wording(text)
        strong = [h for h in hits if h.endswith(":strong")]
        assert strong, f"Expected strong hit for '目标价120', got: {hits}"

    def test_strong_hit_梭哈(self):
        text = "可以梭哈这只股票。"
        hits = scan_forbidden_wording(text)
        strong = [h for h in hits if h.endswith(":strong")]
        assert strong

    def test_strong_hit_抄底(self):
        text = "现在是抄底的好时机。"
        hits = scan_forbidden_wording(text)
        strong = [h for h in hits if h.endswith(":strong")]
        assert strong

    def test_no_false_positive_on_目标(self):
        """Plain '目标' without '价' should not trigger any hit."""
        text = "公司的战略目标是成为行业第一。"
        hits = scan_forbidden_wording(text)
        # Should be empty or only warning (no strong)
        strong = [h for h in hits if h.endswith(":strong")]
        assert not strong

    def test_case_insensitive_english(self):
        text = "Strong Buy recommended by analyst."
        hits = scan_forbidden_wording(text)
        strong = [h for h in hits if h.endswith(":strong")]
        assert strong
