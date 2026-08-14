---
name: hyperf-queue
description: "编写消息队列消费者/生产者和异步任务。涉及 AMQP (RabbitMQ)、Kafka、Redis Async Queue、Job 投递、消费者命令时使用。Use when working with files matching: **/Amqp/**/*.php, **/Kafka/**/*.php, **/Job/**/*.php, **/Client/JobClient.php, **/Command/*ConsumerCommand.php, **/Command/AbstractConsumerCommand.php."
---

# Hyperf 消息队列与异步任务规范

## 队列选型

| 场景 | 队列选择 |
|------|---------|
| 内部异步任务、高吞吐、延迟不敏感 | **Redis Async Queue** |
| 需要路由、广播、可靠 ACK、延迟消息 | **AMQP (RabbitMQ)** |
| 跨服务事件流、高吞吐日志、需要回溯 | **Kafka** |

## 启动方式（铁律）

**消费者不使用框架注解启动**（`#[Consumer]`/`#[KafkaConsumer]` 等），全部通过命令行启动，内部使用 Swoole Process Pool 管理 worker 进程：

```bash
php bin/hyperf.php amqp:consume -c ClassName -w 4 --coroutines 2
php bin/hyperf.php kafka:consume -c ClassName -w 3 --coroutines 2
php bin/hyperf.php redis:consume -p default -w 4 --coroutines 2
```

| 参数 | 说明 | 默认 |
|------|------|------|
| `-w` / `--workers` | worker 进程数（Swoole Pool 管理） | 消费者类的 `$nums` / 1 |
| `--coroutines` | 每个 worker 内的并发协程数 | 1 |
| `-c` / `--consumer` | 消费者类名（短名自动补全命名空间） | — |
| `-p` / `--pool` | Redis 队列 pool 名称 | default |

**并发模型**：`workers × coroutines` = 总并发度。例如 `-w 4 --coroutines 2` = 4 进程 × 2 协程 = 8 并发消费。

## 消费者命令基础设施（AbstractConsumerCommand）

所有消费者命令继承统一的抽象基类 `AbstractConsumerCommand`，它封装了 Swoole Process Pool + 协程并发的公共逻辑：

```php
<?php

declare(strict_types=1);

namespace App\Command;

use App\Utils\Logger\Log;
use Hyperf\Command\Command as HyperfCommand;
use Hyperf\Coordinator\Constants;
use Hyperf\Coordinator\CoordinatorManager;
use Hyperf\Process\ProcessManager;
use Swoole\Process\Pool;
use Swoole\Runtime;
use Symfony\Component\Console\Input\InputOption;
use function Hyperf\Coroutine\parallel;
use function Hyperf\Support\swoole_hook_flags;

abstract class AbstractConsumerCommand extends HyperfCommand
{
    protected bool $coroutine = false;

    public function configure(): void
    {
        parent::configure();
        $this->addOption('workers', 'w', InputOption::VALUE_OPTIONAL, 'Number of worker processes');
        $this->addOption('coroutines', 't', InputOption::VALUE_OPTIONAL, 'Number of coroutines per worker', '1');
    }

    public function handle(): void
    {
        $consumer = $this->resolveConsumer();
        if ($consumer === null) {
            return;
        }

        $workersOption = $this->input->getOption('workers');
        $workerNums = $workersOption !== null ? (int) $workersOption : $this->getWorkerCount($consumer);
        if ($workerNums < 1) {
            $this->error('Workers must be greater than 0');
            return;
        }

        $coroutineCount = max(1, (int) $this->input->getOption('coroutines'));

        $concurrencyInfo = $coroutineCount > 1
            ? "{$workerNums} worker(s) x {$coroutineCount} coroutine(s)"
            : "{$workerNums} worker(s)";
        $this->info("Starting {$this->getConsumerIdentifier($consumer)} with {$concurrencyInfo}");

        ProcessManager::setRunning(true);
        $this->beforeStart($consumer);

        $pool = new Pool($workerNums, SWOOLE_IPC_NONE, 0, true);
        $pool->on('WorkerStart', fn(Pool $pool, int $workerId) => $this->onWorkerStart($consumer, $workerId, $coroutineCount));
        $pool->start();
    }

    protected function beforeStart(mixed $consumer): void {}

    private function onWorkerStart(mixed $consumer, int $workerId, int $coroutineCount): void
    {
        Runtime::enableCoroutine(swoole_hook_flags());
        $this->setLogContext($consumer);

        try {
            if ($coroutineCount > 1) {
                $callables = array_fill(0, $coroutineCount, fn() => $this->consume($consumer, $workerId));
                parallel($callables);
            } else {
                $this->consume($consumer, $workerId);
            }
        } catch (\Throwable $e) {
            Log::get()->error($this->formatException($e), $this->getErrorContext($consumer, $workerId));
        }

        CoordinatorManager::until(Constants::WORKER_EXIT)->resume();
    }

    private function formatException(\Throwable $e): string
    {
        return sprintf(
            "%s: %s(%s) in %s:%s\nStack trace:\n%s",
            get_class($e), $e->getMessage(), $e->getCode(),
            $e->getFile(), $e->getLine(), $e->getTraceAsString()
        );
    }

    /** 解析消费者实例，返回 null 时终止 */
    abstract protected function resolveConsumer(): mixed;

    /** 获取默认 worker 数量（命令行未指定 -w 时的回退） */
    abstract protected function getWorkerCount(mixed $consumer): int;

    /** 设置日志上下文（进程级） */
    abstract protected function setLogContext(mixed $consumer): void;

    /** 实际消费逻辑（运行在协程中） */
    abstract protected function consume(mixed $consumer, int $workerId): void;

    /** 异常时的上下文信息 */
    abstract protected function getErrorContext(mixed $consumer, int $workerId): array;

    /** 消费者标识（日志输出用） */
    abstract protected function getConsumerIdentifier(mixed $consumer): string;
}
```

