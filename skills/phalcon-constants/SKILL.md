---
name: phalcon-constants
description: "定义或引用业务常量、枚举值、枚举映射。涉及 status/type 等整形枚举、标量常量、枚举值之间的映射、constants 目录下的类时使用。Use when working with files matching: library/constants/**/*.php."
---

# Phalcon Constants 规范

## 铁律

- **所有业务枚举值（status、type、整形/标量枚举）必须定义为常量类，维护在 `library/constants/` 目录（`Apps\Constants` 命名空间），禁止硬编码魔术数字/字符串**
- 枚举值之间的映射关系用同一常量类中的 `array` 常量定义
- 代码中引用枚举值必须通过常量类引用，禁止直接写字面量

## 常量类命名规则

| 类型 | 命名 | 示例 |
|------|------|------|
| 业务状态/类型枚举 | `{业务领域}{Enum/Status/Type}` | `OrderStatus`、`MemberType`、`AuditStatus` |
| 基础设施 Key | `{中间件}Key` | `RedisKey` |
| 系统级常量 | 按领域命名 | `SensitiveOperation` |

## 标准模板 — 业务枚举

```php
<?php

namespace Apps\Constants;

class OrderStatus
{
    const PENDING = 1;
    const PROCESSING = 2;
    const COMPLETED = 3;
    const CANCELLED = 4;

    /** 状态 → 中文描述映射 */
    const LABEL_MAP = [
        self::PENDING => '待处理',
        self::PROCESSING => '处理中',
        self::COMPLETED => '已完成',
        self::CANCELLED => '已取消',
    ];
}
```

## 标准模板 — 枚举值映射

```php
<?php

namespace Apps\Constants;

class PaymentType
{
    const WECHAT = 1;
    const ALIPAY = 2;
    const BANK_CARD = 3;

    /** 支付方式 → 结算通道映射 */
    const SETTLEMENT_CHANNEL_MAP = [
        self::WECHAT => SettlementChannel::WECHAT_PAY,
        self::ALIPAY => SettlementChannel::ALIPAY_DIRECT,
        self::BANK_CARD => SettlementChannel::UNION_PAY,
    ];
}
```

## 标准模板 — 动态 Key（含参数拼接）

```php
<?php

namespace Apps\Constants;

class RedisKey
{
    const USER_TOKEN = 'system_name:token';

    const USER_LOCK = 'system_name:lock:%s';

    /**
     * @param int $uid
     * @return string
     */
    public static function getUserLockKey($uid)
    {
        return sprintf(self::USER_LOCK, $uid);
    }
}
```

## 常量定义规则

1. PHP 7.3 兼容：不使用类型声明、不使用属性注解、不使用 `declare(strict_types=1)`
2. 命名风格：`UPPER_SNAKE_CASE`
3. 可见性：省略 `public` 修饰符（PHP 7.x 类常量默认 public），直接写 `const`
4. 一个常量类对应一个业务领域，避免创建巨型常量类
5. 映射数组的 key 和 value 都必须引用常量，禁止直接写字面量
6. 动态 Key 通过 static method + `sprintf` 生成

## 使用方式

```php
// 正确 — 引用常量
if ($order['status'] === OrderStatus::COMPLETED) { ... }
$label = OrderStatus::LABEL_MAP[$order['status']] ?? '未知';

// 错误 — 硬编码魔术数字
if ($order['status'] === 3) { ... }
```
