---
name: using-zw-sdd
description: 统一入口与跨宿主动作契约。处理 OpenSpec、SDD、ZWFlow、需求澄清、方案设计、变更实现、QA、验证、归档，或需要在 Hyperf 与 Phalcon 项目中选择正确工作流和编码规范时使用。即使用户只提到 propose、apply、verify、finish、YApi、部署文档或测试用例，也应先加载本 Skill 完成框架识别和逻辑 Skill 路由。
---

# 使用 ZW SDD

先识别项目框架，再调用最小必要的逻辑 Skill。正文只描述动作，不假设某个宿主存在特定工具。

## 启动顺序

1. 按 [framework-routing.md](references/framework-routing.md) 识别 `hyperf` 或 `phalcon`。无法可靠识别时，提出一个简短问题并等待用户明确选择。
2. 若项目缺少 `openspec/config.yaml` 或所需 schema，调用 `zw-sdd-init` 检查或安装；不得静默覆盖已有文件。
3. 根据请求调用对应的 `openspec-*`、`zwflow-*` 或框架编码规范 Skill。必须加载完整 Skill，不得只凭名称猜测流程。
4. 修改代码前，根据文件路径与任务领域加载所有命中的框架编码规范 Skill；同一文件命中多项时全部生效。
5. 按 [action-contract.md](references/action-contract.md) 保留交互、进度、独立审查和文件操作语义。

## 路由原则

- OpenSpec 原生生命周期由 `openspec-*` Skills 处理。
- 项目增强编排、PRD、实现、QA、评审、部署和收尾由 `zwflow-*` Skills 处理。
- Hyperf 代码加载 `hyperf-*` Skills；Phalcon 代码加载 `phalcon-*` Skills。
- StarRocks 建表加载 `starrocks-ddl`，与 PHP 框架无关。
- 同名工作流 Skill 只有一份正文。遇框架差异时，先读取该 Skill 指向的框架 reference，再继续执行。

## 项目边界

插件负责可复用工作流与框架规范，不取代当前宿主发现的项目根指令。具体项目的架构、命令、路径、权限和发布约束继续由项目根指令维护；详见 [project-boundaries.md](references/project-boundaries.md)。

完成前验证实际产物和命令结果。宿主能力缺失时按动作契约降级，不得伪造已执行、已审查或已通过。
