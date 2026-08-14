# 分层 Review + Verification + 报告

> 本文档定义 Phase 5（Review & Verification）的完整规则。

---

## 统一流程

**所有路径都执行 Verification，Review 深度按变更范围分层：**

```
Phase 5 入口
├── Verification（所有路径）: 全量测试 + 静态分析
└── Review（深度分层）:
    ├── Level 1（0 业务代码变更）: 测试代码规范性
    ├── Level 2（仅产物/数据变更）: + 产物一致性 + 回归
    └── Level 3（有业务代码修复）: + 修复正确性 + 编码规范
```

---

## 变更范围判定

进入 Phase 5 时，先检查 Phase 4 的修复记录判定变更范围：

| 变更范围 | 触发条件 | Review Level |
|---------|---------|-------------|
| 0 业务代码变更 | 首次全部通过（Phase 4 未执行） | Level 1 |
| 仅产物/数据变更 | Phase 4 仅执行了轨道 A（数据补充）和/或轨道 B（产物修复），无轨道 C | Level 2 |
| 有业务代码修复 | Phase 4 执行了轨道 C（代码修复） | Level 3-Lite 或 Level 3-Full |

**Level 3 细分规则**：

| 子级别 | 条件 | 审查方式 |
|--------|------|---------|
| **Level 3-Lite** | 轨道 C 修复文件数 ≤ 2 个 | 主会话直接审查（不开独立子代理） |
| **Level 3-Full** | 轨道 C 修复文件数 > 2 个 | 独立 review 子代理完整审查 |

Level 3-Lite 审查维度：修复正确性 + 编码规范（同 Level 3-Full）
Level 3-Full 额外维度：回归风险分析（仅子代理执行）

---

## Verification（所有路径 MUST 执行）

### 全量测试

```bash
composer test
```

- 阈值：0 failures（QA 测试 + 已有 TDD 测试全部通过）
- 确保修复未破坏已有功能

### 静态分析

```bash
composer analyse
```

- 阈值：0 errors

---

## Review Level 1 — 简化 Review

**触发**：0 业务代码变更（首次全部通过）

**审查内容**：
- 测试代码规范性检查：`@qa-case` 标注是否完整、基类继承是否正确、方法命名规范
- 测试断言可执行性：无模糊断言（如"返回成功"）、断言是否映射 THAN 要求
- P2 建议记录但不阻塞

**执行方式**：主会话直接审查（无需独立 review 子代理）

---

## Review Level 2 — 中等 Review

**触发**：仅产物/数据变更

**审查内容**：
- Level 1 全部
- 产物一致性：qa-doc.md 用例 ↔ yapi.md 接口契约 ↔ 测试代码断言 三方对齐
- 全量回归验证（已在 Verification 中完成）

**执行方式**：主会话审查产物一致性，Verification 覆盖回归

---

## Review Level 3 — 完整 Review

**触发**：有业务代码修复

### 准备审查上下文

1. QA 用例文档（原始需求）
2. 生成的测试代码（`test/QA/Integration/{ChangeName}/`）
3. 修复 diff（`git diff` 修复相关的变更）
4. 当前宿主根指令文件的“编码护栏”章节
5. 修复 diff 涉及文件路径匹配的所有编码规范 Skill 全文（按当前宿主可见的 Skill 路径作用域解析）

### 启动 Review 子代理

派发独立 review 执行单元，审查维度：

- **修复正确性**：修复代码是否正确解决问题，无副作用
- **编码规范**：修复代码是否符合传入的 skill 规范 + 当前宿主根指令文件的编码护栏
- **回归风险**：修复是否可能影响其他功能

### 处理审查反馈

- **P0/P1**：修复后重跑测试确认通过
- **P2**：记录但不阻塞
- **全部通过 / 仅 P2** → 进入报告输出

---

## 输出测试报告（MUST 写入文件）

报告 MUST 写入 change 目录下，默认文件名 `qa-doc-report.md`：

```
openspec/changes/<name>/qa-doc.md          ← 用例文档
openspec/changes/<name>/qa-doc-report.md   ← 测试报告（自动生成）
```

