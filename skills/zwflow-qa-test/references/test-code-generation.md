# 测试代码生成规则

> 本文档定义 Phase 1（解析用例文档）和 Phase 2（生成测试代码）的完整规则。
> 执行本文件前必须已经加载 `references/frameworks/<framework>.md`。

---

## § 解析规则

### 定位文档

- 有 `change_name` 且为 change 名称 → 确认 `openspec/changes/<name>/qa-doc.md` 存在
- 有 `change_name` 且为文件路径 → 确认文件存在后直接使用
- 无 `change_name` → 执行 `find openspec/changes/ -name "qa-doc.md" -type f | sort`，列出供用户选择
- 文件不存在 → 停止，提示用户先通过 `zwflow-qa-doc-gen` Skill 生成用例文档

### 公共约定节解析

**识别**：qa-doc.md 顶部的 `## 公共请求约定` 和 `## 公共失败响应契约` 节。

**提取内容**：

| 节 | 提取字段 | 用途 |
|----|---------|------|
| 公共请求约定 | Method（默认 POST）、Headers（Content-Type/Cookie/csrf 等）、鉴权前置描述、**鉴权类型**、Base URL | 每个 TC 的 WHEN 段省略 URL/Method 时自动补全 |
| 公共失败响应契约 | 错误响应风格（`HTTP 200 + status_code != 1` 或 `HTTP 4xx`） | 所有错误类 THEN 断言的统一格式 |

**鉴权类型提取**：从公共请求约定中识别鉴权方式，用于决定测试代码中的 auth 写法。

| 公共约定中的描述 | 鉴权类型 | 代码生成 |
|----------------|---------|---------|
| 框架引用定义的会话鉴权描述 | 框架会话鉴权 | 使用框架引用定义的测试用户注入方式 |
| "Auth-Id 请求头" / "内部调用 Auth-Id" | `Auth-Id` | `$this->post()` 第三参数传 `['Auth-Id' => '...']` |
| "免鉴权" / "无公共请求头" | `None` | 无需鉴权，直接请求 |
| 未声明 → 默认 | 框架会话鉴权 | 使用框架引用定义的默认方式（兼容旧文档） |

**代码生成影响**：
- **框架会话鉴权** → 使用框架引用定义的测试用户注入方式
- **Auth-Id 鉴权** → 所有 `$this->post()` 必须带 `['Auth-Id' => self::TEST_AUTH_ID]` 第三参数
- **免鉴权（`/api/*` 等）** → 无需鉴权代码
- 错误断言统一为契约声明的格式（不再逐 TC 推断是 HTTP 200 还是 400）

### TC-000 假设消费

**识别**：每个模块的 `### TC-000: 设计假设说明` 节。

**提取内容**：从 TC-000 的 `**说明**:` 列表中提取关键声明：

| 声明模式 | 影响 |
|---------|------|
| "内部接口" / "鉴权由全局中间件处理" | 该模块不生成鉴权/越权/CSRF 类 TC 的测试方法 |
| "公开 API" / "对外接口" | 该模块生成完整鉴权测试 |
| "接口路径含鉴权白名单" | 按声明处理（优先级高于硬编码白名单） |

**与硬编码白名单的关系**：TC-000 声明 > SKILL.md 硬编码白名单。无 TC-000 声明时，回退到默认行为（内部接口跳过鉴权）。

### 解析文档结构

**仅支持格式 A — GIVEN/WHEN/THEN 风格**（qa-doc-gen 的标准产出格式）。

表格格式（格式 B）不再支持。如遇到非标准格式文档，提示用户先用 `zwflow-qa-doc-gen` Skill 重新生成标准格式。

解析目标格式：

```markdown
## 模块：会员管理

### TC-001: 新建会员 - 正常流程
- **前置条件(GIVEN)**: 管理员已登录，企业已开通会员功能
- **操作(WHEN)**: POST /admin/member/create，body={name:"张三", phone:"13800138000"}
- **预期结果(THEN)**:
  - 返回 status_code=1
  - member 表新增记录，name/phone 匹配
```