### 新增消费者命令（基于 AbstractConsumerCommand）

通常只需实现 6 个抽象方法：

```php
<?php

declare(strict_types=1);

namespace App\Command;

use Hyperf\Command\Annotation\Command;

#[Command(name: 'amqp:consume')]
class AmqpConsumerCommand extends AbstractConsumerCommand
{
    // ... 实现 resolveConsumer / getWorkerCount / consume 等方法
}
```

**注意**：消费者命令属于基础设施，通常项目创建时已存在（AMQP/Kafka/Redis 三种），新业务只需新增消费者类（`app/Amqp/Consumer/`、`app/Kafka/Consumer/`），不需要新增 Command。

## 目录结构

```
app/
├── Amqp/
│   ├── BaseConsumer.php          # AMQP 消费者基类
│   ├── BaseProducer.php          # AMQP 生产者基类
│   ├── Consumer/                 # 消费者类
│   │   └── OrderNotifyConsumer.php
│   └── Producer/                 # 生产者类
│       └── OrderNotifyProducer.php
├── Kafka/
│   ├── ConsumerManager.php       # 自定义 ConsumerManager（暴露 createProcess）
│   └── Consumer/                 # 消费者类
│       └── EventLogConsumer.php
├── Job/                          # Redis 异步队列 Job
│   └── SendEmailJob.php
├── Client/
│   └── JobClient.php             # Redis 队列投递客户端
├── Command/                      # 消费命令（基础设施，通常已存在）
│   ├── AbstractConsumerCommand.php
│   ├── AmqpConsumerCommand.php
│   ├── KafkaConsumerCommand.php
│   └── RedisConsumerCommand.php
└── Constants/
    ├── RabbitMqKey.php           # AMQP 队列/交换机/路由键常量
    └── KafkaKey.php              # Kafka topic/groupId 常量
```

## 一、AMQP (RabbitMQ)

### 常量定义

```php
<?php

declare(strict_types=1);

namespace App\Constants;

class RabbitMqKey
{
    public const string ORDER_NOTIFY_EXCHANGE = 'order_notify_exchange';
    public const string ORDER_NOTIFY_ROUTING_KEY = 'order_notify_routing_key';
    public const string ORDER_NOTIFY_QUEUE = 'order_notify_queue';
}
```

### 消费者

```php
<?php

declare(strict_types=1);

namespace App\Amqp\Consumer;

use App\Amqp\BaseConsumer;
use App\Constants\RabbitMqKey;
use App\Utils\Logger\Log;
use Hyperf\Amqp\Result;
use PhpAmqpLib\Message\AMQPMessage;

class OrderNotifyConsumer extends BaseConsumer
{
    protected string $exchange = RabbitMqKey::ORDER_NOTIFY_EXCHANGE;
    protected array|string $routingKey = RabbitMqKey::ORDER_NOTIFY_ROUTING_KEY;
    protected ?string $queue = RabbitMqKey::ORDER_NOTIFY_QUEUE;
    protected int $nums = 2;

    public function consumeMessage($data, AMQPMessage $message): Result
    {
        try {
            Log::get()->info('订单通知消费', ['data' => $data]);
            return Result::ACK;
        } catch (\Throwable $e) {
            Log::get()->error('订单通知消费异常', [
                'data' => $data,
                'error' => $e->getMessage(),
            ]);
            return Result::ACK;
        }
    }
}
```

