"""
Kronos 量化引擎（可选模块）

有 CUDA GPU 时自动启用真实 Kronos 推理；无 GPU 时静默跳过，不影响主流程。
集成策略：
  - 方向信号：预测未来 pred_len 日收盘均价 vs 当前收盘价 → -100~+100 分
  - 波动率调整因子：预测高低价区间 / ATR → 动态扩大止损空间
  - 预测支撑/阻力：提供给前端展示，不参与信号计算

Phase 3 TODO: 替换 kronos_available() 里的模型路径 / 精调适配 A股数据
"""
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

_predictor = None          # 全局单例，避免重复加载模型
_kronos_available = None   # None = 未检测, True/False = 已检测结果


def _check_and_load(model_name: str = "NeoQuasar/Kronos-small") -> bool:
    """尝试加载 Kronos 模型，成功返回 True，失败返回 False（不抛出异常）"""
    global _predictor, _kronos_available
    if _kronos_available is not None:
        return _kronos_available

    try:
        import torch
        if not torch.cuda.is_available():
            logger.info("Kronos: CUDA not available, skipping.")
            _kronos_available = False
            return False

        from model import Kronos, KronosTokenizer, KronosPredictor  # type: ignore

        tokenizer = KronosTokenizer.from_pretrained(model_name.replace("Kronos-small", "Kronos-Tokenizer-base"))
        model = Kronos.from_pretrained(model_name)
        _predictor = KronosPredictor(model, tokenizer, device="cuda:0", max_context=512)
        _kronos_available = True
        logger.info(f"Kronos loaded: {model_name}")
        return True

    except Exception as e:
        logger.info(f"Kronos unavailable: {e}")
        _kronos_available = False
        return False


def _direction_score(current_close: float, pred_closes: list[float]) -> float:
    """从预测收盘价序列提取方向得分 -100 ~ +100"""
    if not pred_closes or current_close <= 0:
        return 0.0
    avg_pred = float(np.mean(pred_closes))
    pct_change = (avg_pred - current_close) / current_close  # -1 ~ +1 理论上
    score = pct_change * 1000   # 放大：1% 变动 → 10分
    return round(float(np.clip(score, -100, 100)), 1)


def _volatility_adj(pred_df: pd.DataFrame, atr: float) -> float:
    """
    预测波动区间 / ATR → 止损调整系数
    返回值：1.0 = 正常，> 1.0 = 预期高波动（扩大止损），< 1.0 = 低波动
    """
    if atr <= 0:
        return 1.0
    avg_range = (pred_df["high"] - pred_df["low"]).mean()
    ratio = float(avg_range / atr)
    # 限制在 0.5 ~ 2.0，避免极端值
    return round(float(np.clip(ratio, 0.5, 2.0)), 2)


def kronos_analyze(df: pd.DataFrame, atr: float, pred_len: int = 5,
                   model_name: str = "NeoQuasar/Kronos-small") -> dict | None:
    """
    主入口：输入历史 OHLCV DataFrame，返回 Kronos 分析结果。
    无 GPU 或模型未安装时返回 None（调用方需处理 None）。

    返回结构：
      score: float          方向得分 -100 ~ +100
      volatility_adj: float 止损调整系数（传给 aggregator 动态调整 ATR 乘数）
      predicted_high: float 预测未来最高价（前端展示用）
      predicted_low: float  预测未来最低价（前端展示用）
      pred_len: int
    """
    if not _check_and_load(model_name):
        return None

    try:
        required_cols = {"open", "high", "low", "close"}
        if not required_cols.issubset(df.columns):
            return None
        if len(df) < 20:
            return None

        # 取最近 min(len, 512) 根K线作为上下文
        context_df = df.tail(min(len(df), 512)).copy()
        x_ts = context_df.index.to_series()
        # 生成未来 pred_len 个交易日时间戳（简单用最后日期 + offset）
        last_ts = pd.Timestamp(x_ts.iloc[-1])
        y_ts = pd.Series([last_ts + pd.tseries.offsets.BDay(i + 1) for i in range(pred_len)])

        pred_df = _predictor.predict(  # type: ignore
            df=context_df,
            x_timestamp=x_ts,
            y_timestamp=y_ts,
            pred_len=pred_len,
            T=1.0,
            top_p=0.9,
            sample_count=1,
        )

        current_close = float(df["close"].iloc[-1])
        pred_closes = pred_df["close"].tolist() if "close" in pred_df.columns else []

        return {
            "score": _direction_score(current_close, pred_closes),
            "volatility_adj": _volatility_adj(pred_df, atr),
            "predicted_high": round(float(pred_df["high"].max()), 3) if "high" in pred_df.columns else None,
            "predicted_low": round(float(pred_df["low"].min()), 3) if "low" in pred_df.columns else None,
            "pred_len": pred_len,
        }

    except Exception as e:
        logger.warning(f"Kronos inference error: {e}")
        return None
