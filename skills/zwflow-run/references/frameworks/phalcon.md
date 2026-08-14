# Phalcon 测试范围

- 源码根目录：`library/`、`apps/`。
- apply 当前模块：`git diff HEAD~1 --name-only -- library/ apps/` 后筛选 PHP 文件。
- verify/finish：以最近 tag 或约定发布基线到 `HEAD` 的 diff 为范围。
- 典型映射：`library/services/Xxx.php` → `test/Cases/Services/XxxTest.php`。
- 测试命令：`vendor/bin/phpunit <test_files>`。
- 受保护配置：`config/config.php` 及项目根指令声明的其它核心配置。