**解析产出**（内部数据结构）：
- 模块列表（每个模块含多个 TC）
- 每个 TC：编号、用例名、前置条件(GIVEN)、操作(WHEN)、预期结果(THEN)
- 每个 TC 额外标记 `tc_type`：
  - `simple` — 标准单次请求（默认）
  - `data_driven` — WHEN 段含数据驱动变体表
  - `multi_step` — WHEN 段含 Step 1/2/3... 多步骤

### 数据驱动变体表解析

**识别信号**：WHEN 段包含"数据驱动"关键词 + markdown 表格。

**源格式**（qa-doc-gen 产出，见 writing-rules 规则 4）：

```markdown
### TC-103: 字段类型错配（多字段数据驱动）

- **操作(WHEN)**:
  - 对下列每组 Body 各发送一次（数据驱动）：
    | page | page_size | zm_id |
    |------|-----------|-------|
    | "one" | 20 | "xxx" |
    | 1 | "twenty" | "xxx" |
    | 1 | 20 | 123456 |
- **预期结果(THEN)**:
  - 每组请求均 HTTP 200 + status_code != 1
```

**解析规则**：

1. 检测 WHEN 段中的 `数据驱动` 关键词 → 标记 `tc_type = data_driven`
2. 提取表格表头列名作为参数名（`page`、`page_size`、`zm_id`）
3. 每一数据行 = 一组参数变体（共 3 组）
4. THEN 段对所有变体统一适用（一致性断言）
5. 如 THEN 中也含表格（每行对应不同预期），则是**决策表**而非数据驱动 → 见下方「决策表矩阵解析」

**代码生成映射**：

```php
// 输入：3 行变体
// → 生成 PHPUnit @dataProvider

/**
 * @qa-case TC-103
 * @title 字段类型错配（多字段数据驱动）
 * @dataProvider provideTc103FieldTypeData
 */
public function testTc103FieldTypeMismatch(array $body, array $expected): void
{
    // 根据公共约定中的鉴权类型选择鉴权方式
    $response = $this->post('/admin/member/list', $body);
    $this->assertJsonApiFail($response);
    // ... 按 $expected 断言
}

public function provideTc103FieldTypeData(): array
{
    return [
        'page 送字符串' => [
            'body' => ['page' => 'one', 'page_size' => 20, 'zm_id' => 'xxx'],
            'expected' => ['status_code' => 0],
        ],
        'page_size 送字符串' => [
            'body' => ['page' => 1, 'page_size' => 'twenty', 'zm_id' => 'xxx'],
            'expected' => ['status_code' => 0],
        ],
        'zm_id 送整数' => [
            'body' => ['page' => 1, 'page_size' => 20, 'zm_id' => 123456],
            'expected' => ['status_code' => 0],
        ],
    ];
}
```

**决策表矩阵解析**（WHEN 表格每行有不同的预期结果）：

**识别信号**：表格最后一列为"预期"或"结果"。

```markdown
- **操作(WHEN)**:
  - 对下列每组 Body 各发送一次（决策表）：
    | is_custom | message | 预期 |
    |-----------|---------|------|
    | 1 | "hello" | ✅ 成功 |
    | 1 | "" | ❌ message 必填 |
    | 0 | "hello" | ❌ message 须为空 |
    | 0 | "" | ✅ 成功 |
```

**解析规则**：
1. 表格含"预期"列 → 标记为决策表类型
2. 每行除数据字段外，额外提取预期结果列（✅/❌标记）
3. ❌ 行 → 预期 `status_code != 1`；✅ 行 → 预期 `status_code = 1`
4. 同样生成 @dataProvider，每行包含 body + expected_success

### TC-5xx Step 多步骤解析

**识别信号**：WHEN 段含 `Step N:` 序号列表 + `$变量名` 占位符。

**源格式**（qa-doc-gen 产出，见 output-template 集成场景章节）：