如用例文档实际命名非 `qa-doc.md`，报告命名为 `{实际文件名}-report.md`。

### 报告模板

```markdown
# QA 测试报告

> **用例文档**: openspec/changes/member-mgmt/qa-doc.md
> **接口文档**: openspec/changes/member-mgmt/yapi.md
> **执行时间**: YYYY-MM-DD HH:mm
> **执行结果**: ✅ 全部通过

> ⚠️ **执行结果字段约束**：该字段值 MUST 基于实际运行结果。禁止填写「⏳ 待 staging 验证」等未经验证结论；若测试未实际运行，报告不得标记为已完成，且不得出现 SKIP/待验证终态（与「所有用例 MUST 最终通过，不存在 SKIP 终态」对齐）。即使确认需 staging 环境，MUST 标注「未执行（原因）」并经用户明确确认，不得绕过 Phase 4 修复循环。

---

## 概览

| 指标 | 数值 |
|------|------|
| 模块数 | 3 |
| 用例总数 | 15 |
| 测试方法数 | 15 |
| ✅ 首次通过 | 12 |
| 🔧 修复后通过 | 2 |
| 🗑️ 移除（用例无效） | 1 |

---

## 执行策略

> 记录实际采用的测试运行方式，取代塞进「已知限制」。

| 运行方式 | 说明 |
|---------|------|
| 全量并发 | 默认方式，所有用例一次性运行 |
| 分批运行 | 连接池/资源超时时切换，每批 3-4 个用例（见 failure-classification.md § 分批运行） |

实际采用：{全量并发 / 分批运行（每批 N 个，共 M 批）}

---

## 初始失败分类汇总

| 分类 | 数量 | 处理方式 |
|------|------|---------|
| 接口文档与实际实现不一致 | 2 | 修复产物（yapi.md + qa-doc.md） |
| 服务端缺少参数校验 | 1 | 修复业务代码 |

---

## 用例执行明细

| 编号 | 用例名 | 模块 | 结果 | 备注 |
|------|--------|------|------|------|
| TC-001 | 创建会员-正常流程 | 会员管理 | ✅ PASS | — |
| TC-002 | 创建会员-手机号重复 | 会员管理 | 🔧 FIXED | 修复: MemberService 缺少唯一性校验 |
| TC-009 | 导出订单-日期范围 | 订单导出 | 🔧 FIXED | 产物修复: yapi.md 补充 date_format 字段说明 |
| TC-012 | 积分查询-已下线接口 | 积分管理 | 🗑️ REMOVED | 接口已废弃，用例移除 |
| TC-013 | 积分扣减-余额不足 | 积分管理 | 🔧 FIXED | 数据补充: 使用真实 zm_id=ZM789012 |

---

## 用例质量反馈

> 即使用例全部通过也 MUST 输出本节（可空表），证明已对 qa-doc.md 做质量回溯。发现的占位符/语义歧义等缺陷反馈回 qa-doc.md 修正（见 repair-loop.md § 轨道 B）。

| TC 编号 | 问题描述 | 修正状态 | 修正 commit |
|---------|---------|---------|------------|
| TC-303 | WHEN 含裸占位符 `[具体任务ID]` | ✅ 已修正为「运行时动态获取」 | — |
| — | 无 | — | — |

---

## 修复记录

### 产物修复

| # | 关联用例 | 不一致点 | 修复内容 |
|---|----------|---------|---------|
| 1 | TC-009 | date_format 为必填但文档未标注 | yapi.md + qa-doc.md 已补充 |

### 代码修复

| # | 关联用例 | 问题描述 | 修复文件 | Commit |
|---|----------|----------|----------|--------|
| 1 | TC-002 | MemberService::create 未校验手机号唯一性 | app/Service/MemberService.php | fix(qa-test): ... |

### 数据补充

| # | 关联用例 | 补充数据 |
|---|----------|---------|
| 1 | TC-013 | zm_id 使用 staging 真实值 ZM789012 |

---

## 验证检查

| # | 检查项 | 阈值 | 实际 | 结果 |
|---|--------|------|------|------|
| 1 | QA 测试全量 | 0 failures | 15/15 pass | ✓ |
| 2 | 全量测试（含回归） | 0 failures | N/N pass | ✓ |
| 3 | 静态分析 | 0 errors | 0 errors | ✓ |

---

## Review 结果

- Review Level: {1/2/3}
- P0/P1 问题：0
- P2 建议：N 条（列出）

---

## 决策纠偏记录（条件触发）

> 仅当执行过程中发生用户介入纠正 AI 决策时 MUST 输出本节；未发生用户纠偏的 QA 运行无需此节。

| AI 原始决策 | 决策依据 | 用户介入点（引用原话） | 纠偏后正确方向 |
|------------|---------|----------------------|--------------|
| 遇认证超时直接进入 mock | 误判外部服务不可达 | 「我提供测试 auth-ID 不就好了，你为什么要做 mock」 | 改用真实 Auth-Id header 走真实 zhangquan 链路 |

---

## 附录：已尝试方案

> 禁止删除已尝试的错误方案记录。最终报告重写时，失败方案过程须移至此处保留（可简化），以支持后续复盘 AI 决策失误根因。

| 已尝试方案 | 结果 | 失败原因 |
|-----------|------|---------|
| （如本次的 5 种 mock 失败方案表，简化保留） | — | — |

---

## 结构化数据

> 以下数据供自动化聚合分析使用，不影响报告正文阅读。

```json
{
  "change": "member-mgmt",
  "executed_at": "2026-06-27T15:30:00+08:00",
  "result": "pass",
  "summary": {
    "total_cases": 15,
    "first_pass": 12,
    "fixed": 2,
    "removed": 1
  },
  "failure_categories": [
    {"name": "接口文档与实际实现不一致", "count": 2},
    {"name": "服务端缺少参数校验", "count": 1}
  ],
  "fixes": {
    "artifact_fixes": 1,
    "code_fixes": 1,
    "data_supplements": 0
  },
  "review_level": 3,
  "review_p0p1_count": 0
}
```
```

