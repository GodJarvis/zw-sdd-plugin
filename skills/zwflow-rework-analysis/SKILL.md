---
name: zwflow-rework-analysis
description: "为 OpenSpec change 的代码生成后质量进行复盘分析。通过对比 apply 阶段（AI 首版生成）与后续修补 commit，量化代码准确率，分类问题根因（业务逻辑 vs 工作流缺口），识别哪些问题可以通过优化 SDD 工作流规范来预防。当用户提到\"复盘分析\"、\"代码质量分析\"、\"post review\"、\"评审后分析\"、\"生成质量报告\"、\"apply后分析\"、\"代码准确率\"、\"返工分析\"时触发。即使用户只是说\"分析下这个 change 的返工情况\"、\"看看首版代码质量怎么样\"、\"这个change改了多少次\"也应触发。"
---

# OpenSpec 代码生成质量复盘分析

通过对比 apply 阶段（AI 首版代码生成）与后续修补 commit 的差异，量化首版代码准确率，将返工原因分类为「业务逻辑问题」和「工作流问题」，从中提炼可落地的 SDD 规范优化建议。

**核心价值**：每次 change 的返工数据都是工作流改进的信号源——业务问题无法通过流程消除，但工作流问题（spec 精度不足、design 蓝图缺失、编码规范违反）可以通过规范迭代系统性预防。

## 触发方式

- `zwflow-rework-analysis` Skill feat-xxx — 分析指定 change
- `zwflow-rework-analysis` Skill — 不指定时，列出可分析的 change 让用户选择

## 执行流程

### 1. 确定目标 change

**指定了 change 名称时：**
- 确认该 change 存在 apply 阶段的 commit 记录（通过 `git log --grep="\[change: <name>"` 搜索）
- 如果找到 → 继续
- 如果未找到 → 提示用户该 change 可能未走标准 apply 流程，让用户手动指定分析窗口

**未指定 change 名称时：**
- 通过 `git log --oneline --grep="\[change:"` 提取所有走过 apply 流程的 change 名称
- 向用户展示选项并等待明确选择

### 2. 定位分析窗口

分析窗口由两个边界确定：

**Apply 结束点（首版代码生成完成）：**
```bash
# 找到该 change 的最后一个 apply commit
git log --oneline --grep="\[change: <name>, task:" --format="%H %s" | head -1
```

**分析终点（返工结束）：**

按以下优先级确定：
1. 归档 commit：`git log --oneline --grep="archive.*<name>\|归档.*<name>"`
2. 用户指定的 commit hash
3. 如果以上都没有，向用户展示选项并等待明确选择：使用 HEAD / 手动指定 commit

**Apply 起点（用于统计首版规模）：**
```bash
# 找到该 change 的第一个 apply commit
git log --oneline --grep="\[change: <name>, task:" --format="%H %s" | tail -1
```

确认后输出："分析窗口已确定：Apply 阶段 <first>..<last>（N 个 commit），返工阶段 <last>..<end>（N 个 commit）"

### 3. 采集数据

#### 3a. Apply 阶段数据

```bash
# Apply 阶段的 commit 列表和统计
git log --oneline <apply_first>^..<apply_last> --grep="\[change: <name>" --stat
# Apply 阶段的总新增/删除行数
git diff --stat <apply_first>^..<apply_last>
```

#### 3b. 返工阶段数据

```bash
# 返工阶段的所有 commit（不限于带 change 标记的）
git log --oneline <apply_last>..<end_point> --format="%H|%s|%ai"
# 每个 commit 的 diff 统计
git diff --stat <commit>^..<commit>
```

对每个返工 commit 记录：
- commit hash（短）
- commit message
- 日期
- 变更文件列表
- 新增/删除行数
- commit 性质初判（基于 message 前缀：feat/fix/refactor/docs/chore/style）

#### 3c. 读取 change 产物（用于分类判定的上下文）

