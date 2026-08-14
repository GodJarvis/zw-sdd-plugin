# ZW SDD Plugin 0.1.0 审计报告

审计日期：2026-07-15

## 结论

通过。插件已经形成一份 canonical `skills/` 与三宿主薄清单；工作流正文没有绑定宿主工具名，Hyperf/Phalcon 差异已下沉为框架 skill 或 `references/frameworks/`，OpenSpec 资产可由确定性安装器按 common + framework overlay 还原。

## 与 Superpowers 去平台化原理的对照

| 原理 | ZW SDD 落地 |
|---|---|
| 一份技能上游 | 46 个 skills 只存在于根 `skills/` |
| 正文描述动作语义 | 询问、计划、独立执行、验证均使用语义契约，不引用宿主工具名 |
| 宿主只负责发现 | Claude Code、Codex、Cursor 目录仅包含 manifest/marketplace |
| 差异按需加载 | 6 个双框架工作流以 `references/frameworks/hyperf.md` 和 `phalcon.md` 承载差异 |
| 项目配置不混入插件 | 项目架构、权限、命令和仓库治理继续由目标项目根指令维护 |

显式映射并非所有动作的必要条件。宿主已原生理解的通用动作由运行时选择等价能力；只有插件发现路径、市场格式、框架事实和缺失能力的降级边界需要显式声明。

## 资产完整性

- 原双模板 skill 并集与插件清单一致：排除旧 `claude-config-sync`，新增 `using-zw-sdd` 与 `zw-sdd-init`。
- 20 个未发生框架差异的共享 skills 与原上游逐文件一致。
- 9 个 Hyperf skills 与 Hyperf 模板逐文件一致。
- 9 个 Phalcon skills 与 Phalcon 模板逐文件一致。
- 6 个存在差异的 ZWFlow skills 已合并为共享正文 + 双框架引用。
- 总数：46 个 canonical skills，无重复 name，目录名与 frontmatter name 一致。

## 去平台化扫描

canonical skills 中以下宿主绑定项均为 0：

- 结构化提问、计划、任务、子智能体等宿主专属工具名。
- `.claude/`、`.agents/`、`.codex/`、`.cursor/` 宿主配置路径。
- 6 个合并工作流正文中的 Hyperf/Phalcon 专属命令、命名空间和配置目录。

## OpenSpec 安装验证

| 验证 | 结果 |
|---|---|
| common + hyperf overlay 安装 | 与原 Hyperf `openspec/` 逐文件一致 |
| common + phalcon overlay 安装 | 与原 Phalcon `openspec/` 逐文件一致 |
| 安装后 `--check` | 两框架均返回无漂移 |
| 冲突原子性 | 返回退出码 2，未创建其它受管文件 |
| 默认覆盖策略 | 发现内容冲突时停止；只有 `--force` 才覆盖 |

## 宿主验证

| 宿主/检查器 | 结果 |
|---|---|
| Codex plugin validator | 通过 |
| 46 个 skill quick validator | 46/46 通过 |
| Claude `plugin validate --strict` | plugin 与 marketplace 均通过 |
| Codex 隔离 HOME 市场安装 | 市场发现、available 列表、安装、启用均通过 |
| Claude 隔离配置目录安装 | 市场添加、插件安装、启用均通过 |
| Cursor 官方 plugin schema | 通过 |
| Cursor 官方 marketplace schema | 通过 |
| Python 编译 | 审计脚本与 OpenSpec 安装器均通过 |
| `git diff --check` | 通过 |

## 保留边界

- ZWFlow 中调用 Superpowers 工程纪律的桥接 skills 仍要求宿主另行安装 Superpowers；本插件不复制第三方插件。
- 插件不分发完整项目根指令文件，目标业务项目仍需维护自身架构、权限、命令与发布约束。
- 当前 GitHub 公共仓库可用于团队市场与公开安装；进入三家官方公共市场前仍需公开法律/支持页面和平台审核。
