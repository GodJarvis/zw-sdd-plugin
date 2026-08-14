---
name: zwflow-verify
description: "桥接层增强验证 — Superpowers verification + OpenSpec 双向反查"
---

触发 Superpowers `verification-before-completion` 原生验证（运行命令出证据），在此基础上追加 OpenSpec 特有的验证项。

**Input**: 当前调用参数（变更名，必填）。如未提供，运行 `openspec list --json` 后向用户展示选项并等待明确选择。

---

## 执行纪律（CRITICAL OVERRIDE）

**逐项强制执行，禁止跳过任何一项。** 每项检查 MUST 按以下模式执行：
1. 运行对应的命令
2. 展示实际命令输出（fresh evidence）
3. 判定结果（✓/✗）并记录到 checklist

未执行命令就标记为通过 = 验证无效。6 项全部执行完毕后方可输出最终报告。

---

## Checklist（MUST 建立进度清单逐项追踪，每项完成后标记为 `completed`）

### ① 测试套件

按 `zwflow-run` Skill 的**测试范围收敛规则**执行变更相关测试（commit diff → 目录映射，不可回退全量）。

- 阈值：0 failures
- 失败 → CRITICAL，停止后续检查

### ② 静态分析

**禁止直接运行 `composer analyse` 全量扫描。** 读取 `references/frameworks/<framework>.md`，按其中的源码范围提取发布基线到 `HEAD` 的变更 PHP 文件，并仅对这些文件运行静态分析。

- 阈值：0 errors
- 失败 → CRITICAL


### ③ Tasks 全勾选

```bash
grep -c '^\- \[ \]' openspec/changes/当前调用参数/tasks.md
```

- 阈值：输出 = 0（或 grep 返回 exit code 1 表示无匹配）
- 失败 → CRITICAL

### ④ Scenario↔Test 双向反查

```bash
# Specs 侧：提取所有 Scenario 名
grep -rh '^#### ' openspec/changes/当前调用参数/specs/ | grep -iE 'Scenario|场景' | sed -E 's/^####\s*(场景（Scenario）|Scenario)[：:]\s*//' | sort > /tmp/spec_scenarios.txt

# Test 侧：提取所有 @scenario 标注
grep -rh '@scenario' test/ | sed -E 's/.*@scenario\s+//' | sort > /tmp/test_scenarios.txt

# 输出两侧内容 + diff
echo "=== Specs 定义的 Scenario ===" && cat /tmp/spec_scenarios.txt
echo "=== Tests 覆盖的 @scenario ===" && cat /tmp/test_scenarios.txt
echo "=== Diff ===" && diff /tmp/spec_scenarios.txt /tmp/test_scenarios.txt
```

- 阈值：diff 输出为空（= 0 行差异）
- **MUST 展示 Specs 侧和 Test 侧的完整列表**，不能只展示 diff 结果
- 失败 → CRITICAL（阻塞归档）

### ⑤ Spec-Code 对齐

逐条核对 specs 中的行为定义与代码实现一致性：

1. 读取 `openspec/changes/当前调用参数/specs/` 中所有 Scenario 的 GIVEN/WHEN/THEN
2. 对每个 Scenario，验证对应代码是否实现了声明的行为（字段名、类型、错误码、响应格式）
3. 输出逐条对照表：

```
| # | Scenario | 实现覆盖？ | 测试覆盖？ | 备注 |
|---|----------|-----------|-----------|------|
| 1 | xxx      | ✓/✗       | ✓/✗       |      |
| 2 | xxx      | ✓/✗       | ✓/✗       |      |
```

- 阈值：全部 ✓
- 失败 → WARNING

### ⑥ 影响半径回归测试

分析本次变更涉及的类/方法，查找直接调用方，确认调用方的测试覆盖情况：

1. 按当前框架 reference 声明的源码根目录获取本次变更的 PHP 文件列表。

2. 对每个变更文件中修改的 public/protected 方法，在当前框架源码根目录查找调用方。

3. 检查调用方是否有对应测试文件存在于 `test/Cases/` 或 `test/Integration/`

4. 输出影响分析表：

```
| # | 变更类/方法 | 直接调用方 | 调用方测试 | 状态 |
|---|------------|-----------|-----------|------|
| 1 | MemberService::getList | OrderService | {框架 reference 映射出的测试文件} | ✓ 已覆盖 |
| 2 | MemberService::getList | ReportController | 无测试文件 | ⚠️ 需补写 |
```

- 阈值：所有调用方均有测试覆盖且运行通过
- 失败 → WARNING（列出缺失测试的调用方，建议补写）

框架源码范围与典型测试映射见 `references/frameworks/<framework>.md`。

---

## 输出验证报告

6 项全部执行完毕后，输出汇总表格：

```
## Verification Report: 当前调用参数

| # | 检查项 | 阈值 | 实际 | 结果 |
|---|--------|------|------|------|
| 1 | 测试套件 | 0 failures | N/N pass | ✓/✗ |
| 2 | 静态分析 | 0 errors | N errors | ✓/✗ |
| 3 | Tasks 全勾选 | 0 unchecked | N/M | ✓/✗ |
| 4 | Scenario↔Test 双向反查 | diff = 0 | diff N lines | ✓/✗ |
| 5 | Spec-Code 对齐 | 全覆盖 | N/M scenarios | ✓/✗ |
| 6 | 影响半径回归 | 调用方全覆盖 | N/M callers covered | ✓/⚠️ |
```

---

## 处理结果

- **全部通过** → 提示执行 `zwflow-rework-analysis` Skill 当前调用参数 返工复盘
- **有 CRITICAL** → 列出问题 + 修复建议，修复后重新执行 `zwflow-verify` Skill
- **仅 WARNING** → 列出问题，询问用户是否接受后提示执行 `zwflow-rework-analysis` Skill 当前调用参数（可跳过）