```markdown
### TC-501: 任务全流程 - 正向主链路(prd)

- **操作(WHEN)**:
  - Step 1: POST /task/create {"name":"集成测试任务"} → $task_id
  - Step 2: POST /task/update-status {"task_id":"$task_id","status":"processing"}
  - Step 3: POST /task/update-status {"task_id":"$task_id","status":"completed"}
  - Step 4: GET /task/list → 验证列表含 $task_id
- **预期结果(THEN)**:
  - Step 1: status_code=1, 返回 task_id, status=draft
  - Step 2: status_code=1, 状态变为 processing
  - Step 3: status_code=1, 状态变为 completed
  - Step 4: list 中含 task_id=$task_id, status=completed
```

**解析规则**：

1. 检测 WHEN 段中的 `Step N:` 序号列表 → 标记 `tc_type = multi_step`
2. 逐个提取每个 Step：
   - `Step N: METHOD /path {body}` → 接口调用
   - `→ $变量名`（可选）→ 变量赋值（从该 Step 响应中提取）
   - `→ 验证...`（可选）→ 该 Step 的附加断言描述
3. 建立变量引用图：`$task_id` 首次出现在 Step 1 的 `→` 右侧，后续 Step 引用时替换
4. 变量命名规则（见 output-template）：
   - 简单链路（2 步 + 变量唯一）→ `$<字段名>`，如 `$task_id`
   - 多步链路（≥3 步或同名字段多次出现）→ `$<step序号>_<字段名>`，如 `$1_task_id`、`$3_record_id`
5. THEN 段按 `Step N:` 序号匹配对应断言

**变量解析优先级**：

| Step 中出现的变量 | 解析为 | 取值来源 |
|------------------|--------|---------|
| `$task_id` | 简单变量 | Step 1 响应 `data.id` |
| `$1_task_id` | 带序号变量 | Step 1 响应 `data.id` |
| `$name` | 简单变量（非 id 字段） | 对应 Step 响应 `data.name` |

**代码生成映射**：

```php
/**
 * @qa-case TC-501
 * @title 任务全流程 - 正向主链路(prd)
 */
public function testTc501TaskFullFlow(): void
{
    // 根据公共约定中的鉴权类型选择鉴权方式
    // 框架会话鉴权 → 使用框架引用定义的测试用户注入方式
    // Auth-Id 鉴权 → 每次请求传 ['Auth-Id' => self::TEST_AUTH_ID]
    // None 免鉴权 → 无需鉴权

    // Step 1: POST /task/create → $task_id
    $res1 = $this->post('/task/create', ['name' => '集成测试任务']);
    $this->assertJsonApiSuccess($res1);
    $taskId = $res1->json('data.id');
    $this->assertEquals('draft', $res1->json('data.status'));

    // Step 2: POST /task/update-status {"task_id":"$task_id","status":"processing"}
    $res2 = $this->post('/task/update-status', [
        'task_id' => $taskId,
        'status' => 'processing',
    ]);
    $this->assertJsonApiSuccess($res2);
    $this->assertEquals('processing', $res2->json('data.status'));

    // Step 3: POST /task/update-status {"task_id":"$task_id","status":"completed"}
    $res3 = $this->post('/task/update-status', [
        'task_id' => $taskId,
        'status' => 'completed',
    ]);
    $this->assertJsonApiSuccess($res3);
    $this->assertEquals('completed', $res3->json('data.status'));

    // Step 4: GET /task/list → 验证列表含 $task_id
    $res4 = $this->get('/task/list');
    $this->assertJsonApiSuccess($res4);
    $taskIds = array_column($res4->json('data.list'), 'id');
    $this->assertContains($taskId, $taskIds);
}
```

**Step 变量提取策略**：

| 变量名模式 | 提取方式 | 说明 |
|-----------|---------|------|
| `$xxx_id` | `json('data.id')` | 常见 ID 字段 |
| `$xxx_token` | `json('data.token')` | Token 类字段 |
| `$N_xxx_id` | Step N 的 `json('data.id')` | 带序号的变量 |
| `$name`（通用字段） | `json('data.name')` | 按字段名提取 |
| 无法确定提取路径 | 暂停询问用户 | 如响应嵌套层级不明确 |

### 输出解析摘要

向用户展示：

