---
name: phalcon-validation
description: "创建或修改请求参数验证器。涉及 apps/*/validation/ 下的 XxxValidation 类、Phalcon\\Validation 规则、必填/格式/数值验证时使用。Use when working with files matching: apps/**/validation/**/*.php."
---

# Phalcon 验证器规范

## 触发机制

验证器**完全由框架自动触发**，不需要在 Controller 里手动调用。

```
请求 /admin/member/index
  → AppBaseController::initialize() 自动调用 validate()
  → 解析为 Apps\Admin\Validation\MemberValidation::index()
  → 失败 → returnJson(STATUS_INVALIDATE, ...) 并中断
  → 通过 → 继续执行 Controller Action
```

## 命名映射

| 规则 | 示例 |
|------|------|
| 路径 | `apps/<module>/validation/<Controller>Validation.php` |
| 命名空间 | `Apps\<Module>\Validation` |
| 类名 | `<Controller>Validation extends \Phalcon\Validation` |
| 方法名 | 与 Action 对应但**去掉 Action 后缀**（`indexAction` → `index()`）|

## 标准模板

```php
<?php

namespace Apps\Admin\Validation;

use Phalcon\Validation;
use Phalcon\Validation\Validator\PresenceOf;
use Phalcon\Validation\Validator\Email;
use Phalcon\Validation\Validator\Numericality;
use Phalcon\Validation\Validator\StringLength;
use Phalcon\Validation\Validator\InclusionIn;

class MemberValidation extends Validation
{
    public function index()
    {
        $this->add('status', new InclusionIn([
            'domain' => [0, 1, -1],
            'message' => 'status 值不合法',
            'allowEmpty' => true,
        ]));
    }

    public function detail()
    {
        $this->add('id', new PresenceOf([
            'message' => 'id 是必填项',
        ]));
        $this->add('id', new Numericality([
            'message' => 'id 必须是数字',
        ]));
    }

    public function create()
    {
        $this->add('name', new PresenceOf(['message' => '姓名必填']));
        $this->add('name', new StringLength([
            'min' => 2,
            'max' => 32,
            'messageMinimum' => '姓名至少 2 个字符',
            'messageMaximum' => '姓名不超过 32 个字符',
        ]));
        $this->add('email', new Email(['message' => '邮箱格式不正确']));
    }
}
```

## 常用验证器

| 验证器 | 用途 | 常用选项 |
|-------|------|---------|
| `PresenceOf` | 必填 | `message`、`cancelOnFail` |
| `Email` | 邮箱格式 | `allowEmpty` |
| `Numericality` | 数值 | `allowEmpty` |
| `StringLength` | 字符串长度 | `min`、`max` |
| `InclusionIn` | 枚举值 | `domain`、`allowEmpty` |
| `Regex` | 正则 | `pattern`、`allowEmpty` |
| `Between` | 区间 | `minimum`、`maximum` |

## 自定义验证器

在 `library/validators/` 下创建：

```php
<?php

namespace Apps\Validators;

use Phalcon\Validation;
use Phalcon\Validation\Validator;

class MobileValidator extends Validator
{
    public function validate(Validation $validation, $attribute): bool
    {
        $value = $validation->getValue($attribute);
        if (!preg_match('/^1[3-9]\d{9}$/', $value)) {
            $validation->appendMessage(
                new Validation\Message(
                    $this->getOption('message', '手机号格式不正确'),
                    $attribute
                )
            );
            return false;
        }
        return true;
    }
}
```

使用：`$this->add('mobile', new MobileValidator(['message' => '请输入正确的手机号']));`

## 链式多规则

同一字段多次 `add()`，按顺序执行。`cancelOnFail => true` 让第一条失败后不再继续校验该字段：

```php
$this->add('email', new PresenceOf(['message' => '邮箱必填', 'cancelOnFail' => true]));
$this->add('email', new Email(['message' => '邮箱格式不正确']));
```

## 常见错误

- ❌ 方法名带 `Action` 后缀（`indexAction()` 不会被触发，正确是 `index()`）
- ❌ 类名漏掉 `Validation` 后缀
- ❌ 在 Controller 里手动调用验证器（框架已自动调用）
- ❌ 在验证方法里写业务逻辑（验证器只描述规则）
- ❌ 验证通过后想读"净化后"的值（Phalcon 3.4 验证器不做值替换，只做校验）
