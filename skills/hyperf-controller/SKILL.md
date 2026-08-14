---
name: hyperf-controller
description: "创建或修改 Hyperf 控制器、路由注解、中间件。涉及 Controller 目录下的接口方法、PostMapping、JSON 返回格式时使用。Use when working with files matching: **/Controller/**/*.php."
---

# Hyperf Controller + Request 规范

## Controller 标准模板

```php
<?php

declare(strict_types=1);

namespace App\Controller\Admin;

use App\Enum\ErrorCode;
use App\Request\Member\GetListRequest;
use App\Request\Member\DetailRequest;
use App\Request\Member\CreateMemberRequest;
use App\Service\MemberService;
use Hyperf\Di\Annotation\Inject;
use Hyperf\HttpServer\Annotation\Controller;
use Hyperf\HttpServer\Annotation\PostMapping;
use Psr\Http\Message\ResponseInterface;

#[Controller(prefix: '/admin/member')]
class MemberController extends BaseController
{
    #[Inject]
    protected MemberService $memberService;

    #[PostMapping(path: 'getList')]
    public function getList(GetListRequest $request): ResponseInterface
    {
        $validated = $request->validated();
        $page = (int)($validated['page'] ?? 1);
        $pageSize = (int)($validated['page_size'] ?? 20);

        [$list, $total] = $this->memberService->getList(
            $validated['status'] ?? 0,
            $page,
            $pageSize
        );

        return $this->paginationReturn($list, $total, $page, $pageSize);
    }

    #[PostMapping(path: 'list')]
    public function list(GetListRequest $request): ResponseInterface
    {
        $validated = $request->validated();
        $list = $this->memberService->getActiveMembers($validated['corp_id']);
        // 非分页列表：直接传数组，不要包裹 ['data' => $list]
        return $this->jsonReturn($list);
    }

    #[PostMapping(path: 'detail')]
    public function detail(DetailRequest $request): ResponseInterface
    {
        $validated = $request->validated();
        $member = $this->memberService->getMemberById((int)$validated['id']);
        if (!$member) {
            return $this->jsonReturn([], ErrorCode::STATUS_FAILURE, '用户不存在');
        }
        return $this->jsonReturn($member->toArray());
    }

    #[PostMapping(path: 'create')]
    public function create(CreateMemberRequest $request): ResponseInterface
    {
        $validated = $request->validated();
        $id = $this->memberService->createMember($validated);
        return $this->jsonReturn(['id' => $id], ErrorCode::STATUS_OK, '创建成功');
    }
}
```

## 参数校验

参数校验通过独立 Request 类实现，每个 Action 对应一个 Request 类，通过方法参数类型声明自动触发验证。详见 `hyperf-validation` skill。

## 路由（注解方式）

```php
#[Controller(prefix: '/admin/member')]
#[Middleware(AuthMiddleware::class)]
class MemberController extends BaseController
{
    #[PostMapping(path: 'detail')]
    public function detail(DetailRequest $request): ResponseInterface {}

    #[PostMapping(path: 'create')]
    public function create(CreateMemberRequest $request): ResponseInterface {}
}
```

所有业务接口统一使用 PostMapping（除非用户明确指定其他方法）。

### 多单词命名示例

```php
#[Controller(prefix: '/admin/corp_ai_quality_review_record')]
class CorpAiQualityReviewRecordController extends BaseController
{
    // 路由：/admin/corp_ai_quality_review_record/qualityControl
    #[PostMapping(path: 'qualityControl')]
    public function qualityControl(Request $request): ResponseInterface {}

    // 路由：/admin/corp_ai_quality_review_record/getReviewList
    #[PostMapping(path: 'getReviewList')]
    public function getReviewList(Request $request): ResponseInterface {}
}
```

**路由转换规则**：
- Controller 前缀：大驼峰 → snake_case（`CorpAiQualityReviewRecord` → `corp_ai_quality_review_record`）
- 方法路径：原样保持 camelCase（`qualityControl` 不转 snake_case）

### AutoController vs Controller 选择

| 场景 | 推荐方式 | 示例 |
|------|---------|------|
| 简单 CRUD 模块 | `#[AutoController]` | `MemberController`、`ProductController` |
| 需要自定义路径 | `#[Controller]` + `#[PostMapping]` | 前缀与类名不一致时 |
| 需要特定中间件 | `#[Controller]` + `#[Middleware]` | 部分接口需要不同鉴权 |

### prefix 提取规则（AutoController）

从命名空间中 `\Controller\` 之后、类名之前的所有层级提取，转 snake_case：

| 命名空间 | 提取结果 |
|---------|---------|
| `App\Controller\Admin\Member\MemberController` | `/admin/member` |
| `App\Controller\Demo\MyDataController` | `/demo/my_data` |
| `App\Controller\MemberController` | `/member` |

### 边界命名转换（框架行为）

**连续大写字母**：逐个拆分，无缩写合并逻辑

| 类名 | 转换结果 | 说明 |
|------|---------|------|
| `IOController` | `i_o` | ❌ 不是 `io` |
| `ABCController` | `a_b_c` | ❌ 不是 `abc` |
| `HTTPServiceController` | `h_t_t_p_service` | ❌ 不是 `http_service` |
| `XMLParserController` | `x_m_l_parser` | ❌ 不是 `xml_parser` |

**数字**：附着于前一个单词，不单独拆分

| 类名 | 转换结果 | 说明 |
|------|---------|------|
| `Controller2` | `controller2` | 数字在末尾 |
| `User2ProfileController` | `user2_profile` | 数字后跟大写时，数字作为上一个词结尾 |
| `V2APIController` | `v2_a_p_i` | 连续大写被拆分 |

**建议**：避免使用连续大写字母缩写，用 `IoController` 代替 `IOController`。

### 路由冲突处理

如发现两个不同控制器生成了相同的路由路径，**必须询问用户确认**，禁止自动覆盖。

## 中间件

```php
use Hyperf\HttpServer\Annotation\Middleware;

#[Middleware(AuthMiddleware::class)]
class MemberController extends BaseController {}
```

全局中间件在 `config/autoload/middlewares.php`。

## 强制规则

- ❌ Controller 写业务逻辑（判断、计算、循环处理、数据组装属于 Service）
- ❌ Controller 直接查数据库（应调 Service）
- ❌ Service 返回 HTTP Response / JSON 字符串
- ❌ 使用 GetMapping（统一 POST，除非用户明确指定）
- ❌ 非分页列表用 `['data' => $list]` 包裹传给 `jsonReturn`（会导致 `data.data` 双层嵌套，分页场景用 `paginationReturn` 自动组装）

## 返回格式

### 通用返回（jsonReturn）

```json
{"status_code": 1, "msg": "", "data": {}, "extra": {}}
```

### 分页返回（paginationReturn）

```json
{"status_code": 1, "msg": "", "data": {"data": [...], "page_info": {"page": 1, "page_size": 20, "total": 100}}, "extra": {}}
```

分页数组 key 为 `data`（非 `list`），由 `$this->paginationReturn($data, $total, $page, $pageSize)` 自动组装。Service 层只需返回 `[$data, $total]`，禁止在 Service 中自行组装 page_info 结构。

### 非分页列表

非分页接口（无 page_info）**直接传数组**给 `jsonReturn`，禁止手动包裹 `['data' => ...]`：

```php
// ✅ 正确：直接传 $list，响应为 {"status_code":1, "data": [...]}
return $this->jsonReturn($list);

// ❌ 错误：会产生 data.data 双层嵌套
return $this->jsonReturn(['data' => $list]);
```
