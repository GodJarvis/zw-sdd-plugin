---
name: phalcon-test
description: "编写 Phalcon 单元测试和集成测试。涉及 test 目录下的测试用例创建、DI 容器 Mock、数据库断言、Service/Controller 测试时使用。触发词：测试、单元测试、集成测试、TDD、TestCase、Mock、phpunit、assertJson、assertDatabaseHas。Use when working with files matching: **/test/**/*.php, **/phpunit.xml*."
---

# Phalcon 测试规范

> 适用于 Phalcon 3.4+ / PHPUnit 9.6+ / PHP 7.3+。

## 测试分类与目录

| 类型 | 目录 | 基类 | 特征 |
|------|------|------|------|
| 单元测试 | `test/Cases/` | `Test\TestCase` | Mock 所有外部依赖，毫秒级执行，不初始化 DI |
| 集成测试 | `test/Integration/` | `Test\IntegrationTestCase` | 初始化 DI 容器，连接真实数据库/Redis，事务自动回滚 |

目录结构按被测类的命名空间映射：
```
test/Cases/Services/     →  测试 Apps\Services\*
test/Cases/Modules/      →  测试 Apps\Modules\*
test/Cases/Constants/    →  测试 Apps\Constants\*
test/Integration/Admin/ →  测试 Admin 模块完整链路
test/Integration/Api/   →  测试 Api 模块完整链路
```

## TDD 流程（严格遵循）

### Step 1：确定测试类型

| 目标 | 选择 | 理由 |
|------|------|------|
| Constants/纯逻辑工具类 | 单元测试 | 无外部依赖 |
| Service 层业务分支 | 单元测试 | Mock Model/外部调用 |
| Modules（JWT/Auth 等） | 单元测试 | Mock 配置和 HTTP |
| 完整接口流程（Controller → Service → DB） | 集成测试 | 需要 DI 容器和真实数据库 |
| 数据库读写正确性 | 集成测试 | 需要真实 SQL 执行 |
| Redis 操作验证 | 集成测试 | 需要真实 Redis 连接 |

### Step 2：创建测试文件

文件命名：`{被测类名}Test.php`

```php
<?php

declare(strict_types=1);

namespace Test\Cases\{子目录};  // 或 Test\Integration\{子目录}

use Test\TestCase;  // 或 Test\IntegrationTestCase

/**
 * @covers \Apps\{被测类完整命名空间}
 */
class {被测类名}Test extends TestCase
{
    // ...
}
```

### Step 3：编写失败测试（Red）

先写测试方法，断言期望行为，此时运行应失败。

### Step 4：编写实现代码（Green）

在 `library/` 或 `apps/` 中写最小实现使测试通过。

### Step 5：运行验证

```bash
# 容器内执行
docker exec {容器名} sh -c "cd {项目路径} && vendor/bin/phpunit --filter {方法名} test/{文件路径}"
```

### Step 6：重构

测试通过后可安全重构，重新运行确保仍然 Green。

---

## 单元测试编写规范

### 基类：`Test\TestCase`

不初始化 DI 容器，不连接任何外部服务。所有依赖通过 Mock 或手动构造。

### 测试替身强制规则

单元测试中，以下依赖 **MUST 使用测试替身（Mock/Stub）**，禁止调用真实实现：

| 依赖类型 | 必须 Mock | 说明 |
|----------|-----------|------|
| Model 层（数据库查询） | ✅ | 禁止触发真实 SQL |
| 外部 HTTP 调用（第三方 API、微服务） | ✅ | 禁止发出真实网络请求 |
| Redis 操作 | ✅ | 禁止连接真实 Redis |
| 队列/消息投递 | ✅ | 禁止触发真实 MQ |
| 文件系统 I/O | ✅ | 禁止读写真实文件 |
| 日志（关键断言时） | ✅ | Mock Logger 验证日志是否写入 |
| 纯计算/枚举/DTO | ❌ | 无副作用，直接使用真实类 |

**原则：单元测试只验证被测类自身的逻辑分支，一切跨边界的依赖都用替身隔离。**

