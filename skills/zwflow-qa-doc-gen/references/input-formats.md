# 输入格式与解析规则

本文档定义三源输入的解析规则。所有后续维度设计与模板输出都基于这些结构。

## 三源输入总览

| 来源 | 文件 | 必要性 | 驱动维度 |
|------|------|--------|---------|
| 接口契约 | `yapi.md` | **必读** | 维度 1-2-3-5（参数/边界/响应） |
| 场景定义 | `specs/*.md` | 主动读取（不存在则功能降级） | 维度 4（业务规则）+ 维度 6（集成场景） |
| 产品需求 | `prd.md` | 可选 | 维度 6（集成场景）增强 |
| 技术设计 | `design.md` | 可选 | 维度 4（状态机）增强 |

---

## 1. yapi.md — 接口契约（必读）

### 统一中间结构

```javascript
{
  method: "POST",
  path: "/game/session/current",
  summary: "查询当前游戏会话列表",
  description: "...",
  headers: [
    { name: "Content-Type", value: "application/json", required: true },
    { name: "zw-csrf-token", required: true, description: "Cookie 中 csrf-token 的 MD5" }
  ],
  query: [],
  path_params: [],
  body_schema: {
    type: "object",
    required: ["zm_id"],
    properties: {
      page:      { type: "integer", default: 1,  description: "页码" },
      page_size: { type: "integer", default: 20, description: "每页条数" },
      zm_id:     { type: "string",  description: "..." }
    }
  },
  auth: {
    type: "cookie+csrf",
    location: "Cookie: zw-authorization + Header: zw-csrf-token",
    description: "..."
  },
  responses: [
    { status: 200, schema: {...}, description: "成功" }
  ]
}
```

字段约定：
- `method`：大写 HTTP 方法（GET/POST/PUT/DELETE/PATCH）
- `path`：去掉 scheme + host 的纯路径，路径参数保留 `{id}` 形式
- `headers` / `query` / `path_params`：数组，元素含 `name / type / required / description / default`
- `body_schema`：JSON Schema 风格（type、required、properties）
- `auth.type`：枚举 `none | bearer | cookie | cookie+csrf | basic | apikey | oauth2`
- 缺失字段一律置为 `null` 或空数组，**不要**编造默认值；进入 TC-000 设计假设节

### Markdown 解析规则

| 源元素 | → 统一结构字段 | 说明 |
|---|---|---|
| 标题中的 `METHOD /path` | `method` / `path` | 大写方法 |
| 标题文字（无方法时） | `summary` | |
| 紧邻描述段 | `description` | 截至下一个 `#` 前 |
| `请求参数` 表 | `body_schema` 或 `query[]` | POST/PUT/PATCH 默认进 body；GET/DELETE 默认进 query |
| `请求头` / `Headers` 表 | `headers[]` | |
| `路径参数` 表 | `path_params[]` | |
| `响应示例` 代码块 | `responses[0].schema` | JSON.parse 推断 schema，status 默认 200 |
| `必填` 列值为"是"/"Y"/"true" | `required: true` | 其余视为 false |

### 脱敏规则

- 表格中"示例"列匹配手机号/邮箱/身份证 → 对应占位符
- 代码块中匹配 Bearer token / csrf hash → 对应占位符
- 内部 URL / 域名保留,业务数据脱敏

---

## 2. specs/*.md — 场景定义（主动读取）

### 读取路径

`openspec/changes/<change_name>/specs/` 下所有 `.md` 文件，递归扫描。

### 支持的格式

自动识别两种 spec 模板：

**格式 A（英文模板）**：
```markdown
### Requirement: 任务数量上限
用户最多同时持有 3 个进行中的任务。

#### Scenario: 超出任务上限时创建失败
- **WHEN** 用户已有 3 个 status=processing 的任务，尝试创建新任务
- **THEN** 返回错误，提示任务数已达上限
```

**格式 B（中文模板）**：
```markdown
### 需求（Requirement）：任务数量上限
用户最多同时持有 3 个进行中的任务。

#### 场景（Scenario）：超出任务上限时创建失败
- **前提（GIVEN）** 用户已有 3 个进行中的任务
- **当（WHEN）** 尝试创建新任务
- **那么（THEN）** 返回错误，提示任务数已达上限
```

### 提取的统一结构

```javascript
[
  {
    requirement: "任务数量上限",
    requirement_text: "用户最多同时持有 3 个进行中的任务。",
    scenario: "超出任务上限时创建失败",
    given: "用户已有 3 个进行中的任务",  // 可能为 null（格式 A 无 GIVEN）
    when: "尝试创建新任务",
    then: "返回错误，提示任务数已达上限",
    source_file: "specs/task-management/spec.md",
    section: "ADDED"  // ADDED | MODIFIED | REMOVED
  }
]
```

