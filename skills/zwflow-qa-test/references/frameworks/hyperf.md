# Hyperf QA 测试配置

| 配置项 | 值 |
|---|---|
| 测试规范 skill | `hyperf-test` |
| 会话鉴权名称 | `Cookie` |
| 会话鉴权文档描述 | `Cookie + CSRF Token`、`已登录=zw-authorization Cookie 有效` |
| 测试用户注入 | `$this->actingAs(1)` 或项目基类要求的 Cookie headers |
| 当前环境文件 | `.env.{APP_ENV}` |
| 配置核验源 | `.env` 与 `config/autoload/system.php` |
| 受保护配置 | `config/autoload/` |
| QA 测试命令 | `docker exec {容器} sh -c "cd {项目路径} && vendor/bin/co-phpunit --prepend test/bootstrap.php test/QA/Integration/{ChangeName}/"` |
| 分批测试命令 | `vendor/bin/co-phpunit --prepend test/bootstrap.php --filter "testTc001|testTc002|testTc003" test/QA/Integration/{ChangeName}/` |
| 全量测试命令 | `composer test` |
| 静态分析命令 | `composer analyse` |
| 测试基类 | `HyperfTest\IntegrationTestCase` |
| QA 命名空间前缀 | `HyperfTest\QA\Integration` |
| DataFactory trait | `HyperfTest\QA\Traits\DataFactory` |
| 队列生产者示例 | `Hyperf\Amqp\Producer` |

环境文件缺失时禁止从其他 `.env.*` 静默复制。涉及 `config/autoload/` 的修复必须按项目根指令中的核心配置护栏处理。
