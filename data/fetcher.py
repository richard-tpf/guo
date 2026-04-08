"""数据采集模块 - 多数据源（腾讯财经优先，Tushare次选，东方财富备选）"""
import time
import random
import requests
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from utils.logger import setup_logger

logger = setup_logger("fetcher")

# Tushare 延迟初始化
_ts_api = None


def _get_tushare_api():
    """延迟初始化 Tushare API"""
    global _ts_api
    if _ts_api is None:
        try:
            from config import TUSHARE_TOKEN
            if not TUSHARE_TOKEN:
                return None
            import tushare as ts
            ts.set_token(TUSHARE_TOKEN)
            _ts_api = ts.pro_api()
        except (ImportError, Exception):
            return None
    return _ts_api


def _fetch_via_tencent(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    通过腾讯财经公开接口获取日K线（无需token，限流宽松，首选）
    接口: web.ifzq.gtimg.cn/appstock/app/fqkline/get
    """
    # 腾讯接口代码格式：深市 sz131810，沪市 sh204001
    if symbol.startswith("13") or symbol.startswith("12"):
        tc_symbol = f"sz{symbol}"
    else:
        tc_symbol = f"sh{symbol}"

    start_dt = datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        "param": f"{tc_symbol},day,{start_str},{end_str},640,qfq",
        "_var": "kline_dayqfq",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://web.ifzq.gtimg.cn/",
    }

    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()

    # 响应格式: kline_dayqfq={json}
    text = resp.text
    # 去掉变量赋值前缀，提取JSON
    if "=" in text:
        text = text.split("=", 1)[1].strip()
    import json
    data = json.loads(text)

    # 解析K线数据
    stock_data = data.get("data", {}).get(tc_symbol, {})
    # 尝试多个可能的key: day, qfqday, priceday
    klines = stock_data.get("day") or stock_data.get("qfqday") or []
    if not klines:
        return pd.DataFrame()

    # 每条记录: [日期, 开盘, 收盘, 最高, 最低, 成交量]
    rows = []
    for k in klines:
        if len(k) >= 6:
            rows.append({
                "date": k[0],
                "open": float(k[1]),
                "close": float(k[2]),
                "high": float(k[3]),
                "low": float(k[4]),
                "volume": float(k[5]),
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = symbol
    # 按日期范围过滤
    df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]
    return df[["date", "symbol", "open", "high", "low", "close", "volume"]]


def _fetch_via_tushare(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """通过 Tushare 获取日行情（需要积分权限）"""
    api = _get_tushare_api()
    if api is None:
        raise RuntimeError("Tushare 不可用")

    if symbol.startswith("13") or symbol.startswith("12"):
        ts_code = f"{symbol}.SZ"
    else:
        ts_code = f"{symbol}.SH"

    df = api.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.rename(columns={
        "trade_date": "date", "open": "open", "close": "close",
        "high": "high", "low": "low", "vol": "volume",
    })
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = symbol
    df = df.sort_values("date").reset_index(drop=True)
    return df[["date", "symbol", "open", "high", "low", "close", "volume"]]


def _fetch_via_eastmoney(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """通过东方财富获取日行情（限流严格，最后备选）"""
    df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                            start_date=start_date, end_date=end_date, adjust="")
    if df.empty:
        return pd.DataFrame()

    df = df.rename(columns={
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume",
    })
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = symbol
    return df[["date", "symbol", "open", "high", "low", "close", "volume"]]


def fetch_repo_daily(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取逆回购日行情（三数据源自动降级：腾讯 -> Tushare -> 东方财富）
    """
    sources = [
        ("腾讯财经", _fetch_via_tencent),
        ("Tushare", _fetch_via_tushare),
        ("东方财富", _fetch_via_eastmoney),
    ]

    for source_name, fetch_fn in sources:
        try:
            time.sleep(0.3 + random.uniform(0, 0.3))
            df = fetch_fn(symbol, start_date, end_date)
            if df.empty:
                logger.warning(f"[{source_name}] 品种 {symbol} 无数据")
                continue
            logger.info(f"[{source_name}] 获取 {symbol} 数据 {len(df)} 条")
            return df
        except Exception as e:
            logger.warning(f"[{source_name}] 获取 {symbol} 失败: {e}")
            continue

    logger.error(f"品种 {symbol} 所有数据源均失败")
    return pd.DataFrame()


def fetch_repo_rate_hist(start_date: str, end_date: str) -> pd.DataFrame:
    """获取回购定盘利率（银行间市场，含FR001/FR007等），开始与结束需在一个月内"""
    try:
        df = ak.repo_rate_hist(start_date=start_date, end_date=end_date)
        if df.empty:
            logger.warning(f"回购定盘利率 {start_date}-{end_date} 无数据")
            return pd.DataFrame()
        logger.info(f"获取回购定盘利率 {len(df)} 条")
        return df
    except Exception as e:
        logger.error(f"获取回购定盘利率失败: {e}")
        return pd.DataFrame()


def fetch_repo_rate_hist_range(start_date: str, end_date: str) -> pd.DataFrame:
    """按月分批获取回购定盘利率（绕过一个月限制）"""
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    frames = []
    current = start
    while current < end:
        month_end = min(current + timedelta(days=28), end)
        s = current.strftime("%Y%m%d")
        e = month_end.strftime("%Y%m%d")
        df = fetch_repo_rate_hist(s, e)
        if not df.empty:
            frames.append(df)
        current = month_end + timedelta(days=1)
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()


def fetch_shibor() -> pd.DataFrame:
    """获取Shibor隔夜利率"""
    try:
        df = ak.rate_interbank(
            market="上海银行同业拆借市场",
            symbol="Shibor人民币",
            indicator="隔夜"
        )
        if df.empty:
            logger.warning("Shibor数据为空")
            return pd.DataFrame()
        df = df.rename(columns={"报告日": "date", "利率": "shibor_on"})
        df["date"] = pd.to_datetime(df["date"])
        logger.info(f"获取Shibor数据 {len(df)} 条")
        return df[["date", "shibor_on"]]
    except Exception as e:
        logger.error(f"获取Shibor数据失败: {e}")
        return pd.DataFrame()


def fetch_dr007() -> pd.DataFrame:
    """获取银行间隔夜拆借利率（Chibor隔夜）作为DR007替代"""
    try:
        df = ak.rate_interbank(
            market="中国银行同业拆借市场",
            symbol="Chibor人民币",
            indicator="隔夜"
        )
        if df.empty:
            logger.warning("Chibor隔夜数据为空")
            return pd.DataFrame()
        df = df.rename(columns={"报告日": "date", "利率": "dr007"})
        df["date"] = pd.to_datetime(df["date"])
        logger.info(f"获取Chibor隔夜数据 {len(df)} 条（作为DR007替代）")
        return df[["date", "dr007"]]
    except Exception as e:
        logger.error(f"获取Chibor隔夜数据失败: {e}")
        return pd.DataFrame()


def fetch_all_repo_daily(codes: dict, start_date: str, end_date: str) -> pd.DataFrame:
    """批量获取多个逆回购品种的日行情"""
    frames = []
    for i, code in enumerate(codes):
        if i > 0:
            time.sleep(0.5 + random.uniform(0, 0.5))
        df = fetch_repo_daily(code, start_date, end_date)
        if not df.empty:
            frames.append(df)
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()
