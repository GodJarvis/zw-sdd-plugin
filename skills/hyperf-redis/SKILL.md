---
name: hyperf-redis
description: "编写 Redis 缓存、锁、计数器等操作。涉及 Redis Key 定义、缓存注解、直接 Redis 操作、连接获取时使用。Use when working with files matching: **/Constants/RedisKey*.php, **/CacheService/**/*.php."
---

# Hyperf Redis 规范

## Key 常量管理

所有 Redis Key MUST 定义在 `App\Constants\RedisKey` 常量类中，禁止在业务代码中硬编码字符串 Key。

```php
<?php

declare(strict_types=1);

namespace App\Constants;

class RedisKey
{
    /** 系统请求日志队列 */
    public const string SYSTEM_REQUEST_LOG = 'log:list:operation_request';

    /** 会员信息缓存 */
    public const string MEMBER_INFO = 'member_info';

    /** OSS STS Token 缓存 */
    public const string OSS_STS_TOKEN = 'oss_sts_token';

    /** SSE 广播流 */
    public const string SSE_STREAM_BROADCAST = 'sse:stream:broadcast';

    /** SSE 用户流（动态 Key） */
    private const string SSE_STREAM_USER = 'sse:stream:user:%s';

    public static function getSseStreamUserKey(int $uid): string
    {
        return sprintf(self::SSE_STREAM_USER, $uid);
    }
}
```

### Key 命名规则

- 格式：`{模块}:{类型}:{实体}` 或 `{模块}:{实体}:{id}`
- 分隔符统一用冒号 `:`
- 全小写，单词间用下划线
- 动态段用 `sprintf` 占位符，通过静态方法生成完整 Key（方法名 `get{用途}Key`）
- 动态 Key 的常量用 `private const`，只暴露工厂方法
- 常量加注释说明用途

## 缓存操作 — 注解模式（推荐）

通过 Hyperf Cache 注解实现缓存的读取、更新、删除，放在 `app/CacheService/` 目录下：

```php
<?php

declare(strict_types=1);

namespace App\CacheService;

use App\Constants\RedisKey;
use App\Repository\MySQL\MemberRepository;
use App\Service\BaseService;
use Hyperf\Cache\Annotation\Cacheable;
use Hyperf\Cache\Annotation\CacheEvict;
use Hyperf\Cache\Annotation\CachePut;

class MemberService extends BaseService
{
    public function __construct(
        private MemberRepository $memberRepository,
    ) {}

    // 读取缓存，未命中时执行方法体并写入
    #[Cacheable(prefix: RedisKey::MEMBER_INFO, value: '#{id}', ttl: 60)]
    public function getCacheMemberById(int $id): ?Member
    {
        return $this->memberRepository->getMemberById($id);
    }

    // 强制刷新缓存（执行方法体并覆盖写入）
    #[CachePut(prefix: RedisKey::MEMBER_INFO, value: '#{id}', ttl: 60)]
    public function updateMemberCache(int $id): ?Member
    {
        return $this->memberRepository->getMemberById($id);
    }

    // 删除缓存
    #[CacheEvict(prefix: RedisKey::MEMBER_INFO, value: '#{id}')]
    public function deleteMemberCache(int $id): bool
    {
        return true;
    }
}
```

### 注解参数说明

- `prefix`：引用 `RedisKey` 常量作为 Key 前缀
- `value`：动态部分，`#{参数名}` 引用方法参数
- `ttl`：过期时间（秒）

## 直接 Redis 操作 — RedisFactory 模式

非缓存场景（队列推送、Stream、日志写入等）通过 `RedisFactory` 直接操作：

```php
<?php

declare(strict_types=1);

namespace App\Utils;

use App\Constants\RedisKey;
use Hyperf\Redis\RedisFactory;
use Hyperf\Codec\Json;

class SystemLog
{
    public function __construct(
        protected RedisFactory $redisFactory,
    ) {}

    public function record(array $params): bool
    {
        $this->redisFactory->get('public_redis')->lpush(
            RedisKey::SYSTEM_REQUEST_LOG,
            Json::encode($params)
        );
        return true;
    }
}
```

### 连接获取

- MUST 通过 `RedisFactory` 获取连接：`$this->redisFactory->get('连接池名')`
- `default`：通用业务缓存、异步队列
- `public_redis`：日志中心专用，不可用于业务
- 其他自定义池：按 `config/autoload/redis.php` 中的配置名获取

## TTL 管理

- 注解模式下 TTL 通过 `ttl` 参数设置
- 直接操作时使用 `setex($key, $ttl, $value)`
- 热点数据注意缓存雪崩（同类 Key 加随机偏移）
- 无 TTL 的写入（`lpush`、`xAdd` 等队列/流操作）是允许的

## 目录结构

```
app/
├── Constants/
│   └── RedisKey.php          # Key 常量定义
├── CacheService/             # 缓存注解层（独立于 Service）
│   ├── MemberService.php
│   └── OssService.php
└── Service/                  # 业务层（调用 CacheService 或直接 RedisFactory）
```

## 强制规则

- ❌ 在业务代码中硬编码 Redis Key 字符串
- ❌ 手动 `new \Redis()` 创建连接
- ❌ 在 Service 层直接写 `#[Cacheable]` 注解（应放在 `CacheService/` 层）
- ❌ 修改 `public_redis` 连接池配置或将其用于业务
- ✅ Key 全部在 `RedisKey` 常量类中定义
- ✅ 缓存操作优先用注解模式 + `CacheService/` 目录
- ✅ 非缓存操作通过 `RedisFactory` + Key 常量
- ✅ 数据变更时通过 `#[CacheEvict]` 主动清除缓存
