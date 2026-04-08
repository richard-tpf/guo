"""日历效应策略

国债逆回购在以下时间点利率通常偏高：
- 月末最后1-3个交易日
- 季末（3/6/9/12月末）
- 年末/春节前
- 长假前（国庆、春节）
"""
from datetime import datetime, timedelta
import chinese_calendar
from utils.logger import setup_logger

logger = setup_logger("calendar_effect")


def is_month_end(date: datetime, lookback: int = 3) -> bool:
    """判断是否接近月末（距月末N个自然日内）"""
    import calendar
    last_day = calendar.monthrange(date.year, date.month)[1]
    return (last_day - date.day) < lookback


def is_quarter_end(date: datetime, lookback: int = 5) -> bool:
    """判断是否接近季末"""
    quarter_end_months = [3, 6, 9, 12]
    if date.month in quarter_end_months:
        import calendar
        last_day = calendar.monthrange(date.year, date.month)[1]
        return (last_day - date.day) < lookback
    return False


def is_year_end(date: datetime, lookback: int = 7) -> bool:
    """判断是否接近年末"""
    if date.month == 12:
        return (31 - date.day) < lookback
    return False


def is_before_holiday(date: datetime, lookback: int = 3) -> bool:
    """判断是否在法定长假前（排除普通周末，只识别真正的节假日）"""
    try:
        for i in range(1, lookback + 1):
            future = date + timedelta(days=i)
            future_date = future.date()
            if chinese_calendar.is_holiday(future_date):
                # 区分法定节假日和普通周末
                detail = chinese_calendar.get_holiday_detail(future_date)
                # detail 返回 (is_holiday, holiday_name_or_None)
                # 法定节假日时 holiday_name 不为 None，普通周末为 None
                if detail[1] is not None:
                    return True
    except Exception:
        pass
    return False


def calc_calendar_score(date: datetime) -> tuple[float, list[str]]:
    """
    计算日历效应评分
    :return: (score, reasons) score 0-40
    """
    score = 0.0
    reasons = []

    if is_year_end(date):
        score += 20
        reasons.append("年末效应")
    elif is_quarter_end(date):
        score += 15
        reasons.append("季末效应")
    elif is_month_end(date):
        score += 10
        reasons.append("月末效应")

    if is_before_holiday(date):
        score += 15
        reasons.append("节假日前效应")

    # 周四效应：周四买1天期，周五到账可用，实际占用1天享受3天利息
    if date.weekday() == 3:  # Thursday
        score += 5
        reasons.append("周四效应(1天期实得3天利息)")

    return min(score, 40), reasons
