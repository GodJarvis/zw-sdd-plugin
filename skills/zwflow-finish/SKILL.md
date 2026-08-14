---
name: zwflow-finish
description: "桥接层分支收尾 — 归档后清理 worktree、合并分支、推送远程"
---

触发 Superpowers `finishing-a-development-branch` 原生 Skill，在 OpenSpec 归档完成后执行分支收尾工作。

**Input**: 当前调用参数（变更名，必填）。如未提供，运行 `openspec list --json` 后向用户展示选项并等待明确选择。

---

## 前置条件（CRITICAL OVERRIDE）

以下约束覆盖 Superpowers finishing-a-development-branch 的默认行为：

- MUST 在 `openspec-archive-change` Skill 完成后执行（未归档则停止）
- 当前在 feature 分支（`feature/当前调用参数`）或对应 worktree 中
- 所有代码已 commit，无未暂存变更
- 分支操作（合并/推送/删除）MUST 逐步获得用户明确确认
- 目标分支默认为 `release`（基于项目分支策略）

---

## Step 1: 确认归档状态

```bash
openspec status --change "当前调用参数" --json
```

确认变更状态为 archived。如未归档则停止，提示先执行 `openspec-archive-change` Skill。

---

## Step 2: 最终验证（Superpowers verification 兜底）

按 `zwflow-run` Skill 的**测试范围收敛规则**执行变更相关测试，确保归档后代码仍然通过测试（防止归档过程引入问题）。

---

## Step 3: 分支收尾（Superpowers finishing-a-development-branch 原生接管）

分支操作、worktree 清理、分支删除由 Superpowers finishing-a-development-branch Skill 原生执行。

桥接层补充约束：
- 目标分支默认为 `release`（基于项目分支策略），Skill 检测时以此为基准
- 所有破坏性操作（合并/推送/分支删除）MUST 逐步获得用户明确确认
- Worktree 清理在分支操作完成后执行

---

## 完成

输出收尾报告：

```
## 分支收尾完成

**变更:** 当前调用参数
**分支:** feature/当前调用参数
**操作:**
- [x] 归档确认
- [x] 测试通过
- [x] 分支合并/推送: <选择的操作>
- [x] Worktree 清理: <已删除/已保留/不适用>
- [x] 分支删除: <已删除/已保留>
```

---

## Guardrails

- 所有破坏性操作（分支删除、force push）MUST 获得用户明确确认
- 如果合并存在冲突 → 暂停，提示用户手动解决
- NEVER 执行 `git push --force`
- 如果测试失败 → 停止收尾流程，提示修复
