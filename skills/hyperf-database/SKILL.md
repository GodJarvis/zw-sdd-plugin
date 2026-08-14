---
name: hyperf-database
description: "编写或修改 Hyperf Model 和 Repository 层。涉及数据库模型定义、查询封装、分页、多连接、查询优化时使用。Use when working with files matching: **/Model/**/*.php, **/Repository/**/*.php."
---

# Hyperf Model + Repository 规范

## Model 定义

```php
<?php

declare(strict_types=1);

namespace App\Model\MySQL;

class Member extends Model
{
    protected ?string $table = 'member';

    protected array $fillable = [
        'name', 'email', 'phone', 'status',
    ];

    protected array $casts = [
        'id' => 'integer',
        'status' => 'integer',
        'create_time' => 'datetime',
        'update_time' => 'datetime',
    ];

    public const CREATED_AT = 'create_time';
    public const UPDATED_AT = 'update_time';
}
```

## Repository 封装

```php
<?php

declare(strict_types=1);

namespace App\Repository\MySQL;

use App\Model\MySQL\Member;
use Hyperf\Database\Model\Builder;

class MemberRepository extends BaseRepository
{
    public function getById(int $id): ?Member
    {
        return Member::find($id);
    }

    public function getList(array $filters, int $page, int $pageSize): array
    {
        $query = $this->buildQuery($filters);
        $total = $query->count();
        $list = $query->select(['id', 'name', 'email', 'status', 'create_time'])
            ->orderBy('id', 'desc')
            ->forPage($page, $pageSize)
            ->get()
            ->toArray();
        return [$list, $total];
    }

    public function getByIds(array $ids): array
    {
        if (empty($ids)) {
            return [];
        }
        return Member::whereIn('id', $ids)
            ->select(['id', 'name', 'email'])
            ->get()
            ->keyBy('id')
            ->toArray();
    }

    public function create(array $data): Member
    {
        return Member::create($data);
    }

    public function updateStatus(int $id, int $status): bool
    {
        return Member::where('id', $id)->update(['status' => $status]) > 0;
    }

    private function buildQuery(array $filters): Builder
    {
        $query = Member::query();
        if (!empty($filters['status'])) {
            $query->where('status', $filters['status']);
        }
        if (!empty($filters['email'])) {
            $query->where('email', 'like', $filters['email'] . '%');
        }
        return $query;
    }
}
```

## 查询优化

### SELECT 只查需要字段

```php
// ❌
$list = Member::all();

// ✅
$list = Member::select(['id', 'name', 'email'])->get();
```

### 避免 N+1

```php
// ❌
foreach ($orders as $order) {
    $member = Member::find($order->member_id);
}

// ✅
$memberIds = $orders->pluck('member_id')->unique()->toArray();
$members = Member::whereIn('id', $memberIds)->get()->keyBy('id');
```

### Eager Loading

```php
$orders = Order::with('member')->where('status', 1)->get();
```

## 多连接

```php
// config/autoload/databases.php 定义多个连接
Member::on('read')->find(1);
Db::connection('write')->table('member')->insert(...);
```

## 强制规则

- ❌ Repository 包含业务判断逻辑（应只做数据存取）
- ❌ 循环中查数据库（N+1）
- ❌ `where("id = $id")` 字符串拼接（SQL 注入）
- ❌ 金额用 float/decimal（应该 int + 分）
- ❌ 手动 `new PDO`（必须通过框架连接池）

## 建表铁律

| 项 | 要求 |
| -- | ---- |
| 存储引擎 | **InnoDB** |
| 字符集 | **utf8mb4** |
| NULL | 尽可能 NOT NULL；字符串默认空字符串 |
| 金额 | **int（分）**，不用 decimal |
| 时间 | **datetime**，必有 `create_time`，尽量 `update_time` |
| 索引字段 | 字符串类型 `varchar`，长度 **≤ 47** |
| 注释 | 表、字段**必须**有注释 |

## 索引设计规则（DDL 生成时 MUST 遵守）

### 核心原则

1. **联合索引优先于单列索引**：查询条件涉及多列时，必须使用联合索引，禁止为同一查询的多个条件列分别建单列索引
2. **列序原则——等值在前、范围在后、排序最后**：联合索引中等值条件列在前，范围查询列在后，ORDER BY 列放末尾；等值列之间按选择性（基数）从高到低排列
3. **禁止对低基数列单独建索引**：status、type、is_deleted 等取值极少的列，不得单独建索引。但在联合索引中低基数列有如下合法用法：
   - **低基数 + 范围列**：低基数在前作为分区键（如 `idx(status, create_time)`），利用不等式缩小区间
   - **低基数 + 高等值列**：高基数等值列必须在前（如 `idx(user_id, status)`），低基数后置仅做过滤
   - 以上两种情况外的中间状态（低基数列位于联合索引中间位置），需在注释中写明列序理由
