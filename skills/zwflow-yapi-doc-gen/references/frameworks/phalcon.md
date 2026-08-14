# Phalcon 路由规则

- 自动路由格式为 `/{module}/{controller}/{action}`。
- module 从控制器目录取得，例如 `apps/admin/controllers/` 对应 `admin`。
- controller 段由大驼峰转为 snake_case。
- action 段去掉 `Action` 后缀，保持 camelCase 原文；禁止转为 snake_case。
- 连续大写字母逐个拆分；数字附着于前一个单词。
