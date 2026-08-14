# 插件与项目配置边界

## 插件维护

- canonical `skills/`：跨项目工作流、OpenSpec 生命周期和框架编码规范的唯一上游。
- Skill references：只承载按需加载的框架差异、模板说明和详细规则。
- 三宿主 manifest：只声明发现路径和市场元数据，不复制 Skill 正文。

## 项目维护

- 当前宿主的项目根指令：项目架构、开发命令、目录、权限、分支和发布约束。
- `openspec/changes/`、`openspec/specs/`：项目实际 SDD 产物。
- `openspec/config.yaml` 与 schema：可由 `zw-sdd-init` 从插件模板安装，但安装后属于项目资产。

项目根指令不得复制整套插件工作流；插件也不得硬编码某个业务项目的容器名、仓库名、凭据或环境地址。
