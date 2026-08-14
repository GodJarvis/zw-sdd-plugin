---
name: hyperf-command
description: "编写 Hyperf CLI 命令（Command）。涉及 app/Command/ 下的业务命令类、命令行参数/选项、定时任务、一次性迁移脚本时使用。消费者命令（amqp:consume/kafka:consume/redis:consume）请使用 hyperf-queue skill。Use when working with files matching: **/Command/**/*.php, !**/Command/*ConsumerCommand.php, !**/Command/AbstractConsumerCommand.php."
---

# Hyperf Command 规范

> **本 skill 覆盖业务命令和一次性脚本**。消费者命令（`*ConsumerCommand`、`AbstractConsumerCommand`）属于队列基础设施，详见 `hyperf-queue` skill。

## 入口与调用

```bash
php bin/hyperf.php <command-name> [arguments] [--options]
```

## 目录结构

```
app/Command/
├── <Domain>Command.php              # 业务命令
├── AbstractConsumerCommand.php      # ← 消费者基类，见 hyperf-queue skill
├── AmqpConsumerCommand.php          # ← 消费者命令，见 hyperf-queue skill
├── KafkaConsumerCommand.php         # ← 消费者命令，见 hyperf-queue skill
├── RedisConsumerCommand.php         # ← 消费者命令，见 hyperf-queue skill
└── onceTask/                        # 一次性迁移/修复脚本
    └── <Purpose>Command.php
```

| 类型 | 目录 | 命名建议 |
|------|------|---------|
| 通用/业务命令 | `app/Command/` | `<Domain>Command.php` |
| 一次性任务 | `app/Command/onceTask/` | `<Purpose>Command.php` |

## 标准模板

```php
<?php

declare(strict_types=1);

namespace App\Command;

use App\Service\MemberService;
use App\Utils\Logger\Log;
use Hyperf\Command\Annotation\Command;
use Hyperf\Command\Command as HyperfCommand;
use Hyperf\Di\Annotation\Inject;
use Psr\Container\ContainerInterface;
use Symfony\Component\Console\Input\InputArgument;
use Symfony\Component\Console\Input\InputOption;

#[Command]
class MemberSyncCommand extends HyperfCommand
{
    #[Inject]
    private MemberService $memberService;

    public function __construct(protected ContainerInterface $container)
    {
        parent::__construct('member:sync');
    }

    public function configure(): void
    {
        parent::configure();
        $this->setDescription('同步会员数据');
    }

    public function handle(): void
    {
        $batchSize = (int) $this->input->getOption('batch');
        $this->line("[开始] 批次大小：{$batchSize}", 'info');

        try {
            $count = $this->memberService->syncAll($batchSize);
            $this->info("[完成] 处理 {$count} 条");
        } catch (\Throwable $e) {
            Log::get()->error('MemberSyncCommand 异常', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);
            $this->error("[失败] " . $e->getMessage());
        }
    }

    protected function getArguments(): array
    {
        return [
            // ['name', InputArgument::REQUIRED, '参数描述'],
        ];
    }

    protected function getOptions(): array
    {
        return [
            ['batch', 'b', InputOption::VALUE_OPTIONAL, '批次大小', '500'],
        ];
    }
}
```

## 命令名称约定

| 格式 | 示例 | 场景 |
|------|------|------|
| `<domain>:<action>` | `member:sync` | 业务命令 |
| `<domain>:<sub-action>` | `file:upload` | 带子操作 |
| `onceTask:<name>` | `onceTask:shotDecoupleMigrate` | 一次性迁移脚本 |

## 参数与选项

```php
// 参数（位置参数）
protected function getArguments(): array
{
    return [
        ['id', InputArgument::REQUIRED, '会员ID'],
        ['name', InputArgument::OPTIONAL, '名称', 'default_value'],
    ];
}

// 选项（--key=value）
protected function getOptions(): array
{
    return [
        ['batch', 'b', InputOption::VALUE_OPTIONAL, '批次大小', '100'],
        ['force', 'f', InputOption::VALUE_NONE, '强制执行'],
        ['ids', null, InputOption::VALUE_REQUIRED, '逗号分隔的ID列表'],
    ];
}

// 获取
$id = $this->input->getArgument('id');
$batch = (int) $this->input->getOption('batch');
$force = $this->input->getOption('force'); // bool
```

## 输出方法

