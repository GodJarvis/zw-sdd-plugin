# 插件架构与维护边界

## Canonical 原则

`skills/` 是唯一技能上游。禁止把同一 skill 复制到 `.claude/skills/`、`.agents/skills/`、`.codex/skills/` 或 `.cursor/skills/` 后分别维护。

三宿主清单只承担发现与分发：

- Claude Code：`.claude-plugin/plugin.json`
- Codex：`.codex-plugin/plugin.json` 与 `.agents/plugins/marketplace.json`
- Cursor：`.cursor-plugin/plugin.json`

## 三层内容边界

| 层 | 放置内容 | 不应放置 |
|---|---|---|
| canonical skill | 跨宿主动作语义、共享工作流、框架工程规范 | 宿主工具名、宿主配置路径 |
| framework reference | 测试命令、源码范围、路由规则、配置目录等框架事实 | 完整复制的工作流正文 |
| project root instructions | 目标仓库架构、权限、命令、发布策略、业务红线 | 插件维护流程、另一框架的约束 |

## OpenSpec 资产分层

`zw-sdd-init/assets/openspec/common/` 只存两个框架完全相同的文件；`frameworks/hyperf/` 和 `frameworks/phalcon/` 只存不同的配置、schema 与模板。安装器在内存中合并 common 与 framework overlay 后再执行预检和写入。

## 新增框架

新增同类框架时，应：

1. 增加框架识别事实与 `using-zw-sdd` 路由说明。
2. 为需要差异的工作流新增 `references/frameworks/<framework>.md`。
3. 在 `zw-sdd-init/assets/openspec/frameworks/<framework>/` 增加 overlay。
4. 更新安装器允许的框架值与审计断言。

如果新增框架需要复制任一完整 ZWFlow skill，说明差异层仍未抽象到位。