```
## QA 用例解析结果

**文档**: openspec/changes/member-mgmt/qa-doc.md
**模块数**: 3
**用例总数**: 15

### 模块明细
1. 会员管理（6 个用例）
   - TC-001: 新建会员 - 正常流程
   - TC-002: 新建会员 - 手机号重复
   - ...
2. 订单导出（5 个用例）
   - ...
3. 积分管理（4 个用例）
   - ...

确认开始生成测试代码？
```

获得用户明确确认。用户可在此排除某些模块或调整。

---

## § 代码生成

### 加载测试规范

MUST invoke 框架引用指定的测试规范 skill，确保测试编码规范在上下文中。

### 目录结构

```
test/QA/Integration/{ChangeName}/{ModuleName}/XxxTest.php
```

- `{ChangeName}`：从 change 目录名提取，kebab-case 转 PascalCase（连字符去掉、每段首字母大写。如 `member-mgmt` → `MemberMgmt`；`v7-gift-pack` → `V7GiftPack`）
- `{ModuleName}`：从 `## 模块：xxx` 提取，转 PascalCase（如 `会员管理` → `MemberManagement`）
- 命名空间：使用框架引用中的 QA 命名空间前缀并追加 `{ChangeName}\{ModuleName}`

### 测试文件生成规则

每个模块生成一个测试文件：`{ModuleName}Test.php`

```php
<?php

declare(strict_types=1);

namespace {QA_NAMESPACE}\{ChangeName}\{ModuleName};

use {TEST_BASE_CLASS};

/**
 * QA 测试用例 — {模块中文名}
 * @source {用例文档路径}
 */
class {ModuleName}Test extends IntegrationTestCase
{
    // Header-based 鉴权项目：Phase 2 已向用户获取 Auth-Id，直接使用
    private const TEST_AUTH_ID = '{用户提供的掌权UID}';

    /**
     * @qa-case TC-001
     * @title 新建会员 - 正常流程
     */
    public function testTc001CreateMemberSuccess(): void
    {
        // GIVEN: 前置条件
        // ... 准备测试数据

        // WHEN: 操作
        // (Auth-Id header 已在 $this->post() 第三参数中携带)
        $response = $this->post('/admin/member/create', [...], [
            'Auth-Id' => self::TEST_AUTH_ID,
        ]);

        // THEN: 断言
        $this->assertJsonApiSuccess($response);
        $this->assertDatabaseHas('member', [...]);

        // THEN: 副作用验证（如有）
    }
}
```

**生成约束**：
- 基类：使用框架引用指定的测试基类（含 DB 事务回滚、HTTP 请求和真实认证链路集成）
- 每个 TC 生成一个测试方法，方法名：`testTcNNN_{用例名PascalCase}`
- PHPDoc MUST 标注 `@qa-case TC-NNN` 和 `@title 用例名`
- 测试方法内按 GIVEN/WHEN/THEN 结构组织代码，用注释分隔
- 前置条件涉及已登录 → 根据公共约定与框架引用选择会话鉴权或 `Auth-Id` header
- 前置条件涉及数据库记录 → 使用 DataFactory 模式（见 § DataFactory 模式）
- 预期结果涉及响应格式 → 使用项目断言方法（`assertJsonApiSuccess` 等）
- 预期结果涉及数据库状态 → 使用 `assertDatabaseHas` / `assertDatabaseMissing`
- 预期结果涉及副作用（队列投递、通知发送、外部 HTTP 调用）→ 在「副作用验证」注释块中通过 Mock 断言验证调用契约（次数 + 参数）。**生成测试时 MUST 探索被测接口源码检测外部调用，如有则自动填充 Mock 验证断言**

**测试实现保真约束**：
- 禁止静默修改测试基类/框架默认行为（`connectionsToTransact` / 中间件白名单 / `setUp` 框架钩子等）；确需修改 MUST 暂停提示用户确认并记录原因到报告
- 测试实现须与用例 WHEN/THEN 一致；若因环境/数据限制需构造性变通（如历史日期强制空结果）MUST 在测试方法注释标注「实现偏离：原因」并经用户确认
- 区分合法测试设计（如互斥条件必然返回空、边界值取离点）与非法规避（如用无关日期过滤绕过系统实际行为使测试恒通过）
- Phase 2 加载既有测试文件时 MUST 执行「保真审计」：逐 TC 校验实现与 qa-doc.md 操作步骤是否一致，发现偏离即暂停标注

