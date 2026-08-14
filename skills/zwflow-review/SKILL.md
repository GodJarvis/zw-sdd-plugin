---
name: zwflow-review
description: "桥接层 Code Review — 触发 Superpowers review + Spec 合规性审查"
---

触发 Superpowers `requesting-code-review` 原生 Skill，补充 OpenSpec 特有的审查上下文。

**Input**: 当前调用参数（变更名，必填）。如未提供，运行 `openspec list --json` 后向用户展示选项并等待明确选择。

---

## Step 1: 准备审查上下文

除 Superpowers 默认传给 review 子代理的代码 diff 外，额外读取并提供：

1. `openspec/changes/当前调用参数/specs/` — 所有 Scenario，用于 Spec 合规性审查
2. `openspec/changes/当前调用参数/design.md` — 架构决策，用于架构合规性审查
3. 当前宿主根指令文件的编码护栏章节 — 用于项目规范审查

---

## Step 2: 启动 Review 子代理

派发独立 review 执行单元：

- **MUST 使用逻辑 Agent `code-reviewer`**
- prompt 中包含：
- 代码 diff（`git diff release...HEAD`，即当前分支相对于 release 基线的所有变更）
- 上述 3 项额外上下文
- diff 涉及文件路径匹配的所有编码规范 Skill 全文（按当前宿主可见的 Skill 路径作用域解析）
- 审查维度声明：
  - **Spec 合规性**：代码行为是否与 Scenario 定义一致
  - **架构合规性**：是否遵循 design.md 的决策
  - **测试质量**：每个 Scenario 是否有 `@scenario` 标注的测试覆盖
  - **编码规范**：是否符合传入的 skill 规范 + 当前宿主根指令文件的编码护栏

---

## Step 3: 处理审查反馈（CRITICAL OVERRIDE）

以下规则覆盖 Superpowers `receiving-code-review` 的默认行为：

Review 子代理返回问题列表后：

- **P0/P1（Critical/Major）**：
  1. 逐个修复
  2. 修复后 MUST 重跑相关测试确认通过
  3. Commit 格式：`fix(<module>): review 修复 [change: 当前调用参数]`（review 修复可能横跨多个 task，故省略 task: N）
  4. 修复涉及 spec 级别变更 → 暂停，先更新 specs 再改代码

- **P2（Minor）**：
  - 记录在审查报告中，不阻塞流程

- **全部通过 / 仅 P2**：
  - 提示进入 `zwflow-verify` Skill 当前调用参数

---

## Guardrails

- Review 子代理 MUST 是独立 Agent（不复用当前会话上下文，避免"自己审自己"）
- 修复代码后 MUST 重跑测试，不允许只改代码不验证