```php
$this->line('普通输出');
$this->line('带颜色', 'info');    // 绿色
$this->info('成功信息');           // 绿色
$this->error('错误信息');          // 红色
$this->warn('警告信息');           // 黄色
```

## 依赖注入

Command 支持 `#[Inject]` 注解注入：

```php
#[Command]
class ExportCommand extends HyperfCommand
{
    #[Inject]
    private MemberService $memberService;

    #[Inject]
    private Redis $redis;
}
```

## 定时任务（cron）

```cron
# 每小时同步
0 * * * * cd /path/to/project && php bin/hyperf.php member:sync --batch=500 >> /path/to/log/cron/member_sync.log 2>&1

# 每天凌晨 3 点清理
0 3 * * * cd /path/to/project && php bin/hyperf.php data:clean-expired >> /path/to/log/cron/clean.log 2>&1
```

## 一次性迁移脚本

放在 `app/Command/onceTask/` 目录，命名前缀 `onceTask:`：

```php
<?php

declare(strict_types=1);

namespace App\Command\onceTask;

use Hyperf\Command\Annotation\Command;
use Hyperf\Command\Command as HyperfCommand;
use Hyperf\DbConnection\Db;
use Hyperf\Redis\RedisFactory;
use Psr\Container\ContainerInterface;
use Psr\Log\LoggerInterface;
use Hyperf\Logger\LoggerFactory;

use function Hyperf\Support\make;

#[Command]
class DataMigrateCommand extends HyperfCommand
{
    private const BATCH_SIZE = 1000;
    private const LOCK_KEY = 'project:migrate:data_migrate';
    private const LOCK_TTL = 3600;

    private LoggerInterface $logger;

    public function __construct(protected ContainerInterface $container)
    {
        parent::__construct('onceTask:dataMigrate');
        $this->logger = $container->get(LoggerFactory::class)->get('data_migrate', 'default');
    }

    public function configure(): void
    {
        parent::configure();
        $this->setDescription('数据迁移：xxx（幂等可重复执行）');
    }

    public function handle(): void
    {
        $redis = make(RedisFactory::class)->get('default');

        // 分布式锁防止并发执行
        if (!$redis->set(self::LOCK_KEY, '1', ['NX', 'EX' => self::LOCK_TTL])) {
            $this->logger->warning('另一个迁移任务正在执行，退出');
            return;
        }

        try {
            $this->stepOne();
            $this->stepTwo();
            $this->logger->info('全部迁移完成');
        } finally {
            $redis->del(self::LOCK_KEY);
        }
    }

    private function stepOne(): void
    {
        $this->logger->info('[1/2] 开始...');
        // 批量处理逻辑
        $this->logger->info('[1/2] 完成');
    }

    private function stepTwo(): void
    {
        $this->logger->info('[2/2] 开始...');
        // 批量处理逻辑
        $this->logger->info('[2/2] 完成');
    }
}
```

**一次性脚本规范**：
- 必须幂等（可重复执行不产生副作用）
- 必须加分布式锁（防止多实例并发）
- 必须有步骤日志（`[N/M]` 格式标记进度）
- 大数据量必须分批处理（chunk/batch）
- 完成后无需删除（留作记录），但命令名称前缀 `onceTask:` 表明不应放入 cron

## 日志

Command 中使用日志而非 `echo`（守护进程/cron 场景看不到标准输出）：

```php
use App\Utils\Logger\Log;

// 简单日志
Log::get()->info('同步完成', ['count' => $count]);
Log::get()->error('异常', ['error' => $e->getMessage()]);

// 带频道的日志（写入独立日志文件）
$logger = $this->container->get(LoggerFactory::class)->get('channel_name', 'default');
$logger->info('步骤完成');
```

**日志 + 控制台双输出**（定时任务推荐）：
```php
$this->info("[完成] 处理 {$count} 条");
Log::get()->info('处理完成', ['count' => $count]);
```

## 常见错误

- ❌ 忘记 `#[Command]` 注解（命令不会被注册）
- ❌ 构造函数中忘记调用 `parent::__construct('command:name')`
- ❌ 定时任务忘记重定向日志到文件
- ❌ 一次性脚本不加分布式锁
- ❌ 大数据量不分批处理（内存溢出）
- ❌ 用 `echo` 代替日志（守护进程后看不到）
- ❌ 异常不记录日志直接退出
- ❌ 命名空间函数裸调用（MUST `use function Hyperf\Support\make;`）