**模糊处理**：
- 用例描述模糊（无法确定接口路径、参数格式、响应结构）→ 先探索 codebase（查找对应 Controller/路由），仍不明确则暂停询问用户
- 用例涉及的接口不存在 → 暂停，提示用户确认（可能是尚未开发的功能）

### 外部服务处理

被测接口内部调用外部服务（HTTP 客户端、第三方 API、微服务、队列、通知）时，MUST 在测试 setup 中 Mock 注入容器，保证测试不依赖外部环境。具体写法参考框架引用指定的测试规范 skill 中的外部服务 Mock 规则。

### 生成完成确认

所有测试文件生成后，输出文件清单：

```
## 测试代码已生成

| 文件 | 测试方法数 |
|------|-----------|
| test/QA/Integration/MemberMgmt/MemberManagement/MemberManagementTest.php | 6 |
| test/QA/Integration/MemberMgmt/OrderExport/OrderExportTest.php | 5 |
| ... | ... |

**总计**: N 个文件，M 个测试方法
```

---

## § DataFactory 模式

> DataFactory 封装 P1-P4 数据准备策略，将 AI 生成代码时的复杂决策树下沉为 DataFactory 内部的运行时决策。

### 核心原理

AI 在 Phase 2 开始时的探索流程（增量复用）：

```
Step 0: 读取已有 DataFactory 注册表（避免重复探索）
  ├── 检查 test/QA/Traits/DataFactory.php 是否存在
  │   ├── 不存在 → 首次使用，进入完整探索（Step 1-3）
  │   └── 存在 → 提取已有的 EntityRegistry / SideEffectMap / SchemaRegistry
  ├── 与当前 yapi.md 接口集做 diff：
  │   ├── 已在注册表中的实体 → 跳过探索，直接复用
  │   ├── 不在注册表中的新实体 → 进入 Step 1 探索
  │   └── 注册表有但 yapi.md 无的实体 → 保留不删（标记为"历史注册"）
  └── 如果新实体数为 0 → 跳过 Step 1 探索，直接进入 Step 2 生成代码

Step 1: 仅探索新实体（未在注册表中的）
  ├── 读 yapi.md 中对应接口 → 填充 EntityRegistry
  ├── 探索 create 接口源码 → 填充 SideEffectMap
  └── 读 Model/Migration → 填充 SchemaRegistry

Step 2: 合并注册表 → 生成/更新 DataFactory trait 代码
  ├── 已有条目保持不动
  └── 新增条目追加到对应注册表数组末尾

Step 3: AI 生成各模块测试代码（调用 DataFactory 方法）
```

**SchemaRegistry 过期检测**（Step 0 中执行）：

对 EntityRegistry 中已有的实体，快速校验 SchemaRegistry 是否过期：

```
已有实体 → 对比当前 Model/Migration 字段列表
├── Model 有但 SchemaRegistry 无 → 追加入口（新字段）
├── SchemaRegistry 有但 Model 无 → 标记 // STALE: 字段可能已废弃
└── 一致 → 直接复用
```

- 检测到新字段 → 自动追加，不阻塞
- 检测到 STALE 字段 → 回报中提示"DataFactory 有 L 个字段可能过期，建议确认"
- STALE 不影响流程，P3 INSERT 时会因字段不存在而报错 → 归入 Phase 3 正常失败分类

**判断 "已在注册表中" 的标准**：EntityRegistry 中存在相同实体名（`bgm_task` / `label` 等），且 `has_create_api` + `path` 与 yapi.md 一致。仅实体名匹配但路径不同 → 视为新实体（接口路径已变更）。

**公共文件位置**：`test/QA/Traits/DataFactory.php`，所有 change 共享，持续追加。

### 三个注册表

#### EntityRegistry — 实体→API 映射

从 yapi.md 解析获得，记录每个实体是否有 create API：

