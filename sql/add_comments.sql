-- ============================================================
-- 为 repo_quant 数据库补全所有缺失的表/字段 COMMENT
-- 基于 SHOW CREATE TABLE 实际结构生成，类型完全匹配
-- ============================================================

-- 1. repo_daily —— 字段全部缺少 COMMENT
ALTER TABLE repo_daily
    MODIFY COLUMN date   DATE           NOT NULL COMMENT '交易日期',
    MODIFY COLUMN symbol VARCHAR(10)    NOT NULL COMMENT '品种代码（如204001、131810）',
    MODIFY COLUMN open   DECIMAL(10,4)  NULL     COMMENT '开盘价（年化利率%）',
    MODIFY COLUMN high   DECIMAL(10,4)  NULL     COMMENT '最高价（年化利率%）',
    MODIFY COLUMN low    DECIMAL(10,4)  NULL     COMMENT '最低价（年化利率%）',
    MODIFY COLUMN close  DECIMAL(10,4)  NULL     COMMENT '收盘价（年化利率%）',
    MODIFY COLUMN volume DECIMAL(20,2)  NULL     COMMENT '成交量';

-- 2. signals —— 字段全部缺少 COMMENT
ALTER TABLE signals
    MODIFY COLUMN date               DATE                                NOT NULL COMMENT '信号日期',
    MODIFY COLUMN symbol             VARCHAR(10)                         NOT NULL COMMENT '品种代码',
    MODIFY COLUMN score              DECIMAL(6,2)                        NULL     COMMENT '综合评分（0-100）',
    MODIFY COLUMN reason             TEXT                                NULL     COMMENT '信号触发原因说明',
    MODIFY COLUMN recommended_action VARCHAR(20)                         NULL     COMMENT '建议操作（建议买入/观望等）',
    MODIFY COLUMN created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL     COMMENT '记录创建时间';

-- 3. funding_rate —— 表和字段已有 COMMENT，补充 date 字段
ALTER TABLE funding_rate
    MODIFY COLUMN date DATE NOT NULL COMMENT '日期';

-- 4. virtual_trades —— 大部分已有 COMMENT，补充缺失的字段
ALTER TABLE virtual_trades
    MODIFY COLUMN id         INT AUTO_INCREMENT                        COMMENT '自增主键',
    MODIFY COLUMN date       DATE                                      NOT NULL COMMENT '交易日期',
    MODIFY COLUMN symbol     VARCHAR(10)                               NOT NULL COMMENT '品种代码',
    MODIFY COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP       NULL     COMMENT '记录创建时间';
