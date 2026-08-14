---
name: hyperf-test
description: "编写 Hyperf 单元测试和集成测试。涉及 test 目录下的测试用例创建、Mock 依赖、数据库断言、HTTP 请求测试时使用。触发词：测试、单元测试、集成测试、TDD、TestCase、Mock、co-phpunit、assertJson、assertDatabaseHas。Use when working with files matching: **/test/**/*.php, **/phpunit.xml*."
---

# Hyperf 测试规范

> 适用于 Hyperf 3.1+ / PHPUnit 10+ / Swoole 协程环境。

## 测试分类与目录

| 类型 | 目录 | 基类 | 特征 |
|------|------|------|------|
| 单元测试 | `test/Cases/` | `Hyperf\Testing\TestCase` 或 `HyperfTest\HttpTestCase` | Mock 所有外部依赖，毫秒级执行 |
| 集成测试 | `test/Integration/` | `HyperfTest\IntegrationTestCase` | 真实数据库，完整 HTTP 链路，事务自动回滚 |

目录结构按被测类的命名空间映射：
```
test/Cases/Service/Auth/   →  测试 App\Service\Auth\*
test/Cases/Enum/           →  测试 App\Enum\*
test/Integration/Member/   →  测试会员模块完整链路
```

## TDD 流程（严格遵循）

### Step 1：确定测试类型

根据要测试的目标判断：

| 目标 | 选择 | 理由 |
|------|------|------|
| Enum/Constants/纯逻辑类 | 单元测试 | 无外部依赖 |
| Service 层业务分支 | 单元测试 | Mock Repository，验证逻辑 |
| Exception/Handler | 单元测试 | Mock Logger/Response |
| 完整接口流程（API → DB） | 集成测试 | 需要真实数据库验证端到端 |
| 数据库读写正确性 | 集成测试 | 需要真实 SQL 执行 |

### Step 2：创建测试文件

文件命名：`{被测类名}Test.php`

```php
<?php

declare(strict_types=1);

namespace HyperfTest\Cases\{子目录};  // 或 HyperfTest\Integration\{子目录}

use Hyperf\Testing\TestCase;  // 或对应基类

/**
 * @internal
 * @covers \App\{被测类完整命名空间}
 */
class {被测类名}Test extends TestCase
{
    // ...
}
```

### Step 3：编写失败测试

先写测试方法，断言期望行为，此时运行应**失败**（Red）。

### Step 4：编写实现代码

在 `app/` 中写最小实现使测试通过（Green）。

### Step 5：运行验证

```bash
# 容器内执行
docker exec {容器名} sh -c "cd {项目路径} && vendor/bin/co-phpunit --prepend test/bootstrap.php --filter {方法名} test/{文件路径}"
```

### Step 6：重构

测试通过后可安全重构，重新运行确保仍然 Green。

---

## 单元测试编写规范

### 基类选择

| 场景 | 基类 |
|------|------|
| 纯逻辑（无 HTTP、无容器） | `Hyperf\Testing\TestCase` |
| 需要发送 HTTP 请求（返回 `TestResponse`，Cookie/CSRF 鉴权） | `HyperfTest\IntegrationTestCase` |
| 需要发送 HTTP 请求（返回 `array`，Header-based 鉴权） | `HyperfTest\HttpTestCase` |
| 需要 Mock 容器服务 | `Hyperf\Testing\TestCase` + use `MockContainerTrait` |

### 认证鉴权策略 —— 编写测试前 MUST 检测

集成测试要穿过 `AuthMiddleware` 验证完整 HTTP 链路。不同项目的鉴权机制不同，**编写测试前 MUST 执行 Step 0 检测**，禁止未经检测就硬编码 `actingAs()` 或 `Auth-Id`。

#### Step 0: 探索检测（MUST）

1. 定位项目的 AuthMiddleware 实现（通常 `app/Middleware/Http/AuthMiddleware.php` 或 `config/autoload/middlewares.php` 中 `http` 节指向的类）
2. 阅读 `process()` 方法，确认认证流程
3. 按以下规则判定鉴权类型：

