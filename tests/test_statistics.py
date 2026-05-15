"""统计严肃性子系统单元测试 — 验证 DSR/PBO/IC 显著性公式正确性"""
import math
import random


def test_ic_significance_matches_normal_approximation():
    from backend.backtest.statistics import ic_significance

    # IC=0.0228, N=12797（阶段A 当时的数字）
    res = ic_significance(0.0228, 12797)
    assert res.std_err == 1.0 / math.sqrt(12797)
    # t = 0.0228 * sqrt(12797) ≈ 2.58
    assert 2.5 < res.t_stat < 2.7
    # 双尾 p ≈ 0.0099（落在"极显著"边界内侧）
    assert 0.005 < res.p_value_two_sided < 0.02
    assert res.is_significant(alpha=0.05)
    assert res.verdict() == "极显著"


def test_ic_significance_low_sample_not_significant():
    from backend.backtest.statistics import ic_significance

    res = ic_significance(0.05, 100)  # t ≈ 0.5
    assert not res.is_significant()
    assert res.verdict() == "不显著"


def test_ic_significance_handles_degenerate_n():
    from backend.backtest.statistics import ic_significance

    res = ic_significance(0.1, 1)
    assert res.p_value_two_sided == 1.0
    assert res.t_stat == 0.0


def test_expected_max_sharpe_grows_with_n_trials():
    from backend.backtest.statistics import expected_max_sharpe

    # 8 个虚拟 Sharpe，方差固定 → SR_0 应随 n_trials 增大而增大
    sharpes = [0.21, 0.38, 0.39, 0.53, 0.56, 0.57, 0.60, 0.72]
    sr0_small = expected_max_sharpe(sharpes, n_trials=2)
    sr0_large = expected_max_sharpe(sharpes, n_trials=8)
    sr0_huge = expected_max_sharpe(sharpes, n_trials=100)
    assert sr0_small < sr0_large < sr0_huge


def test_deflated_sharpe_penalizes_multi_trial_winners():
    """若是 8 方案扫出来的最高 Sharpe，DSR 应低于单试验下的同 Sharpe"""
    from backend.backtest.statistics import deflated_sharpe

    rng = random.Random(42)
    returns = [rng.gauss(0.001, 0.01) for _ in range(252)]
    trial_sharpes = [0.21, 0.38, 0.39, 0.53, 0.56, 0.57, 0.60, 0.72]
    res_multi = deflated_sharpe(returns, trial_sharpes, sharpe_observed=0.72,
                                n_trials=8)
    res_single = deflated_sharpe(returns, [0.72], sharpe_observed=0.72,
                                 n_trials=1)
    assert res_multi.dsr < res_single.dsr
    assert res_multi.sharpe_threshold > 0


def test_deflated_sharpe_strong_evidence_passes():
    """正态收益 + 高 Sharpe + 长样本 → DSR 应很接近 1"""
    from backend.backtest.statistics import deflated_sharpe

    rng = random.Random(7)
    # 日均收益 0.002，日波动 0.005 → 年化 Sharpe ≈ 6.3（非常强）
    returns = [rng.gauss(0.002, 0.005) for _ in range(2520)]  # 10年日数据
    res = deflated_sharpe(returns, [0.5, 0.7], n_trials=2)
    assert res.dsr > 0.95
    assert res.is_significant()


def test_deflated_sharpe_to_dict_round_trips():
    from backend.backtest.statistics import deflated_sharpe

    returns = [0.01, -0.005, 0.02, -0.01, 0.015]
    res = deflated_sharpe(returns, [0.3, 0.4], n_trials=2)
    d = res.to_dict()
    assert {"sharpe", "dsr", "p_value", "n_trials", "n_samples",
            "skew", "kurt"}.issubset(d.keys())


def test_pbo_zero_for_consistent_winners():
    """构造一个策略在 IS/OOS 上一致领先 → PBO 应低"""
    from backend.backtest.statistics import pbo

    rng = random.Random(1)
    t, n = 240, 4
    matrix = []
    # 策略 0 始终是赢家（drift 较大），其他策略噪音
    for _ in range(t):
        row = [rng.gauss(0.003, 0.01)] + [rng.gauss(0.0, 0.01) for _ in range(n - 1)]
        matrix.append(row)
    res = pbo(matrix, n_blocks=12)
    assert res.pbo < 0.5
    assert res.n_splits > 0


def test_pbo_high_for_random_winners():
    """所有策略均为噪音 → IS 赢家在 OOS 上是随机的，PBO 应接近 0.5"""
    from backend.backtest.statistics import pbo

    rng = random.Random(2)
    t, n = 240, 6
    matrix = [[rng.gauss(0.0, 0.01) for _ in range(n)] for _ in range(t)]
    res = pbo(matrix, n_blocks=12)
    assert 0.3 < res.pbo < 0.7


def test_pbo_handles_short_series():
    from backend.backtest.statistics import pbo

    matrix = [[0.1, 0.2], [0.05, 0.1]]
    res = pbo(matrix, n_blocks=16)
    assert res.pbo == 0.0
    assert res.note


def test_stage_a_ic_audit_reproduces_t_stat():
    """阶段A 历史声称：IC=0.0228 → Qlib 不合格。
    在 N=12797 下 t ≈ 2.58，按现代统计学应判'显著'。
    这条测试是历史结论的回算证据 — 阶段A 当时未做。"""
    from backend.backtest.statistics import ic_significance

    res = ic_significance(0.0228, 12797)
    assert res.is_significant(alpha=0.05), \
        f"IC 0.0228 在 N=12797 时 p={res.p_value_two_sided:.4f}，应被判显著"
