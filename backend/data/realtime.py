"""
实时行情：直连东方财富 API，绕过系统代理（proxies=None）。
不修改任何系统代理配置，仅对这个模块的请求禁用代理。
"""
import logging
import requests

logger = logging.getLogger(__name__)

# 东方财富实时行情接口
_URL = "https://push2.eastmoney.com/api/qt/stock/get"

# 市场前缀：SH=1, SZ=0
_MARKET_PREFIX = {
    "60": "1", "68": "1",          # 上证主板 / 科创板
    "00": "0", "30": "0", "30": "0",  # 深证主板 / 创业板
}

_FIELDS = "f43,f57,f58,f169,f170,f46,f44,f45,f51,f52,f47,f48,f50"
# f43=最新价 f57=代码 f58=名称 f169=涨跌额 f170=涨跌幅(×100)
# f46=今开  f44=最低 f45=最高 f51=涨停 f52=跌停
# f47=成交量(手) f48=成交额 f50=量比


def _market_prefix(code: str) -> str:
    return _MARKET_PREFIX.get(code[:2], "0")


def fetch_realtime_quote(symbol: str) -> dict | None:
    """
    获取单只A股实时行情。
    返回 dict，价格单位：元（已除以100）；失败返回 None。
    """
    secid = f"{_market_prefix(symbol)}.{symbol}"
    try:
        resp = requests.get(
            _URL,
            params={"secid": secid, "fields": _FIELDS, "ut": "fa5fd1943c7b386f172d6893dbfba10b"},
            proxies={"http": None, "https": None},  # 直连，绕过系统代理
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json().get("data") or {}
        if not data or data.get("f43", "-") in ("-", None):
            return None
        return {
            "symbol":   data.get("f57", symbol),
            "name":     data.get("f58", ""),
            "price":    _div100(data.get("f43")),
            "open":     _div100(data.get("f46")),
            "high":     _div100(data.get("f44")),
            "low":      _div100(data.get("f45")),
            "pct_chg":  _div100(data.get("f170")),   # 涨跌幅，已是百分比×100
            "chg":      _div100(data.get("f169")),
            "limit_up": _div100(data.get("f51")),
            "limit_dn": _div100(data.get("f52")),
            "volume":   data.get("f47"),              # 手
            "amount":   data.get("f48"),              # 元
        }
    except Exception as e:
        logger.warning("realtime fetch failed %s: %s", symbol, e)
        return None


def fetch_realtime_quotes(symbols: list[str]) -> dict[str, dict]:
    """批量获取，返回 {symbol: quote_dict}，失败的股票不在结果中。"""
    result = {}
    for sym in symbols:
        q = fetch_realtime_quote(sym)
        if q:
            result[sym] = q
    return result


def _div100(val):
    if val is None or val == "-":
        return None
    try:
        return round(float(val) / 100, 2)
    except (TypeError, ValueError):
        return None