| 检测信号 | 鉴权类型 | 测试写法 |
|----------|---------|---------|
| `resolveUser()` 出现 `$request->getHeader('Auth-Id')` 且调用外部 API 验证 | **Header-based 鉴权** | `$this->post()` 第三参数传 `['Auth-Id' => '...']`，返回 `array` |
| `resolveUser()` 出现 `$request->getCookieParams()` / `authenticateByCookie()` | **Cookie/CSRF 鉴权** | 基类有 `actingAs()` → 用 `$this->actingAs()`；否则传 Cookie header |
| `authenticate()` 为空方法或直接 `return` | **免鉴权（开放接口）** | 无需鉴权，直接 `$this->post()` |

#### Header-based 鉴权模式（Auth-Id）

适用于：AuthMiddleware 从 `Auth-Id` 请求头获取用户，调掌权等外部 API 验证。

```php
// 测试类定义 Auth-Id 常量（需替换为掌权中真实用户）
private const TEST_AUTH_ID = 'CHANGE_ME_TO_REAL_AUTH_ID';

// POST 请求携带 Auth-Id header
$result = $this->post('/admin/aiToolTask/aiImageTaskList', [
    'group_id' => 0,
], [
    'Auth-Id' => self::TEST_AUTH_ID,
]);

$this->assertIsArray($result);
$this->assertArrayHasKey('list', $result);
```

**注意事项**：
- `Auth-Id` 必须对应掌权中真实存在且有对应路由权限的用户
- 接口内部调用 `Context::get(User::class)` + `Context::get(DataAuth::class)` → AuthMiddleware 鉴权成功后自动写入 Context
- 项目用 `HttpTestCase`（`__call` 委托 `Hyperf\Testing\Client`）→ 返回 `array`（已 JSON 解码）
- 项目用 `IntegrationTestCase`（`MakesHttpRequests` trait）→ 返回 `TestResponse`，用 `$response->json()` 取值

#### Cookie/CSRF 鉴权模式

适用于：AuthMiddleware 从 Cookie + CSRF Token 验证用户身份。

```php
// 基类有 actingAs() 方法
$this->actingAs(1);  // 默认用户
$this->actingAs(42, ['username' => 'admin', 'is_super' => true]);  // 超级管理员

$response = $this->post('/admin/member/get', ['id' => 1]);
$this->assertJsonApiSuccess($response);
```

**基类无 `actingAs()` 时**，手动传 Cookie + CSRF header：
```php
$result = $this->post('/admin/...', $data, [
    'Cookie' => 'zw-authorization=xxx; zw-csrf-token=yyy',
    'zw-csrf-token' => md5('yyy'),
]);
```

### 测试替身强制规则

单元测试中，以下依赖 **MUST 使用测试替身（Mock/Stub）**，禁止调用真实实现：

| 依赖类型 | 必须 Mock | 说明 |
|----------|-----------|------|
| Repository / DAO 层 | ✅ | 禁止触发真实 SQL |
| 外部 HTTP 调用（第三方 API、微服务） | ✅ | 禁止发出真实网络请求 |
| Redis 操作 | ✅ | 禁止连接真实 Redis |
| 队列/消息投递 | ✅ | 禁止触发真实 MQ |
| 文件系统 I/O | ✅ | 禁止读写真实文件 |
| 日志（关键断言时） | ✅ | Mock Logger 验证日志是否写入 |
| 纯计算/枚举/DTO | ❌ | 无副作用，直接使用真实类 |

**原则：单元测试只验证被测类自身的逻辑分支，一切跨边界的依赖都用替身隔离。**

### Mock 依赖模板

#### 基础：Mock 注入容器的服务（最常用）

