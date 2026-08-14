# Hyperf 路由规则

- `#[AutoController]` 自动路由格式为 `/{prefix}/{methodName}`。
- prefix 默认取命名空间中 `\Controller\` 之后、类名之前的全部层级，并转为 snake_case；显式 `prefix` 参数优先。
- action 使用方法名原文，不做大小写或 snake_case 转换。
- 连续大写字母逐个拆分；数字附着于前一个单词。
- `#[Controller]` 配合 `#[PostMapping]` 或 `#[RequestMapping]` 时，path 参数是最终路径。
- `config/routes.php` 中的显式路由定义优先于自动推导。