### 解析规则

- 识别 `### Requirement:` 或 `### 需求（Requirement）：` 作为需求块起始
- 识别 `#### Scenario:` 或 `#### 场景（Scenario）：` 作为场景块
- 一个 Requirement 下可含多个 Scenario
- 提取 `**WHEN**` / `**当（WHEN）**` 后的文本（到行尾）
- 提取 `**THEN**` / `**那么（THEN）**` 后的文本（到行尾）
- 提取 `**GIVEN**` / `**前提（GIVEN）**` 后的文本（可选，格式 A 可能没有）
- `## ADDED Requirements` / `## MODIFIED Requirements` / `## REMOVED Requirements` 下的 section 标记
- 各 section 的处理策略见下方「Scenario 变更类型的回归处理」

### Scenario 变更类型的回归处理

| Section | 生成策略 | 标记 |
|---|---|---|
| **ADDED** | 正常生成 TC-3xx / TC-5xx | 无特殊标记 |
| **MODIFIED** | 正常生成 TC-3xx / TC-5xx，标题末尾加 `(回归)` | `### TC-3xx: xxx - 业务规则(spec)(回归)` |
| **REMOVED** | **不生成**新 TC | 无 |

**增量更新时的 REMOVED 处理**：

当 qa-doc.md 已存在且选择"增量合并"时，REMOVED scenario 对应的已有 TC 需要提示删除：
1. 从 REMOVED scenario 的 `scenario` 名称匹配已有 qa-doc.md 中 TC 标题
2. 在回报中列出"建议删除的 TC"清单（含编号和标题）
3. 不自动删除 — 由用户确认后手动或再次执行处理

**MODIFIED 回归标记的用途**：
- 提示测试执行人重点回归验证
- 增量更新时优先重新生成这些 TC（断言可能已变更）
- 标记仅出现在标题，不影响 GIVEN/WHEN/THEN 正文

---

### Scenario → 接口映射规则

将提取的 scenario 映射到 yapi.md 中的具体接口：

| 映射信号 | 示例 | 匹配方式 |
|---------|------|---------|
| WHEN 中含路径 | "POST /task/create" | 精确匹配 |
| WHEN 中含动词 + 资源 | "创建任务" / "删除用户" | 动词 → method，资源 → path 中的名词 |
| Requirement 名称含资源 | "任务数量上限" | 关联所有 /task/ 路径的接口 |
| WHEN 涉及多个动作 | "创建任务后查询状态" | 映射到多个接口 → 归入 TC-5xx |

### 映射优先级与冲突解决

**优先级**（从高到低）：

