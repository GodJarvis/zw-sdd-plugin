---
name: zwflow-qa-doc-gen
description: "为 openspec change 生成接口测试用例文档(qa-doc.md)。触发：`zwflow-qa-doc-gen` Skill、`qa-doc-gen`、`qa-doc 生成`、`生成测试用例`。三源融合：yapi.md(接口契约) + specs(场景定义) + prd(业务流程)，按 6 维度系统化设计用例，输出到 change 同目录 qa-doc.md。"
---

# 接口测试用例生成专家

## 触发

- `zwflow-qa-doc-gen` Skill [change_name]
- 自然语言提到 "qa-doc-gen" / "qa-doc 生成" / "为 change xxx 生成测试用例"

## 工作流

### 步骤 1：确定 change

```
├── 提供了 change_name
│   ├── openspec/changes/<change_name>/ 存在且含 yapi.md → 直接使用
│   ├── 存在但无 yapi.md → 报错,提示先执行 `zwflow-yapi-doc-gen` Skill
│   └── 不存在 → 报错 + `openspec list --json` 列出可选,让用户重选
│
└── 未提供
    ├── 运行 `openspec list --json` 获取所有变更
    ├── 过滤出含 yapi.md 的 change
    └── 向用户展示选项并等待明确选择（按最近修改排序，标记 Recommended）
```

始终提示："正在为 change: \<name\> 生成测试用例"

### 步骤 2：三源读取

按 `references/input-formats.md` 定义的解析规则，依次读取：

1. **必读** `yapi.md` → 接口契约（解析为统一中间结构）
2. **主动读取** `specs/*.md` → 提取所有 Scenario 的 GIVEN/WHEN/THEN（不存在则降级，见下方降级策略）
3. **可选读取** `prd.md` → 提取业务流程/验收标准（不存在则跳过，无提示）
4. **可选读取** `design.md` → 提取状态机定义（不存在则跳过，无提示）
5. **取标题** `proposal.md` → 仅取 H1 作为项目名

### 步骤 3：融合分析

```
├── 将 spec scenario 映射到具体接口（通过路径/动词/资源名匹配）
├── 从 design.md 提取状态机 → 关联到对应接口的状态字段
├── 从 prd.md 提取跨接口业务链路（若存在）
├── 映射失败的 scenario(无法关联到 yapi.md 中任何接口) → 列入 TC-000 假设节
└── 识别涉及多个接口的 scenario → 归入 TC-5xx 候选
```

### 步骤 4：批量策略与大纲确认

**N = yapi.md 中解析出的接口总数**：

```
├── N = 1        → 直接进入步骤 5
├── 2 ≤ N ≤ 3   → 全部生成,直接进入步骤 5
├── 4 ≤ N ≤ 20  → 输出结构大纲(含下方内容),等用户确认后进入步骤 5
└── N > 20      → 按 path 首段分组让用户先选组,选完后输出大纲确认
```

多接口默认合并为 1 份汇总文档。

**大纲内容（N ≥ 4 时输出，一次性确认）**：

```
├── 模块列表(接口名 + 路径)
├── 预计合并信号("模块 A 与模块 B 参数结构相同,建议合并为多端通用模块")
├── 公共节预判("预计抽取: 公共字段约束-客服管理")
├── 预估各模块 TC 数量范围
├── 用户确认 → 进入步骤 5
└── 用户调整 → 修改合并策略/排除某模块后重新输出大纲
```

### 步骤 5：按 6 维度生成用例

| 维度 | ID 前缀 | 驱动来源 | 说明 |
|------|---------|---------|------|
| 1. 正常场景 | TC-0xx | yapi.md | 合法参数、默认值、业务枚举取值 |
| 2. 参数校验 | TC-1xx | yapi.md | 必填缺失、类型错、空、null、超长 |
| 3. 边界场景 | TC-2xx | yapi.md + design.md | 数值/长度边界 |
| 4. 业务规则 | TC-3xx | **specs scenario** + design 状态机 | spec 驱动优先,通用推断兜底 |
| 5. 响应校验 | TC-4xx | yapi.md | 字段完整性、类型、排序 |
| 6. 集成场景 | TC-5xx | **prd + specs + design** | 跨接口链路,≤5 条 |

**TC-5xx 超出 5 条时的取舍优先级**（从高到低）：
1. prd 主流程正向链路（端到端核心路径）
2. 状态机全链路遍历（初态→终态）
3. spec 多步骤 scenario（WHEN 涉及多接口）
4. 流程中断一致性（中间步骤失败后数据完整性）

详见 `references/coverage-dimensions.md`。

### 步骤 6：落盘与交付

1. 检查 `qa-doc.md` 是否已存在：
   - 不存在 → 直接写入
   - 已存在 → 向用户展示四个选项并等待明确选择：
     - **覆盖**：全量替换
     - **增量合并**：仅更新变更模块（见下方增量策略）
     - **另存为** `qa-doc-v2.md`
     - **取消**
