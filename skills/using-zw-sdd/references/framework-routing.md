# 框架识别与 Skill 路由

按证据优先级识别框架，不根据仓库名或用户习惯猜测。

## Hyperf

任一强证据即可确认：

- `composer.json` 依赖包含 `hyperf/` 包。
- 存在 `bin/hyperf.php`。
- 同时存在 `app/` 与 `config/autoload/`，且代码使用 Hyperf 命名空间或注解/Attribute。

加载与任务领域匹配的 `hyperf-*` Skills。

## Phalcon

任一强证据即可确认：

- `composer.json` 声明 Phalcon 扩展或相关包。
- 存在 `run/cli.php`。
- 同时存在 `apps/` 与 `library/`，且控制器继承项目 Phalcon 基类。

加载与任务领域匹配的 `phalcon-*` Skills。

## 冲突与未知

- 两类强证据同时出现：列出证据并询问当前变更所属框架。
- 只有弱目录特征：读取入口文件或 `composer.json` 后再判断。
- 仍无法确认：一次只问一个问题，不得同时加载互斥的框架规则后自行折中。