```php
use Hyperf\Context\ApplicationContext;
use Mockery;

// Mock 并注入容器
$repository = Mockery::mock(MemberRepository::class);
$repository->shouldReceive('getMemberById')->with(1)->andReturn($member);

$container = ApplicationContext::getContainer();
$container->define(MemberRepository::class, fn () => $repository);

$service = $container->get(MemberService::class);
```

#### Mock 外部 HTTP 客户端

```php
$httpClient = Mockery::mock(GuzzleHttp\ClientInterface::class);
$httpClient->shouldReceive('request')
    ->with('POST', '/api/user/info', Mockery::any())
    ->andReturn(new Response(200, [], json_encode(['code' => 0, 'data' => ['name' => 'test']])));

$container->define(ClientInterface::class, fn () => $httpClient);
```

#### Mock Redis

```php
$redis = Mockery::mock(Hyperf\Redis\Redis::class);
$redis->shouldReceive('get')->with('user:1')->andReturn(json_encode(['id' => 1]));
$redis->shouldReceive('set')->andReturn(true);

$container->define(\Redis::class, fn () => $redis);
```

#### 验证方法调用次数与参数

```php
$service = Mockery::mock(NotifyService::class);
$service->shouldReceive('sendMessage')
    ->once()                          // 必须调用恰好 1 次
    ->with(Mockery::on(fn ($msg) => str_contains($msg, '审批')))  // 参数断言
    ->andReturn(true);
```

### tearDown 必须关闭 Mockery

```php
protected function tearDown(): void
{
    Mockery::close();
    parent::tearDown();
}
```

### HttpTestCase 断言方法

```php
$response = $this->post('/path', ['param' => 'value']);
$this->assertJsonSuccess($response);                    // status_code = 1
$this->assertJsonError($response, ErrorCode::STATUS_FAILURE);  // 指定错误码
$this->assertJsonPagination($response);                 // 分页结构
```

---

## 集成测试编写规范

### 基类：`HyperfTest\IntegrationTestCase`

已内置能力：
- `RunTestsInCoroutine` — 测试自动在协程中执行
- `MakesHttpRequests` — `$this->get/post/json/put/delete()` 返回 `TestResponse`
- `InteractsWithDatabase` — `$this->assertDatabaseHas/Missing()`
- `InteractsWithContainer` — `$this->mock()` / `$this->swap()`
- `DatabaseTransactionTrait` — 每个测试自动开启事务并回滚

### 事务回滚控制

```php
// 默认包裹 default 连接
protected array $connectionsToTransact = ['default'];

// 多连接
protected array $connectionsToTransact = ['default', 'starrocks'];

// 不需要数据库
protected array $connectionsToTransact = [];
```

### 发送请求并断言

```php
$response = $this->post('/admin/member/get', ['id' => 1]);

// 项目信封格式断言
$this->assertJsonApiSuccess($response);
$this->assertJsonApiError($response, ErrorCode::STATUS_FAILURE);
$this->assertJsonApiPagination($response);

// TestResponse 链式断言（仅 IntegrationTestCase / MakesHttpRequests 返回 TestResponse）
$response->assertOk();
$response->assertJsonPath('data.name', 'test');
$response->assertJsonStructure(['status_code', 'msg', 'data' => ['id', 'name']]);
$response->assertJsonFragment(['status_code' => 1]);
$response->assertJsonCount(3, 'data.data');

// 原始 array 断言（HttpTestCase / Client 返回 array）
$this->assertIsArray($result);
$this->assertArrayHasKey('status_code', $result);
$this->assertEquals(1, $result['status_code']);
```

### 数据库断言

```php
// 表名不含前缀（框架自动加）
$this->assertDatabaseHas('member', ['id' => 1, 'name' => 'test']);
$this->assertDatabaseMissing('member', ['name' => 'deleted_user']);
```

### 准备测试数据

```php
use Hyperf\DbConnection\Db;

// 直接插入（事务回滚会清理）
$id = Db::table('member')->insertGetId([
    'name' => 'test_user',
    'create_time' => time(),
    'update_time' => time(),
]);
```