### Mock 依赖模板（使用 PHPUnit 内置 Mock）

#### 基础：Mock Model / Service

```php
use PHPUnit\Framework\MockObject\MockObject;

// 创建 Mock
$model = $this->createMock(\Apps\Models\Member::class);
$model->method('findFirst')->willReturn((object)['id' => 1, 'name' => 'test']);

// 验证方法被调用
$service = $this->createMock(\Apps\Services\MemberService::class);
$service->expects($this->once())
    ->method('getMemberById')
    ->with(1)
    ->willReturn(['id' => 1]);
```

#### Mock 外部 HTTP 客户端

```php
$httpClient = $this->createMock(\GuzzleHttp\ClientInterface::class);
$httpClient->method('request')
    ->with('POST', '/api/user/info', $this->anything())
    ->willReturn(new \GuzzleHttp\Psr7\Response(200, [], json_encode(['code' => 0, 'data' => ['name' => 'test']])));
```

#### Mock Redis

```php
$redis = $this->createMock(\Redis::class);
$redis->method('get')->with('user:1')->willReturn(json_encode(['id' => 1]));
$redis->method('set')->willReturn(true);
```

#### 通过反射注入 Mock 到 Service（静态方法/私有属性场景）

```php
$service = new SomeService();
$reflection = new \ReflectionClass($service);
$prop = $reflection->getProperty('httpClient');
$prop->setAccessible(true);
$prop->setValue($service, $httpClientMock);
```

#### 验证方法调用次数与参数

```php
$notifyService = $this->createMock(NotifyService::class);
$notifyService->expects($this->once())
    ->method('sendMessage')
    ->with($this->callback(fn ($msg) => str_contains($msg, '审批')))
    ->willReturn(true);
```

### 测试 Service 层

```php
namespace Test\Cases\Services;

use Test\TestCase;
use Apps\Services\MemberService;

class MemberServiceTest extends TestCase
{
    public function testGetMemberByIdReturnsArray(): void
    {
        $service = new MemberService();
        // 直接测试不依赖 DI 的逻辑
        // 或通过反射注入 Mock 依赖
    }
}
```

### 测试 Modules（JWT 等）

```php
namespace Test\Cases\Modules;

use Test\TestCase;
use Apps\Modules\Jwt\Token;

class JwtTest extends TestCase
{
    public function testTokenGenerationReturnsString(): void
    {
        // 手动构造所需配置
        $jwt = new Token(['key' => 'test_secret']);
        $token = $jwt->encode(['user_id' => 1]);
        $this->assertIsString($token);
    }
}
```

---

## 集成测试编写规范

### 基类：`Test\IntegrationTestCase`

已内置能力：
- Phalcon DI 容器初始化（`$this->di`）
- Config 服务（合并 `config.php` + `config.develop.php`）
- Redis 服务
- 事务自动回滚（`DatabaseTransactionTrait`）
- 认证辅助（`actingAs()` — 详见「认证鉴权策略」节）

### 事务回滚控制

```php
// 默认包裹 db 服务
protected array $connectionsToTransact = ['db'];

// 不需要数据库
protected array $connectionsToTransact = [];
```

### 认证鉴权策略 —— 编写测试前 MUST 检测

集成测试要穿过认证中间件验证完整 HTTP 链路。不同项目的鉴权机制不同，**编写测试前 MUST 探索项目认证实现**，禁止未经检测就硬编码 `actingAs()` 或特定 header。

#### Step 0: 探索检测

1. 定位项目认证实现（通常 `Apps\Components\Auth` 或 `Plugins\SecurityPlugin`）
2. 确认认证流程
3. 按以下规则判定：

| 检测信号 | 鉴权类型 | 测试写法 |
|----------|---------|---------|
| DI 注册 `auth` 服务，通过 `$this->di->get('auth')` 获取用户 | **DI/Cookie 鉴权** | `$this->actingAs($id, $attributes)` |
| 认证入口从 `$request->getHeader('Auth-Id')` 读取 | **Header-based 鉴权** | `$this->post()` 第三参数传 `['Auth-Id' => '...']` |
| 无认证中间件或白名单路径 | **免鉴权** | 无需鉴权，直接请求 |

