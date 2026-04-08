"""实时监控模块（模拟交易版）"""
import pandas as pd
from datetime import datetime, timedelta
from config import SZ_REPO_CODES, STRATEGY_CONFIG, INITIAL_CAPITAL
from data.fetcher import fetch_repo_daily, fetch_shibor, fetch_dr007
from data.storage import (
    load_funding_rate, load_repo_daily, load_virtual_trades,
    save_virtual_trade, save_signal, save_repo_daily, save_funding_rate
)
from strategy.signal import generate_signal
from monitor.notifier import send_wechat, format_signal_message
from utils.logger import setup_logger

logger = setup_logger("realtime")


def get_capital_status() -> tuple[bool, str]:
    """
    检查资金是否可用（基于虚拟交易记录）
    :return: (is_available, info)
    """
    trades = load_virtual_trades()
    if trades.empty:
        return True, "无持仓"

    last = trades.iloc[-1]
    buy_date = pd.to_datetime(last["date"])
    days = int(last["days"])
    free_date = buy_date + timedelta(days=days + 1)
    today = datetime.now()

    if today >= free_date:
        return True, f"上笔{last['symbol']}已到期"
    else:
        remain = (free_date - today).days
        return False, f"持有{last['symbol']} 剩余{remain}天"


def select_best_signal(signals: list[dict]) -> dict | None:
    """
    动态选品：根据利率高低选择最优品种
    与回测引擎逻辑一致
    """
    max_days = STRATEGY_CONFIG["max_hold_days"]
    buy_candidates = [
        s for s in signals
        if s["action"] == "建议买入" and s["days"] <= max_days
    ]
    if not buy_candidates:
        return None

    # 判断利率是否处于近期高位
    repo_df = load_repo_daily(symbol="131810")  # R-001作为基准
    if repo_df.empty:
        repo_df = load_repo_daily(symbol="204001")

    is_high_rate = False
    if not repo_df.empty and len(repo_df) >= 5:
        recent = repo_df.tail(20)["close"]
        percentile = STRATEGY_CONFIG["rate_high_percentile"]
        threshold = recent.quantile(percentile / 100)
        current = recent.iloc[-1]
        is_high_rate = current >= threshold

    if is_high_rate:
        prefer_days = STRATEGY_CONFIG["high_rate_prefer_days"]
    else:
        prefer_days = STRATEGY_CONFIG["normal_rate_prefer_days"]

    preferred = [c for c in buy_candidates if c["days"] in prefer_days]
    pool = preferred if preferred else buy_candidates
    # 排序策略：优先利率最高，同利率按评分降序，再按日均收益降序
    pool.sort(key=lambda x: (-x["rate"], -x["score"], -x["daily_profit"]))

    best = pool[0]
    best["select_reason"] = "高位锁定" if is_high_rate else "短期灵活"
    return best


def run_daily_check():
    """
    每日检查：获取当日数据，生成信号，动态选品，推送通知
    建议通过定时任务在交易日14:30-15:00之间运行
    """
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    logger.info(f"开始每日检查: {date_str}")

    # 1. 获取当日逆回购行情（深市）
    repo_data = {}
    daily_frames = []
    for code in SZ_REPO_CODES:
        df = fetch_repo_daily(code, date_str, date_str)
        if not df.empty:
            row = df.iloc[-1]
            repo_data[code] = {"close": row["close"]}
            daily_frames.append(df)

    # 将当日行情存入 repo_daily 表，保持数据持续积累
    if daily_frames:
        save_repo_daily(pd.concat(daily_frames, ignore_index=True))

    if not repo_data:
        logger.warning("今日无逆回购行情数据（可能非交易日）")
        return

    # 2. 获取资金面数据
    dr007_val, shibor_val = None, None
    try:
        dr007_df = fetch_dr007()
        if not dr007_df.empty:
            dr007_val = dr007_df.iloc[-1]["dr007"]
    except Exception as e:
        logger.warning(f"获取DR007失败: {e}")

    try:
        shibor_df = fetch_shibor()
        if not shibor_df.empty:
            shibor_val = shibor_df.iloc[-1]["shibor_on"]
    except Exception as e:
        logger.warning(f"获取Shibor失败: {e}")

    hist_dr007 = None
    funding_df = load_funding_rate()
    if not funding_df.empty and "dr007" in funding_df.columns:
        hist_dr007 = funding_df["dr007"].dropna()

    # 将当日资金面数据存入 funding_rate 表
    if dr007_val is not None or shibor_val is not None:
        today_funding = pd.DataFrame([{
            "date": today.strftime("%Y-%m-%d"),
            "shibor_on": shibor_val,
            "dr007": dr007_val,
        }])
        save_funding_rate(today_funding)

    # 3. 生成信号
    signals = generate_signal(today, repo_data, dr007_val, shibor_val, hist_dr007)

    # 保存信号到虚拟信号表
    for s in signals:
        save_signal(
            s["date"], s["symbol"], s["score"],
            "; ".join(s["reasons"]) if isinstance(s["reasons"], list) else str(s["reasons"]),
            s["action"]
        )

    # 4. 检查资金状态 + 动态选品
    capital_available, capital_info = get_capital_status()
    recommendation = None

    if capital_available:
        recommendation = select_best_signal(signals)
        if recommendation:
            # 记录虚拟交易
            save_virtual_trade(
                today.strftime("%Y-%m-%d"),
                recommendation["symbol"],
                "buy", INITIAL_CAPITAL,
                recommendation["rate"],
                recommendation["days"],
                recommendation["expected_profit"]
            )
            logger.info(
                f"[模拟买入] {recommendation['name']} "
                f"利率:{recommendation['rate']:.2f}% "
                f"[{recommendation['select_reason']}]"
            )

    # 5. 构建推送内容
    title = f"逆回购信号 {today.strftime('%m-%d')}"
    if recommendation:
        title += f" | 建议买入{recommendation['name']}"
    elif not capital_available:
        title += f" | {capital_info}"
    else:
        title += " | 无买入信号"

    content = format_signal_message(signals)
    # 追加选品建议和资金状态
    content += f"<p>资金状态: {capital_info}</p>"
    if recommendation:
        r = recommendation
        content += (
            f"<p>📌 今日建议: <b>{r['name']}({r['symbol']})</b> "
            f"{r['days']}天 利率{r['rate']:.2f}% "
            f"评分{r['score']:.0f} [{r['select_reason']}]</p>"
        )

    send_wechat(title, content)

    # 6. 打印摘要
    print(f"\n{'='*50}")
    print(f"日期: {today.strftime('%Y-%m-%d')} 信号摘要")
    print(f"资金状态: {capital_info}")
    print(f"{'='*50}")
    for s in signals[:5]:
        flag = "✅" if s["action"] == "建议买入" else "⬜"
        print(f"  {flag} {s['name']}({s['symbol']}) "
              f"利率:{s['rate']:.2f}% 评分:{s['score']:.0f}")
    if recommendation:
        print(f"\n  📌 建议买入: {recommendation['name']} "
              f"{recommendation['days']}天 利率:{recommendation['rate']:.2f}% "
              f"[{recommendation['select_reason']}]")
    print(f"{'='*50}\n")

    return signals
