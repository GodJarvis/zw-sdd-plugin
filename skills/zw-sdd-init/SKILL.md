---
name: zw-sdd-init
description: 在 Hyperf 或 Phalcon 项目中初始化、检查、修复 OpenSpec SDD schema 与模板资产。用户提到初始化 SDD、安装 openspec 配置、补齐 schema、检查模板漂移、把 ZW 工作流接入现有项目，或项目缺少 openspec/config.yaml 时使用。
---

# 初始化 ZW SDD

使用随 Skill 提供的确定性脚本组装共享 OpenSpec 资产与框架差异，避免维护两份完整模板。

## 执行

1. 在目标项目根目录识别框架；识别规则见 `using-zw-sdd` 的 `framework-routing.md`。
2. 先检查，不修改：

   ```bash
   python3 <本 Skill 目录>/scripts/install_openspec.py --target . --framework auto --check
   ```

3. 缺少文件时执行安装：

   ```bash
   python3 <本 Skill 目录>/scripts/install_openspec.py --target . --framework auto
   ```

4. 已有文件内容不同时，先展示冲突列表和差异。只有用户明确要求采用插件模板时才加 `--force`。
5. 安装后再次执行 `--check`，并运行项目可用的 OpenSpec 校验命令。

## 约束

- 默认只创建缺失文件；整批预检发现冲突时不写任何文件。
- `--force` 只覆盖本 Skill 清单管理的 OpenSpec 配置与 schema，不删除其它项目文件。
- 不生成或覆盖当前宿主的项目根指令文件；这些文件保存项目自身约束。
- `openspec/changes/` 和 `openspec/specs/` 属于项目数据，脚本永不触碰。

资产分层和受管文件清单见 [asset-layout.md](references/asset-layout.md)。
