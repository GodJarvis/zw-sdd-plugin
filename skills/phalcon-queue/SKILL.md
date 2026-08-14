---
name: phalcon-queue
description: "编写 Redis 队列或 RabbitMQ 队列的生产/消费逻辑。涉及 rpush/blPop、RabbitMqHelper、常驻 Task、Swoole Process Pool 时使用。Use when working with files matching: run/tasks/**/*.php, library/services/**/*.php."
---

# Phalcon 队列规范（Redis + RabbitMQ）

| 场景 | 队列选择 |
|------|---------|
| 内部异步任务、延迟不敏感、高吞吐 | **Redis List** |
| 需要路由、广播、可靠 ACK、跨服务 | **RabbitMQ** |
| 需要延迟消息 | **RabbitMQ**（`isDelayed=true`）|

## 一、Redis 队列

### 强制规则

- **生产必须 `rpush`，禁止 `lpush`**
- **消费必须 `blPop`**（FIFO）
- 队列 key 在 `library/constants/RedisKey.php` 定义，**禁止硬编码**

### 生产消息

```php
use Apps\Constants\RedisKey;
use Apps\Modules\DiUtils;

$redis = DiUtils::redis('redis');
$redis->rpush(
    RedisKey::MEMBER_SYNC_QUEUE,
    json_encode($data, JSON_UNESCAPED_UNICODE)
);
```

新增队列时在 `RedisKey.php` 加常量：

```php
class RedisKey
{
    const MEMBER_SYNC_QUEUE = 'member:sync:queue';
}
```

### 消费消息（常驻 Task）

```php
<?php

namespace Run\Tasks\Tasks;

use Phalcon\Cli\Task;
use Swoole\Process;
use Swoole\Process\Pool;
use Apps\Constants\RedisKey;
use Apps\Modules\DiUtils;

class MemberSyncTask extends Task
{
    public function consumeAction()
    {
        $pool = new Pool(1);
        $pool->set(['enable_coroutine' => true]);

        $pool->on('WorkerStart', function (Pool $pool, int $workerId) {
            // 必须在 worker 内部 hook，使 phpredis 的 blPop 协程化
            // 协程化后 blPop 等待时会 yield，SIGTERM 信号才能被处理
            \Swoole\Runtime::enableCoroutine(SWOOLE_HOOK_ALL);

            $running = true;
            Process::signal(SIGTERM, function () use (&$running) {
                $running = false;
            });

            $redis = DiUtils::redis('redis');
            $redisKey = RedisKey::MEMBER_SYNC_QUEUE;

            while ($running) {
                if ($lists = $redis->blPop($redisKey, 3)) {
                    $data = json_decode($lists[1], true);
                    try {
                        $this->handle($data);
                    } catch (\Throwable $e) {
                        DiUtils::getLog('member_sync_exception')->error(
                            '消费异常：' . $e->getMessage(),
                            ['data' => $data, 'trace' => $e->getTraceAsString()]
                        );
                    }
                }
            }
        });

        $pool->on('WorkerStop', function (Pool $pool, int $workerId) {});
        $pool->start();
    }

    private function handle(array $data): void
    {
        // 业务处理
    }
}
```

### Redis 队列要点

- **必须在 WorkerStart 内调用 `\Swoole\Runtime::enableCoroutine(SWOOLE_HOOK_ALL)`**——这是平滑重启的前提，使 `blPop` 协程化，等待期间可响应 SIGTERM
- `blPop` 超时**必须 3-5 秒**（太长则退出延迟大）
- `blPop` 返回 `[队列名, 值]`，取 `$lists[1]`
- 异常必须捕获 + 记日志，**不能让异常逃出循环导致进程退出**
- pop 后消息即从 Redis 中移除，进程中断会丢消息，因此**平滑重启是强制要求**

## 二、RabbitMQ 队列

### 强制规则

**所有操作必须通过 `Apps\Modules\RabbitMqHelper`**，禁止直接操作 `\AMQPConnection`、`\AMQPQueue`。

### 生产消息

