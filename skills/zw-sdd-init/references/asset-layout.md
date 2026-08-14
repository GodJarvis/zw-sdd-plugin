# OpenSpec 资产分层

`assets/openspec/common/` 保存双框架完全一致的术语表、hotfix schema，以及 ZW workflow 的 proposal/spec 模板。

`assets/openspec/frameworks/hyperf/` 和 `assets/openspec/frameworks/phalcon/` 只保存确有差异的：

- `config.yaml`
- `schemas/zw-workflow/schema.yaml`
- `schemas/zw-workflow/templates/design.md`
- `schemas/zw-workflow/templates/tasks.md`

安装时将 common 与所选 framework 叠加到目标项目的 `openspec/`。新增同类框架差异时放入对应 framework 目录；新增双框架一致资产时只放 common。
