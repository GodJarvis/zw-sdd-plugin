---
name: phalcon-service
description: "编写或修改 library/services/ 下的业务服务层类。涉及业务逻辑封装、跨模块调用、Model 操作、事务处理时使用。Use when working with files matching: library/services/**/*.php."
---

# Phalcon 服务层规范

## 职责边界

服务层**只做业务逻辑编排**：

- ✅ 组装业务流程（调用 Model 方法获取数据、计算、调用其他 Service）
- ✅ 跨模型的事务管理（事务写法见 `phalcon-database` skill）
- ✅ 调用 `library/modules/` 中的工具（Redis、RabbitMQ、外部 API）
- ✅ 向 Controller 返回纯数据（数组或对象，**不直接返回 JSON**）
- ❌ 不读取 HTTP 请求参数（由 Controller 传入）
- ❌ 不返回 JSON / HTTP 响应
- ❌ 不在 Service 中直接使用 SqlBuilder / `Model::from()` 查询（查询逻辑封装在 Model 方法中）
- ❌ 不拼装分页返回结构（page_info / data 包裹）。分页场景只返回 `[$list, $total]`，由 Controller 统一组装 `{data, page_info}` 结构
- ❌ 不在 Service 中编写 validate/校验方法或入参格式校验逻辑（必填、格式、枚举范围、数值区间等），所有入参校验由 Validation 类自动触发，Service 仅处理需查库的业务规则校验（如唯一性、存在性、状态流转）

## 命名与位置

- 位置：`library/services/`
- 命名空间：`Apps\Services\` 或 `Apps\Services\<SubModule>\`
- 类名：`<Domain>Service`，如 `MemberService`、`OrderService`

## 标准模板

```php
<?php

namespace Apps\Services;

use Apps\Models\Admins;
use Apps\Modules\DiUtils;
class MemberService
{
    public function getMemberById(int $id): ?array
    {
        return Admins::getById($id);
    }

    /**
     * @return array [列表, 总数]
     */
    public function getList(int $status, int $page, int $pageSize): array
    {
        $filters = [];
        if ($status > 0) {
            $filters['status'] = $status;
        }
        return Admins::getList($filters, $page, $pageSize);
    }

    public function createMember(array $data): int
    {
        $db = DiUtils::getDb();
        $db->begin();
        try {
            $insertId = Admins::createOne($data);
            $db->commit();
            return $insertId;
        } catch (\Throwable $e) {
            $db->rollback();
            DiUtils::getLog()->error(
                '创建会员异常：' . $e->getMessage(),
                ['data' => $data, 'trace' => $e->getTraceAsString()]
            );
            throw $e;
        }
    }
}
```

## 服务之间的调用

直接实例化调用：

```php
class OrderService
{
    public function createOrder(int $memberId, array $items): int
    {
        $member = (new MemberService())->getMemberById($memberId);
        if (!$member) {
            throw new \InvalidArgumentException('会员不存在');
        }
        // ...
    }
}
```

## 返回类型约定

| 场景 | 返回类型 |
|------|---------|
| 查询单条 | `array|null` |
| 查询列表+分页 | `array [列表, 总数]` |
| 查询统计数据 | `array`（关联数组）|
| 创建 | `int`（返回 ID）|
| 更新/删除 | `bool` |

## 精度处理

涉及金额、概率、百分比、比例等数值运算时，MUST 使用 bc 系列函数，禁止浮点运算后强转 int：

```php
// ❌ 浮点精度丢失：19.99 * 100 = 1998.9999... → intval 截断为 1998
$amount = intval($price * 100);

// ✅ 正确：用 bcmul 避免浮点运算
$amount = (int)bcmul($price, '100', 0);

// ❌ 浮点累加后比对：累加误差导致 != 100
$sum += $item['probability'];
if ($sum != 100) { throw ... }

// ✅ 正确：bcadd 逐项累加 + bccomp 比对
$sum = bcadd($sum, $item['probability'], 2);
if (bccomp($sum, '100', 2) !== 0) { throw ... }
```

**规则**：
- 金额：存储为 int（分），展示时 `bcdiv($amount, '100', 2)`
- 概率/百分比：存储为 int（扩大 100 或 10000 倍），运算全程 bc 函数
- 凡涉及"累加校验=某值"的场景，MUST 用 `bcadd` + `bccomp`
- `intval($float * N)` 是经典精度丢失写法，遇到即替换为 `(int)bcmul()`

## 异常处理

- 业务异常抛 `\InvalidArgumentException` / `\RuntimeException` 或自定义异常
- 数据库事务必须 try-catch + rollback（完整写法见 `phalcon-database` skill）
- 异常日志必须带上下文：

```php
DiUtils::getLog('member_exception')->error(
    '异常：' . sprintf(
        "%s: %s(%s) in %s:%s\nStack trace:\n%s",
        get_class($e), $e->getMessage(), $e->getCode(),
        $e->getFile(), $e->getLine(), $e->getTraceAsString()
    ),
    ['member_id' => $memberId, 'data' => $data]
);
```

## 常见错误

- ❌ 在 Service 里调用 `$this->getParam()` 或 `$this->returnJson()`
- ❌ 在 Service 中直接使用 `Model::from()` / SqlBuilder 查询（查询必须封装在 Model 方法中，Service 只调用）
- ❌ 直接 `new \ZhangWan\Database\Query\Builder()`（必须走 `Model::from()` 或 `new SqlBuilder()`）
- ❌ 使用 Phalcon 原生 ORM 方法（`findFirst`、`find`、`save`、`create`、`update`、`delete`）
- ❌ 事务忘记 rollback
- ❌ 循环中查数据库（用 `whereIn` 批量）
- ❌ 在 Service 中定义 validate() 方法做入参校验（应拆到 Validation 类）
- ❌ 将前端传参直接用于权益/资源/金额决策（判定标准：该参数值变化会直接改变用户获得的结果）。这类值 MUST 从 Model/Cache 获取服务端权威数据