### 生产者

```php
<?php

declare(strict_types=1);

namespace App\Amqp\Producer;

use App\Amqp\BaseProducer;
use App\Constants\RabbitMqKey;
use Hyperf\Amqp\Annotation\Producer;

#[Producer(exchange: RabbitMqKey::ORDER_NOTIFY_EXCHANGE, routingKey: RabbitMqKey::ORDER_NOTIFY_ROUTING_KEY)]
class OrderNotifyProducer extends BaseProducer
{
    public function __construct($data)
    {
        $this->payload = $data;
    }
}
```

### 投递消息

```php
use App\Amqp\Producer\OrderNotifyProducer;
use Hyperf\Amqp\Producer;
use Hyperf\Di\Annotation\Inject;

#[Inject]
protected Producer $producer;

$this->producer->produce(new OrderNotifyProducer(['order_id' => 123]));
```

### 延迟消息

消费者和生产者均需引入 Trait：

```php
// Consumer
use Hyperf\Amqp\Message\ConsumerDelayedMessageTrait;
use Hyperf\Amqp\Message\ProducerDelayedMessageTrait;

class DelayOrderConsumer extends BaseConsumer
{
    use ProducerDelayedMessageTrait;
    use ConsumerDelayedMessageTrait;
    // ...
}

// Producer
use Hyperf\Amqp\Message\ProducerDelayedMessageTrait;

class DelayOrderProducer extends BaseProducer
{
    use ProducerDelayedMessageTrait;
    // ...
}

// 投递时指定延迟（毫秒）
$producer->produce(new DelayOrderProducer($data), true, 5000);
```

### BaseConsumer 基类

```php
<?php

declare(strict_types=1);

namespace App\Amqp;

use App\Enum\AppEnv;
use Hyperf\Amqp\Message\ConsumerMessage;
use Hyperf\Amqp\Message\Type;

abstract class BaseConsumer extends ConsumerMessage
{
    protected Type|string $type = Type::DIRECT;

    protected int $maxConsumption = 10000;

    protected ?array $qos = [
        'prefetch_size' => 0,
        'prefetch_count' => 5,
        'global' => false,
    ];

    public function getNums(): int
    {
        if (AppEnv::current() !== AppEnv::PRODUCTION) {
            return 1;
        }
        return parent::getNums();
    }
}
```

### BaseProducer 基类

```php
<?php

declare(strict_types=1);

namespace App\Amqp;

use Hyperf\Amqp\Message\ProducerMessage;
use Hyperf\Amqp\Message\Type;

abstract class BaseProducer extends ProducerMessage
{
    protected Type|string $type = Type::DIRECT;
}
```

## 二、Kafka

### 常量定义

```php
<?php

declare(strict_types=1);

namespace App\Constants;

class KafkaKey
{
    public const string ORDER_EVENT_TOPIC = 'order_event';
    public const string ORDER_EVENT_GROUP_ID = 'order_event_hyperf';
}
```

### 消费者

```php
<?php

declare(strict_types=1);

namespace App\Kafka\Consumer;

use App\Constants\KafkaKey;
use App\Utils\Logger\Log;
use Hyperf\Kafka\AbstractConsumer;
use longlang\phpkafka\Consumer\ConsumeMessage;

class OrderEventConsumer extends AbstractConsumer
{
    public array|string $topic = KafkaKey::ORDER_EVENT_TOPIC;
    public ?string $groupId = KafkaKey::ORDER_EVENT_GROUP_ID;

    public function consume(ConsumeMessage $message): void
    {
        $data = json_decode($message->getValue(), true);
        Log::get()->info('Kafka 消息消费', ['data' => $data]);
    }
}
```

### ConsumerManager（基础设施）

