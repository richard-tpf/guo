"""回测报告与可视化"""
import pandas as pd
import os
from utils.logger import setup_logger

logger = setup_logger("report")


def generate_report(result: pd.DataFrame, output_dir: str = "output"):
    """生成回测报告"""
    if result.empty:
        logger.warning("无数据，跳过报告生成")
        return

    os.makedirs(output_dir, exist_ok=True)

    buy = result[result["action"].isin(["建议买入", "已买入"])].copy()
    executed = result[result["action"] == "已买入"].copy()
    watch = result[result["action"] == "观望"]

    summary = {
        "总信号数": len(result),
        "触发买入信号数": len(buy),
        "实际执行交易数": len(executed),
        "观望信号数": len(watch),
        "平均评分": round(result["score"].mean(), 2),
        "执行交易平均评分": round(executed["score"].mean(), 2) if len(executed) > 0 else 0,
        "执行交易平均利率(%)": round(executed["rate"].mean(), 2) if len(executed) > 0 else 0,
        "实际预期总收益(元)": round(executed["expected_profit"].sum(), 4) if len(executed) > 0 else 0,
    }

    print("\n========== 回测报告 ==========")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("==============================\n")

    # 保存详细结果
    result.to_csv(os.path.join(output_dir, "backtest_detail.csv"), index=False, encoding="utf-8-sig")

    if len(buy) > 0:
        # 按品种统计（所有触发的买入信号）
        by_symbol = buy.groupby("name").agg(
            信号次数=("score", "count"),
            平均评分=("score", "mean"),
            平均利率=("rate", "mean"),
            总预期收益=("expected_profit", "sum"),
        ).round(4)
        print("触发买入信号统计:")
        print(by_symbol.to_string())
        by_symbol.to_csv(os.path.join(output_dir, "backtest_by_symbol.csv"), encoding="utf-8-sig")

    if len(executed) > 0:
        # 按品种统计（实际执行的交易）
        by_exec = executed.groupby("name").agg(
            执行次数=("score", "count"),
            平均评分=("score", "mean"),
            平均利率=("rate", "mean"),
            总预期收益=("expected_profit", "sum"),
        ).round(4)
        print("\n实际执行交易统计（资金约束后）:")
        print(by_exec.to_string())
        by_exec.to_csv(os.path.join(output_dir, "backtest_executed.csv"), encoding="utf-8-sig")

    logger.info(f"报告已保存至 {output_dir}/")
