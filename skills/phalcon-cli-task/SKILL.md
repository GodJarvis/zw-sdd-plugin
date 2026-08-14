---
name: phalcon-cli-task
description: "编写 CLI 任务（Phalcon Task）。涉及 run/tasks/ 下的任务类、命令行参数、定时任务、常驻进程、APP_ENV 环境时使用。Use when working with files matching: run/**/*.php."
---

# Phalcon CLI 任务规范

## 入口与路由

- **入口**：`php run/cli.php`
- **调用格式**：`php run/cli.php <module> <task> <action> [params...]`
- **默认**：`Task` = `MainTask`，`Action` = `mainAction`
- **`<task>` 命名规则（MUST）**：Phalcon CLI dispatcher 对 `<task>` 做 camelize 时会**先将所有字符小写化**，再按 `_` 分隔驼峰拼接并补 `Task` 后缀匹配类名。因此 `<task>` 必须用 **全小写 + 下划线 `_` 拼接**，禁止驼峰/大写
  - ✅ `member_sync` → 小写化+按`_`分隔 → `MemberSync` → 匹配 `MemberSyncTask`
  - ❌ `memberSync` → 小写化 → `membersync`（无分隔符）→ `Membersync` → 找不到类，报错
  - ❌ `MemberSync` → 小写化 → `membersync` → 同上

```bash
php run/cli.php tasks main main            # MainTask::mainAction
php run/cli.php tasks member sync 100      # MemberTask::syncAction 带参数
php run/cli.php tasks member_sync consume  # MemberSyncTask::consumeAction 常驻消费
```

## 目录结构

```
run/
├── cli.php                    # CLI 入口
├── config/
│   ├── cliRoutes.php          # CLI 路由配置
│   └── services.php           # 服务注册
└── tasks/
    └── tasks/                 # 任务类
        ├── MainTask.php
        └── MemberTask.php
```

## 任务类模板

```php
<?php

namespace Run\Tasks\Tasks;

use Phalcon\Cli\Task;
use Apps\Modules\DiUtils;

/**
 * 会员相关任务
 * User: 张三
 * Date: 2026/04/23
 */
class MemberTask extends Task
{
    public function mainAction()
    {
        echo "MemberTask 可用动作：\n";
        echo "  sync [batchSize]  同步会员数据\n";
    }

    public function syncAction()
    {
        $params = $this->dispatcher->getParams();
        $batchSize = (int)($params[0] ?? 100);

        echo "[" . date('Y-m-d H:i:s') . "] 开始同步，批次大小：{$batchSize}\n";

        try {
            $count = $this->doSync($batchSize);
            echo "[" . date('Y-m-d H:i:s') . "] 同步完成，处理 {$count} 条\n";
        } catch (\Throwable $e) {
            DiUtils::getLog('member_sync_exception')->error(
                '同步异常：' . $e->getMessage(),
                ['trace' => $e->getTraceAsString()]
            );
            echo "[ERROR] " . $e->getMessage() . "\n";
            exit(1);
        }
    }

    private function doSync(int $batchSize): int
    {
        return 0;
    }
}
```

## 参数获取

```php
// php run/cli.php tasks member sync arg1 arg2
$params = $this->dispatcher->getParams();
// $params = ['arg1', 'arg2']
$batchSize = (int)($params[0] ?? 100);
```

## 常驻任务 vs 定时任务

| 类型 | 触发方式 | 是否需要 Process\Pool | 退出行为 |
|------|---------|---------------------|---------|
| 定时任务 | cron 调度 | 不需要 | 跑完即退出 |
| 常驻任务 | supervisor 守护 | **必须** | 永不退出 |

- **常驻任务**（消费队列、轮询）的完整写法见 `phalcon-queue` skill，包括 `Swoole\Process\Pool`、SIGTERM 信号处理、supervisor 配置。

## 定时任务（cron）

```cron
# 每小时同步
0 * * * * cd /path/to/project && APP_ENV=production php run/cli.php tasks member sync 500 >> data/log/cron/member_sync.log 2>&1

# 每天凌晨 3 点清理
0 3 * * * cd /path/to/project && APP_ENV=production php run/cli.php tasks member clean 30 >> data/log/cron/member_clean.log 2>&1

# 每 10 分钟执行订单超时关闭（双单词 task 用下划线拼接）
*/10 * * * * cd /path/to/project && APP_ENV=production php run/cli.php tasks order_timeout close >> data/log/cron/order_timeout_close.log 2>&1
```

## 环境变量

`APP_ENV` 决定配置文件，默认 `develop`：

```bash
APP_ENV=production php run/cli.php tasks member sync 100
```

## 日志

**不要用 `echo` 作为正式日志**（守护进程后看不到）：

```php
DiUtils::getLog('member_task')->info('同步完成', ['count' => 100]);
```

`DiUtils::getLog($filename)` 会自动按日期切分。

## 路由注册

新增 task 要在 `run/config/cliRoutes.php` 中注册：

```php
return [
    'tasks' => [
        'className' => 'Run\Tasks\Module',
        'path' => __DIR__ . '/../tasks/Module.php',
    ],
];
```

## 常见错误

- ❌ 方法名漏掉 `Action` 后缀
- ❌ 类名漏掉 `Task` 后缀
- ❌ `<task>` 用驼峰命名（如 `memberSync`），MUST 用下划线拼接（`member_sync`）
- ❌ 常驻任务不用 `Process\Pool`（详见 `phalcon-queue`）
- ❌ 用 `echo` 代替日志
- ❌ 定时任务忘了加 `APP_ENV`
- ❌ 定时任务忘了重定向日志
- ❌ 一次性任务用死循环
