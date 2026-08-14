---
name: zwflow-apply
description: "桥接层 TDD Apply — 读取 OpenSpec 产物，按执行计划调度 Superpowers TDD"
---

读取 OpenSpec 产物，按执行计划调度，让 Superpowers `test-driven-development` + `subagent-driven-development` 原生接管实现过程。

**Input**: 当前调用参数（变更名，必填）。如未提供，运行 `openspec list --json` 后向用户展示选项并等待明确选择。

---

## 模块进度可视化

启动时 MUST 解析 tasks.md 中所有功能模块（`## N. 模块标题`），为每个模块建立进度项：

- **subject**：`N. 模块标题`（与 tasks.md 一致）
- **activeForm**：`正在实现 <模块名>`
- 开始模块 → 将对应进度项标记为 `in_progress`
- 模块完成（测试通过 + 静态验证通过 + commit/审查完成） → 将对应进度项标记为 `completed`
- 并行模式下，同一 Phase 的多个模块可同时标记为 `in_progress`
- 中断恢复时，根据 tasks.md 勾选状态将已完成模块直接标记 `completed`，从第一个未完成模块继续

---

## Before：准备上下文

**首次启动时 MUST 读取**：`openspec/GLOSSARY.md` 领域术语表，确保实现过程中对业务概念的理解与项目定义一致。

对每个待执行的 Task，按以下步骤准备上下文：

1. **读取执行计划**：解析 tasks.md 头部执行计划表格，确定当前 Phase 和模块调度顺序
2. **提取测试蓝图**：从 specs/ 中找到当前 Task 对应的 `#### Scenario:` 段落（即测试蓝图）
3. **提取验收契约**：从 tasks.md 当前 Task 下找到 MUST/SHALL 断言
4. **读取技术方案**：从 design.md 中提取当前模块的实现方案段落
5. **检查 TDD 豁免**：如 Task 标注了 `[TDD-EXEMPT: reason]`，跳过 TDD 红绿循环

6. **加载框架参考与编码规范 Skill**：先根据 `using-zw-sdd` 的识别结果读取本 Skill 的 `references/frameworks/<framework>.md`，再根据当前 Task 的目标文件路径加载全部匹配的编码规范 Skill。MUST 在写第一行代码前完成加载；并行调度时将匹配 Skill 全文传入独立执行单元上下文。

将以上信息整合为当前 Task 的执行上下文。

---

## During：执行约束（CRITICAL OVERRIDE）

以下规则在 Superpowers TDD Skill 执行时强制叠加，覆盖 Superpowers 默认行为：

### TDD 强制门控（NEVER SKIP — 无论任何执行模式）

**连续模式 ≠ 跳过 TDD。** 连续模式仅意味着不暂停等待人工审查，TDD 红绿循环的执行纪律不因执行模式改变。

对每个非 TDD-EXEMPT 的 Task，MUST 严格执行以下顺序：

1. **先写测试**（Red）— 创建测试文件，编写断言期望行为的测试方法
2. **运行测试确认失败** — 执行测试命令，确认测试 FAIL（证明测试有效）
3. **再写实现**（Green）— 编写最小实现代码使测试通过
4. **运行测试确认通过** — 执行测试命令，确认测试 PASS

**硬性禁止：**
- ❌ NEVER 在测试文件不存在时编写实现代码
- ❌ NEVER 先写实现再补测试（这不是 TDD，是事后补测试）
- ❌ NEVER 以"快速完成"、"连续模式"、"效率优先"为由跳过红绿循环
- ❌ NEVER 将测试推迟到所有实现完成后批量补写

**违反判定**：如果一个非 TDD-EXEMPT Task 的实现代码被写入，但对应测试文件不存在或测试未先运行过 → 视为 TDD 违规，MUST 立即补写测试并重新走红绿循环。

### TDD 适配

- 测试蓝图来源：从 specs/ 的 `#### Scenario:` 和 tasks.md 的验收契约提取，不自行发明
- 测试 PHPDoc MUST 标注 `@scenario <Scenario中文名>`，与 specs 1:1 对应
- TDD 豁免：tasks.md 中标注 `[TDD-EXEMPT: reason]` 的 Task 跳过红绿循环，改为逐条核实验收契约中的 MUST/SHALL 条件均已满足后标记完成
- 非 TDD-EXEMPT 的 Task：测试 PASS 后方可标记 Task 完成
- 红绿循环的执行纪律由 Superpowers TDD Skill 原生接管，桥接层不重复定义