```php
use Apps\Modules\RabbitMqHelper;

$helper = new RabbitMqHelper(
    $exchangeName,    // 交换机
    $routingKey,      // 路由键
    $queueName,       // 队列名
    $exchangeType,    // direct/fanout/topic/headers
    $isDelayed,       // 是否延迟交换机
    $configKey        // 默认 'rabbitmq'
);
$helper->publish($data);
```

### 消费消息（常驻 Task）

RabbitMQ 使用手动 ACK，未 ACK 的消息在进程中断后自动回到队列重新投递，因此**平滑重启非强制**（不会丢消息）。但如果希望优雅退出（处理完当前消息再停），可使用下方平滑重启方案。消费逻辑必须保证**幂等**（重复投递不产生副作用）。

**方案一：简单模式（不平滑，supervisor 硬 kill）**

```php
<?php

namespace Run\Tasks\Tasks;

use Phalcon\Cli\Task;
use Swoole\Process\Pool;
use Apps\Modules\RabbitMqHelper;
use Apps\Modules\DiUtils;

class OrderMqTask extends Task
{
    public function consumeAction()
    {
        $pool = new Pool(1);
        $pool->on('WorkerStart', function (Pool $pool, int $workerId) {
            $helper = $this->buildHelper();

            while (true) {
                try {
                    $helper->consume(function (\AMQPEnvelope $envelope, \AMQPQueue $queue) {
                        $data = json_decode($envelope->getBody(), true);
                        if (empty($data)) {
                            $queue->ack($envelope->getDeliveryTag());
                            return;
                        }
                        try {
                            $this->handle($data);
                            $queue->ack($envelope->getDeliveryTag());
                        } catch (\Throwable $e) {
                            $queue->ack($envelope->getDeliveryTag());
                            DiUtils::getLog('order_mq_exception')->error(
                                '业务异常：' . $e->getMessage(),
                                ['data' => $data]
                            );
                        }
                    });
                } catch (\Throwable $e) {
                    DiUtils::getLog('order_mq_consume')->error(
                        '消费异常：' . $e->getMessage()
                    );
                    sleep(10);
                    $helper = $this->buildHelper();
                }
            }
        });

        $pool->start();
    }

    private function buildHelper(): RabbitMqHelper
    {
        return new RabbitMqHelper(
            'order.exchange', 'order.notify',
            'order.notify.queue', 'direct', false, 'rabbitmq'
        );
    }

    private function handle(array $data): void
    {
        // 业务处理（必须幂等）
    }
}
```

**方案二：平滑重启（处理完当前消息后退出）**

AMQP 扩展的 `consume()` 无法被协程 hook，改用 `AMQPQueue::get()` 非阻塞拉取 + `Coroutine::sleep()` 轮询，使 SIGTERM 可被响应：

```php
<?php

namespace Run\Tasks\Tasks;

use Phalcon\Cli\Task;
use Swoole\Process;
use Swoole\Process\Pool;
use Apps\Modules\RabbitMqHelper;
use Apps\Modules\DiUtils;

class OrderMqTask extends Task
{
    public function consumeAction()
    {
        $pool = new Pool(1);
        $pool->set(['enable_coroutine' => true]);

        $pool->on('WorkerStart', function (Pool $pool, int $workerId) {
            \Swoole\Runtime::enableCoroutine(SWOOLE_HOOK_ALL);

            $running = true;
            Process::signal(SIGTERM, function () use (&$running) {
                $running = false;
            });

            $helper = $this->buildHelper();
            $queue = $helper->getQueue();

            while ($running) {
                try {
                    $envelope = $queue->get();
                    if ($envelope) {
                        $data = json_decode($envelope->getBody(), true);
                        try {
                            $this->handle($data);
                            $queue->ack($envelope->getDeliveryTag());
                        } catch (\Throwable $e) {
                            $queue->ack($envelope->getDeliveryTag());
                            DiUtils::getLog('order_mq_exception')->error(
                                '业务异常：' . $e->getMessage(),
                                ['data' => $data]
                            );
                        }
                    } else {
                        \Swoole\Coroutine::sleep(0.5);
                    }
                } catch (\Throwable $e) {
                    DiUtils::getLog('order_mq_consume')->error(
                        '消费异常：' . $e->getMessage()
                    );
                    \Swoole\Coroutine::sleep(10);
                    $helper = $this->buildHelper();
                    $queue = $helper->getQueue();
                }
            }
        });

        $pool->on('WorkerStop', function (Pool $pool, int $workerId) {});
        $pool->start();
    }

    private function buildHelper(): RabbitMqHelper
    {
        return new RabbitMqHelper(
            'order.exchange', 'order.notify',
            'order.notify.queue', 'direct', false, 'rabbitmq'
        );
    }

    private function handle(array $data): void
    {
        // 业务处理（必须幂等）
    }
}
```

