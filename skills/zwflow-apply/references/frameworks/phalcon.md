# Phalcon Apply 差异

## 文件完成检查

1. 按文件路径命中的编码规范 Skill 决定 `strict_types`，通用 Apply 不强制统一。
2. 保持 Controller → Service → Model 单向依赖。
3. Controller 通过 `$this->getParam()` 取参，不直接使用原生请求方法绕过项目封装。
4. SQL 使用 `ModelBase::from()` 的 SqlBuilder，不使用项目禁止的原生 ORM 写法。
5. Controller 通过 `returnJson()` 返回并保持项目响应信封。
6. 通过 DiUtils 或 DI 容器获取服务，不硬编码连接。
7. Model 时间戳使用 `create_time`、`update_time`。
8. Controller Action 方法包含项目要求的路由注释。

## 变更范围与验证

- PHP 源码范围：`library/*.php`、`apps/*.php` 及其实际子目录。
- 静态分析：对筛选出的变更 PHP 文件执行 `vendor/bin/phpstan analyse`。
- 典型测试映射：`library/services/Xxx.php` → `test/Cases/Services/XxxTest.php`。
- 测试命令：`vendor/bin/phpunit <测试文件列表>`；在容器项目中通过项目规定的容器入口执行。
- 高风险配置：`config/config.php` 及项目根指令声明的其它核心配置。
