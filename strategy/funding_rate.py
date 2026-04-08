"""资金面策略

通过Shibor和DR007判断市场资金面松紧程度：
- 资金面偏紧时，逆回购利率通常较高，是较好的参与时机
- 资金面宽松时，利率偏低，收益有限
"""
import pandas as pd
from config import STRATEGY_CONFIG
from utils.logger import setup_logger

logger = setup_logger("funding_rate")


def calc_funding_score(dr007: float, shibor_on: float, hist_dr007: pd.Series = None) -> tuple[float, list[str]]:
    """
    计算资金面评分
    :param dr007: 当日DR007利率（%）
    :param shibor_on: 当日Shibor隔夜利率（%）
    :param hist_dr007: 历史DR007序列，用于计算分位数
    :return: (score, reasons) score 0-30
    """
    score = 0.0
    reasons = []
    threshold = STRATEGY_CONFIG["dr007_tight_threshold"]

    if dr007 > threshold:
        score += 15
        reasons.append(f"DR007={dr007:.2f}%偏高(>{threshold}%)")

    if shibor_on > threshold:
        score += 10
        reasons.append(f"Shibor隔夜={shibor_on:.2f}%偏高")

    # 如果有历史数据，计算当前DR007所处分位数
    if hist_dr007 is not None and len(hist_dr007) > 20:
        percentile = (hist_dr007 < dr007).sum() / len(hist_dr007) * 100
        if percentile > 80:
            score += 5
            reasons.append(f"DR007处于历史{percentile:.0f}%分位(偏高)")

    return min(score, 30), reasons