读取以下文件（如存在）：
- `openspec/changes/<name>/specs/` — 行为规范
- `openspec/changes/<name>/design.md` — 技术设计
- `openspec/changes/<name>/tasks.md` — 任务清单
- `openspec/changes/<name>/yapi.md` — 接口文档

### 4. 分类分析

对每个返工 commit 执行分类判定。判定依据是 **diff 内容 + 产物对照**，不是 commit message（message 可能不准确）。

#### 问题分类体系

| 大类 | 子类 | 判定标准 |
|------|------|----------|
| 业务逻辑问题 | 需求理解偏差 | diff 修改的逻辑在 spec 中有明确定义，但首版实现与 spec 不符 |
| 业务逻辑问题 | 需求遗漏 | diff 新增的功能/场景在 spec 中未定义，属于联调/测试时补充的需求 |
| 业务逻辑问题 | 数据源/字段错误 | diff 修改了数据获取方式（换 Service/换 Model/换字段来源） |
| 工作流问题 | spec 精度不足 | spec 有相关描述但未声明关键细节（如精度策略、权威态来源、枚举值范围），导致实现歧义 |
| 工作流问题 | design 蓝图缺失 | design 遗漏了该组件的关键决策（如缓存失效时机、基础设施能力确认、跨模块同步） |
| 工作流问题 | 接口契约缺漏 | diff 修改了接口返回结构/新增字段，yapi.md 中未覆盖 |
| 工作流问题 | 编码规范违反 | diff 修复的问题属于现有 skill 已明确禁止的模式（如 intval 精度丢失、Service 返回信封） |
| 环境/配置问题 | 配置调整 | diff 仅修改常量值/配置项/默认参数，不涉及逻辑变更 |
| 环境/配置问题 | 表结构补漏 | diff 包含 ALTER TABLE / 新字段 / 新索引的追加 |

#### 分类判定流程

对每个返工 commit：

1. 读取 diff 内容（`git show <hash> --stat` + 关键文件的 `git show <hash> -- <file>`）
2. 如果 diff 过大（单 commit 变更 >500 行），只读 stat + 关键文件的核心片段，概括性判定
3. 对照 spec/design 产物，确定问题归属：
   - diff 修改内容 spec 有明确定义 → 业务逻辑-需求理解偏差
   - diff 新增内容 spec 完全未提及 → 业务逻辑-需求遗漏
   - diff 修改数据获取链路 → 业务逻辑-数据源错误
   - diff 修改内容 spec 有但含糊 → 工作流-spec 精度不足
   - diff 补充 design 遗漏的同步/缓存/复用逻辑 → 工作流-design 蓝图缺失
   - diff 修改接口字段/结构 → 工作流-接口契约缺漏
   - diff 修复的模式在现有 skill 中已有禁止规则 → 工作流-编码规范违反
   - diff 仅改常量/配置数值 → 环境-配置调整
   - diff 是 DDL 追加 → 环境-表结构补漏
4. 无法确定时标记为「⚠️ 待人工判定」，给出最接近的两个候选分类

### 5. 量化统计

| 指标 | 公式 |
|------|------|
| 行数级保留率 | `(apply_additions - rework_deletions) / apply_additions × 100%` |
| Commit 一次通过率 | `apply_commits / (apply_commits + rework_commits) × 100%` |
| 工作流可优化比例 | `workflow_issue_commits / total_rework_commits × 100%` |
| 各分类占比 | `category_commits / total_rework_commits × 100%` |

注意：
- `rework_deletions` 只统计对 apply 阶段文件的删除行（非新文件的删除）
- 行数级保留率偏乐观（无法反映同一行被多次修改的成本），报告中标注此局限

### 6. 生成报告

**输出路径判定：**
- change 目录仍存在 → 输出到 `openspec/changes/<name>/rework-analysis.md`
- change 已归档 → 输出到 `openspec/archive/<name>/rework-analysis.md`（如 archive 目录也不存在则询问用户）

**报告结构：**

