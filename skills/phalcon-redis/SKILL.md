---
name: phalcon-redis
description: "编写 Redis 缓存、锁、计数器等操作。涉及 Redis Key 定义、CacheKey 动态生成、Redis 操作封装、连接获取时使用。Use when working with files matching: library/constants/RedisKey*.php, library/modules/CacheKey*.php, library/modules/Redis*.php."
---

# Phalcon Redis 规范

## Key 常量管理

Redis Key 通过两个类管理：

### RedisKey — 静态常量 Key

固定不变的 Key 定义在 `Apps\Constants\RedisKey`：

```php
<?php

namespace Apps\Constants;

class RedisKey
{
    /** 用户 Token */
    public const USER_TOKEN = 'system_name:token';

    /** ZQ 授权 */
    public const USER_ZQ_AUTHORIZATION = 'system_name:zq:authorization';

    /** 系统请求日志队列 */
    public const SYSTEM_REQUEST_LOG = 'log:list:operation_request';

    /** 摘要日志队列 */
    public const ABSTRACT_LOG = 'nacos:list:summary_rquest';
}
```

### CacheKey — 动态生成 Key

含动态参数的 Key 通过 `Apps\Modules\CacheKey` 的静态方法生成：

```php
<?php

namespace Apps\Modules;

class CacheKey
{
    public static $prefix;

    public static function operationAuthority($phone)
    {
        return self::$prefix . 'operationAuthority.' . $phone;
    }

    public static function userRateLimit($adminId, $route)
    {
        return self::$prefix . ':' . $route . ':' . $adminId;
    }

    public static function mInfo($memberID)
    {
        return self::$prefix . 'mInfo.' . $memberID;
    }

    public static function zmSystemUserList()
    {
        return self::$prefix . 'zmSystemUserList';
    }
}
```

### Key 命名规则

- 静态 Key 格式：`{系统}:{模块}:{用途}`，冒号分隔
- 动态 Key 通过 `CacheKey::方法名($参数)` 生成，前缀通过 `$prefix` 统一管理
- 新增 Key 时根据是否含动态参数决定放 `RedisKey`（静态）还是 `CacheKey`（动态）

## Redis 封装类

`Apps\Modules\Redis` 通过 `__call` 魔术方法代理原生 `\Redis` 操作，并提供公共工具方法：

```php
<?php

namespace Apps\Modules;

class Redis
{
    private $_connect;

    public function __construct($redisConfig)
    {
        $this->_connect = new \Redis();
        $this->_connect->connect($redisConfig['host'], $redisConfig['port']);

        if (!empty($redisConfig['auth'])) {
            $this->_connect->auth($redisConfig['auth']);
        }
        if (!empty($redisConfig['index'])) {
            $this->_connect->select($redisConfig['index']);
        }
    }

    public function __call($method, $args)
    {
        return call_user_func_array([$this->_connect, $method], $args);
    }

    /**
     * 频率限制检查
     * @param string $key 限流 Key
     * @param int $expire 窗口期（秒）
     * @param int $limit 窗口内最大次数
     * @return bool true=未超限，false=已超限
     */
    public function checkLock($key, $expire, $limit)
    {
        if ($this->_connect->exists($key)) {
            $this->_connect->incr($key);
        } else {
            $this->_connect->set($key, 1, $expire);
        }
        return !($this->_connect->get($key) > $limit);
    }
}
```

新增公共操作（如分布式锁、批量删除等）MUST 加在此类中，禁止在业务代码中直接操作原生 `\Redis`。

## 连接获取

### 三种获取方式

```php
// 1. DiUtils（推荐，Service/工具类中使用）
$redis = DiUtils::redis();              // 默认 'redis' 实例
$redis = DiUtils::redis('compassRedis'); // 指定实例

// 2. Controller 属性（Controller 中直接使用）
$this->redis->set(...);

// 3. DI 容器（不推荐，仅兼容旧代码）
$redis = $this->getDI()->getShared('redis');
```

### 实例说明

- `redis`：共享单例，业务用
- `compassRedis`：共享单例，日志中心专用
- `redisM`：非单例，后台多进程场景（每次获取新连接）

## 常用操作模式

### 缓存读写

```php
use Apps\Constants\RedisKey;
use Apps\Modules\CacheKey;
use Apps\Modules\DiUtils;

// 字符串缓存
$redis = DiUtils::redis();
$cached = $redis->get($key);
if (empty($cached)) {
    $data = $this->fetchFromDb();
    $redis->set($key, serialize($data), 600); // TTL 600秒
}

// Hash 缓存（按字段存取）
$val = $redis->hget(CacheKey::mInfo($memberID), $field);
if (empty($val)) {
    $mInfo = Members::from()->where('member_id', $memberID)->fetch();
    if (!empty($mInfo[$field])) {
        $redis->hset(CacheKey::mInfo($memberID), $field, $mInfo[$field]);
    }
}
```

### Token 管理

```php
// 写入 Token（带 TTL）
$this->redis->set(
    RedisKey::USER_TOKEN . ':' . $phone,
    $token,
    self::TOKEN_EXPIRES_TIME  // 86400 = 24小时
);

// 删除 Token
$this->redis->del(RedisKey::USER_TOKEN . ':' . $phone);
```

### 日志队列推送

```php
$redis = DiUtils::redis('compassRedis');
$redis->lpush(RedisKey::SYSTEM_REQUEST_LOG, json_encode($params));
```

### 缓存清除

```php
$this->redis->del(CacheKey::operationAuthority($this->user->phone));
```

## TTL 管理

- Token 类：`3600 * 24`（24小时）
- 业务缓存：`600`（10分钟）到 `3600`（1小时）按变更频率设置
- 频率限制：按接口要求设置窗口期
- 队列推送（`lpush`）：无需 TTL

建议将常用 TTL 定义为 `RedisKey` 或 `CacheKey` 类中的常量：

```php
class RedisKey
{
    public const TOKEN_EXPIRES_TIME = 3600 * 24;
    public const CACHE_SHORT = 600;
    public const CACHE_MEDIUM = 3600;
    public const CACHE_LONG = 86400;
}
```

## 强制规则

- ❌ 在业务代码中硬编码 Redis Key 字符串
- ❌ 手动 `new \Redis()` 创建连接（应通过 DI 获取 `Apps\Modules\Redis` 实例）
- ❌ 使用 `compassRedis` 实例做业务缓存
- ❌ 共享实例 `redis` 用于后台多进程（应使用 `redisM`）
- ✅ 静态 Key 放 `RedisKey`，动态 Key 放 `CacheKey`
- ✅ 新增公共操作方法写在 `Apps\Modules\Redis` 类中
- ✅ Service 层通过 `DiUtils::redis()` 获取连接
- ✅ 数据变更时主动 `del` 对应缓存
