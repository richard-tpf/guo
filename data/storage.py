"""MySQL 数据存储"""
import pymysql
import pandas as pd
from config import MYSQL_CONFIG
from utils.logger import setup_logger

logger = setup_logger("storage")


def get_conn() -> pymysql.Connection:
    return pymysql.connect(**MYSQL_CONFIG)


def init_db():
    """检查数据库连接（表已手动创建）"""
    try:
        conn = get_conn()
        conn.close()
        logger.info("MySQL连接成功，数据库初始化完成")
    except Exception as e:
        logger.error(f"MySQL连接失败: {e}")
        raise


def save_repo_daily(df: pd.DataFrame):
    if df.empty:
        return
    conn = get_conn()
    cursor = conn.cursor()
    sql = """INSERT INTO repo_daily (date, symbol, open, high, low, close, volume)
             VALUES (%s, %s, %s, %s, %s, %s, %s)
             ON DUPLICATE KEY UPDATE
             open=VALUES(open), high=VALUES(high), low=VALUES(low),
             close=VALUES(close), volume=VALUES(volume)"""
    rows = []
    for _, r in df.iterrows():
        rows.append((
            str(r["date"])[:10], r["symbol"],
            float(r["open"]), float(r["high"]),
            float(r["low"]), float(r["close"]),
            float(r["volume"])
        ))
    cursor.executemany(sql, rows)
    conn.commit()
    cursor.close()
    conn.close()
    logger.info(f"保存逆回购日行情 {len(rows)} 条")


def save_funding_rate(df: pd.DataFrame):
    if df.empty:
        return
    conn = get_conn()
    cursor = conn.cursor()
    sql = """INSERT INTO funding_rate (date, shibor_on, dr007)
             VALUES (%s, %s, %s)
             ON DUPLICATE KEY UPDATE
             shibor_on=VALUES(shibor_on), dr007=VALUES(dr007)"""
    rows = []
    for _, r in df.iterrows():
        shibor = float(r["shibor_on"]) if "shibor_on" in r and pd.notna(r["shibor_on"]) else None
        dr007 = float(r["dr007"]) if "dr007" in r and pd.notna(r["dr007"]) else None
        rows.append((str(r["date"])[:10], shibor, dr007))
    cursor.executemany(sql, rows)
    conn.commit()
    cursor.close()
    conn.close()
    logger.info(f"保存资金面数据 {len(rows)} 条")


def save_signal(date: str, symbol: str, score: float, reason: str, action: str):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO signals (date, symbol, score, reason, recommended_action)
           VALUES (%s, %s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE
           score=VALUES(score), reason=VALUES(reason),
           recommended_action=VALUES(recommended_action)""",
        (date, symbol, score, reason, action)
    )
    conn.commit()
    cursor.close()
    conn.close()


def save_virtual_trade(date, symbol, direction, amount, rate, days, expected_profit):
    conn = get_conn()
    cursor = conn.cursor()
    # 先检查是否已存在同日同品种同方向的记录
    cursor.execute(
        "SELECT id FROM virtual_trades WHERE date=%s AND symbol=%s AND direction=%s",
        (date, symbol, direction)
    )
    if cursor.fetchone():
        # 已存在则更新
        cursor.execute(
            """UPDATE virtual_trades
               SET amount=%s, rate=%s, days=%s, expected_profit=%s
               WHERE date=%s AND symbol=%s AND direction=%s""",
            (amount, rate, days, expected_profit, date, symbol, direction)
        )
    else:
        cursor.execute(
            """INSERT INTO virtual_trades
               (date, symbol, direction, amount, rate, days, expected_profit, actual_profit)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 0)""",
            (date, symbol, direction, amount, rate, days, expected_profit)
        )
    conn.commit()
    cursor.close()
    conn.close()


def load_repo_daily(symbol: str = None) -> pd.DataFrame:
    conn = get_conn()
    if symbol:
        df = pd.read_sql("SELECT * FROM repo_daily WHERE symbol=%s", conn, params=(symbol,))
    else:
        df = pd.read_sql("SELECT * FROM repo_daily", conn)
    conn.close()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def load_funding_rate() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM funding_rate", conn)
    conn.close()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def load_virtual_trades() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM virtual_trades", conn)
    conn.close()
    return df


# ============ 回测专用存储函数 ============

def clear_backtest_data():
    """清空回测表数据（每次回测前调用）"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM backtest_signals")
    cursor.execute("DELETE FROM backtest_trades")
    conn.commit()
    cursor.close()
    conn.close()
    logger.info("已清空回测信号和交易记录")


def save_backtest_signal(date: str, symbol: str, score: float, reason: str, action: str):
    """保存回测信号到回测专用表"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO backtest_signals (date, symbol, score, reason, recommended_action)
           VALUES (%s, %s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE
           score=VALUES(score), reason=VALUES(reason),
           recommended_action=VALUES(recommended_action)""",
        (date, symbol, score, reason, action)
    )
    conn.commit()
    cursor.close()
    conn.close()


def save_backtest_trade(date, symbol, direction, amount, rate, days, expected_profit):
    """保存回测交易到回测专用表"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO backtest_trades
           (date, symbol, direction, amount, rate, days, expected_profit, actual_profit)
           VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
           ON DUPLICATE KEY UPDATE
           amount=VALUES(amount), rate=VALUES(rate), days=VALUES(days),
           expected_profit=VALUES(expected_profit)""",
        (date, symbol, direction, amount, rate, days, expected_profit)
    )
    conn.commit()
    cursor.close()
    conn.close()
