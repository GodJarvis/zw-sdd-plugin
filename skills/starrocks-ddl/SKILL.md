---
name: starrocks-ddl
description: "Use when generating StarRocks DDL or CREATE TABLE statements. 当生成 StarRocks 表结构、建表语句、db.starrocks.sql 文件时触发。确保表模型、分区、属性配置、字段命名等符合团队规范。"
---

# StarRocks 建表规范

## 概述

团队标准的 StarRocks CREATE TABLE 语句规范。生成 StarRocks DDL 时必须严格遵守以下规则。

**目标版本：StarRocks v3.3.8**（支持 PRIMARY KEY 与 ORDER BY 使用不同字段）

## 表模型选择

**默认使用主键表（PRIMARY KEY）**

如果业务场景明显适合其它模型，需询问用户确认后再使用：
- Duplicate Key — 日志/事件流，数据只追加不修改
- Aggregate Key — 预聚合统计（SUM、MAX、MIN 等）

不确定时使用主键表，并与用户确认。

## ENGINE

每张表必须包含 `ENGINE=OLAP`，位于列定义闭括号之后、KEY 定义之前：

```sql
) ENGINE=OLAP
PRIMARY KEY(`id`, `corp_id`)
```

## 分区

使用 `date_trunc()` 表达式分区，不使用 RANGE PARTITION：

```sql
PARTITION BY date_trunc('day', `create_time`)
PARTITION BY date_trunc('month', `create_time`)
PARTITION BY date_trunc('hour', `event_time`)
PARTITION BY date_trunc('year', `report_date`)
```

选择规则：
- 高数据量（百万/天）→ 按天分区
- 中等数据量 → 按月分区
- 极高频（IoT、实时事件）→ 按小时分区
- 低数据量长期保留 → 按年分区

不确定时默认按天分区。

## 分桶

使用 `DISTRIBUTED BY HASH(column)` **不指定 BUCKETS 数量**，由 server 自动分桶：

```sql
-- ✅ 正确
DISTRIBUTED BY HASH(`corp_id`)

-- ❌ 错误：不要指定桶数
DISTRIBUTED BY HASH(`corp_id`) BUCKETS 32
```

哈希列选择：
- 高基数列（ID、唯一键）
- 频繁出现在 WHERE/JOIN 条件中的列

## 字段命名与类型

- 字段名统一 `snake_case`，用反引号包裹
- 类型必须带显示宽度：`int(11)`、`tinyint(1)`、`bigint(20)`
- 时间字段用 `datetime` 类型
- ID 字段以 `_id` 结尾

### 金额字段

金额统一使用 **int 类型，单位：分**，不用 DECIMAL：

```sql
-- ✅ 正确
`total_amount` int(11) NULL COMMENT "订单总金额(单位:分)"

-- ❌ 错误
`total_amount` DECIMAL(12, 2) COMMENT '订单总金额'
```

### 软删除字段

软删除用 `tinyint(1)` 配合 0/1 值，不用 BOOLEAN：

```sql
-- ✅ 正确
`is_deleted` tinyint(1) NULL DEFAULT "0" COMMENT "是否删除 0-否 1-是"

-- ❌ 错误
`is_deleted` BOOLEAN COMMENT '是否已删除'
```

### 标准时间字段

每张表末尾必须包含以下两个字段，格式固定：

```sql
`create_time` datetime NULL COMMENT "创建时间",
`update_time` datetime NULL COMMENT "记录更新时间"
```

## 排序键

根据业务查询模式确定排序键：
- 最常出现在 WHERE 过滤条件中的列
- 用于范围扫描的列
- 高基数的点查列

基于具体业务场景自行判断。

## 索引策略

按业务需求添加索引：
- **Bitmap 索引** — 低基数且频繁过滤的列（状态、类型、枚举）
- **Bloom Filter 索引** — 高基数的点查列（ID、编码）

根据查询模式给出最优方案。

## 注释（强制）

每张表必须有表注释，每个字段必须有字段注释，注释使用双引号。

```sql
`name` varchar(100) NULL COMMENT "用户名称"
) ENGINE=OLAP
PRIMARY KEY(`id`)
COMMENT "用户表"
```

## PROPERTIES（必填）

生产环境：

```sql
PROPERTIES (
    "compression" = "LZ4",
    "enable_persistent_index" = "true",
    "fast_schema_evolution" = "false",
    "replicated_storage" = "true",
    "replication_num" = "3"
);
```

测试环境（仅 replication_num 不同）：

```sql
PROPERTIES (
    "compression" = "LZ4",
    "enable_persistent_index" = "true",
    "fast_schema_evolution" = "false",
    "replicated_storage" = "true",
    "replication_num" = "1"
);
```

默认使用生产配置。用户指定测试环境时用 replication_num = "1"。

## 完整示例

```sql
CREATE TABLE `user_orders` (
    `order_id` bigint(20) NOT NULL COMMENT "订单唯一ID",
    `user_id` bigint(20) NOT NULL COMMENT "用户ID",
    `order_status` tinyint(1) NULL COMMENT "订单状态: 1=待付款 2=已付款 3=已发货 4=已完成",
    `total_amount` int(11) NULL COMMENT "订单总金额(单位:分)",
    `discount_amount` int(11) NULL DEFAULT "0" COMMENT "优惠金额(单位:分)",
    `is_deleted` tinyint(1) NULL DEFAULT "0" COMMENT "是否删除 0-否 1-是",
    `create_time` datetime NULL COMMENT "创建时间",
    `update_time` datetime NULL COMMENT "记录更新时间"
) ENGINE=OLAP
PRIMARY KEY(`order_id`)
COMMENT "用户订单表"
PARTITION BY date_trunc('day', `create_time`)
DISTRIBUTED BY HASH(`order_id`)
PROPERTIES (
    "compression" = "LZ4",
    "enable_persistent_index" = "true",
    "fast_schema_evolution" = "false",
    "replicated_storage" = "true",
    "replication_num" = "3"
);
```

## 常见错误

| 错误做法 | 正确做法 |
|---------|---------|
| 指定 BUCKETS N | 不指定桶数，server 自动分桶 |
| 金额用 DECIMAL | 用 int(11)，单位分 |
| 软删除用 BOOLEAN | 用 tinyint(1)，0/1 值 |
| 缺少 ENGINE=OLAP | KEY 定义前必须有 ENGINE=OLAP |
| 使用 RANGE PARTITION | 用 `PARTITION BY date_trunc()` 表达式分区 |
| 缺少表注释/字段注释 | 每个表和字段都必须有 COMMENT |
| 字段名用 camelCase | 统一 snake_case |
| COMMENT 用单引号 | 统一用双引号 |
| 用 created_at/updated_at | 统一用 create_time/update_time |
| 类型不带显示宽度 | 必须带：int(11)、tinyint(1)、bigint(20) |
