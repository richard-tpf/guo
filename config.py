"""系统配置"""

# ============ 基本配置 ============
INITIAL_CAPITAL = 3000  # 本金（元）

# ============ 微信推送配置（pushplus） ============
# 注册地址：https://www.pushplus.plus/
# 登录后获取token填入下方
PUSHPLUS_TOKEN = "fdaefe42ad4e49e7b996af94bad09b51"  # 填入你的pushplus token

# ============ 逆回购品种配置 ============
# 沪市品种
SH_REPO_CODES = {
    "204001": {"name": "GC001", "days": 1},
    "204002": {"name": "GC002", "days": 2},
    "204003": {"name": "GC003", "days": 3},
    "204004": {"name": "GC004", "days": 4},
    "204007": {"name": "GC007", "days": 7},
    "204014": {"name": "GC014", "days": 14},
    "204028": {"name": "GC028", "days": 28},
    "204091": {"name": "GC091", "days": 91},
    "204182": {"name": "GC182", "days": 182},
}

# 深市品种
SZ_REPO_CODES = {
    "131810": {"name": "R-001", "days": 1},
    "131811": {"name": "R-002", "days": 2},
    "131800": {"name": "R-003", "days": 3},
    "131809": {"name": "R-004", "days": 4},
    "131801": {"name": "R-007", "days": 7},
    "131802": {"name": "R-014", "days": 14},
    "131803": {"name": "R-028", "days": 28},
    "131805": {"name": "R-091", "days": 91},
    "131806": {"name": "R-182", "days": 182},
}

# ============ 策略参数 ============
STRATEGY_CONFIG = {
    # 日历效应：月末/季末/年末前N个交易日开始关注
    "calendar_lookback_days": 3,
    # 利率阈值：年化收益率超过此值触发信号（%）
    "rate_threshold": 1.5,
    # 资金面紧张判断：DR007超过此值认为资金面偏紧（%）
    "dr007_tight_threshold": 1.8,
    # 综合评分阈值：超过此值发出买入信号（0-100）
    "signal_score_threshold": 35,
    # 最大持仓天数（排除超长期品种）
    "max_hold_days": 14,
    # 利率高位分位数阈值：超过近20日此分位数认为利率处于高位
    "rate_high_percentile": 50,
    # 利率高位时偏好的持仓天数范围
    "high_rate_prefer_days": [7, 14],
    # 利率一般时偏好的持仓天数范围
    "normal_rate_prefer_days": [7, 14, 4, 3],
}

# ============ 数据库配置（MySQL） ============
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "repo_quant",
    "charset": "utf8mb4",
}

# ============ Tushare配置 ============
# 注册地址：https://tushare.pro/register
# 登录后在个人主页获取token
TUSHARE_TOKEN = "653842f5687965c632592bef3c3f0eb57ebdd2d32c2aaf801fc9967e"  # 填入你的tushare token

# ============ 日志配置 ============
LOG_PATH = "logs/system.log"