#### DI/Cookie 鉴权模式（Phalcon 默认）

```php
// 模拟已登录用户（绕过 JWT/ZQ 认证）
$this->actingAs(1, ['username' => 'test_user']);

// 模拟超级管理员
$this->actingAs(42, ['username' => 'admin', 'is_super' => true]);
```

#### Header-based 鉴权模式（Auth-Id）

```php
// 测试类定义 Auth-Id 常量
private const TEST_AUTH_ID = 'CHANGE_ME_TO_REAL_AUTH_ID';

// POST 请求携带 Auth-Id header
$response = $this->post('/admin/...', $data, [
    'Auth-Id' => self::TEST_AUTH_ID,
]);
```

### 访问 DI 服务

```php
// 获取配置
$config = $this->di->getShared('config');

// 获取 Redis
$redis = $this->di->getShared('redis');

// 注册自定义 Mock 服务
$this->di->setShared('someService', function () {
    return $this->createMock(SomeService::class);
});
```

### 数据库操作与断言

```php
use Phalcon\Db\Adapter\Pdo\Mysql;

// 获取 DB 连接
$db = $this->di->getShared('db');

// 插入测试数据（事务自动回滚）
$db->insert('member', [
    'name' => 'test_user',
    'create_time' => date('Y-m-d H:i:s'),
], ['name', 'create_time']);

// 断言数据库中存在记录
$this->assertDatabaseHas('member', ['name' => 'test_user']);

// 断言数据库中不存在记录
$this->assertDatabaseMissing('member', ['name' => 'deleted_user']);
```

### 响应格式断言

项目统一返回格式：`{status_code, msg, data, extra}`

```php
// 断言成功响应
$this->assertJsonApiSuccess($result);  // status_code = 1

// 断言失败响应
$this->assertJsonApiError($result, -1);

// 断言分页结构
$this->assertJsonApiPagination($result);
```

### 外部服务 Mock（集成测试中）

集成测试验证完整链路，但被测接口内部调用外部服务时 **MUST Mock**，保证测试不依赖外部环境且可重复执行：

| 外部依赖 | Mock 方式 | 说明 |
|----------|----------|------|
| HTTP 客户端（第三方 API / 微服务） | DI 注入 Mock | 替换 httpClient 服务 |
| 队列 / MQ 投递 | DI 注入 Mock | 替换 queue 服务 |
| 通知服务（钉钉/邮件/短信） | DI 注入 Mock | 替换 notifyService 等 |
| 外部缓存（非本地 Redis） | DI 注入 Mock | 如调用了跨服务的 Redis |

**写法示例**：

```php
// Mock 外部 HTTP 客户端
$httpClient = $this->createMock(\GuzzleHttp\ClientInterface::class);
$httpClient->method('request')
    ->willReturn(new \GuzzleHttp\Psr7\Response(200, [], json_encode([
        'code' => 0,
        'data' => ['result' => 'success'],
    ])));

$this->di->setShared('httpClient', function () use ($httpClient) {
    return $httpClient;
});

// Mock 队列投递（验证投递但不真实发送）
$queue = $this->createMock(QueueService::class);
$queue->expects($this->once())                                        // ← 验证被调用了 1 次
    ->method('push')
    ->with($this->callback(fn ($msg) => str_contains($msg, 'task.create')))  // ← 验证参数
    ->willReturn(true);
$this->di->setShared('queue', function () use ($queue) {
    return $queue;
});

// 测试结束时 PHPUnit 自动验证 expects() 约束是否满足
// 若 push() 未被调用或参数不匹配 → 测试 FAIL

// Mock 通知服务
$notify = $this->createMock(NotifyService::class);
$notify->expects($this->any())->method('send')->willReturn(true);
$this->di->setShared('notifyService', function () use ($notify) {
    return $notify;
});
```

