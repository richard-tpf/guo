-- 查看 repo_quant 数据库中各表的实际建表语句
-- 执行后根据输出结果校对 add_comments.sql 中的字段类型

SHOW CREATE TABLE repo_daily\G
SHOW CREATE TABLE funding_rate\G
SHOW CREATE TABLE signals\G
SHOW CREATE TABLE virtual_trades\G