### 测试分类规则

- **默认写单元测试**（`test/Cases/`）：TDD 红绿循环在此目录下进行
- **以下情况 MUST 额外补集成测试**（`test/Integration/`）：
  - Controller 层的 HTTP 端点 — 凡涉及接口的 Task 都需要 HTTP 端点测试
  - 涉及复杂 SQL JOIN/事务的 Repository 方法
  - 跨服务调用链路
- 集成测试基类：使用项目 `test/IntegrationTestCase.php`（含 DB 事务回滚）
- 一个 Task 可以同时产生单元测试 + 集成测试（如 Service 单测 + Controller 端点测试）

### 测试目录组织

按 `<change-name>/<功能模块>/` 组织测试文件，功能模块名对应 tasks.md 中的 `## N. 模块标题`：

```
test/Cases/<change-name>/<ModuleName>/XxxTest.php
test/Integration/<change-name>/<ModuleName>/XxxTest.php
```

- `<change-name>`：与 openspec 变更目录名一致（kebab-case）
- `<ModuleName>`：取 tasks.md 模块标题的 PascalCase 形式（如"积分 Service" → `PointsService`）
- 同一功能模块的单元测试和集成测试在各自目录下使用相同的子路径
- 命名空间跟随目录：`Test\Cases\FeatUserPoints\PointsService\GetBalanceTest`

### TDD 豁免清单

| 豁免标记 | 适用场景 | 替代行为（MUST） |
|----------|---------|-----------------|
| `[TDD-EXEMPT: migration]` | 数据库迁移 / DDL | **禁止尝试执行 DDL**（不连 DB、不跑 mysql、不建 PDO）。确认 SQL 文件存在于 `db.mysql.sql`/`db.rollback.sql`，核对字段/索引/约束与 spec 一致，标记完成 |
| `[TDD-EXEMPT: config]` | 纯配置变更 | 确认配置文件存在、key 名正确、值与 spec 一致 |
| `[TDD-EXEMPT: model-definition]` | 纯 Model 定义（字段/关系声明，无业务逻辑） | 确认类定义、属性、getter/setter、关系绑定与 spec/design 一致 |
| `[TDD-EXEMPT: dto]` | 纯 DTO / Entity 定义 | 确认类定义、字段、类型声明与 spec 一致 |
| `[TDD-EXEMPT: sdk-wrapper]` | 第三方 SDK 透传封装（无转换逻辑） | 确认封装方法签名、参数透传正确，无业务逻辑混入 |
| `[TDD-EXEMPT: docs]` | 文档更新 | 确认文档内容与变更一致 |

### 子代理适配

- 并行子代理 MUST NOT 直接修改 tasks.md（返回完成报告，主线统一勾选）
- Commit 格式 MUST 遵循 `feat(<module>): 描述 [change: <name>, task: N]`

### 调试触发

- 同一测试连续 2 次 FAIL（非首次 RED）→ 自动执行 `zwflow-debug` Skill

### 编码护栏强制校验（MUST — 每个文件写完后立即执行）

**写完任何 PHP 文件后（新增或修改），MUST 立即对照当前宿主根指令文件的编码护栏逐条验证，不得跳过、不得推迟到 Task 完成后批量检查。**

校验 checklist 由当前框架 reference 定义。逐条执行 reference 中的“文件完成检查”，并叠加当前文件路径命中的全部编码规范 Skill；不得把两个框架的规则混合折中。

**执行纪律**：
- 这不是“读完根指令文件就记住了”的背景知识，而是每个文件的 exit criteria
- config 文件、Model 定义等"简单"文件同样适用，不因文件简单而跳过
- 发现违规 → 当场修复 → 修复后继续，不标记 Task 完成直到所有文件通过校验

---

## After：回写 OpenSpec

### Task 勾选（CRITICAL — Task 完成的 exit criteria）

**每个 Task 的代码实现 + 测试通过后，MUST 立即勾选 tasks.md 对应条目：`- [ ]` → `- [x]`。**

- 这是 Task 完成的 **最后一步**，未勾选 = 未完成
- NEVER 将勾选推迟到模块结束后批量执行 — 必须逐个 Task 即时勾选
- NEVER 以"稍后统一处理"、"先继续下一个"为由跳过
- 并行子代理场景：子代理 MUST NOT 修改 tasks.md，但 MUST 在返回结果中明确报告已完成的 Task 编号列表；主线收到报告后 MUST 立即逐个勾选
- TDD-EXEMPT 的 Task：验收契约全部核实满足后立即勾选
- **判定规则**：进入下一个 Task 前，上一个 Task 的 `- [x]` MUST 已写入文件（可通过回读文件验证）

