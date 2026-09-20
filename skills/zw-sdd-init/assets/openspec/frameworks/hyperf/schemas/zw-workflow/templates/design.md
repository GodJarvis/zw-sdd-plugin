## 概述（Overview）

**目标：** <!-- 一句话描述本设计要实现什么 -->
**架构方向：** <!-- 2-3 句概括技术方案 -->
**非目标：** <!-- 明确排除的范围 -->

---

## 全局决策（Global Decisions）

<!-- 影响多个模块的跨领域决策放在这里；只影响单个模块的决策放到对应模块的「架构说明」内 -->

| 决策 | 选择 | 理由（为什么不选其他方案） |
|------|------|--------------------------|

## 风险与权衡（Risks / Trade-offs）

<!-- 全局性风险，格式：[风险] → 缓解措施 -->

---

## 模块 1: <!-- 模块名称 -->

### 架构说明

<!-- 本模块的设计思路、核心约束、与其他模块的依赖关系 -->
<!-- 条件性段落：协程安全/异步任务/可观测性如果只涉及本模块，放这里而非全局 -->

#### Redis 缓存设计

<!-- 条件性：涉及 Redis 缓存/锁/计数器时 MUST 保留，不涉及则删除本段 -->
<!-- 覆盖范围：缓存读写、分布式锁、计数器/限流。队列/Stream 不在此段，由异步任务段管辖 -->

<!-- MUST 包含以下内容（按实际涉及的场景选择）：

     **缓存场景**（涉及时必填）：
     - 每个 Key 的命名模式（含动态参数占位符，如 `member_info:{uid}`）
     - Redis 数据类型（string/hash/set/zset/list）
     - 过期策略：TTL 数值 + 设置方式（固定/随机偏移/滑动窗口）
     - 失效策略：哪个操作触发缓存清除 + 一致性级别（强/最终）
     - 异常场景防护：穿透/雪崩/击穿的具体防护措施

     **分布式锁场景**（涉及时必填）：
     - 锁粒度（Key 模式，如 `lock:bindCard:{uid}`）
     - 超时时间
     - 是否可重入
     - 竞争失败处理方式（重试/报错/等待）

     **计数器/限流场景**（涉及时必填）：
     - Key 模式（如 `rate:login:{ip}:{date}`）
     - 窗口期 + 阈值
     - 超限处理方式 -->

#### 筛选项数据源

<!-- 条件性：模块包含列表/搜索接口且有筛选字段时 MUST 保留，不涉及则删除本段 -->
<!-- 项目约定：所有筛选下拉框统一走 SearchConditionController/SearchController::index 的 switch($k) 路由 -->
<!-- 逐一列出每个筛选字段的数据来源和 SearchController case 覆盖情况 -->

<!-- 格式示例：
| 筛选字段 | 数据类型 | SearchController case | 状态 |
|---------|---------|----------------------|------|
| service_type | 枚举常量 | `service_type` | 待新增 case |
| vendor | 动态数据（数据库） | `vendor` | 待新增 case |
| status | 固定枚举 0/1/2 | — | 前端硬编码，常量类已定义 |
-->

### 文件结构

| 操作 | 路径 | 职责 |
|------|------|------|
| 新增 | `app/Repository/XxxRepository.php` | <!-- 职责 --> |
| 新增 | `app/Service/XxxService.php` | <!-- 职责 --> |
| 新增 | `app/Request/Xxx/CreateXxxRequest.php` | <!-- 入参校验 --> |
| 修改 | `app/Controller/XxxController.php` | <!-- 职责 --> |

### 实现蓝图

<!-- 每个组件按复杂度选择粒度：
     - 核心逻辑 → 签名级（方法签名 + 实现步骤 + 关键约束 + 参照代码）
     - 简单 CRUD → 模式引用级（文件路径 + 参照 + 一句约束）
     - TDD-EXEMPT 组件不需要蓝图 -->

#### XxxRepository（签名级示例）

**文件**: `app/Repository/XxxRepository.php`
**参照**: `app/Repository/MemberRepository.php`

```php
class XxxRepository
{
    public function methodA(int $param): ReturnType
    public function methodB(int $param, string $other): bool
}
```

**实现要点**:
- <!-- 关键约束、锁策略、调用上下文等 -->

#### XxxController（模式引用级示例）

**文件**: `app/Controller/XxxController.php`
**参照**: `app/Controller/MemberController::detail`
**Skill**: `hyperf-controller`（apply 时 MUST invoke 此 skill）
**约束**: 标准信封返回，每个 Action 注入独立 Request 类

#### CreateXxxRequest（模式引用级示例）

**文件**: `app/Request/Xxx/CreateXxxRequest.php`
**参照**: `app/Request/Drama/CreateDramaRequest.php`
**Skill**: `hyperf-validation`（apply 时 MUST invoke 此 skill）
**约束**: 每个 Action 独立 Request 类，通过参数注入触发

#### RedisKey 常量扩展（签名级示例）

<!-- 条件性：涉及 Redis 新增/修改 Key 时 MUST 保留 -->

**文件**: `app/Constants/RedisKey.php`
**参照**: 现有 `RedisKey` 常量结构

```php
class RedisKey
{
    /** 会员信息缓存 */
    public const string MEMBER_INFO = 'member_info';

    /** 绑卡操作锁 */
    private const string LOCK_BIND_CARD = 'lock:bindCard:%d';

    /** 登录限流 */
    private const string RATE_LOGIN = 'rate:login:%s:%s';

    public static function getLockBindCardKey(int $uid): string

    public static function getRateLoginKey(string $ip, string $date): string
}
```

**实现要点**:
- 动态 Key 常量用 `private const`，通过静态方法暴露
- 方法命名 `get{用途}Key`

---

## 数据库变更（Database Changes）

<!-- 条件性：涉及数据库结构变更时保留，概述涉及哪些库/表，完整 DDL 在伴生文件 db.*.sql 中 -->

<!-- 涉及新建索引时 MUST 说明每个索引的设计意图：
     - 对应的具体查询模式：服务哪个接口/方法，各列角色（等值/范围/排序），不得写脱离实际 SQL 的泛化描述
     - 列序符合「等值在前、范围在后、排序最后」默认原则时无需逐列解释；偏离时 MUST 说明理由
     - 索引列必须与服务查询的 WHERE/ORDER BY/SELECT 一一对应，禁止追加查询未引用的列（含默认追加主键）
     - 如果索引数超过 5 个，说明为什么必须超限 -->

## 迁移计划（Migration）

<!-- 条件性：需要分步部署时保留 -->