| 优先级 | 信号类型 | 置信度 | 示例 |
|---|---|---|---|
| 1 | WHEN 中含精确路径 | 高 | "POST /task/create" |
| 2 | WHEN 中含动词+资源名 | 中 | "创建任务" → POST /task/create |
| 3 | Requirement 名称含资源 | 低 | "任务数量上限" → /task/* |
| 4 | WHEN 涉及多个动作 | 高（多接口） | "创建后查询" → TC-5xx |

**冲突解决规则**：

| 冲突场景 | 处理 |
|---|---|
| 一个 scenario 命中 ≥2 个不同接口 | 判断 WHEN 语义：若为顺序动作（"A 后 B"）→ TC-5xx；若为单动作但多接口同名 → 取 method+path 最匹配的 |
| 一个 scenario 命中同一资源的多个操作（如 create + update） | 取 WHEN 动词最直接匹配的单个接口 → TC-3xx |
| 仅靠优先级 3（Requirement 名称）匹配 | TC 标题加 `(推断)` 标记：`### TC-3xx: xxx - 业务规则(推断)` |
| 完全无法映射 | 归入 TC-000 假设节（见下方） |

**低置信度映射提示**：当映射仅靠 Requirement 名称匹配时，在 TC 标题标 `(推断)`，提示执行人需确认该 TC 是否归属正确接口。

---

**映射失败处理**：无法关联到任何接口的 scenario → 标注在 TC-000 假设节，提示"以下 spec scenario 未找到对应接口，可能需要补充 yapi.md"。

### 不存在时的降级

specs/ 目录不存在或为空时：
- 不报错，继续执行
- 维度 4（TC-3xx）退回通用推断模式（从字段名推断业务规则）
- 维度 6（TC-5xx）跳过不生成
- 在回报中提示：

```
⚠️ specs/ 未找到，本次仅生成接口契约测试（维度 1-2-3-5）。
业务规则(TC-3xx)基于通用模式推断，集成场景(TC-5xx)已跳过。
建议：完成 spec 后重新执行 `zwflow-qa-doc-gen` Skill 以获得完整测试覆盖。
```

---

## 3. prd.md — 产品需求（可选）

### 读取路径

`openspec/changes/<change_name>/prd.md`，不存在则跳过，无提示。

### 提取内容

启发式提取，无需严格结构：

| 提取目标 | 识别信号 | 用途 |
|---------|---------|------|
| 业务流程 | 含「流程」「步骤」「先...再...然后」、有序列表描述操作序列 | TC-5xx 跨接口链路 |
| 验收标准 | 含「验收标准」「AC」「Acceptance Criteria」 | TC-5xx 断言依据 |
| 业务约束 | 含「限制」「规则」「不允许」「必须」 | TC-3xx 业务规则补充 |

### 提取的统一结构

```javascript
{
  flows: [
    {
      name: "创建画布并生成图片",
      steps: ["创建画布", "选择模板", "提交生成", "查询状态", "下载结果"],
      source_line: "用户创建画布后选择模板，提交生成任务..."
    }
  ],
  constraints: [
    {
      text: "每个用户最多创建 10 个画布",
      source_line: "..."
    }
  ],
  acceptance_criteria: [
    {
      text: "生成完成后用户可下载 PNG 格式图片",
      source_line: "..."
    }
  ]
}
```

---

## 4. design.md — 技术设计（可选）

### 读取路径

`openspec/changes/<change_name>/design.md`，不存在则跳过，无提示。

### 提取内容

| 提取目标 | 识别信号 | 用途 |
|---------|---------|------|
| 状态机 | `→` / `->` 连接的状态、含「状态」列的表格 | TC-3xx 状态转换用例 + TC-5xx 全链路 |
| 字段约束 | 表格中含 min/max/长度/约束 | TC-2xx 边界值 |
| 决策表 | 条件 × 条件 → 结果的表格 | TC-3xx 决策表用例 |

### 状态机提取

识别模式：
- `draft → published → archived`（箭头分隔）
- `pending -> processing -> completed | failed`（含分支）
- 表格：`| 当前状态 | 事件 | 目标状态 |`

提取为：
```javascript
{
  states: ["draft", "published", "archived"],
  transitions: [
    { from: "draft", to: "published", trigger: "publish" },
    { from: "published", to: "archived", trigger: "archive" }
  ],
  terminal_states: ["archived"],
  source: "design.md"
}
```

---

## openspec changes 输入约定

### Change 定位方式

通过 OpenSpec CLI 定位 change:

- **提供了 change_name** → 直接使用 `openspec/changes/<change_name>/`,验证含 yapi.md
- **未提供** → 运行 `openspec list --json` 获取所有变更,过滤含 yapi.md 的 change,向用户展示选项并等待明确选择

选择界面展示:
- Change 名称
- qa-doc.md 状态(已生成/未生成)
- 最近修改时间(从 `lastModified` 字段)
- 标记最近修改的 change 为 "(Recommended)"

### 路径约定

- **必读**: `openspec/changes/<change_name>/yapi.md`
- **主动读取**: `openspec/changes/<change_name>/specs/*.md`（递归）
- **可选读取**: `openspec/changes/<change_name>/prd.md`
- **可选读取**: `openspec/changes/<change_name>/design.md`
- **取标题**: `openspec/changes/<change_name>/proposal.md`（仅取 H1 作为项目名）

**反模式**: 不要把 prd/design 当接口文档解析 — 它们提供业务上下文和约束，不是接口契约定义。

---

## 输出语言规则

中英混合接口文档时,用例生成遵循 `writing-rules.md` 规则 5:

| 元素 | 语言 |
|---|---|
| 用例标题、GIVEN / WHEN / THEN 正文 | 中文 |
| 字段名(`userId` / `external_userid`) | 保留接口原文,不翻译 |
| 枚举值(`"draft"` / `"published"`) | 保留原文 |
| Body JSON 示例 | 完整保留原 JSON,字段名与值不动 |
| msg / 错误信息关键词 | 按接口实际响应语言推测 |

判断 msg 语言信号:
- 响应示例 msg 含中文字符 → msg 关键词用中文
- 响应示例 msg 含英文 + 中文混合 → 写两个候选
- 响应示例只有英文 → 关键词用英文