```php
// EntityRegistry 示例
[
    'bgm_task' => [
        'has_create_api' => true,
        'method' => 'POST',
        'path' => '/admin/bgmTask/create',
        'required_params' => ['name', 'template_id'],
    ],
    'label' => [
        'has_create_api' => false,  // 无 create API → P3 直接 INSERT
    ],
]
```

#### SideEffectMap — create API 副作用

探索 create 接口源码（Controller → Service），记录外部调用：

```php
// SideEffectMap 示例
[
    'POST /admin/bgmTask/create' => [
        'side_effects' => [
            ['type' => 'queue', 'class' => '{FRAMEWORK_QUEUE_PRODUCER}', 'event' => 'task.create'],
        ],
    ],
]
```

#### SchemaRegistry — 表结构

读取 Model 文件 / Migration，记录字段信息：

```php
// SchemaRegistry 示例
[
    'bgm_task' => [
        'table' => 'bgm_task',
        'columns' => [
            'id' => ['type' => 'int', 'auto_increment' => true],
            'name' => ['type' => 'varchar', 'not_null' => true],
            'template_id' => ['type' => 'int', 'not_null' => true],
            'status' => ['type' => 'tinyint', 'not_null' => true, 'default' => 1],
            'create_time' => ['type' => 'int', 'not_null' => true],
        ],
    ],
]
```

### DataFactory 决策树

```
DataFactory::create(entity, data, overrides?)
│
├── Step 1: 查 EntityRegistry ── 该实体是否有 create API？
│   ├── 无 → P3 直接 INSERT（查 SchemaRegistry 取表结构）
│   └── 有 → 进入 Step 2
│
├── Step 2: 副作用重叠检查 ── create API 的副作用 ∩ 当前 TC 验证目标？
│   ├── 重叠 → P3 降级 INSERT
│   └── 无重叠 → 进入 Step 3
│
├── Step 3: 是否需要特殊状态？
│   ├── overrides 非空（如 status=3, create_time=30天前）
│   │   └── P2: API 创建 → DB update 覆盖字段 → 返回 ID
│   └── overrides 为空 → P1 纯 API 创建
│
└── Step 4 (P1/P2 内部): 快照/恢复
    ├── 查 SideEffectMap → 保存原始外部服务引用
    ├── try { 注入临时 Mock → 调 API → 断言成功 → 取 ID }
    └── finally { 恢复原始服务引用 }
```

### AI 生成测试代码时的调用方式

```php
// 简单创建（P1 自动决策）
$taskId = $this->dataFactory->create('bgm_task', [
    'name' => '测试任务',
    'template_id' => 1,
]);

// 创建 + 状态覆盖（触发 P2）
$taskId = $this->dataFactory->create('bgm_task', [
    'name' => '测试任务',
    'template_id' => 1,
], ['status' => 3]);  // overrides → P2: API创建后UPDATE status

// 直接 INSERT（无 create API 的实体，P3）
$labelId = $this->dataFactory->insert('label', [
    'name' => '测试标签',
    'create_time' => time(),
]);
```

### 数据准备约束（保留）

- **被测接口自身不可用于准备自身数据**：测 create 接口的 TC-001 时，其前置依赖用 DataFactory.insert()（P3）准备
- **参数来源优先级**：yapi.md body_schema → Controller validate → 最小参数试探 → 询问用户
- **NOT NULL 字段兜底**：P3 INSERT 时所有 NOT NULL 且无 DEFAULT 的字段 MUST 提供值
- **P4 占位**：无法自造的外部数据，使用 `PLACEHOLDER_NEED_REAL_DATA` 占位 + TODO 注释，归入 Phase 4 数据补充轨道
- **副作用重叠判断**：P1 create API 的副作用覆盖当前 TC 验证目标 → 降级 P3（原则：宁可牺牲一条 API 链路，也不产生假阳性）

### DataFactory trait 生成位置

DataFactory 作为测试 trait 随首次 QA 测试生成时写入：

```
test/QA/Traits/DataFactory.php
```

后续 change 的 QA 测试复用同一个 DataFactory。如新 change 引入新实体，AI 在 Phase 2 扩展 DataFactory 的 EntityRegistry/SideEffectMap/SchemaRegistry。