每个功能模块全部 Task 完成后，按以下顺序执行（任一步骤失败则停止修复后重跑）：

### 模块级静态验证（MUST — commit 前硬门控）

**禁止直接运行 `composer analyse` 全量扫描。** 使用当前框架 reference 的源码范围提取本模块变更文件，再按 reference 中的静态分析命令仅扫描这些文件。

**执行规则**：
- MUST 在每个功能模块的所有 Task 完成后、git commit 前执行
- 报错 → 立即修复所有 error → 重新运行直到 0 errors
- 通过后方可进入 commit 步骤
- 连续模式下同样执行，NEVER 以效率为由跳过

### Commit

- 逐模块审查模式：询问用户是否通过审查，确认前 NEVER commit
- 用户确认后（或连续模式下直接）执行 git commit
- Commit 格式：`feat(<module>): 描述 [change: 当前调用参数, task: N]`

### 模块回归验证（MUST — commit 后立即执行）

commit 完成后，MUST 验证本模块变更未引入回归。**禁止直接运行 `composer test` 或全量 `test/Cases/`。**

模块变更范围 = 当前 commit 的 diff。按以下流程执行：

**Step 1: 提取变更文件**

使用当前框架 reference 的源码范围读取当前 commit diff。

**Step 2: 定位回归测试文件**

按当前框架 reference 的目录映射从变更源文件推导测试文件：
- 合并 commit 中新增/修改的测试文件：`git diff HEAD~1 --name-only -- 'test/'`
- 去重

**Step 3: 运行回归测试**

按当前框架 reference 的测试命令运行筛选后的测试文件列表。

- 阈值：0 failures, 0 errors
- 失败 → 停止，修复后重跑直到通过，不得跳过进入下一模块

> **高风险变更**（框架 reference 声明的配置范围、基类修改）：目录映射无法覆盖全部下游影响。MUST 自动扩展测试范围。结构化代码图可用时使用影响分析；不可用时搜索子类和引用方并按目录约定映射。详见 `zwflow-run` Skill 的测试范围收敛规则。

---

## 并行调度

当执行计划中同一 Phase 有多个无依赖模块时：
- 为每个模块派发独立执行单元（MUST 使用当前宿主的通用执行配置）
- 每个子代理 prompt MUST 包含以下完整上下文：
  1. 该模块的 Scenario + 验收契约 + design 片段（业务上下文）
  2. 该模块目标文件路径匹配的所有编码规范 Skill 全文（按当前宿主可见的 Skill 路径作用域解析）
  3. 当前宿主根指令文件的编码护栏章节（显式传入强化优先级）
- 子代理完成后 MUST 执行两阶段审查再合并：
  1. **Spec 合规审查**：子代理产出的代码是否与 Scenario 定义一致
  2. **编码规范审查**：是否符合传入的 skill 规范 + 当前宿主根指令文件的编码护栏
- 两阶段审查通过后主线统一：勾选 tasks.md → commit

---

## 中断恢复

重新执行 `zwflow-apply` Skill 时：
1. 读取 tasks.md 勾选状态，找到第一个未完成的 Task
2. 如 worktree 已存在，直接进入继续
3. 如有未 commit 的已完成模块代码，先 commit 再继续

---

## 完成

### 全量勾选扫描（MUST — 最终兜底）

所有 Task 执行完毕后、提示用户下一步之前，MUST 执行一次全量扫描：

1. 读取 tasks.md 全文，统计所有 `- [ ]`（未勾选）条目
2. 如存在未勾选条目 → 逐个检查对应代码/测试是否已实现：
   - 已实现但漏勾 → 立即补勾 `- [x]`
   - 未实现 → 停止，报告遗漏的 Task 列表，询问用户如何处理
3. 全部确认为 `- [x]` 后方可进入下一步

**禁止以"看起来都完成了"为由跳过扫描 — MUST 实际读取 tasks.md 文件验证。**

---

所有 Task 完成后，提示用户：
- 如果是 `zwflow-run` Skill 流程中：自动进入 Stage 4（Review）
- 如果是独立执行：建议执行 `zwflow-review` Skill 当前调用参数
