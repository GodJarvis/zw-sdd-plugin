---
name: zwflow-yapi-doc-gen
description: "基于远程 YApi 原文档 + spec 标注 + 代码推导三源合并生成接口文档（yapi.md）。当用户提到\"生成接口文档\"、\"yapi文档\"、\"yapi-gen\"时触发。"
---

基于三数据源（远程 YApi 原文档 + spec 定义 + 代码推导）生成或更新接口文档（yapi.md）。

本 skill 为 yapi.md 的唯一生成入口（yapi.md 不是 schema 管理的产物，propose 流程不涉及）。

---

**输入**：change 名称（可选）。

**步骤**

1. **确定 change**

   如果提供了 change 名称，检查 `openspec/changes/<name>/` 是否存在：
   - 存在 → 直接使用
   - 不存在 → 报错退出

   如果未提供名称：
   - 运行 `openspec list --json` 获取所有变更
   - 向用户展示目标变更选项并等待明确选择

   始终提示："正在为 change: <name> 生成接口文档"

2. **读取 change 产物**

   读取以下文件（必须已存在）：
   - `openspec/changes/<name>/specs/` — 所有 spec 文件
   - `openspec/changes/<name>/design.md` — 技术设计

   如果 specs 或 design 不存在 → 报错："请先完成 specs 和 design（`openspec-propose` Skill 或 `openspec-continue-change` Skill）"

3. **提取接口列表**

   先识别当前项目框架，并读取 `references/frameworks/<framework>.md`。路由路径必须按选定框架的路由规则解析。

   从 specs 和 design 中提取所有涉及的 HTTP 接口：
   - 路由路径
   - 请求方法
   - 操作类型初判（新增 / 更新）

   **路由路径确定原则**：
   - spec/design 中显式定义的路径优先于代码推导。
   - 未显式定义时，按框架引用中的路由机制从代码推导。
   - spec 和代码均无法确定路径时，禁止猜测，必须询问用户。

   如果本次变更不涉及任何接口 → 提示用户"本次变更不涉及接口，yapi.md 将标记为跳过" → 写入跳过声明后结束。

4. **选择 YApi MCP 服务（MUST — 远程查询前必须确认）**

   检测当前环境中所有可用的 YApi MCP 工具，通过检查哪些 MCP 工具前缀包含 `yapi` 相关工具（如 `mcp__xxx-yapi__get_interface`）。

   提取 MCP 服务名（中间段，如 `base-logCenter-yapi`、`pigeon-admin-yapi`）。

   - 如果只有一个 YApi MCP 服务可用：自动选择
   - 如果有多个：向用户展示选项并等待明确选择
   - 提示："使用 MCP 服务: <service-name>"

   保存选定的 MCP 前缀，用于本次会话中所有 `get_cat_menu`、`get_interface` 等调用。

5. **确定 YApi 分类（支持多分类）**

   将步骤 3 提取的接口按功能模块分组（依据 Controller 归属或 spec 中的模块划分）。

   对每个分组，向用户展示该组接口的目标分类选项并等待明确选择：
   - 通过 MCP `get_cat_menu` 列出已有分类供选择
   - 允许输入新分类名称
   - 如果所有接口属于同一功能模块，仅询问一次

   确定后记录映射关系：接口分组 → 分类名。后续写入 yapi.md 时，每个分组使用独立的 `### <分类名称>` 标题。

   **提问格式示例**（多分组时）：
   ```
   本次变更涉及以下接口分组：
   1. 用户模块：POST /admin/user/list, POST /admin/user/detail
   2. 权限模块：POST /admin/permission/update

   请为每组选择 YApi 分类：
   ```

   **单组简化**：如果所有接口归属同一分组，直接询问一次分类名即可。