**何时 Mock**：
- 被测接口源码中有外部 HTTP 调用、队列投递、通知发送 → Mock
- 纯 DB 操作 + 内部逻辑 → 不需要 Mock
- 涉及副作用验证的 TC（预期结果中要求验证通知/队列/外部调用），Mock MUST 添加调用次数和参数验证（`expects($this->once())` + `with($this->callback(...))`）。纯数据准备 P1 的临时 Mock 不需要验证调用次数

**与 P1 数据准备的关系**：当用 P1 调 create 接口准备数据时，如果 create 内部有外部调用，需要在 P1 调用前完成 Mock 注入。

---

## 测试方法命名规范

使用 `test` + 动词 + 场景描述：

```php
public function testGetMemberByIdReturnsModel(): void {}
public function testGetMemberByIdReturnsNullWhenNotFound(): void {}
public function testCreateMemberThrowsOnDuplicatePhone(): void {}
public function testListReturnsCorrectPagination(): void {}
```

---

## 运行命令

```bash
composer test                                          # 全部测试
composer test-unit                                     # 仅单元测试
composer test-integration                              # 仅集成测试

# 单个测试方法
vendor/bin/phpunit --filter testMethodName test/路径/SomeTest.php

# 覆盖率报告
composer test-coverage
```

---

## 变更影响回归测试

当版本迭代或优化需求修改了某个模块的代码时，**不仅要覆盖被修改模块本身的测试，还必须覆盖所有直接调用方的回归测试**。

### 影响分析流程

```
1. 识别变更范围 → 哪些类/方法被修改了
2. 查找直接调用方 → 谁在用这些类/方法（grep / IDE / CodeGraph callers）
3. 检查调用方测试 → 已有测试是否覆盖了调用路径
4. 补写/运行回归 → 缺失则补写，已有则确认通过
```

### 强制规则

| 场景 | 测试要求 |
|------|----------|
| 修改了方法签名（参数/返回值） | MUST 补写或更新所有调用方的测试 |
| 修改了方法内部逻辑（返回值语义变化） | MUST 运行所有调用方的现有测试，失败则修复 |
| 修改了异常/错误处理行为 | MUST 验证调用方的 catch 逻辑仍正确 |
| 纯内部重构（行为完全不变） | 运行现有调用方测试即可，无需新增 |
| 新增方法（无调用方） | 只需当前模块测试 |

### 回归测试最小覆盖

```php
/**
 * @covers \Apps\Services\MemberService::getList
 * @depends Apps\Services\OrderService  ← 标注依赖方，方便后续追踪
 *
 * 回归原因：MemberService::getList 返回结构变更，
 * 验证 OrderService 调用该方法后仍能正确处理
 */
public function testOrderServiceHandlesMemberListChange(): void
{
    // 模拟 MemberService 新的返回结构
    // 验证 OrderService 的处理逻辑仍正确
}
```

### 影响半径查找方法

```bash
# 方式 1：grep 查找调用方
grep -rn "MemberService" library/services/ apps/ --include="*.php" | grep -v "class MemberService"

# 方式 2：使用 CodeGraph（如已配置）
# codegraph_callers MemberService::getList

# 方式 3：运行全量测试观察是否有失败
composer test
```

---

## 红线

- ❌ 集成测试使用了错误基类：Cookie/DI 鉴权项目 MUST 用 `IntegrationTestCase`；Header-based 鉴权项目按项目约定选择基类。基类选错会导致事务回滚缺失或鉴权方式不匹配
- ❌ 单元测试初始化 DI 容器或连接真实数据库（应全部 Mock）
- ❌ 单元测试发起真实 HTTP 请求或连接真实 Redis/MQ（所有外部依赖必须用测试替身）
- ❌ 测试方法不以 `test` 开头或不声明 `: void` 返回类型
- ❌ 集成测试中硬编码已存在的数据 ID（数据库状态不稳定，应自行插入测试数据）
- ❌ 在 `test/Cases/` 中放集成测试或反之（目录决定 testsuite 归属）
- ❌ 测试中直接使用 `new \Phalcon\Di\FactoryDefault()`（应继承 IntegrationTestCase）