```markdown
# <Change 名称> 代码生成质量分析报告

> 分析时间：YYYY-MM-DD
> Apply 窗口：<first_hash>..<last_hash>（N 个 commit）
> 返工窗口：<last_hash>..<end_hash>（N 个 commit）

---

## 1. 量化概览

| 指标 | 数值 | 解读 |
|------|------|------|
| Apply 阶段 commit 数 | N | — |
| 返工 commit 数 | N | — |
| Commit 一次通过率 | X% | apply/(apply+返工) |
| Apply 新增行数 | +N 行 | — |
| 返工修改行数 | +N/-N 行 | — |
| 行数级保留率 | X% | 偏乐观，无法反映同行多次改写 |

---

## 2. 问题分类明细

### 业务逻辑问题（N 个 commit，占比 X%）

| Commit | 子类 | 摘要 | 涉及文件 |
|--------|------|------|----------|
| `hash` | 子类名 | 一句话描述修改内容和原因 | file1, file2 |

### 工作流问题（N 个 commit，占比 X%）

| Commit | 子类 | 摘要 | 可优化方向 |
|--------|------|------|-----------|
| `hash` | 子类名 | 一句话描述 | 具体规范优化建议 |

### 环境/配置问题（N 个 commit，占比 X%）

| Commit | 子类 | 摘要 |
|--------|------|------|
| `hash` | 子类名 | 一句话描述 |

### 待人工判定（N 个 commit）

| Commit | 摘要 | 候选分类 |
|--------|------|----------|
| `hash` | 一句话描述 | A 或 B |

---

## 3. 工作流优化建议

> 本节仅基于「工作流问题」类 commit 的共性模式提炼，不含业务逻辑问题。

| 优先级 | 问题模式 | 出现次数 | 建议优化位置 | 具体建议 |
|--------|---------|---------|-------------|---------|
| P0/P1/P2 | 模式名称 | N 次 | config.yaml rules / skill / 根指令文件 | 一句话规则建议 |

**优先级判定标准：**
- P0：出现 ≥3 次，或涉及资损/安全风险
- P1：出现 2 次，或涉及联调阻塞
- P2：出现 1 次，影响面较小

---

## 4. 高强度修复时段

| 日期 | Commit 数 | 集中问题 | 触发原因推测 |
|------|----------|---------|-------------|
| YYYY-MM-DD | N | 问题类型 | 联调首日 / 测试反馈 / 评审返工 |

---

## 5. 结论

- **核心结论**：一句话概括
- **首版质量评价**：常规功能一次通过率 vs 高风险点一次通过率
- **工作流可优化比例**：X%（N/M 个返工 commit 可通过规范优化预防）
- **Top 优化建议**：按优先级列出前 3 条
```

### 7. 完成提示

输出摘要：
- Commit 一次通过率：X%
- 工作流可优化比例：X%（N 个 commit 可预防）
- Top 3 优化建议（一行一条）
- 报告路径
- 提示："报告仅为分析产物，如需将优化建议落地到规范中，请手动评估后修改对应文件"
- 按发布场景提示：版本上线时执行 `zwflow-deploy-doc-gen` Skill 生成上线文档；非版本上线时执行 `openspec-archive-change` Skill <change-name> 归档。

## 护栏

- **判定基于 diff 内容**：分类必须读 diff + 对照产物，禁止仅凭 commit message 推测
- **不强行归类**：无法确定的标记「待人工判定」+ 候选分类
- **只分析不修改**：报告是分析产物，不自动修改任何规范文件（config.yaml / skill / 根指令文件）
- **零返工短路**：返工 commit 数为 0 时，告知用户"首版代码无返工记录，无需深度分析"，不生成深度报告，但仍按完成提示给出下一步
- **大 diff 降级**：单 commit 变更 >500 行时，只读 stat + 核心文件片段，概括性分类
- **产物缺失降级**：如果 spec/design 产物不存在（已归档删除），仅基于 diff 内容分类，在报告中标注"产物已归档，分类基于 diff 推断"