6. **确定鉴权类型与调试地址**

   **6a. 鉴权类型**

   向用户展示本次变更的鉴权类型选项并等待明确选择（默认：普通鉴权）：

   | 鉴权类型 | 公共请求头 | curl 认证头 |
   |---------|-----------|------------|
   | 普通鉴权 | `zw-csrf-token: md5(cookie 中的 zw-csrf-token)` | `-H 'Cookie: zw-authorization=<token>; zw-csrf-token=<csrf>' -H 'zw-csrf-token: <md5_of_csrf>'` |
   | 内部调用 | `Auth-Id: <internal_user_id>` | `-H 'Auth-Id: 10001'` |
   | 免鉴权 | （无公共请求头） | （无额外认证头） |

   **6b. 调试地址（curl base URL）**

   统一使用占位符 `http://<dev-domain>`，写入同步配置的「调试地址」字段，所有 curl 示例统一使用此地址。开发者使用时替换为实际开发环境地址。

7. **逐接口三源合并**（核心步骤）

   对每个接口执行以下流程：

   **7a. 远程基准获取（MUST — 不可跳过）**

   通过 MCP `get_interface` 按路径查询远程 YApi：
   - 存在 → 操作类型确认为"更新"，提取远程所有字段作为**基准文档**；同时记录该接口的 `project_id` 和 `interface_id`（用于构造远程地址）
   - 不存在 → 操作类型确认为"新增"，基准为空；远程地址标记为待回填

   **7b. Spec 标注提取**

   从 specs 中提取该接口的定义：
   - 新增字段（spec 中有，基准中无）
   - 修改字段（spec 中与基准不一致：类型变更、必填性变更、含义变更）
   - 删除字段（spec 明确标注移除的）

   **7c. 代码推导补充（条件执行）**

   根据操作类型决定是否执行代码推导：

   **更新接口（代码已存在）— MUST 执行：**
   读取该接口对应的 Controller → Service → Model 代码：
   - 从代码中推导出实际使用的字段（参数获取、返回组装）
   - 对比基准 + spec：如果代码中存在但基准和 spec 均未覆盖的字段 → 标记为"代码推导补充"

   **新增接口（代码尚未实现）— 跳过：**
   - SDD 流程中 yapi-gen 在 apply 之前执行，新接口此时无代码实现
   - 仅使用两个数据源：远程基准（空）+ spec 标注
   - 所有字段统一标记 `🆕 新增（spec定义）`
   - 不得凭空推测字段，spec 未定义的字段不纳入

   **7d. 合并生成**

   将三个来源合并为完整接口定义：
   - 基准字段（远程已有） → 变更列标记 `—`
   - Spec 新增字段 → 变更列标记 `🆕 新增（spec定义）`
   - Spec 修改字段 → 变更列标记 `✏️ 修改（spec变更）`
   - Spec 删除字段 → 变更列标记 `🗑️ 删除（spec删除）`
   - 代码推导补充字段 → 变更列标记 `🆕 新增（代码推导补充）`

   **新增接口**（无远程基准 + 无代码实现）：
   - 所有字段统一标记 `🆕 新增（spec定义）`
   - 禁止出现 `🆕 新增（代码推导补充）` 标记（新接口无代码可推导）

8. **生成 yapi.md（增量写入 + 断点续传）**

   **8a. 检查已有文件**

   如果 `openspec/changes/<name>/yapi.md` 已存在：
   - 解析已有内容，判定每个接口是否完整（包含全部必填区块）
   - 向用户展示状态并选择操作：
     - **续写** — 保留已完成接口，从第一个未完成接口继续
     - **全量重新生成** — 覆盖整个文件

   **8b. 增量写入策略**

   按以下顺序写入（确保中断后可恢复）：
   1. 首次写入：同步配置 + 接口地址速查（占位） + 接口清单标题
   2. 逐接口追加：每个接口生成完毕后立即写入文件
   3. 末尾更新：所有接口完成后，回填接口地址速查代码块

   即使中途中断，已写入的接口内容不丢失，下次可从断点续写。

   **8c. 文档结构**

   按模板格式输出，写入 `openspec/changes/<name>/yapi.md`：
   - 同步配置（鉴权类型 + 调试地址 + 公共请求头）
   - 接口地址速查（代码块）
   - 接口清单（每个接口含完整字段定义 + 变更列）

   格式要求（不变）：
   - 响应信封 {status_code, msg, data, extra} 四字段 required
   - 分页结构 {data, page_info: {page, page_size, total}}
   - 嵌套字段点号路径法
   - 请求参数示例 + 返回数据示例 + curl 调试示例

