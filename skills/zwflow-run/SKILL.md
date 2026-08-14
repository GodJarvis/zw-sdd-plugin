---
name: zwflow-run
description: "一键编排完整桥接流程：前置检查 → Worktree → TDD Apply → Review → Verify"
---

一键执行完整融合工作流。桥接层负责：
1. 读取 OpenSpec 产物，喂给 AI 上下文
2. 按阶段编排 Superpowers 原生 Skill 的执行顺序
3. 在各 Skill 执行后回写 OpenSpec 体系（勾选 tasks、标准 commit）

**依赖**：Superpowers 插件已通过插件系统安装。

**Input**: 当前调用参数（变更名，必填）。如未提供，运行 `openspec list --json` 后向用户展示选项并等待明确选择。

---

## 阶段进度可视化

启动时 MUST 建立以下阶段进度清单，并逐阶段更新状态（in_progress → completed）：

1. 环境检测
2. 启动与前置检查
3. Worktree 隔离
4. TDD Apply
5. Code Review
6. Verification

---

## Stage 0: Superpowers 环境检测

执行两层检查确认融合环境状态：

**第一层：Superpowers 能力检测**

使用当前宿主的 Skill 发现能力确认本流程引用的 Superpowers Skill 已加载；不要根据某一宿主的插件安装文件推断其它宿主状态。

**第二层：桥接配置检测**

确认当前宿主根指令文件包含“Superpowers 融合配置”，并确认当前步骤动态引用的全部 ZWFlow Skill 均可由宿主发现。命令入口仅为可选兼容别名，缺少命令入口不影响 Skill 直接执行。

**处理逻辑**：
- 第一层失败（插件未安装）→ 使用当前宿主的原生插件安装机制安装 Superpowers；不得调用其它宿主的安装命令。宿主不支持会话内安装时，说明缺失依赖并停止，待用户安装后重新执行
- 安装失败 → 询问用户是否降级为 `openspec-apply-change` Skill（无 TDD 强制、无 review 子代理），用户拒绝则停止
- 第二层失败（桥接配置缺失）→ 停止，提示调用 `claude-config-sync` Skill 部署桥接配置
- 两层均通过 → 继续 Stage 1

---

## Superpowers 技能调度声明

当正在执行 `zwflow-run` Skill 的任一 Stage（从 Stage 0 到流程结束）时，以下规则生效：

**NEVER 触发以下 skill**（功能已被 OpenSpec 产物流程覆盖，触发会导致重复规划）：
- ❌ brainstorming — 功能由 `openspec-explore` Skill + `openspec-propose` Skill 承担
- ❌ writing-plans — 功能由 OpenSpec tasks.md（含验收契约+执行计划）承担
- ❌ executing-plans — 功能由 `zwflow-apply` Skill 编排承担

**判定条件**：从本 Skill 被调用开始，直到输出"所有 Stage 完成"或用户中断为止，上述 3 个 skill 均不得触发。用户在此期间的追问、补充指令不改变此约束。

**MUST 启用以下 skill**（执行层增强）：
- ✅ test-driven-development — apply 每个 Task 强制 TDD 红绿循环
- ✅ using-git-worktrees — apply 前创建隔离工作区
- ✅ subagent-driven-development — 并行 Phase 的模块由子代理执行
- ✅ dispatching-parallel-agents — 与 subagent-driven-development 配合，负责并行任务派发
- ✅ systematic-debugging — 测试反复失败时自动触发 4 阶段根因分析
- ✅ requesting-code-review — apply 完成后独立子代理审查
- ✅ receiving-code-review — 收到审查反馈后执行修复流程
- ✅ verification-before-completion — 运行命令出证据
- ✅ finishing-a-development-branch — archive 后分支清理

---

## Stage 1: 启动与前置检查

1. **确定变更**
   ```bash
   openspec status --change "当前调用参数" --json
   ```
   确认变更存在且 specs 已冻结。

2. **读取全部上下文文件**
   ```bash
   openspec instructions apply --change "当前调用参数" --json
   ```
   读取 contextFiles 中所有文件：proposal、specs、design、tasks。

3. **确认执行模式**（向用户展示选项并等待明确选择）
   - 无人值守连续模式
   - 逐阶段确认模式
   - 逐阶段 + 逐模块审查模式

4. **验证前提条件**（全部不通过则停止）
   - specs 已冻结（status 中确认）
   - 如 specs 涉及接口变更 → yapi.md 已生成

---

## Stage 2: Worktree 隔离（可选）

询问用户是否需要 worktree 隔离：
- **不需要隔离（推荐，已在 dev 分支）** — 跳过 worktree 创建，直接在当前分支工作
- **需要隔离** — 创建 worktree 分支

