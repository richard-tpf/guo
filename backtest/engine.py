"""回测引擎"""
import pandas as pd
from datetime import datetime, timedelta
from config import SH_REPO_CODES, SZ_REPO_CODES, INITIAL_CAPITAL, STRATEGY_CONFIG
from strategy.signal import generate_signal
from data.storage import load_repo_daily, load_funding_rate, clear_backtest_data, save_backtest_signal, save_backtest_trade
from utils.logger import setup_logger

logger = setup_logger("backtest")

ALL_CODES = {**SH_REPO_CODES, **SZ_REPO_CODES}


def run_backtest(start_date: str, end_date: str) -> pd.DataFrame:
    """
    回测：遍历历史每个交易日，生成信号并统计收益
    资金占用约束：同一时间只能持有一个品种，到期后才能再买
    """
    repo_df = load_repo_daily()
    funding_df = load_funding_rate()

    if repo_df.empty:
        logger.error("无逆回购历史数据，请先运行数据采集")
        return pd.DataFrame()

    # 清空回测表，避免与上次回测数据混淆
    clear_backtest_data()

    repo_df["date"] = pd.to_datetime(repo_df["date"])
    mask = (repo_df["date"] >= start_date) & (repo_df["date"] <= end_date)
    repo_df = repo_df[mask]

    if not funding_df.empty:
        funding_df["date"] = pd.to_datetime(funding_df["date"])

    dates = sorted(repo_df["date"].unique())
    all_signals = []
    executed_trades = []
    capital_free_date = None  # 资金释放日期，None表示当前可用

    for date in dates:
        dt = pd.Timestamp(date).to_pydatetime()
        day_data = repo_df[repo_df["date"] == date]

        # 构建当日行情字典
        repo_data = {}
        for _, row in day_data.iterrows():
            repo_data[row["symbol"]] = {"close": row["close"]}

        # 获取当日资金面数据
        dr007, shibor_on, hist_dr007 = None, None, None
        if not funding_df.empty:
            day_fund = funding_df[funding_df["date"] == date]
            if not day_fund.empty:
                dr007 = day_fund.iloc[0].get("dr007")
                shibor_on = day_fund.iloc[0].get("shibor_on")
            hist = funding_df[funding_df["date"] < date]
            if "dr007" in hist.columns and len(hist) > 0:
                hist_dr007 = hist["dr007"].dropna()

        signals = generate_signal(dt, repo_data, dr007, shibor_on, hist_dr007)

        # 判断资金是否可用
        capital_available = (capital_free_date is None) or (dt >= capital_free_date)

        for s in signals:
            s["capital_available"] = capital_available
            if s["action"] == "建议买入" and not capital_available:
                s["action"] = "资金占用中"

        # 如果资金可用，动态选品
        if capital_available:
            max_days = STRATEGY_CONFIG["max_hold_days"]
            buy_candidates = [
                s for s in signals
                if s["action"] == "建议买入" and s["days"] <= max_days
            ]
            if buy_candidates:
                # 判断当前利率是否处于近期高位
                # 用1天期品种的利率作为基准
                day1_rates = repo_df[
                    (repo_df["symbol"].isin(["204001", "131810"])) &
                    (repo_df["date"] <= date) &
                    (repo_df["date"] >= date - pd.Timedelta(days=30))
                ]["close"]

                is_high_rate = False
                if len(day1_rates) >= 5:
                    percentile = STRATEGY_CONFIG["rate_high_percentile"]
                    threshold = day1_rates.quantile(percentile / 100)
                    current_1d = day1_rates.iloc[-1] if len(day1_rates) > 0 else 0
                    is_high_rate = current_1d >= threshold

                # 动态选品：高利率选长期锁定，一般利率选短期灵活
                if is_high_rate:
                    prefer_days = STRATEGY_CONFIG["high_rate_prefer_days"]
                else:
                    prefer_days = STRATEGY_CONFIG["normal_rate_prefer_days"]

                # 优先从偏好天数中选，没有再从全部候选中选
                preferred = [c for c in buy_candidates if c["days"] in prefer_days]
                pool = preferred if preferred else buy_candidates

                # 排序策略：优先利率最高，同利率按评分降序，再按日均收益降序
                pool.sort(key=lambda x: (-x["rate"], -x["score"], -x["daily_profit"]))
                best = pool[0]
                best["action"] = "已买入"
                best["select_reason"] = "高位锁定" if is_high_rate else "短期灵活"
                capital_free_date = dt + timedelta(days=best["days"] + 1)
                executed_trades.append(best)

                # 保存回测交易到数据库
                save_backtest_trade(
                    best["date"], best["symbol"], "buy",
                    INITIAL_CAPITAL, best["rate"], best["days"], best["expected_profit"]
                )

        # 保存回测信号到数据库
        for s in signals:
            save_backtest_signal(
                s["date"], s["symbol"], s["score"],
                "; ".join(s["reasons"]) if isinstance(s["reasons"], list) else str(s["reasons"]),
                s["action"]
            )

        all_signals.extend(signals)

    if not all_signals:
        logger.warning("回测期间无信号产生")
        return pd.DataFrame()

    result = pd.DataFrame(all_signals)
    total_profit = sum(t["expected_profit"] for t in executed_trades)
    trade_count = len(executed_trades)

    logger.info(f"回测完成: {start_date} ~ {end_date}")
    logger.info(f"总交易日: {len(dates)}")
    logger.info(f"实际执行交易: {trade_count} 笔")
    logger.info(f"预期总收益: {total_profit:.4f}元 (本金{INITIAL_CAPITAL}元)")
    logger.info(f"预期年化: {total_profit / INITIAL_CAPITAL * 100:.2f}%")

    # 打印执行的交易明细
    if executed_trades:
        print(f"\n{'='*60}")
        print(f"实际执行交易明细（资金约束后）")
        print(f"{'='*60}")
        for t in executed_trades:
            reason = t.get("select_reason", "")
            print(f"  {t['date']} {t['name']}({t['symbol']}) "
                  f"{t['days']}天 利率:{t['rate']:.2f}% "
                  f"评分:{t['score']:.0f} 收益:{t['expected_profit']:.4f}元 "
                  f"[{reason}]")
        print(f"{'='*60}")
        print(f"  总交易: {trade_count}笔 | 总收益: {total_profit:.4f}元 "
              f"| 年化: {total_profit / INITIAL_CAPITAL * 100:.2f}%")
        print(f"{'='*60}\n")

    return result
