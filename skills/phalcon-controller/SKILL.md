---
name: phalcon-controller
description: "创建或修改 Phalcon 控制器、接口、路由、参数获取、返回格式。涉及 apps/*/controllers 下的 Action 方法、JSON 返回、掌权鉴权、ControllerBase 继承时使用。Use when working with files matching: apps/**/controllers/**/*.php."
---

# Phalcon 控制器与接口规范

## 继承关系

```
AppBaseController          # 框架提供，包含 returnJson、getParam、fileLog 等
  └── ControllerBase       # 各模块自定义，负责掌权鉴权、登录校验
        └── IndexController  # 业务控制器
```

**业务控制器一定继承模块自己的 `ControllerBase`**，不要直接继承 `AppBaseController`。

## 控制器职责

- 接收请求 → 参数获取 → 调用服务层 → 返回响应
- **允许**：参数基础校验（空值、格式、类型检查）、响应结构组装
- **禁止**：业务规则判断（存在性校验、状态流转、金额计算、权限逻辑），业务逻辑全部放在 `library/services/`
- Action 方法必须以 `Action` 结尾（Phalcon 路由约定）

## 标准模板

```php
<?php

namespace Apps\Admin\Controllers;

use Apps\Services\MemberService;

/**
 * 会员管理
 * User: 张三
 * Date: 2026/04/23
 */
class MemberController extends ControllerBase
{
    public function indexAction()
    {
        $page = $this->page(1);
        $pageSize = $this->pageSize(20);
        $status = (int)$this->getParam('status', 0);

        $service = new MemberService();
        [$list, $total] = $service->getList($status, $page, $pageSize);

        $data = [
            'data' => $list,
            'page_info' => [
                'page' => $page,
                'page_size' => $pageSize,
                'total' => $total,
            ],
        ];
        $this->returnJson(self::STATUS_OK, '', $data);
    }

    public function listAction()
    {
        $corpId = (string)$this->getParam('corp_id', '');

        $list = (new MemberService())->getActiveMembers($corpId);
        // 非分页列表：直接传数组，不要包裹 ['data' => $list]
        $this->returnJson(self::STATUS_OK, '', $list);
    }

    public function detailAction()
    {
        $id = (int)$this->getParam('id', 0);
        $member = (new MemberService())->getMemberById($id);

        if (!$member) {
            $this->returnJson(self::STATUS_FAILURE, '用户不存在');
        }
        $this->returnJson(self::STATUS_OK, '', $member->toArray());
    }
}
```

## 参数获取

| 用途     | 调用                         |
| ------ | -------------------------- |
| 获取单个参数 | `$this->getParam('id', 0)` |
| 获取所有参数 | `$this->getParam()`        |
| 获取当前页码 | `$this->page(1)`           |
| 获取每页数量 | `$this->pageSize(20)`      |

全部已自动 `trim()`，支持 json / form-data / query string。

## 返回格式

**只用** `$this->returnJson($status_code, $msg, $data = [], $extra = [])`。

```php
$this->returnJson(self::STATUS_OK, '', $data);           // 成功
$this->returnJson(self::STATUS_FAILURE, '参数错误');       // 失败
$this->returnJson(self::STATUS_NEED_LOGIN, '请重新登录');   // 需登录
```

状态码常量（`AppBaseController` 上）：`STATUS_OK = 1`、`STATUS_FAILURE = -1`、`STATUS_FORBIDDEN = -99`、`STATUS_NEED_LOGIN = -100`、`STATUS_PARAM_ERROR = -101`、`STATUS_INVALIDATE = -102`。

### 分页列表 data 结构

```php
$data = [
    'data' => $list,
    'page_info' => [
        'page' => $page,
        'page_size' => $pageSize,
        'total' => $total,
    ],
];
$this->returnJson(self::STATUS_OK, '', $data);
```

### 非分页列表 data 结构

非分页接口（无 page_info）**直接传数组**作为第三个参数，禁止再包裹 `['data' => ...]`：

```php
$list = SomeService::getList($corpId, $userid);
// ✅ 正确：直接传 $list
$this->returnJson(self::STATUS_OK, '操作成功', $list);

// ❌ 错误：会产生 data.data 双层嵌套
$this->returnJson(self::STATUS_OK, '操作成功', ['data' => $list]);
```

## 路由

路由在 `settings/routes.php` 按模块注册，格式 `/<module>/<controller>/<action>`。不要使用注解路由。

### 多单词命名示例

```php
/**
 * AI 质检记录管理
 */
class CorpAiQualityReviewRecordController extends ControllerBase
{
    // 路由：/admin/corp_ai_quality_review_record/qualityControl
    public function qualityControlAction()
    {
        // ...
    }

    // 路由：/admin/corp_ai_quality_review_record/getReviewList
    public function getReviewListAction()
    {
        // ...
    }
}
```

**路由转换规则**：
- Controller 段：大驼峰 → snake_case（`CorpAiQualityReviewRecord` → `corp_ai_quality_review_record`）
- Action 段：去掉 `Action` 后缀，保持 camelCase 原样（`qualityControlAction` → `qualityControl`）
- ❌ 禁止将 action 转 snake_case（`quality_control` 会导致路由不可达）

### 路由详细规则

**Module 来源**：从控制器目录名获取

| 目录路径 | Module |
|---------|--------|
| `apps/admin/controllers/MemberController.php` | `admin` |
| `apps/api/controllers/OrderController.php` | `api` |

**完整路由推导**：`/{module}/{controller}/{action}`

| 控制器 | 方法 | 路由 |
|--------|------|------|
| `apps/admin/controllers/MemberController.php` | `detailAction()` | `/admin/member/detail` |
| `apps/admin/controllers/CorpAiQualityReviewRecordController.php` | `qualityControlAction()` | `/admin/corp_ai_quality_review_record/qualityControl` |

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

## 验证器

如果当前 Action 需要参数校验，在 `apps/<module>/validation/<Controller>Validation.php` 创建同名方法（去掉 Action 后缀）即可，框架自动触发，**不需要在控制器中手动调用**。详见 `phalcon-validation` skill。

## 常见错误

- ❌ 方法名漏掉 `Action` 后缀（`index()` 不会被路由识别）
- ❌ 在控制器里直接写 DB 查询（应该调 Service 层）
- ❌ 自己拼数组返回（必须用 `returnJson`）
- ❌ 忘记 `(int)` 强转用户输入的 ID 参数
- ❌ 继承了 `AppBaseController` 而不是模块的 `ControllerBase`（会丢失鉴权）
- ❌ 非分页列表用 `['data' => $list]` 包裹（会导致 `data.data` 双层嵌套，只有分页接口才需要 `['data' => $list, 'page_info' => ...]` 结构）
