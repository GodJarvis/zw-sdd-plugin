# ZW SDD Plugin

ZW SDD Plugin 把 Hyperf 与 Phalcon 两套配置模板中的可复用能力收敛成一份 canonical `skills/`，供 Claude Code、Codex 与 Cursor 共同加载。宿主目录只保留清单和市场元数据，不复制 skill 正文。

当前版本：`0.1.0`

## 核心设计

```text
一份 skills/
├── using-zw-sdd             # 统一入口与框架路由
├── zw-sdd-init              # OpenSpec 资产安装/审计
├── openspec-*               # OpenSpec 原生工作流
├── zwflow-*                 # ZWFlow 编排层
├── hyperf-* / phalcon-*     # 框架工程规范
└── starrocks-ddl            # 数据库专项规范

三份薄清单
├── .claude-plugin/
├── .codex-plugin/ + .agents/plugins/
└── .cursor-plugin/
```

工作流正文描述“询问用户、维护计划、委派独立任务”等动作语义，不绑定某个宿主的工具名。真正有差异的内容分两类处理：

- 宿主差异：由各宿主运行时把动作语义映射到自身能力。
- 框架差异：放在 skill 内的 `references/frameworks/hyperf.md` 与 `phalcon.md`，主流程按项目事实选择。

## 能力范围

插件共包含 46 个 skills：

| 分组 | 数量 | 说明 |
|---|---:|---|
| 统一入口与初始化 | 2 | 框架识别、能力路由、OpenSpec 资产安装与漂移审计 |
| OpenSpec | 11 | explore、propose、apply、verify、archive 等原生流程 |
| ZWFlow | 14 | 编排、调试、评审、验证、QA、YApi、上线文档与收尾 |
| Hyperf 工程规范 | 9 | Controller、Service、Database、Redis、Queue、Validation、Test 等 |
| Phalcon 工程规范 | 9 | Controller、Service、Database、Redis、Queue、CLI Task、Test 等 |
| StarRocks | 1 | DDL 生成规范 |

## 前置依赖

- 项目使用 Hyperf 或 Phalcon，并由 `composer.json` 或约定目录提供可识别的框架事实。
- 使用 OpenSpec 流程时，本机需可执行 `openspec` CLI。
- `zwflow-run`、`zwflow-apply`、`zwflow-debug`、`zwflow-review`、`zwflow-verify` 与 `zwflow-finish` 会调用 Superpowers 的工程纪律 skills；需要这些桥接能力时，应在当前宿主中另行安装 Superpowers。ZW SDD 不复制第三方插件内容。

## 安装

### Claude Code

在 Claude Code 中执行：

```text
/plugin marketplace add https://github.com/GodJarvis/zw-sdd-plugin.git
/plugin install zw-sdd-plugin@zw-sdd-marketplace
/reload-plugins
```

### Codex

```bash
codex plugin marketplace add https://github.com/GodJarvis/zw-sdd-plugin.git
codex plugin add zw-sdd-plugin@zw-sdd-marketplace
codex plugin list
```

### Cursor

在 Cursor 中打开 Plugins & Marketplace，使用 `/add-plugin` 添加仓库：

```text
https://github.com/GodJarvis/zw-sdd-plugin.git
```

私有仓库需要当前 Git 环境已经具备访问凭据。

## 使用

安装后优先调用统一入口：

```text
使用 using-zw-sdd 初始化当前项目
使用 using-zw-sdd 为当前 change 执行 ZWFlow
使用 zw-sdd-init --check 审计 OpenSpec 资产
```

`zw-sdd-init` 安装器也可以直接运行：

```bash
python3 skills/zw-sdd-init/scripts/install_openspec.py --target /path/to/project --dry-run
python3 skills/zw-sdd-init/scripts/install_openspec.py --target /path/to/project
python3 skills/zw-sdd-init/scripts/install_openspec.py --target /path/to/project --check
```

安装器先完成全量预检。默认遇到已有文件冲突时不写入任何文件；只有显式传入 `--force` 才覆盖受管资产。

## 项目根指令边界

插件不会把两套模板的完整 `CLAUDE.md` 或 `AGENTS.md` 打包三份：

- 可复用的工作流纪律由 `using-zw-sdd` 和对应 skills 提供。
- 目标项目的架构边界、命令、权限、仓库策略与业务约束继续保留在项目根指令文件中。
- OpenSpec schema 与模板由 `zw-sdd-init` 按 common + framework overlay 安装。

因此，同一插件可以跨项目复用，同时不会把 Hyperf 的项目根约束错误注入 Phalcon 项目，反之亦然。

## 开发与审计

```bash
python3 scripts/audit_plugin.py
python3 -m py_compile scripts/audit_plugin.py skills/zw-sdd-init/scripts/install_openspec.py
claude plugin validate . --strict
```

发版时必须同步更新三份 `plugin.json`、`CHANGELOG.md`，然后运行审计，创建并推送 `vX.Y.Z` tag；GitHub Actions 会依据对应 Changelog 条目自动创建 Release。

完整发布、安装、更新与市场维护手册见管理工作区的 `doc/zw-sdd-plugin-marketplace-guide.md`。

## License

[MIT](LICENSE)
