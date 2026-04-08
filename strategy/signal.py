"""信号生成模块

综合日历效应 + 资金面 + 利率水平，生成买入信号
评分体系（满分100）：
- 日历效应：0-40分
- 资金面：0-30分
- 利率水平：0-30分
"""
import pandas as pd
from datetime import datetime
from config import STRATEGY_CONFIG, SH_REPO_CODES, SZ_REPO_CODES, INITIAL_CAPITAL
from strategy.calendar_effect import calc_calendar_score
from strategy.funding_rate import calc_funding_score
from utils.logger import setup_logger

logger = setup_logger("signal")

ALL_CODES = {**SH_REPO_CODES, **SZ_REPO_CODES}


def calc_rate_score(current_rate: float) -> tuple[float, list[str]]:
    """
    利率水平评分（连续评分，区分度更高）
    :param current_rate: 当前年化利率（%）
    :return: (score, reasons) score 0-30
    """
    reasons = []
    threshold = STRATEGY_CONFIG["rate_threshold"]
    max_rate = threshold * 3  # 满分对应的利率上限

    if current_rate <= 0:
        return 0.0, [f"利率{current_rate:.2f}%无效"]

    if current_rate >= max_rate:
        score = 30.0
        reasons.append(f"利率{current_rate:.2f}%极高(>={max_rate:.1f}%)")
    elif current_rate >= threshold * 0.8:
        # 线性插值：从 threshold*0.8 到 max_rate 映射到 5~30 分
        score = 5 + (current_rate - threshold * 0.8) / (max_rate - threshold * 0.8) * 25
        score = round(score, 2)
        if current_rate >= threshold * 2:
            reasons.append(f"利率{current_rate:.2f}%很高(>={threshold*2:.1f}%)")
        elif current_rate >= threshold * 1.5:
            reasons.append(f"利率{current_rate:.2f}%较高(>={threshold*1.5:.1f}%)")
        elif current_rate >= threshold:
            reasons.append(f"利率{current_rate:.2f}%达标(>={threshold:.1f}%)")
        else:
            reasons.append(f"利率{current_rate:.2f}%接近达标")
    else:
        score = 0.0
        reasons.append(f"利率{current_rate:.2f}%偏低")

    return score, reasons


def generate_signal(
    date: datetime,
    repo_data: dict,
    dr007: float = None,
    shibor_on: float = None,
    hist_dr007: pd.Series = None,
) -> list[dict]:
    """
    生成交易信号
    :param date: 日期
    :param repo_data: {symbol: {"close": rate, ...}} 各品种当日行情
    :param dr007: 当日DR007
    :param shibor_on: 当日Shibor隔夜
    :param hist_dr007: 历史DR007
    :return: 信号列表
    """
    signals = []

    # 1. 日历效应评分
    cal_score, cal_reasons = calc_calendar_score(date)

    # 2. 资金面评分
    fund_score, fund_reasons = 0, []
    if dr007 is not None and shibor_on is not None:
        fund_score, fund_reasons = calc_funding_score(dr007, shibor_on, hist_dr007)

    for symbol, data in repo_data.items():
        rate = data.get("close", 0)
        if rate <= 0:
            continue

        # 3. 利率水平评分
        rate_score, rate_reasons = calc_rate_score(rate)

        total_score = cal_score + fund_score + rate_score
        all_reasons = cal_reasons + fund_reasons + rate_reasons

        code_info = ALL_CODES.get(symbol, {})
        days = code_info.get("days", 1)
        name = code_info.get("name", symbol)

        # 计算预期收益（3000元本金）
        expected_profit = INITIAL_CAPITAL * (rate / 100) * days / 365
        # 收益效率 = 日均收益（考虑T+1到账，实际占用天数 = days + 1）
        occupy_days = days + 1
        daily_profit = expected_profit / occupy_days if occupy_days > 0 else 0

        action = "观望"
        if total_score >= STRATEGY_CONFIG["signal_score_threshold"]:
            action = "建议买入"

        signal = {
            "date": date.strftime("%Y-%m-%d"),
            "symbol": symbol,
            "name": name,
            "days": days,
            "rate": rate,
            "score": total_score,
            "reasons": all_reasons,
            "action": action,
            "expected_profit": round(expected_profit, 4),
            "daily_profit": round(daily_profit, 6),
            "occupy_days": occupy_days,
        }
        signals.append(signal)

        if action == "建议买入":
            logger.info(
                f"[信号] {signal['date']} {name}({symbol}) "
                f"评分:{total_score} 利率:{rate:.2f}% "
                f"预期收益:{expected_profit:.4f}元 -> {action}"
            )

    # 按评分排序
    signals.sort(key=lambda x: x["score"], reverse=True)
    return signals
