---
name: hyperf-validation
description: "创建或修改请求参数验证器。涉及 app/Request/ 下的 FormRequest 类、验证规则、自定义错误消息、条件性校验、自定义验证规则时使用。Use when working with files matching: **/Request/**/*.php."
---

# Hyperf Request 验证器规范

## 核心原则

**所有入参校验 MUST 放在 Request 类中**，通过 Controller Action 参数类型声明自动触发验证。Service 层禁止编写入参校验逻辑。

## 命名与文件结构

| 规则 | 说明 |
|------|------|
| 路径 | `app/Request/<Module>/<Action>Request.php` |
| 命名空间 | `App\Request\<Module>` |
| 类名 | `<Action>Request`（如 `CreateMemberRequest`、`GetListRequest`） |
| 基类 | `Hyperf\Validation\Request\FormRequest` |
| 一个 Action 一个 Request | ✅ 每个 Controller Action 对应一个独立的 Request 类 |

不分模块的简单场景可直接放 `app/Request/<Action>Request.php`。

## 标准模板

```php
<?php

declare(strict_types=1);

namespace App\Request\Member;

use Hyperf\Validation\Request\FormRequest;

class CreateMemberRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'name' => 'required|string|min:2|max:32',
            'email' => 'required|email',
            'phone' => 'nullable|regex:/^1[3-9]\d{9}$/',
            'status' => 'required|integer|in:0,1',
        ];
    }

    public function messages(): array
    {
        return [
            'name.required' => '姓名必填',
            'name.min' => '姓名至少 2 个字符',
            'email.email' => '邮箱格式不正确',
            'phone.regex' => '手机号格式不正确',
        ];
    }

    public function attributes(): array
    {
        return [
            'name' => '姓名',
            'email' => '邮箱',
            'phone' => '手机号',
            'status' => '状态',
        ];
    }
}
```

## Controller 中触发验证

通过 Action 方法参数类型声明自动触发，**不需要手动调用任何验证方法**：

```php
use App\Request\Member\CreateMemberRequest;

#[PostMapping(path: 'create')]
public function create(CreateMemberRequest $request): ResponseInterface
{
    $validated = $request->validated(); // 获取验证通过的数据
    $id = $this->memberService->createMember($validated);
    return $this->jsonReturn(['id' => $id]);
}
```

## 条件性规则

### 使用内置条件规则

```php
public function rules(): array
{
    return [
        'script_type' => 'required|integer|in:1,2',
        // 仅当 script_type=2 时，language 必填
        'language' => 'required_if:script_type,2|integer',
        'cover' => 'nullable|string|max:255',
    ];
}
```

### 根据输入动态追加规则

当条件逻辑较复杂时，在 `rules()` 中读取 `$this->input()` 动态 merge 规则：

```php
public function rules(): array
{
    $rules = [
        'style' => 'required|integer|in:1,2,3,4',
        'global_config' => 'nullable|array',
    ];

    $style = (int) $this->input('style', 0);
    $globalConfig = $this->input('global_config');

    // 仅在特定 style 且 global_config 存在时校验嵌套结构
    if ($style !== 4 && is_array($globalConfig)) {
        $rules = array_merge($rules, [
            'global_config.img_config' => 'required|array',
            'global_config.img_config.ai_model' => 'required|string|max:64',
            'global_config.img_config.resolution' => 'required|string|max:32',
        ]);
    }

    return $rules;
}
```

## 数组验证

使用点号语法 + `*` 通配符验证数组元素：

```php
public function rules(): array
{
    return [
        'items' => 'required|array|min:1',
        'items.*.product_id' => 'required|integer|min:1',
        'items.*.quantity' => 'required|integer|min:1|max:999',
        'items.*.price' => 'required|integer|min:0',
    ];
}

public function attributes(): array
{
    return [
        'items.*.product_id' => '商品ID',
        'items.*.quantity' => '数量',
        'items.*.price' => '价格',
    ];
}
```

## 数据预处理（prepareForValidation）

验证前对数据做预处理（补默认值、格式转换），使用 `prepareForValidation` + `merge()`：

```php
protected function prepareForValidation(): void
{
    $this->merge([
        'status' => $this->input('status', 1),
        'amount' => (int) $this->input('amount', 0),
    ]);
}
```

## 自定义验证规则

