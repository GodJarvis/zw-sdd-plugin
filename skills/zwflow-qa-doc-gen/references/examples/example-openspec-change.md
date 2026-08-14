# 示例：三源融合 — `zwflow-qa-doc-gen` Skill → qa-doc.md

> 演示通过 `zwflow-qa-doc-gen` Skill 命令为 openspec change 生成三源融合的 qa-doc.md

---

## 示例 change 结构

```
openspec/changes/feat-task-management/
├── proposal.md          # H1 = "任务管理功能"
├── prd.md               # 含业务流程
├── specs/
│   └── task-crud/
│       └── spec.md      # 含 4 个 Scenario
├── design.md            # 含状态机定义
└── yapi.md              # 3 个接口
```

---

## 触发

```
`zwflow-qa-doc-gen` Skill feat-task-management
```

## Skill 执行流程

```
步骤 1: 确定 change
  ├── openspec/changes/feat-task-management/ ✓ 存在
  ├── 内含 yapi.md ✓
  └── 提示:"正在为 change: feat-task-management 生成测试用例"

步骤 2: 三源读取
  ├── yapi.md → 3 个接口:
  │   - POST /task/create
  │   - POST /task/update-status
  │   - GET /task/list
  ├── specs/task-crud/spec.md → 4 个 Scenario:
  │   - "创建任务成功"
  │   - "超出任务上限时创建失败"
  │   - "已完成任务不可修改状态"
  │   - "创建后可在列表中查到"
  ├── prd.md → 1 个业务流程:
  │   - "用户创建任务 → 执行 → 标记完成 → 列表查看"
  └── design.md → 1 个状态机:
      - draft → processing → completed | failed

步骤 3: 融合分析
  ├── Scenario 映射:
  │   - "创建任务成功" → POST /task/create (单接口 → TC-3xx)
  │   - "超出任务上限时创建失败" → POST /task/create (单接口 → TC-3xx)
  │   - "已完成任务不可修改状态" → POST /task/update-status (单接口 → TC-3xx)
  │   - "创建后可在列表中查到" → create + list (多接口 → TC-5xx 候选)
  ├── 状态机: draft → processing → completed | failed
  │   → TC-3xx: 非法转换(draft → completed 跳跃)
  │   → TC-5xx: 全链路遍历(draft → processing → completed)
  └── prd 流程: "创建 → 执行 → 完成 → 查看"
      → TC-5xx: 端到端正向链路

步骤 4: 批量策略
  └── N=3, 全部生成, 合并为 1 份汇总文档

步骤 5: 按 6 维度生成

步骤 6：写入 → qa-doc.md
```

---

## 生成的 qa-doc.md 示例（节选）

