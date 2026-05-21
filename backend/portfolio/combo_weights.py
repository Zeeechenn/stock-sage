"""
仓位管理模块
三种仓位算法：等权 / 凯利 / 波动率加权

输入：候选股票列表 + 历史统计 → 输出：每只股票的仓位权重（和为1）
"""


# ── 等权分配 ─────────────────────────────────────────────────────────
def equal_weight(n: int, max_per: float = 0.30) -> list[float]:
    """
    等权分配，每只 min(1/n, max_per)。
    剩余权重留作现金（不做归一化，避免破坏单股上限）。
    n=5, max_per=0.30 → [0.2, 0.2, 0.2, 0.2, 0.2]
    n=2, max_per=0.20 → [0.2, 0.2]（40% 现金）
    """
    if n <= 0:
        return []
    w = min(1.0 / n, max_per)
    return [round(w, 6)] * n


# ── 凯利准则 ─────────────────────────────────────────────────────────
def kelly_weight(
    candidates: list[dict],
    win_rate_default: float = 0.50,
    avg_win_default: float = 5.0,
    avg_loss_default: float = 3.5,
    fraction: float = 0.5,          # half-Kelly，控制激进程度
    max_per: float = 0.30,
) -> list[float]:
    """
    半凯利仓位分配。
    candidates 列表中若含 win_rate / avg_win / avg_loss 字段则优先使用；
    否则使用默认值（来自 backtest_v3 有色金属板块统计）。

    Kelly公式：f* = (p*b - q) / b，其中 b = avg_win/avg_loss，q=1-p
    实际使用 half-Kelly = f* * fraction，并限制最大仓位。
    """
    if not candidates:
        return []

    raw = []
    for c in candidates:
        p    = c.get("win_rate", win_rate_default)
        aw   = c.get("avg_win",  avg_win_default)
        al   = c.get("avg_loss", avg_loss_default)
        b    = aw / max(al, 0.1)
        q    = 1 - p
        f    = (p * b - q) / b if b > 0 else 0.0
        f    = max(0.0, f) * fraction          # half-Kelly，剔除负值
        f    = min(f, max_per)
        raw.append(f)

    total = sum(raw)
    if total <= 0:
        return equal_weight(len(candidates), max_per)
    if total > 1.0:
        # scale down to fit within 100% capital, re-apply per-stock cap
        return [round(min(x / total, max_per), 6) for x in raw]
    return [round(x, 6) for x in raw]


# ── 波动率加权（逆波动率） ────────────────────────────────────────────
def vol_weight(
    candidates: list[dict],
    max_per: float = 0.30,
) -> list[float]:
    """
    逆波动率加权：波动率越低 → 权重越高，各位置风险贡献趋于均等。
    candidates 中须含 'vol20' 字段（20日年化波动率，%）。
    缺失时退化为等权。
    """
    if not candidates:
        return []

    vols: list[float | None] = [c.get("vol20", None) for c in candidates]
    if any(v is None or v <= 0 for v in vols):
        return equal_weight(len(candidates), max_per)

    valid_vols = [v for v in vols if v is not None]
    inv = [1.0 / v for v in valid_vols]
    total_inv = sum(inv)
    raw = [min(x / total_inv, max_per) for x in inv]
    # Don't renormalize — sum < 1 means remaining is cash, preserving per-stock cap
    return [round(x, 6) for x in raw]


# ── 板块集中度检查 ────────────────────────────────────────────────────
def apply_sector_cap(
    candidates: list[dict],
    weights: list[float],
    sector_max: float = 0.40,
    max_per: float | None = None,
) -> list[float]:
    """
    对同一板块的持仓总权重不超过 sector_max（默认40%）。
    超出时按比例削减，剩余权重重新分配给其他板块。
    最多迭代3轮收敛。
    """
    w = list(weights)
    for _ in range(3):
        sector_sum: dict[str, float] = {}
        for c, wi in zip(candidates, w, strict=False):
            sec = c.get("sector", "未知")
            sector_sum[sec] = sector_sum.get(sec, 0) + wi

        adjusted = False
        for sec, sw in sector_sum.items():
            if sw > sector_max + 1e-9:
                scale = sector_max / sw
                excess = sw - sector_max
                other_sum = sum(wj for c, wj in zip(candidates, w, strict=False)
                                if c.get("sector") != sec)
                for k, c in enumerate(candidates):
                    if c.get("sector") == sec:
                        w[k] *= scale
                    elif other_sum > 0:
                        w[k] += excess * (w[k] / other_sum)
                    if max_per is not None:
                        w[k] = min(w[k], max_per)
                adjusted = True

        if not adjusted:
            break

    # Only normalize down if total exceeds 100%; never inflate weights
    total = sum(w)
    if total > 1.0 + 1e-9:
        w = [x / total for x in w]
    if max_per is not None:
        w = [min(x, max_per) for x in w]
    return [round(x, 6) for x in w]


# ── 汇总入口 ─────────────────────────────────────────────────────────
def size_positions(
    candidates: list[dict],
    method: str = "equal",        # "equal" | "kelly" | "vol"
    max_per: float = 0.30,
    sector_max: float = 0.40,
) -> list[dict]:
    """
    对 candidates 列表按指定方法计算仓位权重，返回含 weight 字段的新列表。

    Args:
        candidates: pick_stocks() 返回的列表，每项含 sym/name/sector/vol20 等
        method:     仓位算法
        max_per:    单股最大权重（默认30%）
        sector_max: 单板块最大权重（默认40%）

    Returns:
        同 candidates，每项追加 weight（0~1）和 capital_pct（%）字段
    """
    if not candidates:
        return []

    if method == "kelly":
        weights = kelly_weight(candidates, max_per=max_per)
    elif method == "vol":
        weights = vol_weight(candidates, max_per=max_per)
    else:
        weights = equal_weight(len(candidates), max_per=max_per)

    weights = apply_sector_cap(candidates, weights, sector_max, max_per=max_per)

    result = []
    for c, w in zip(candidates, weights, strict=False):
        item = dict(c)
        item["weight"]      = w
        item["capital_pct"] = round(w * 100, 2)
        result.append(item)
    return result


# ── 快速测试 ────────────────────────────────────────────────────────
if __name__ == "__main__":
    test = [
        {"sym": "sh601899", "name": "紫金矿业", "sector": "有色金属",
         "vol20": 35.0, "win_rate": 0.60, "avg_win": 8.0, "avg_loss": 4.0},
        {"sym": "sh603986", "name": "兆易创新", "sector": "半导体",
         "vol20": 55.0, "win_rate": 0.53, "avg_win": 6.0, "avg_loss": 4.5},
        {"sym": "sz300308", "name": "中际旭创", "sector": "AI算力",
         "vol20": 70.0, "win_rate": 0.50, "avg_win": 7.0, "avg_loss": 5.0},
        {"sym": "sz300750", "name": "宁德时代", "sector": "新能源",
         "vol20": 40.0, "win_rate": 0.52, "avg_win": 5.5, "avg_loss": 4.0},
        {"sym": "sh600309", "name": "万华化学", "sector": "化工",
         "vol20": 30.0, "win_rate": 0.50, "avg_win": 5.0, "avg_loss": 3.5},
    ]

    for method in ["equal", "kelly", "vol"]:
        sized = size_positions(test, method=method)
        print(f"\n{method.upper()} 分配：")
        for s in sized:
            print(f"  {s['name']:8} [{s['sector']:6}]  vol={s.get('vol20','-'):5}  "
                  f"权重 {s['weight']:.4f}  ({s['capital_pct']:.2f}%)")
