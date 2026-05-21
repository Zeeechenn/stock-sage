"""Walk-forward harness 单元测试 — 不依赖 DB"""


def test_generate_windows_respects_holdout():
    from backend.backtest.walk_forward import HOLDOUT_START, generate_windows

    windows = generate_windows("2024-01-01", "2026-05-15",
                               train_days=365, test_days=60, step_days=60)
    assert len(windows) >= 1
    for w in windows:
        assert w.test_end < HOLDOUT_START, f"窗口 {w.label} 越界 holdout"
        assert w.train_end < w.test_start
        assert w.test_start <= w.test_end


def test_generate_windows_progressive_step():
    from backend.backtest.walk_forward import generate_windows

    windows = generate_windows("2024-01-01", "2025-12-31",
                               train_days=180, test_days=30, step_days=30)
    assert len(windows) >= 2
    for i in range(1, len(windows)):
        assert windows[i].train_start > windows[i - 1].train_start
        assert windows[i].test_start > windows[i - 1].test_start


def test_generate_windows_handles_short_range():
    from backend.backtest.walk_forward import generate_windows

    windows = generate_windows("2025-12-01", "2025-12-15",
                               train_days=365, test_days=60, step_days=60)
    assert windows == []


def test_run_walk_forward_aggregates_metric():
    from backend.backtest.walk_forward import generate_windows, run_walk_forward

    windows = generate_windows("2024-01-01", "2025-12-31",
                               train_days=180, test_days=60, step_days=60)

    def evaluator(w):
        seed = sum(int(c) for c in w.test_start if c.isdigit())
        return {"sharpe": (seed % 7) * 0.1, "n": seed}

    res = run_walk_forward(windows, evaluator, metric_key="sharpe")
    assert res["summary"]["n_windows"] == len(windows)
    assert res["summary"]["n_evaluated"] == len(windows)
    assert "mean" in res["summary"]
    assert "multi_window_sr_threshold" in res["summary"]
    assert len(res["per_window"]) == len(windows)


def test_run_walk_forward_handles_evaluator_exception():
    from backend.backtest.walk_forward import WalkWindow, run_walk_forward

    windows = [
        WalkWindow("2024-01-01", "2024-06-30", "2024-07-01", "2024-08-30"),
        WalkWindow("2024-03-01", "2024-08-31", "2024-09-01", "2024-10-30"),
    ]

    def evaluator(w):
        if w.test_start == "2024-09-01":
            raise RuntimeError("boom")
        return {"sharpe": 1.0}

    res = run_walk_forward(windows, evaluator)
    assert res["summary"]["n_windows"] == 2
    assert res["summary"]["n_evaluated"] == 1
    assert any("error" in p for p in res["per_window"])


def test_holdout_window_default_uses_today():
    from backend.backtest.walk_forward import HOLDOUT_START, holdout_window

    w = holdout_window()
    assert w.test_start == HOLDOUT_START
    assert w.test_end >= HOLDOUT_START
    assert w.train_start == ""  # holdout 无 train


def test_holdout_window_explicit_end():
    from backend.backtest.walk_forward import holdout_window

    w = holdout_window(start="2026-01-01", end="2026-05-15")
    assert w.test_start == "2026-01-01"
    assert w.test_end == "2026-05-15"
    assert "HOLDOUT" in w.label
