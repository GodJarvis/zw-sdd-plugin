---
name: hyperf-constants
description: "定义或引用业务常量、枚举值、枚举映射。涉及 status/type 等整形枚举、标量常量、枚举值之间的映射、Constants 目录下的类时使用。Use when working with files matching: app/Constants/**/*.php."
---

# Hyperf Constants 规范

## 铁律

- **所有业务枚举值（status、type、整形/标量枚举）必须定义为常量类，维护在 `app/Constants/` 目录（`App\Constants` 命名空间），禁止硬编码魔术数字/字符串**
- 枚举值之间的映射关系用同一常量类中的 `array` 常量定义
- 代码中引用枚举值必须通过常量类引用，禁止直接写字面量

## 常量类命名规则

| 类型 | 命名 | 示例 |
|------|------|------|
| 业务状态/类型枚举 | `{业务领域}{Enum/Status/Type}` | `OrderStatus`、`MemberType`、`AuditStatus` |
| 基础设施 Key | `{中间件}Key` | `RedisKey`、`KafkaKey`、`RabbitMqKey` |
| 系统级常量 | 按领域命名 | `System`、`SensitiveOperation` |

## 标准模板 — 业务枚举

```php
<?php

declare(strict_types=1);

namespace App\Constants;

class OrderStatus
{
    public const int PENDING = 1;
    public const int PROCESSING = 2;
    public const int COMPLETED = 3;
    public const int CANCELLED = 4;

    /** 状态 → 中文描述映射 */
    public const array LABEL_MAP = [
        self::PENDING => '待处理',
        self::PROCESSING => '处理中',
        self::COMPLETED => '已完成',
        self::CANCELLED => '已取消',
    ];
}
```

## 标准模板 — 带 Message 注解（需要框架 getMessage 能力时）

```php
<?php

declare(strict_types=1);

namespace App\Constants;

use Hyperf\Constants\Annotation\Constants;
use Hyperf\Constants\Annotation\Message;
use Hyperf\Constants\ConstantsTrait;

#[Constants]
class AuditStatus
{
    use ConstantsTrait;

    #[Message('待审核')]
    public const int PENDING = 1;

    #[Message('审核通过')]
    public const int APPROVED = 2;

    #[Message('审核拒绝')]
    public const int REJECTED = 3;
}
```

## 标准模板 — 枚举值映射

```php
<?php

declare(strict_types=1);

namespace App\Constants;

class PaymentType
{
    public const int WECHAT = 1;
    public const int ALIPAY = 2;
    public const int BANK_CARD = 3;

    /** 支付方式 → 结算通道映射 */
    public const array SETTLEMENT_CHANNEL_MAP = [
        self::WECHAT => SettlementChannel::WECHAT_PAY,
        self::ALIPAY => SettlementChannel::ALIPAY_DIRECT,
        self::BANK_CARD => SettlementChannel::UNION_PAY,
    ];
}
```

## 标准模板 — 动态 Key（含参数拼接）

```php
<?php

declare(strict_types=1);

namespace App\Constants;

class RedisKey
{
    public const string USER_TOKEN = 'system:token:%s';

    public static function getUserTokenKey(int $uid): string
    {
        return sprintf(self::USER_TOKEN, $uid);
    }
}
```

动态 Key 的常量声明为 `private const`（当仅通过 static method 访问时）或 `public const`（当需要直接引用模板时）。

## 常量定义规则

1. 类型声明：所有常量必须声明类型（`int`、`string`、`array`）
2. 命名风格：`UPPER_SNAKE_CASE`
3. 可见性：默认 `public const`，仅通过 static method 访问的模板 Key 用 `private const`
4. 一个常量类对应一个业务领域，避免创建巨型常量类
5. 映射数组的 key 和 value 都必须引用常量，禁止直接写字面量

## 使用方式

```php
// 正确 — 引用常量
if ($order->status === OrderStatus::COMPLETED) { ... }
$label = OrderStatus::LABEL_MAP[$order->status] ?? '未知';

// 错误 — 硬编码魔术数字
if ($order->status === 3) { ... }
```