### 结构化数据字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `change` | string | change 目录名 |
| `executed_at` | string | ISO 8601 带时区时间戳 |
| `result` | string | `pass`（全部通过）/ `partial`（有移除）/ 其他 |
| `summary.total_cases` | int | 用例总数 |
| `summary.first_pass` | int | 首次运行通过的用例数 |
| `summary.fixed` | int | 修复后通过的用例数 |
| `summary.removed` | int | 经确认移除的用例数 |
| `failure_categories[].name` | string | 失败分类名称（动态中文标签） |
| `failure_categories[].count` | int | 该分类的失败用例数 |
| `fixes.artifact_fixes` | int | 产物修复次数 |
| `fixes.code_fixes` | int | 代码修复次数 |
| `fixes.data_supplements` | int | 数据补充次数 |
| `review_level` | int | Review 深度（1/2/3） |
| `review_p0p1_count` | int | Review 发现的 P0+P1 问题数 |

### 跨 change 聚合分析用法

```bash
# 提取所有 change 的 JSON 数据
find openspec/changes/ -name "qa-doc-report.md" -type f | sort | while read f; do
  # 提取文件底部最后的 JSON 代码块
  awk '/^```json$/,/^```$/' "$f" | tail -n +2 | head -n -1
done
```

```php
// AI 做跨 change 分析时的伪代码逻辑
$reports = glob('openspec/changes/*/qa-doc-report.md');
$stats = [];
foreach ($reports as $file) {
    $content = file_get_contents($file);
    // 提取最后一个 JSON 代码块
    preg_match('/```json\n(.*?)\n```/s', $content, $m);
    $stats[] = json_decode($m[1], true);
}
// 聚合：按 failure_categories[].name 汇总
// 聚合：计算平均首次通过率
```

---

## 完成提示

全部完成后向用户输出摘要：

- QA 测试报告已写入 `openspec/changes/<name>/qa-doc-report.md`
- 所有用例已通过（首次通过 N + 修复后通过 M）
- 修复内容：产物修复 X 处 + 代码修复 Y 处 + 数据补充 Z 处
- Review Level + 审查结果
- 修复代码已 commit（如有），已通过 Review + 全量回归