**用户选择"需要隔离"时**：

Superpowers `using-git-worktrees` 自动生效。

桥接层补充约束（CRITICAL OVERRIDE — 覆盖 Superpowers 默认 baseRef）：
- MUST 基于用户当前所处分支切出，禁止使用默认的 master/main。具体方式：以当前 HEAD 为基准创建 worktree 分支 `feature/当前调用参数`
- 如果 worktree 已存在（中断恢复场景），直接进入该 worktree 继续

**用户选择"不需要隔离"时**：

- 跳过 worktree 创建，后续 Stage 3-5 在当前分支直接执行
- 失败回退方式：`git reset --hard` 到 apply 前的 commit（需用户确认）

---

## ★ Stage Gate 1（逐阶段模式下暂停等待用户确认）

---

## Stage 3: TDD Apply

执行 `zwflow-apply` Skill 当前调用参数。

该命令会按执行计划调度所有 Task，触发 TDD 红绿循环、并行子代理、自动调试。

---

## ★ Stage Gate 2（逐阶段模式下暂停等待用户确认）

---

## Stage 4: Code Review

执行 `zwflow-review` Skill 当前调用参数。

触发独立 review 子代理，传入 specs + design + 编码护栏作为额外审查上下文。

P0/P1 问题修复后重跑相关测试确认。

---

## ★ Stage Gate 3（逐阶段模式下暂停等待用户确认）

---

## Stage 5: Verification

执行 `zwflow-verify` Skill 当前调用参数。

Superpowers 验证 + OpenSpec 双向反查 + 全勾选检查。

---

## 完成

全部通过后提示用户执行 `zwflow-rework-analysis` Skill 当前调用参数 进行返工复盘。
复盘完成后，按发布场景提示：
- 版本上线：执行 `zwflow-deploy-doc-gen` Skill 生成上线文档，再按文档包含的 change 逐个执行 `openspec-archive-change` Skill <change-name>，最后执行 `zwflow-finish` Skill <change-name> 分支收尾。
- 非版本上线：执行 `openspec-archive-change` Skill 当前调用参数 归档，再执行 `zwflow-finish` Skill 当前调用参数 分支收尾。

---

## 测试范围收敛规则

SDD 工作流中所有需要运行测试验证的节点（verify、finish、apply 模块完成后），MUST 使用以下策略缩小测试范围，**禁止直接运行全量 `composer test`**。

### 核心原则

变更范围 = commit diff。每个模块独立 commit，commit 边界天然定义了模块变更范围，无需额外声明。

### 收敛流程

**Step 1: 提取变更文件**

读取 `references/frameworks/<framework>.md`，使用其中的源码范围提取 apply 当前模块 commit，或 verify/finish 相对发布基线的变更文件。

**Step 2: 定位回归测试文件**

按当前框架 reference 的目录约定从变更源文件推导测试文件：
- 合并 diff 中新增/修改的测试文件
- 去重

**Step 3: 运行测试**

使用当前框架 reference 的测试命令运行筛选后的测试文件。

- 阈值：0 failures, 0 errors

### 高风险变更

以下场景的目录映射无法覆盖全部下游影响，MUST 在 Step 2 基础上自动扩展测试范围：

**基类变更**（Controller 基类、Model 基类、Service 基类等）：

1. 从变更文件中提取基类的完整类名
2. 在当前框架 reference 声明的源码根目录中搜索所有子类
3. 按目录约定映射到测试文件，追加到测试列表

**受保护配置变更**（范围由当前框架 reference 定义）：

1. 从变更文件中提取变更的配置键
2. 在当前框架 reference 声明的源码根目录中搜索引用方
3. 按目录约定映射到测试文件，追加到测试列表

**优先级**：结构化代码图影响分析 > 原生文本搜索。代码图可用时优先使用；不可用时由原生搜索自动接管，无需用户介入。

### 适用范围

本规则在以下节点生效：
- **zwflow-apply skill** — 模块 commit 后的回归验证（内联于该 skill 的「模块回归验证」步骤）
- **zwflow-verify skill** — Stage 5 的 ① 测试套件检查
- **zwflow-finish skill** — 分支收尾前的最终验证

`zwflow-apply` 的 TDD 红绿循环中每个 Task 本身只跑对应测试，不适用此规则。

---

## Guardrails

- 工程纪律由 Superpowers 原生 Skill 执行，桥接层只做编排 + 上下文适配 + 结果回写
- Superpowers 插件未安装时（Stage 0 检测失败）：按当前宿主的原生插件机制安装；无法安装则询问用户是否降级为 `openspec-apply-change` Skill，用户拒绝则停止
- 中断恢复：重新执行时根据 tasks.md 勾选状态和 worktree 存在性判断断点
