# Hyperf Apply 差异

## 文件完成检查

1. Hyperf 函数式辅助方法使用 `use function` 显式引入。
2. 文件顶部声明 `declare(strict_types=1)`。
3. 保持 Controller → Service → Repository → Model 单向依赖。
4. 不引入不安全的全局或静态状态；连接通过框架工厂获取。
5. 业务异常使用项目 BusinessException，错误码已定义。
6. Model 时间戳使用 `create_time`、`update_time`。
7. Controller 方法包含项目要求的路由注释或 Attribute。

## 变更范围与验证

- PHP 源码范围：`app/*.php` 及其实际子目录；执行命令时使用能递归匹配项目 PHP 文件的路径规则。
- 静态分析：对筛选出的变更 PHP 文件执行 `vendor/bin/phpstan analyse`。
- 典型测试映射：`app/Xxx/Yyy.php` → `test/Cases/Xxx/YyyTest.php`。
- 测试命令：`vendor/bin/co-phpunit --prepend test/bootstrap.php <测试文件列表>`；在容器项目中通过项目规定的容器入口执行。
- 高风险配置：`config/autoload/` 下的 databases、redis、amqp、kafka、server 等基础设施配置。