### 外部服务 Mock（集成测试中）

集成测试验证完整 HTTP 链路，但被测接口内部调用外部服务时 **MUST Mock**，保证测试不依赖外部环境且可重复执行：

| 外部依赖 | Mock 方式 | 说明 |
|----------|----------|------|
| HTTP 客户端（第三方 API / 微服务） | 容器注入 Mock | 替换 `ClientInterface` 或具体 Client 类 |
| 队列 / MQ 投递 | 容器注入 Mock | 替换 Producer / Driver，验证投递参数 |
| 通知服务（钉钉/邮件/短信） | 容器注入 Mock | 替换 NotifyService 等 |
| 外部缓存（非本地 Redis） | 容器注入 Mock | 如调用了跨服务的 Redis |

**写法示例**：

```php
use Hyperf\Context\ApplicationContext;
use Mockery;

// Mock 外部 HTTP 客户端
$httpClient = Mockery::mock(\GuzzleHttp\ClientInterface::class);
$httpClient->shouldReceive('request')
    ->andReturn(new \GuzzleHttp\Psr7\Response(200, [], json_encode([
        'code' => 0,
        'data' => ['result' => 'success'],
    ])));

$container = ApplicationContext::getContainer();
$container->define(\GuzzleHttp\ClientInterface::class, fn () => $httpClient);
```

**何时 Mock**：
- 被测接口源码中有 `$this->httpClient->request()`、`$producer->produce()`、`$notifyService->send()` 等外部调用 → Mock
- 纯 DB 操作 + 内部逻辑 → 不需要 Mock
- 涉及副作用验证的 TC（预期结果中要求验证通知/队列/外部调用），Mock MUST 添加调用次数和参数验证（`->once()` + `->with()`）。纯数据准备 P1 的临时 Mock 不需要验证调用次数

**与 P1 数据准备的关系**：当用 P1 调 create 接口准备数据时，如果 create 内部有外部调用，需要在 P1 调用前完成 Mock 注入。

---

## 测试方法命名规范

使用 `test` + 动词 + 场景描述：

```php
public function testGetMemberByIdReturnsModel(): void {}
public function testGetMemberByIdReturnsNullWhenNotFound(): void {}
public function testCreateMemberThrowsOnDuplicateOpenId(): void {}
public function testListReturnsCorrectPagination(): void {}
```

---

## 运行命令

```bash
composer test                # 全部测试
composer test-unit           # 仅单元测试（test/Cases/）
composer test-integration    # 仅集成测试（test/Integration/）

# 单个测试方法
vendor/bin/co-phpunit --prepend test/bootstrap.php --filter testMethodName test/路径/SomeTest.php
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
 * @covers \App\Service\MemberService::getList
 * @depends App\Service\OrderService  ← 标注依赖方，方便后续追踪
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
grep -rn "MemberService" app/ --include="*.php" | grep -v "class MemberService"

# 方式 2：使用 CodeGraph（如已配置）
# codegraph_callers MemberService::getList

# 方式 3：运行全量测试观察是否有失败
composer test
```

---

## 红线

- ❌ 集成测试使用了错误基类：Cookie 鉴权项目 MUST 用 `IntegrationTestCase`；Header-based 鉴权项目用 `HttpTestCase`。基类选错会导致事务回滚缺失或鉴权方式不匹配
- ❌ 单元测试连接真实数据库（应全部 Mock）
- ❌ 单元测试发起真实 HTTP 请求或连接真实 Redis/MQ（所有外部依赖必须用测试替身）
- ❌ 忘记 `Mockery::close()`（导致残留状态影响后续测试）
- ❌ 测试方法不以 `test` 开头或不声明 `: void` 返回类型
- ❌ 集成测试中硬编码已存在的数据 ID（数据库状态不稳定，应自行插入测试数据）
- ❌ 在 `test/Cases/` 中放集成测试或反之（目录决定 testsuite 归属）
