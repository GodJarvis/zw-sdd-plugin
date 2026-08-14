# Phalcon QA 测试配置

| 配置项 | 值 |
|---|---|
| 测试规范 skill | `phalcon-test` |
| 会话鉴权名称 | `Cookie/DI` |
| 会话鉴权文档描述 | `Cookie + CSRF Token`、`已登录=DI 注入用户` |
| 测试用户注入 | `$this->actingAs(1)`，由 Phalcon DI 容器注入测试用户 |
| 当前环境文件 | `config/config.{APP_ENV}.php` |
| 配置核验源 | `config/config.{APP_ENV}.php` |
| 受保护配置 | `config/` |
| QA 测试命令 | `docker exec {容器} sh -c "cd {项目路径} && vendor/bin/phpunit test/QA/Integration/{ChangeName}/"` |
| 分批测试命令 | `vendor/bin/phpunit --filter "testTc001|testTc002|testTc003" test/QA/Integration/{ChangeName}/` |
| 全量测试命令 | `composer test` |
| 静态分析命令 | `composer analyse` |
| 测试基类 | `Test\IntegrationTestCase` |
| QA 命名空间前缀 | `Test\QA\Integration` |
| DataFactory trait | `Test\QA\Traits\DataFactory` |
| 队列生产者示例 | `Phalcon\Queue\Producer` |

环境文件缺失时禁止从其他 `config/config.*.php` 静默复制。涉及 `config/` 的修复必须按项目根指令中的核心配置护栏处理。
