-- ============================================================
-- 回测专用表（与虚拟交易表分离）
-- ============================================================

-- 回测信号表
CREATE TABLE IF NOT EXISTS backtest_signals (
    id              INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    date            DATE           NOT NULL COMMENT '信号日期',
    symbol          VARCHAR(10)    NOT NULL COMMENT '品种代码',
    score           DECIMAL(6,2)   NULL     COMMENT '综合评分（0-100）',
    reason          TEXT           NULL     COMMENT '信号触发原因说明',
    recommended_action VARCHAR(20) NULL     COMMENT '建议操作（建议买入/已买入/观望/资金占用中）',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL COMMENT '记录创建时间',
    UNIQUE KEY uk_date_symbol (date, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回测信号记录';

-- 回测交易表
CREATE TABLE IF NOT EXISTS backtest_trades (
    id              INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    date            DATE           NOT NULL COMMENT '交易日期',
    symbol          VARCHAR(10)    NOT NULL COMMENT '品种代码',
    direction       VARCHAR(10)    NOT NULL COMMENT '交易方向（buy/sell）',
    amount          DECIMAL(12,2)  NULL     COMMENT '交易金额',
    rate            DECIMAL(10,4)  NULL     COMMENT '年化利率（%）',
    days            INT            NULL     COMMENT '持仓天数',
    expected_profit DECIMAL(10,4)  NULL     COMMENT '预期收益（元）',
    actual_profit   DECIMAL(10,4)  DEFAULT 0 COMMENT '实际收益（元）',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL COMMENT '记录创建时间',
    UNIQUE KEY uk_date_symbol_dir (date, symbol, direction)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回测交易记录';
