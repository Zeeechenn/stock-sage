"""统计严肃性子系统 — DSR / PBO / IC 显著性。

设计动机：让"我的 Sharpe / IC 在统计学上能不能信"成为项目可回答的问题。
参考：Bailey & López de Prado, SSRN 2460551 (DSR) + 2326253 (PBO)。
"""
from backend.backtest.statistics.deflated_sharpe import (
    DSRResult,
    deflated_sharpe,
    expected_max_sharpe,
)
from backend.backtest.statistics.probability_overfitting import (
    PBOResult,
    pbo,
)
from backend.backtest.statistics.significance import (
    ICSignificance,
    ic_significance,
)

__all__ = [
    "DSRResult", "deflated_sharpe", "expected_max_sharpe",
    "PBOResult", "pbo",
    "ICSignificance", "ic_significance",
]
