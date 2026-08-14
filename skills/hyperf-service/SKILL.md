---
name: hyperf-service
description: "编写或修改 Hyperf Service 层业务逻辑。涉及业务编排、事务处理、服务间调用、BusinessException 时使用。Use when working with files matching: **/Service/**/*.php."
---

# Hyperf Service 规范

## 职责边界

- ✅ 业务逻辑编排、调用 Repository、管理事务、调用其他 Service
- ❌ 不接触 HTTP Request/Response，不直接操作 Model
- ❌ 禁止组装分页返回结构（page_info / data 包裹）。分页场景只返回 `[$list, $total]`，由 Controller 的 `paginationReturn` 统一组装
- ❌ 禁止循环依赖注入：若 A Service 已注入 B Service，则 B Service 禁止注入 A Service。双向调用场景须通过以下方式解耦：
  - 提取公共逻辑到第三个 Service（两者依赖它，它不依赖任何一方）
  - 反向调用改用事件驱动（EventDispatcherInterface）
  - 将对方的数据查询下沉到 Repository 层直接访问
- ❌ 禁止在 Service 中编写 validate/校验方法或入参格式校验逻辑（必填、格式、枚举范围、数值区间、数组结构等），所有入参校验 MUST 放在 Request 类中。Service 仅处理需要查询数据库才能判定的业务规则校验（如唯一性、存在性、状态流转）

## 标准模板

```php
<?php

declare(strict_types=1);

namespace App\Service;

use App\Exception\BusinessException;
use App\Model\MySQL\Member;
use App\Repository\MySQL\MemberRepository;
use Hyperf\DbConnection\Db;
use Hyperf\Di\Annotation\Inject;

class MemberService extends BaseService
{
    #[Inject]
    public MemberRepository $memberRepository;

    public function getMemberById(int $id): ?Member
    {
        return $this->memberRepository->getMemberById($id);
    }

    /**
     * @return array{0: array, 1: int}
     */
    public function getList(int $status, int $page, int $pageSize): array
    {
        return $this->memberRepository->getList($status, $page, $pageSize);
    }

    public function createMember(array $data): int
    {
        return Db::transaction(function () use ($data): int {
            $member = $this->memberRepository->create($data);
            return $member->id;
        });
    }

    public function updateStatus(int $id, int $status): bool
    {
        $member = $this->memberRepository->getMemberById($id);
        if (!$member) {
            throw new BusinessException('会员不存在');
        }
        return $this->memberRepository->updateStatus($id, $status);
    }
}
```

## 事务

```php
use Hyperf\DbConnection\Db;

// 闭包事务（推荐），异常自动回滚
Db::transaction(function () use ($data) {
    $this->memberRepository->create($data);
    $this->logService->writeCreateLog($data);
});
```

## 服务间调用

```php
class OrderService extends BaseService
{
    #[Inject]
    protected MemberService $memberService;

    public function createOrder(int $memberId, array $items): int
    {
        $member = $this->memberService->getMemberById($memberId);
        if (!$member) {
            throw new BusinessException('会员不存在');
        }
        // ...
    }
}
```

## 返回类型约定

| 场景 | 类型 |
|------|------|
| 查单条 | `?Model` |
| 查列表+总数 | `array{0: array, 1: int}` |
| 创建 | `int`（返回 ID） |
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

## 强制规则

- ❌ Service 直接操作 Model（必须通过 Repository）
- ❌ Service 返回 HTTP Response
- ❌ Service 中使用全局/静态变量存储状态
- ❌ 跨 Service 调用时绕过 DI 手动 new
- ❌ 在 Service 中定义 private/protected validate() 方法做入参校验（应拆到 Request 类）
- ❌ 将前端传参直接用于权益/资源/金额决策（判定标准：该参数值变化会直接改变用户获得的结果）。这类值 MUST 从 Repository/Cache 获取服务端权威数据