9. **完整性自检（MUST — 不可跳过）**

   生成完成后逐项验证，缺失任何一项即补全：

   **文档级：**
   - [ ] 同步配置（鉴权类型 + 调试地址 + 公共请求头表）
   - [ ] 接口地址速查代码块（每个接口占两行：名称行 + URL行）

   **每个接口：**
   - [ ] 分类名称（### 标题）
   - [ ] 接口名称（复选框行）
   - [ ] 接口说明
   - [ ] 操作（新增/更新）
   - [ ] 方法 + 路径
   - [ ] 请求参数表（含变更列）
   - [ ] 请求参数示例（完整 JSON）
   - [ ] 返回数据表（含变更列 + 信封四字段）
   - [ ] 返回数据示例（完整 JSON，含信封）
   - [ ] curl 调试示例（可直接执行的完整命令）

   任何一项为空、占位或遗漏 → 立即补全，不得以"后续补充"跳过。

10. **完成提示**

   展示摘要：
   - 接口数量（新增 N 个 / 更新 N 个）
   - 每个接口的变更字段统计
   - "yapi.md 已生成：`openspec/changes/<name>/yapi.md`"
   - "「接口地址速查」中已有远程地址的接口可直接访问；标记为「新增接口」的地址将在 `zwflow-yapi-doc-sync` Skill 完成后自动回填"
   - "请审阅后执行 `zwflow-yapi-doc-sync` Skill 同步到远程 YApi"

**三源合并优先级**

当三个来源对同一字段的定义冲突时：
1. **Spec 定义优先** — spec 是需求规格，具有最高权威性
2. **代码实现次之** — 代码反映实际行为，用于补充 spec 未覆盖的字段
3. **远程基准兜底** — 作为已发布的稳定版本，未被前两者涉及的字段原样保留

**新增接口的合并简化**：
新增接口只有一个有效来源（spec），无优先级冲突。远程基准为空，代码不存在，全部字段来自 spec。

**护栏**

- 更新接口时 MUST 先调用 MCP get_interface 获取远程基准，NEVER 仅从 spec/代码推导
- 新增接口无需调用 get_interface（远程不存在）
- 新增接口无需执行代码推导（SDD 流程中 apply 在 yapi-gen 之后，新接口此时无代码实现）
- 字段来源必须在变更列中标注，禁止模糊标记
- 如果 MCP 调用失败（网络/权限），暂停并告知用户，不得跳过降级为纯推导
- yapi.md 已存在时，解析完成度后询问用户：续写（从断点继续）还是全量重新生成
- 每个接口生成完毕后必须立即写入文件（增量持久化），禁止全部生成完再一次性写入
- 生成完成后不自动执行同步（`zwflow-yapi-doc-sync` Skill），等待用户审阅

**接口地址速查规则**

- URL 格式：`https://doc.wozhangwan.com/project/{project_id}/interface/api/{interface_id}`
- 更新接口：从 MCP `get_interface` 响应中提取 project_id 和 _id（interface_id），构造完整 URL
- 新增接口：gen 阶段无远程 ID，写入占位文本 `（新增接口 — 同步后回填地址）`
- yapi-sync 完成后 MUST 回填新增接口的实际地址（由 zwflow-yapi-doc-sync skill 负责）
- 每个接口占两行：第一行为「分类名-接口名称  方法 路径」，第二行为 URL 或占位文本
- 接口之间空行分隔