2. 写入 `openspec/changes/<change_name>/qa-doc.md`
3. 会话回报：文件链接 + 用例数量分维度摘要表 + 自检结果

文件命名、元信息、格式规范详见 `references/output-template.md`。

#### 增量合并策略

选择"增量合并"时执行以下流程：

```
├── 1. 解析已有 qa-doc.md 的模块索引(接口名 + 路径)
├── 2. 对比 yapi.md 当前接口集 vs 已有模块索引:
│   ├── 新增接口(yapi 有,qa-doc 无) → 新生成模块,插入对应位置
│   ├── 已删接口(qa-doc 有,yapi 无) → 标记为"建议删除",列入回报(不自动删)
│   └── 已有接口(两侧都有) → 一律重新生成该模块(覆盖原内容)
├── 3. 检查 specs/ 中 ADDED/MODIFIED/REMOVED scenario → 更新对应 TC-3xx + TC-5xx
│   ├── ADDED scenario（含首次补充 specs/ 的场景）→ 新生成 TC-3xx/TC-5xx
│   ├── MODIFIED scenario → 重新生成对应 TC
│   └── REMOVED scenario → 提示删除对应 TC
├── 4. 重跑 TC-5xx(集成场景依赖全局接口集,必须全量刷新)
├── 5. 更新模块索引表的用例数和合计
├── 6. 重扫跨模块对称冗余（新模块可能满足合并阈值）
│   ├── 已有合并结构（多端通用模块 / 公共字段约束）保持不变
│   ├── 新满足阈值（如新增模块与已有模块构成同业务多端入口、或共享 ≥3 同质 TC）
│   │   └── 输出合并建议，获得用户明确确认后执行合并或抽公共节
│   └── 不满足阈值 → 跳过
└── 7. 回报中输出 diff 摘要(新增 N 个模块/更新 M 个/建议删除 K 个/合并建议 L 条)
```

> **设计选择**：已有接口一律重新生成而非保留，因为 AI 无法可靠判断 yapi.md 自上次生成以来是否变更（qa-doc 不记录源内容 hash）。如用户有手工修改希望保留，应选"另存为"再手动 merge。

### 步骤 7：落盘前自检（必做）

**必须按 `references/writing-rules.md` 文末「落盘前自检清单」逐项核对，任一未通过则修订后再落盘。**

额外检查（writing-rules 清单之外的 openspec 特有项）：

- **spec 覆盖**：specs/ 中每个相关 Scenario 都有对应 TC-3xx
- **集成场景**：TC-5xx 每个 Step 的接口路径存在于 yapi.md
- **降级提示**：specs/ 不存在时已输出降级提示

---

## 降级策略

| 条件 | 行为 |
|------|------|
| specs/ 存在 + prd.md 存在 | 完整三源融合（6 维度全出） |
| specs/ 存在 + 无 prd.md | TC-3xx spec 驱动 + TC-5xx 仅从 spec 多步骤场景推导 |
| specs/ 不存在 + 有 prd.md | TC-3xx 通用推断 + TC-5xx 从 prd 流程推导 |
| 都不存在 | 纯接口测试（维度 1-2-3-5），TC-3xx 通用推断，TC-5xx 跳过 + 提示 |

---

## 强制书写规范

生成用例前，**先阅读 `references/writing-rules.md`**：

1. **用例必须写入文件**，禁止粘贴会话
2. **GIVEN/THEN 一行一断言**，禁用 `；` / `、` 串接
3. **批量改写先读取全貌再依次局部编辑**
4. **落盘前按 10 条冗余模式自检**

## 默认行为（无需反问用户）

- **内部接口默认跳过鉴权类用例**：openspec changes 工作流默认按内部接口处理。
- **多接口合并为 1 份汇总文档**
- **跨模块对称冗余扫描**
- **失败响应固化**：THEN 不写择一描述
- **不输出装饰内容**：无 curl 段、无优先级/测试方法字段
- **不生成分页参数用例**

## 错误处理

| 场景 | 处理 |
|---|---|
| `openspec list --json` 无可用 change | 报错：请先 `openspec-propose` Skill |
| change_name 不存在 | 报错 + 列出可选 |
| change 下无 yapi.md | 报错 + 提示 `zwflow-yapi-doc-gen` Skill |
| qa-doc.md 已存在 | 向用户展示选项并等待明确选择：覆盖 / 增量合并 / 另存为 / 取消 |
| specs/ 不存在 | 降级 + 提示（不报错） |
| 接口数 > 20 | 按 path 首段分组让用户先选 |

## 子文档索引

按需加载：

- `references/writing-rules.md` — **【强制】书写硬规则与自检清单**
- `references/input-formats.md` — 三源输入解析规则（yapi/specs/prd/design）
- `references/coverage-dimensions.md` — 6 维度设计规则与示例
- `references/output-template.md` — 输出模板（含 TC-5xx 集成场景格式）
- `references/examples/example-openspec-change.md` — 完整流程示例
