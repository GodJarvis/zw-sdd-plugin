# Hyperf 测试范围

- 源码根目录：`app/`。
- apply 当前模块：`git diff HEAD~1 --name-only -- app/` 后筛选 PHP 文件。
- verify/finish：以最近 tag 或约定发布基线到 `HEAD` 的 diff 为范围。
- 典型映射：`app/Xxx/Yyy.php` → `test/Cases/Xxx/YyyTest.php`。
- 测试命令：`vendor/bin/co-phpunit --prepend test/bootstrap.php <test_files>`。
- 受保护配置：`config/autoload/` 下的 databases、redis、amqp、kafka、server 等基础设施配置。
