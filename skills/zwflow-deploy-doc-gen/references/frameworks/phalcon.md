# Phalcon 上线文档差异

## 基础设施类型

- 消息基础设施重点识别 Kafka topic、Redis stream、RabbitMQ 队列。

## 任务配置

- 常驻任务包括通过 Swoole Process Pool 运行的消息队列消费者和守护进程。
- 扫描关键字：`cli.php`、`blPop`、`rpush`、`RabbitMqHelper`、`crontab`、`task`、`nohup`、`常驻`、`定时`、`一次性`、`迁移脚本`。
- CLI 任务命令格式：`php run/cli.php <module> <task> <action>`。
- `<task>` 必须使用全小写单词，并以 `_` 连接；禁止驼峰命名。