### RabbitMQ 要点

- **平滑重启可选**：手动 ACK 模式下未 ACK 消息自动重投，不丢数据。平滑方案用于避免重复消费
- **平滑方案原理**：用 `AMQPQueue::get()`（非阻塞）替代 `consume()`（阻塞），配合 `Coroutine::sleep()` 让出执行权使信号可响应
- **平滑方案代价**：`get()` 轮询有 ~0.5s 延迟（无消息时等待间隔），吞吐量略低于 `consume()`
- **消费逻辑必须幂等**：无论哪种方案，进程被 kill 后消息都可能重新投递
- **业务异常** → `ack` + 记日志（避免消息反复投递造成死循环）
- **连接异常** → sleep 后重建 `RabbitMqHelper`
- 延迟队列：`isDelayed = true`，`publish($data, $delayMs)`
- **方案选择**：对延迟不敏感且消费幂等 → 方案一简单可靠；需要精确控制退出时机 → 方案二

## 三、常驻进程通用规则

### 平滑重启

| 队列类型 | 是否强制 | 方案 |
|---------|---------|------|
| Redis | **强制**（pop 后消息不可恢复） | `Runtime::enableCoroutine(SWOOLE_HOOK_ALL)` + `Process::signal` + `blPop` 短超时 |
| RabbitMQ | 可选（未 ACK 消息自动重投） | `Runtime::enableCoroutine(SWOOLE_HOOK_ALL)` + `Process::signal` + `AMQPQueue::get()` 轮询 |

核心原理：
1. `\Swoole\Runtime::enableCoroutine(SWOOLE_HOOK_ALL)` 使阻塞 IO 协程化
2. `Process::signal(SIGTERM, ...)` 注册协程信号回调（仅在协程 yield 时触发）
3. 阻塞操作必须能定期 yield：Redis 用 `blPop` 短超时，RabbitMQ 用 `get()` + `Coroutine::sleep()`

```php
// 1. 启用协程 hook（使 blPop 协程化，等待时可响应信号）
\Swoole\Runtime::enableCoroutine(SWOOLE_HOOK_ALL);

// 2. 注册信号只改标记
$running = true;
Process::signal(SIGTERM, function () use (&$running) {
    $running = false;
});

// 3. 循环检查标记 + blPop 短超时
while ($running) {
    $redis->blPop($key, 3); // 最多 3 秒返回，检查 $running
}
```

RabbitMQ 使用手动 ACK，不需要平滑重启——未 ACK 消息自动重投。

### 日志

- 消费异常：`DiUtils::getLog('<task>_exception')`
- 连接异常：`DiUtils::getLog('<task>_consume')`
- **必须带上下文数据**

## 常见错误

- ❌ 生产用 `lpush`（必须 `rpush`）
- ❌ 队列 key 硬编码字符串
- ❌ 绕过 `RabbitMqHelper` 直接操作 AMQP
- ❌ `blPop($key, 0)` 无超时阻塞（信号无法响应）
- ❌ Redis 消费不启用 `Runtime::enableCoroutine(SWOOLE_HOOK_ALL)`（无法平滑重启）
- ❌ 消费回调不 ack
- ❌ 消费异常没 try-catch（进程退出）
- ❌ RabbitMQ 消费逻辑不幂等（重启后重复投递会产生副作用）
- ❌ 不用 `Swoole\Process\Pool`