```php
<?php

declare(strict_types=1);

namespace App\Kafka;

use Hyperf\Kafka\AbstractConsumer;
use Hyperf\Kafka\ConsumerManager as BaseConsumerManager;
use Hyperf\Process\AbstractProcess;

class ConsumerManager extends BaseConsumerManager
{
    public function createProcess(AbstractConsumer $consumer): AbstractProcess
    {
        return parent::createProcess($consumer);
    }
}
```

## 三、Redis Async Queue

### Job 类

```php
<?php

declare(strict_types=1);

namespace App\Job;

use App\Utils\Logger\Log;
use Hyperf\AsyncQueue\Job;

class SendEmailJob extends Job
{
    public array $payload;

    public function __construct(array $payload)
    {
        $this->payload = $payload;
    }

    public function handle(): void
    {
        Log::get()->info('发送邮件', ['payload' => $this->payload]);
    }
}
```

### 投递（通过 JobClient）

```php
use App\Client\JobClient;
use App\Job\SendEmailJob;
use Hyperf\Di\Annotation\Inject;

#[Inject]
protected JobClient $jobClient;

// 立即投递
$this->jobClient->publish(new SendEmailJob(['to' => 'user@example.com']));

// 延迟投递（秒）
$this->jobClient->publish(new SendEmailJob($payload), 60);
```

### JobClient

```php
<?php

declare(strict_types=1);

namespace App\Client;

use Hyperf\AsyncQueue\Driver\DriverFactory;
use Hyperf\AsyncQueue\JobInterface;
use Hyperf\Di\Annotation\Inject;

class JobClient
{
    #[Inject]
    public DriverFactory $driverFactory;

    public function publish(JobInterface $job, int $delay = 0): bool
    {
        return $this->driverFactory->get('default')->push($job, $delay);
    }
}
```

### 配置（config/autoload/async_queue.php）

```php
return [
    'default' => [
        'driver' => \Hyperf\AsyncQueue\Driver\RedisDriver::class,
        'redis' => ['pool' => 'default'],
        'channel' => sprintf('%s:async_queue', env('SYSTEM_CHARACTER', 'hyperf')),
        'timeout' => 2,
        'retry_seconds' => 5,
        'handle_timeout' => 10,
        'processes' => 1,
        'concurrent' => ['limit' => 10],
        'max_messages' => 10000,
    ],
];
```

## 四、协程并发配置指引

| 场景 | 推荐配置 | 原因 |
|------|---------|------|
| IO 密集（HTTP 回调、外部 API） | `-w 2 --coroutines 4` | 协程切换提高吞吐，少量进程即可 |
| CPU 密集（数据计算、图片处理） | `-w 4 --coroutines 1` | CPU 任务无法被协程切换加速，多进程更有效 |
| 通用业务逻辑 | `-w 2 --coroutines 2` | 平衡方案 |
| 单条消息处理时间长（>5s） | `-w N --coroutines 1` | 避免协程饥饿 |

**注意**：
- `--coroutines > 1` 时，消费逻辑必须协程安全（不使用共享变量、全局状态）
- 总并发 = workers × coroutines，调整时结合下游承载能力
- 非生产环境消费者 worker 数强制为 1（BaseConsumer 已处理）

## 五、定时任务

通过服务器 crontab 调用 Hyperf Command：

```cron
# 每小时清理过期数据
0 * * * * cd /path/to/project && php bin/hyperf.php app:clean-expired >> /path/to/log/cron.log 2>&1

# 每天凌晨同步
0 3 * * * cd /path/to/project && php bin/hyperf.php app:daily-sync >> /path/to/log/cron.log 2>&1
```

定时任务 Command 的完整写法（类结构、参数、日志、一次性脚本）详见 `hyperf-command` skill。

## 强制规则

- ❌ 消费者使用 `#[Consumer]` / `#[KafkaConsumer]` 注解启动（必须命令行启动）
- ❌ 队列 key / topic / exchange 硬编码字符串（必须定义在 Constants）
- ❌ consumeMessage 中异常逃逸（必须 try-catch + 日志）
- ❌ 消费逻辑不幂等（AMQP/Kafka 重投递场景下会重复消费）
- ❌ 手动 new Redis / new AMQPConnection（必须通过框架连接池）
- ❌ Job::handle() 中抛出未捕获异常（会进入 failed 队列）
- ❌ 协程模式下使用全局变量/静态属性存储状态（`--coroutines > 1` 时会竞态）
- ❌ 新增消费者命令文件（基础设施已存在 AbstractConsumerCommand，只需新增消费者类）