```markdown
# 任务管理功能 测试用例

> **编写人**:
> **日期**: 2026-06-17
> **关联需求**: [./yapi.md](./yapi.md)

> ⚠️ token / cookie / csrf 已脱敏。

---

## 公共请求约定

- **Method**: POST / GET
- **Headers**: Content-Type: application/json, Cookie, zw-csrf-token
- **鉴权前置**: "已登录" = Cookie + csrf Header 有效

## 公共失败响应契约

> 业务校验失败统一返回 HTTP 200 + status_code != 1。

---

## 模块索引

| # | 接口名 | 路径 | 用例数 |
|---|---|---|---|
| 1 | 创建任务 | POST /task/create | 8 |
| 2 | 修改任务状态 | POST /task/update-status | 6 |
| 3 | 任务列表 | GET /task/list | 4 |
| 集成 | 集成场景 | — | 3 |
| | | **合计** | **21** |

---

## 模块 1: 创建任务

> **路径**: `POST /task/create`

### TC-001: 主链路 - 合法参数创建
...

### TC-101: name 必填字段缺失
...

### TC-301: 创建任务成功 - 业务规则(spec)

- **前置条件(GIVEN)**:
  - 已登录(同公共约定)
  - 用户当前进行中的任务数 < 3
- **操作(WHEN)**:
  - Body: {"name":"新任务","type":"normal"}
- **预期结果(THEN)**:
  - HTTP 200
  - status_code = 1
  - data.id 为非空字符串
  - data.status = "draft"

### TC-302: 超出任务上限时创建失败 - 业务规则(spec)

- **前置条件(GIVEN)**:
  - 已登录(同公共约定)
  - 用户已有 3 个 status=processing 的任务
- **操作(WHEN)**:
  - Body: {"name":"第四个任务","type":"normal"}
- **预期结果(THEN)**:
  - HTTP 200
  - status_code != 1
  - msg 含 "上限" 或 "exceed"

---

## 模块 2: 修改任务状态

> **路径**: `POST /task/update-status`

### TC-001: 主链路 - draft → processing
...

### TC-301: 已完成任务不可修改状态 - 业务规则(spec)

- **前置条件(GIVEN)**:
  - 已登录
  - 任务 task_id=T1 状态为 completed
- **操作(WHEN)**:
  - Body: {"task_id":"T1","status":"processing"}
- **预期结果(THEN)**:
  - HTTP 200
  - status_code != 1
  - msg 含 "已完成" 或 "不可修改"
  - 查询确认状态仍为 completed

### TC-302: 非法状态跳转 draft → completed - 业务规则(状态机)

- **前置条件(GIVEN)**:
  - 已登录
  - 任务 task_id=T2 状态为 draft
- **操作(WHEN)**:
  - Body: {"task_id":"T2","status":"completed"}
- **预期结果(THEN)**:
  - HTTP 200
  - status_code != 1
  - msg 含 "状态" 或 "非法"

---

## 模块 3: 任务列表

> **路径**: `GET /task/list`

### TC-001: 主链路 - 有数据时正常返回
...

### TC-401: 响应结构契约
...

---

## 集成场景

> 以下用例验证跨接口的业务流程联动，需按 Step 顺序依次执行。

### TC-501: 任务全流程 - 创建到完成(prd)

- **前置条件(GIVEN)**:
  - 已登录
  - 用户当前无进行中的任务
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

### TC-502: 状态机全链路遍历(状态机)

- **前置条件(GIVEN)**:
  - 已登录
  - 新建任务处于 draft 状态
- **操作(WHEN)**:
  - Step 1: draft → processing (POST /task/update-status)
  - Step 2: processing → completed (POST /task/update-status)
- **预期结果(THEN)**:
  - Step 1: status_code=1, 确认 status=processing
  - Step 2: status_code=1, 确认 status=completed
  - 到达终态后再次修改 → status_code != 1

### TC-503: 创建后列表可查 - 数据一致性(spec)

- **前置条件(GIVEN)**:
  - 已登录
  - 任务列表当前为空或已知数量
- **操作(WHEN)**:
  - Step 1: POST /task/create {"name":"一致性验证"} → $task_id
  - Step 2: GET /task/list
- **预期结果(THEN)**:
  - Step 1: status_code=1
  - Step 2: list 中存在 id=$task_id 的记录, name="一致性验证"
```

---

## 维度分布摘要

```
已生成 → [changes/feat-task-management/qa-doc.md](./qa-doc.md)

| 维度 | 用例数 | 驱动来源 |
|---|---|---|
| TC-0xx 正常场景 | 4 | yapi.md |
| TC-1xx 参数校验 | 4 | yapi.md |
| TC-2xx 边界场景 | 2 | yapi.md + design.md |
| TC-3xx 业务规则 | 5 | specs(3) + 状态机(1) + 通用推断(1) |
| TC-4xx 响应校验 | 3 | yapi.md |
| TC-5xx 集成场景 | 3 | prd(1) + 状态机(1) + spec(1) |
| **合计** | **21** | |

自检:
- 规则 1 ✓ 已写入文件
- 规则 2 ✓ 一行一断言
- 规则 4 ✓ 已扫描冗余
- spec 覆盖 ✓ 4 个 scenario 全部映射(3→TC-3xx, 1→TC-5xx)
- 集成场景 ✓ TC-5xx 各 Step 路径均存在于 yapi.md
- 内部接口跳过鉴权 ✓
```

---

## 降级示例：specs 不存在

若 `openspec/changes/feat-task-management/specs/` 不存在：

```
⚠️ specs/ 未找到，本次仅生成接口契约测试（维度 1-2-3-5）。
业务规则(TC-3xx)基于通用模式推断，集成场景(TC-5xx)已跳过。
建议：完成 spec 后重新执行 `zwflow-qa-doc-gen` Skill 以获得完整测试覆盖。

已生成 → qa-doc.md (15 条 TC, 无 TC-5xx)
```
