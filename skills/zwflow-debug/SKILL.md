---
name: zwflow-debug
description: "桥接层系统化调试 — 触发 Superpowers 4 阶段根因分析 + OpenSpec 上下文"
---

触发 Superpowers `systematic-debugging` 原生 Skill（4 阶段根因分析：Investigate → Hypothesize → Verify → Fix）。

**Input**: 当前调用参数（可选，变更名）。如在 `zwflow-apply` Skill 过程中自动触发，自动继承当前变更名。

---

## 自动触发条件（CRITICAL OVERRIDE）

覆盖 Superpowers systematic-debugging 的默认触发时机：

- `zwflow-apply` Skill 过程中同一测试连续 2 次 FAIL（非首次 RED）→ 自动调用本 Skill
- 修复后回归测试的 `@scenario` 标注 MUST 关联到对应 Scenario

---

## Step 1: 补充 OpenSpec 上下文

如果当前在某个 OpenSpec 变更的 apply 过程中：
- 读取当前 Task 对应的 Scenario + 验收契约（明确期望行为）
- 读取 design.md 相关技术方案（理解设计意图）
- 读取当前宿主根指令文件中的开发命令（Docker、测试命令、日志路径等环境信息）

---

## Step 2: 触发 Superpowers systematic-debugging

4 阶段根因分析（Investigate → Hypothesize → Verify → Fix）由 Superpowers systematic-debugging Skill 原生接管，桥接层不重复定义。

桥接层补充约束：
- Step 1 中注入的 OpenSpec 上下文（Scenario + 验收契约 + design）作为期望行为的参照
- **铁律：Phase 1 未完成前 NEVER 提出修复方案**（与 Superpowers Iron Law 一致，此处强调）

---

## Step 3: 回写 OpenSpec

修复完成后：
- 如修复涉及某个 Task 的代码：确保该 Task 所有测试仍绿
- 如产生新的回归测试：测试 PHPDoc 标注 `@scenario` 关联到对应 Scenario
- Commit 格式：`fix(<module>): 描述 [change: 当前调用参数, task: N]`

---

## Guardrails

- 严禁跳过 Phase 1 直接猜测修复（"shotgun debugging"）
- 每次假设验证 MUST 有命令输出作为证据
- 修复后 MUST 展示测试通过的实际输出
