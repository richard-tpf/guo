"""
国债逆回购量化系统 - 主入口

用法:
    python main.py init          # 初始化数据库
    python main.py fetch         # 采集历史数据
    python main.py backtest      # 运行回测
    python main.py check         # 每日信号检查（配合定时任务）
    python main.py status        # 查看虚拟交易统计
"""
import sys
from datetime import datetime, timedelta
from data.storage import init_db, save_repo_daily, save_funding_rate, load_virtual_trades
from data.fetcher import fetch_all_repo_daily, fetch_shibor, fetch_dr007, fetch_repo_rate_hist_range
from backtest.engine import run_backtest
from backtest.report import generate_report
from monitor.realtime import run_daily_check
from config import SH_REPO_CODES, SZ_REPO_CODES, INITIAL_CAPITAL
from utils.logger import setup_logger

logger = setup_logger("main")


def cmd_init():
    """初始化数据库"""
    init_db()
    print("数据库初始化完成")


def cmd_fetch():
    """采集历史数据（默认最近1年）"""
    import pandas as pd
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    print(f"采集数据: {start} ~ {end}")

    # 深市逆回购（stock_zh_a_hist 可正常获取）
    print("采集深市逆回购...")
    sz_df = fetch_all_repo_daily(SZ_REPO_CODES, start, end)
    save_repo_daily(sz_df)

    # 沪市逆回购（stock_zh_a_hist 不支持沪市逆回购代码）
    # 用回购定盘利率作为沪市参考
    print("采集回购定盘利率（FR001/FR007，作为沪市利率参考）...")
    repo_rate_df = fetch_repo_rate_hist_range(start, end)
    if not repo_rate_df.empty:
        print(f"获取回购定盘利率 {len(repo_rate_df)} 条")
        logger.info(f"回购定盘利率列名: {list(repo_rate_df.columns)}")
        # 将FR001映射为204001，FR007映射为204007，FR014映射为204014
        fr_mapping = {
            "FR001": "204001",
            "FR007": "204007",
            "FR014": "204014",
        }
        for fr_col, symbol in fr_mapping.items():
            if fr_col in repo_rate_df.columns:
                tmp = repo_rate_df[["date", fr_col]].dropna(subset=[fr_col]).copy()
                tmp = tmp.rename(columns={fr_col: "close"})
                tmp["symbol"] = symbol
                tmp["open"] = tmp["close"]
                tmp["high"] = tmp["close"]
                tmp["low"] = tmp["close"]
                tmp["volume"] = 0
                tmp["date"] = pd.to_datetime(tmp["date"])
                save_repo_daily(tmp[["date", "symbol", "open", "high", "low", "close", "volume"]])
                print(f"  {fr_col} -> {symbol}: {len(tmp)} 条")

    # 资金面数据
    print("采集Shibor数据...")
    shibor_df = fetch_shibor()

    print("采集DR007数据...")
    dr007_df = fetch_dr007()

    if not shibor_df.empty and not dr007_df.empty:
        funding = pd.merge(shibor_df, dr007_df, on="date", how="outer")
        funding = funding.sort_values("date")
        save_funding_rate(funding)
    elif not shibor_df.empty:
        save_funding_rate(shibor_df)
    elif not dr007_df.empty:
        save_funding_rate(dr007_df)

    print("数据采集完成")


def cmd_backtest():
    """运行回测"""
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    print(f"回测区间: {start} ~ {end}")
    result = run_backtest(start, end)
    generate_report(result)


def cmd_check():
    """每日信号检查"""
    run_daily_check()


def cmd_status():
    """查看虚拟交易统计"""
    trades = load_virtual_trades()
    if trades.empty:
        print("暂无虚拟交易记录")
        return

    print(f"\n{'='*50}")
    print(f"虚拟交易统计 (本金: {INITIAL_CAPITAL}元)")
    print(f"{'='*50}")
    print(f"  总交易次数: {len(trades)}")
    print(f"  预期总收益: {trades['expected_profit'].sum():.4f}元")
    print(f"  平均单次收益: {trades['expected_profit'].mean():.4f}元")
    print(f"  最近5笔交易:")
    for _, t in trades.tail(5).iterrows():
        print(f"    {t['date']} {t['symbol']} 利率:{t['rate']:.2f}% 预期收益:{t['expected_profit']:.4f}元")
    print(f"{'='*50}\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()
    commands = {
        "init": cmd_init,
        "fetch": cmd_fetch,
        "backtest": cmd_backtest,
        "check": cmd_check,
        "status": cmd_status,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
