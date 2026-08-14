---
name: zwflow-qa-test
description: "QA 用例驱动测试 — 解析测试用例文档 → 生成集成测试 → 运行 & 分类 → 多轨修复至全部通过 → Review → Verify。触发：`zwflow-qa-test` Skill、`qa-test`、`运行QA测试`。"
---

# QA 集成测试执行专家

开始执行前先识别当前项目框架，并读取 `references/frameworks/<framework>.md`。测试规范 skill、鉴权术语、环境配置位置、运行命令、命名空间和受保护配置范围均以该引用为准。

## 触发

- `zwflow-qa-test` Skill [change_name]
- 自然语言提到 "qa-test" / "运行 QA 测试" / "执行 QA 用例"

## 工作流

### Phase 1: 解析用例文档

详见 `references/test-code-generation.md` § 解析规则。

1. 定位 `qa-doc.md`（指定 change_name → 验证存在；未指定 → 扫描 `openspec/changes/` 含 `qa-doc.md` 的 change，向用户展示选项并等待明确选择）
2. 解析 GIVEN/WHEN/THEN 格式（**仅支持标准格式 A**，表格格式 B 不再支持）
3. 输出解析摘要（模块数 + 用例总数 + 模块明细）
4. 获得用户明确确认后进入 Phase 2

### Phase 2: 生成测试代码

详见 `references/test-code-generation.md` § 代码生成 + § DataFactory 模式。

- 加载框架引用指定的测试编码规范 skill
- **鉴权配置（MUST）**：解析 qa-doc.md 公共约定中的鉴权类型：
  - 框架会话鉴权 → 使用框架引用指定的默认测试用户注入方式，无需询问
  - `Auth-Id` → 询问用户「请提供测试环境可用的 Auth-Id（掌权用户 UID）」→ 写入测试常量 `TEST_AUTH_ID`
  - `None` → 无需鉴权，跳过
- 按模块生成测试文件到 `test/QA/Integration/{ChangeName}/{ModuleName}/`
- **数据准备**：AI 先一次性探索填充 EntityRegistry/SideEffectMap/SchemaRegistry，随后调用 DataFactory 模式生成测试代码
- 生成完成后展示文件清单，确认后进入 Phase 3

### Phase 2.5: 环境预检（运行测试前 MUST 执行）

详见 `references/failure-classification.md` § 环境预检。

运行测试前 MUST 完成以下轻量预检（只检查、不修改框架引用定义的核心配置，遵守当前项目根指令中的配置变更护栏）。任一项失败则暂停，列出问题清单等用户确认补齐方式后再进入 Phase 3：

1. **环境文件存在性**：框架引用指定的当前环境文件存在；缺失则 MUST 暂停并询问用户，禁止从其他环境文件静默创建或复制
2. **关键 HOST 配置**：从框架引用指定的配置源检查认证与数据依赖的外部服务 HOST，确认没有使用默认回落值
3. **外部服务连通性**：容器内 curl 认证/数据依赖的外部服务（如 zhangquan）健康端点
4. **DB 连通性**：涉及 DB（PG/MySQL/Hologres）的 TCP+握手测试
5. **冒烟测试**：运行任一已存在 HTTP 集成测试（如 ExampleIntegrationTest）验证测试框架+中间件链端到端可用——能立即暴露“所有 HTTP 测试均挂起”的链路级故障

### Phase 3: 运行测试 & 失败分类

详见 `references/failure-classification.md`。

- 运行 QA 测试套件
- 全绿 → 直接进入 Phase 5（Level 1 简化 Review）
- 有失败 → 根因分析 + 动态中文分类标签 → 展示分类结果 → 确认开始修复

### Phase 4: 多轨修复循环

详见 `references/repair-loop.md`。

- **并行三轨道启动**：数据补充（等用户）∥ 产物修复 ∥ 代码修复
- 每条轨道独立推进，汇合点全量回归
- 退出条件：所有 TC 全部 PASS（无 SKIP 终态）

### Phase 5: Review & Verification

详见 `references/review-verify.md`。

- 所有路径 → Verification（全量测试 + 静态分析）
- Review 深度按变更范围分层：
  - Level 1（0 业务代码变更）→ 测试代码规范性检查
  - Level 2（仅产物/数据变更）→ + 产物一致性 + 回归
  - Level 3（有代码修复）→ + 修复正确性 + 编码规范 + 回归风险
- 输出测试报告 `qa-doc-report.md`

## 框架配置

测试运行命令、全量测试命令、静态分析命令、测试基类、QA 命名空间、编码规范 skill 和 DataFactory trait 命名空间统一从 `references/frameworks/<framework>.md` 读取，禁止在主流程中自行推断。

## 默认行为

- 内部接口默认跳过鉴权类用例（同 qa-doc-gen 约定）
- 每个 TC MUST 生成独立测试方法，PHPDoc 标注 `@qa-case TC-NNN` 和 `@title 用例名`
- 不存在 SKIP 终态 — 所有用例最终必须通过
- 失败分类使用动态中文标签，不使用固定编码（ABCD）
- Review 子代理 MUST 独立（不复用当前会话）
- **用户回答超时处理纪律**：超时后禁止自主选择降级/绕过策略，MUST 重新提出同一问题（最多重试 2 次），仍无响应则暂停流程等待用户显式指令，不得写任何“待验证”类结论或绕过 Phase 4 修复循环

## 子文档索引

按需加载：

- `references/test-code-generation.md` — **Phase 1-2：解析规则 + 测试代码生成模板 + DataFactory 模式**
- `references/failure-classification.md` — **Phase 3：失败根因分类规则与动态中文标签**
- `references/repair-loop.md` — **Phase 4：并行多轨修复循环 + 汇合点模型**
- `references/review-verify.md` — **Phase 5：分层 Review + Verification + 报告模板**

## 错误处理

| 场景 | 处理 |
|------|------|
| change 下无 `qa-doc.md` | 报错，提示先执行 `zwflow-qa-doc-gen` Skill |
| 用例描述的接口不存在 | 暂停，提示用户确认（可能尚未开发） |
| 用例描述模糊无法确定参数 | 先探索 codebase，仍不明确则暂停询问用户 |
| 同一测试连续 3 次 FAIL | 自动触发 `zwflow-debug` Skill 系统化调试 |
| 用例本身无效 | 经用户确认后删除测试方法 + 从 qa-doc.md 移除 → 报告标记 🗑️ REMOVED |