**yapi.md 输出格式模板（EXHAUSTIVE — 模板中的每个区块均为必填，禁止省略任何一项）**

```markdown
## 同步配置

鉴权类型：<普通鉴权 | 内部调用 | 免鉴权>
调试地址：http://<dev-domain>

<!-- 根据鉴权类型填充公共请求头：-->
<!-- 普通鉴权 → zw-csrf-token 表 -->
<!-- 内部调用 → Auth-Id 表 -->
<!-- 免鉴权 → 写入"（无公共请求头）" -->

**公共请求头（同步时自动注入每个接口，无需在接口中重复定义）：**

| Header | 值 | 说明 |
|--------|-----|------|
| zw-csrf-token | md5(cookie 中的 zw-csrf-token) | CSRF 校验头 |

---

## 接口地址速查

> 同步完成后，复制下方代码块发送给前端即可按地址查看接口文档。

​```
<分类名称>-<接口名称>  <方法> <路径>
https://doc.wozhangwan.com/project/<project_id>/interface/api/<interface_id>

<分类名称>-<接口名称>  <方法> <路径>
（新增接口 — 同步后回填地址）
​```

---

## 接口清单

### <分类名称>

- [ ] **1** <接口名称>

接口说明：<功能描述>
操作：新增
方法：POST
路径：`/admin/xxx/xxx`

**请求参数：**

| 名称 | 类型 | 是否必须 | 默认值 | 备注 | 变更 |
|------|------|----------|--------|------|------|
| field | string | 是 | | 字段说明 | 🆕 新增（spec定义） |

**请求参数示例：**

​```json
{}
​```

**返回数据：**

| 名称 | 类型 | 是否必须 | 默认值 | 备注 | 变更 |
|------|------|----------|--------|------|------|
| status_code | int | 是 | | 状态码（1=成功） | — |
| msg | string | 是 | | 提示信息 | — |
| data | object | 是 | | 业务数据 | — |
| data.field | string | 是 | | 字段说明 | 🆕 新增（spec定义） |
| extra | object | 是 | | 扩展信息 | — |

**返回数据示例：**

​```json
{
    "status_code": 1,
    "msg": "操作成功",
    "data": {},
    "extra": {}
}
​```

**curl 调试示例：**

<!-- 根据鉴权类型选择对应模板 -->

<!-- 普通鉴权 -->
​```bash
curl -X POST '<调试地址>/admin/xxx/xxx' \
  -H 'Content-Type: application/json' \
  -H 'Cookie: zw-authorization=<token>; zw-csrf-token=<csrf>' \
  -H 'zw-csrf-token: <md5_of_csrf>' \
  -d '{}'
​```

<!-- 内部调用 -->
​```bash
curl -X POST '<调试地址>/admin/xxx/xxx' \
  -H 'Content-Type: application/json' \
  -H 'Auth-Id: 10001' \
  -d '{}'
​```

<!-- 免鉴权 -->
​```bash
curl -X POST '<调试地址>/admin/xxx/xxx' \
  -H 'Content-Type: application/json' \
  -d '{}'
​```
```

**鉴权类型与公共请求头映射**：

| 鉴权类型 | 公共请求头表内容 | curl 认证头 |
|---------|---------------|------------|
| 普通鉴权 | `zw-csrf-token: md5(cookie 中的 zw-csrf-token)` | Cookie + zw-csrf-token |
| 内部调用 | `Auth-Id: <internal_user_id>` | Auth-Id |
| 免鉴权 | 写入"（无公共请求头）"，省略表格 | 无额外头 |

**格式要求**：
- 嵌套字段点号路径法：`data.data[].id`
- 数组元素用 `[]`：`data.items[]`
- 响应信封 {status_code, msg, data, extra} 四字段 required
- 分页 data 内：{data, page_info: {page, page_size, total}}
- 备注列必须填写业务含义
- curl 示例中的地址前缀使用「同步配置」中的调试地址值
- 完成标准：所有接口复选框 `[x]` 后视为同步完成