4. **WHERE + ORDER BY 覆盖**：索引应尽量同时覆盖查询条件和排序字段，避免 filesort
5. **高频查询考虑覆盖索引**：当 SELECT 的列能完全被索引覆盖时，应设计为覆盖索引避免回表，尤其适用于高频列表查询
6. **索引数量限制**：每张表索引不超过 5 个（含主键），超过时必须在 design 中说明理由
7. **禁止重复索引**：已被联合索引最左前缀覆盖的单列/组合索引不得重复创建（如有 idx(a,b,c) 则不得再建 idx(a) 或 idx(a,b)）
8. **索引必须有场景注释**：DDL 中每个索引定义后 MUST 添加行内注释，统一格式如下：
   - 单列外键 → `-- 关联查询：按xxx查xxx`
   - 筛选+排序联合索引 → `-- 列表查询：按xxx筛选+时间排序`
   - 唯一键 → `-- 业务唯一性约束：xxx`
   - 其他 → `-- 查询场景：xxx`
9. **索引命名规范——语义化缩写**：普通索引 `idx_` 开头，唯一索引 `uk_` 开头，全小写下划线。MUST 使用语义化缩写，禁止机械拼接完整字段名或生硬加表名：
   - 每列取**核心名词**（去 `_id`、`_time`、`_at` 等后缀），按列序用下划线拼接
   - 示例：`member_id` → `member`，`member_id + project_id` → `idx_member_project`，`status + create_time` → `idx_status_create`
   - 索引名长度应明显短于全字段名拼接，且保持语义可读（读到索引名就知道是哪几个列）
10. **必建索引场景**：① 关联查询列（JOIN）② 列表接口的筛选+排序组合 ③ 业务唯一性约束列（UNIQUE KEY）
11. **禁止外键**：禁止使用 FOREIGN KEY 约束，关联关系通过应用层保证，关联列建普通索引供 JOIN 使用

### DDL 示例

```sql
CREATE TABLE `order` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned NOT NULL DEFAULT 0,
  `status` tinyint unsigned NOT NULL DEFAULT 0,
  `amount` int unsigned NOT NULL DEFAULT 0,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_member` (`member_id`), -- 关联查询：按会员查订单
  KEY `idx_status_create` (`status`, `create_time`) -- 列表查询：按状态筛选+时间排序
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## DDL 生成自审清单（输出前 MUST 逐项检查）

生成 CREATE TABLE / ALTER TABLE 语句后、写入 `db.mysql.sql` 前，MUST 逐项执行以下检查：

### 1. 最左前缀去重

- 列出所有索引（含 PRIMARY）及其列序列
- 若某索引 A 的列序列是另一索引 B 列序列的**前缀** → A 为冗余索引，删除 A
- 示例：`idx_project_id (project_id)` 被 `idx_source (project_id, source_table, source_id)` 覆盖 → 删除前者
- 被删索引的查询场景 MUST 合并注释到保留的联合索引上

### 2. UNIQUE KEY 黑名单

- 遍历所有 UNIQUE KEY，检查是否包含以下**禁止列**：
  `is_delete`、`is_valid`、`status`（作为状态标记时）、`deleted_at`
- 命中 → 从 UNIQUE KEY 中移除该列，改为：
  - 方案 A（推荐）：唯一约束只含业务数据列，应用层查询时加 `WHERE is_delete=0`，先查再判
  - 方案 B：唯一约束不含软删除字段，改为唯一约束 + 删除时间戳字段 `deleted_at` 的组合判重

### 3. 命名语义化校验

- 遍历所有索引名，检查：
  - 是否以 `idx_` / `uk_` 开头
  - 是否包含完整字段名机械拼接（如 `member_id_project_id`、`status_create_time`）→ 应缩写为核心名词（`member_project`、`status_create`）
  - 是否包含表名 → 表名不出现在索引名中
- 不满足 → 按语义化缩写规则重命名

### 4. 场景注释完整性

- 遍历所有 KEY / UNIQUE KEY 行，检查行尾是否有 `-- ` 引导的场景注释
- 缺失 → 根据列组合自动推断补充：
  - 单列 + 是其他表关联列 → `-- 关联查询：按xxx查xxx`
  - 状态/类型列 + 时间列 → `-- 列表查询：按xxx筛选+时间排序`
  - 联合唯一键 → `-- 业务唯一性约束：xxx`
- 推断不确定时标注 `-- ⚠️ 请人工补充查询场景`

### 5. 索引数量上限

- 统计 DDL 中索引总数（PRIMARY + KEY + UNIQUE KEY）
- n ≤ 5 → 通过
- n > 5 → 按优先级从低到高删减（PRIMARY > UNIQUE KEY > JOIN 关联列 > 列表筛选联合索引 > 其他单列索引）
- 同级多个候选时，按列选择性（基数）从低到高删减：低基数列优先让位于高基数列
- 被删索引的查询场景合并注释到保留的联合索引上

### 6. 联合索引列序合理性

- 对每个联合索引，根据对应的查询场景判定列序是否正确：
  - **判定 1**：等值条件列 vs 范围/排序列 → 等值在前
  - **判定 2**：多个等值列之间 → 高基数在前，低基数在后
  - **判定 3**：低基数等值 + 范围列 → 低基数在前作为分区键（此时低基数只是缩小初始区间，不等同于"有过滤效果"）
- 示例：
  - `WHERE user_id=? AND status=?` → `idx(user_id, status)` ✅（两个等值，高基数在前）
  - `WHERE status=? AND create_time>? ORDER BY create_time` → `idx(status, create_time)` ✅（等值在前，范围在后）
  - `WHERE status=? AND user_id=?` → `idx(user_id, status)` ✅（两个等值，高基数在前，与 status 是否有范围无关）
- 列序不符合以上判定 → 调整列序并在注释中说明理由