### 通过 Listener 注册全局自定义规则

在 `app/Listener/` 下创建监听器：

```php
<?php

declare(strict_types=1);

namespace App\Listener;

use Hyperf\Event\Annotation\Listener;
use Hyperf\Event\Contract\ListenerInterface;
use Hyperf\Validation\Contract\ValidatorFactoryInterface;
use Hyperf\Validation\Event\ValidatorFactoryResolved;
use Hyperf\Validation\Validator;

#[Listener]
class ValidatorFactoryResolvedListener implements ListenerInterface
{
    public function listen(): array
    {
        return [
            ValidatorFactoryResolved::class,
        ];
    }

    public function process(object $event): void
    {
        /** @var ValidatorFactoryInterface $validatorFactory */
        $validatorFactory = $event->validatorFactory;

        // 注册手机号验证规则
        $validatorFactory->extend('mobile', function (string $attribute, mixed $value, array $parameters, Validator $validator): bool {
            return (bool) preg_match('/^1[3-9]\d{9}$/', (string) $value);
        });

        $validatorFactory->replacer('mobile', function (string $message, string $attribute, string $rule, array $parameters): string {
            return str_replace(':attribute', $attribute, ':attribute 手机号格式不正确');
        });
    }
}
```

使用：`'phone' => 'required|mobile'`

### 验证后钩子（after）

复杂的跨字段业务校验（如范围不重叠、折扣价≤官方价），通过 `withValidator` 添加 `after` 钩子：

```php
/**
 * 配置验证器实例，添加验证后钩子
 */
public function withValidator(\Hyperf\Validation\Validator $validator): void
{
    $validator->after(function (\Hyperf\Validation\Validator $validator) {
        $ranges = $this->input('ranges', []);
        if (!$this->validateRangesNotOverlap($ranges)) {
            $validator->errors()->add('ranges', '价格区间不允许重叠');
        }
    });
}

private function validateRangesNotOverlap(array $ranges): bool
{
    // 排序后检查相邻区间是否重叠
    usort($ranges, fn($a, $b) => $a['min'] <=> $b['min']);
    for ($i = 1; $i < count($ranges); $i++) {
        if ($ranges[$i]['min'] < $ranges[$i - 1]['max']) {
            return false;
        }
    }
    return true;
}
```

## 常用验证规则速查

| 规则 | 用途 | 示例 |
|------|------|------|
| `required` | 必填 | `'name' => 'required'` |
| `nullable` | 可为 null | `'cover' => 'nullable\|string'` |
| `integer` | 整数 | `'id' => 'required\|integer'` |
| `string` | 字符串 | `'name' => 'required\|string'` |
| `email` | 邮箱格式 | `'email' => 'required\|email'` |
| `in:a,b,c` | 枚举值 | `'status' => 'required\|in:0,1,-1'` |
| `min:N` / `max:N` | 最小/最大值 | `'age' => 'integer\|min:0\|max:150'` |
| `regex:/pattern/` | 正则匹配 | `'phone' => 'regex:/^1[3-9]\d{9}$/'` |
| `required_if:field,val` | 条件必填 | `'lang' => 'required_if:type,2'` |
| `array` | 数组 | `'items' => 'required\|array'` |
| `exists:table,col` | 数据库存在性 | `'user_id' => 'exists:users,id'` |
| `unique:table,col` | 唯一性 | `'email' => 'unique:users,email'` |
| `between:min,max` | 区间 | `'score' => 'between:0,100'` |
| `lte:field` | 小于等于另一字段 | `'discount' => 'lte:price'` |

## 常见错误

- ❌ 把入参校验逻辑放在 Service 层的 validate() 方法中（MUST 放 Request 类）
- ❌ 在 Controller 中手动实例化 Request 调用验证（应通过 Action 参数类型声明自动触发）
- ❌ 多个 Action 共用一个 Request 类（每个 Action 对应独立 Request）
- ❌ 使用 `$scenes` 场景切换模式（统一使用独立 Request 类）
- ❌ 在 Request 中编写业务逻辑（Request 只定义规则，不做数据库查询和业务判断）
- ❌ 忘记配置全局中间件 `ValidationMiddleware`（否则参数注入方式不生效）
- ❌ 忘记配置异常处理器 `ValidationExceptionHandler`（否则验证失败无法正确返回错误信息）
