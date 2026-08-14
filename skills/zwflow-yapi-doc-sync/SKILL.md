---
name: zwflow-yapi-doc-sync
description: "将 yapi.md 中的接口同步到远程 YApi（通过 MCP）。当用户想要同步接口文档、推送接口到 YApi、或继续之前中断的 YApi 同步时触发。"
---

将 yapi.md 中定义的接口同步到远程 YApi（通过 MCP），支持基于复选框的断点续传。

**输入**：可选指定 change 名称。未指定时从上下文推断或提示选择。

**步骤**

1. **选择 change**

   如果提供了名称，直接使用。否则：
   - 从对话上下文中推断用户提到的 change
   - 如果只有一个活跃 change，自动选择
   - 如果有多个，执行 `openspec list --json` 获取列表，向用户展示选项并等待明确选择

   始终提示："正在为 change: <name> 同步 YApi"

2. **选择 YApi MCP 服务（MUST — 同步前必须确认）**

   询问用户要同步到哪个 MCP 服务。

   检测当前环境中所有可用的 YApi MCP 工具，通过检查哪些 MCP 工具前缀包含 `yapi` 相关工具（如 `mcp__xxx-yapi__save_interface`）。

   提取 MCP 服务名（中间段，如 `base-logCenter-yapi`、`pigeon-admin-yapi`）。

   - 如果只有一个 YApi MCP 服务可用：自动选择
   - 如果有多个：向用户展示可用 MCP 服务选项并等待明确选择
   - 提示："使用 MCP 服务: <service-name>"

   保存选定的 MCP 前缀，用于本次会话的所有后续调用。

3. **检查并读取 yapi.md**

   检查 `openspec/changes/<change-name>/yapi.md` 是否存在：

   - **不存在** → 提示用户："该 change 尚未生成接口文档。请先执行 `zwflow-yapi-doc-gen` Skill <name> 生成 yapi.md，审阅确认后再执行同步。" → 停止
   - **存在但包含占位声明**（"待通过 `zwflow-yapi-doc-gen` Skill 生成接口文档"）→ 同上提示 → 停止
   - **存在且包含"跳过 YApi 同步"** → 提示"本次变更不涉及接口" → 停止
   - **正常存在** → 读取内容，继续下一步

4. **解析同步状态**

   从 yapi.md 中提取：
   - **同步配置**：鉴权类型、公共请求头定义
   - **接口清单**：所有接口条目及其复选框状态

   **公共请求头处理**：
   - 读取「公共请求头」表格，根据鉴权类型确定 `req_headers` 值
   - 普通鉴权：`[{name: "zw-csrf-token", value: "", example: "md5_of_csrf_cookie", desc: "CSRF 校验头"}]`
   - 内部调用：`[{name: "Auth-Id", value: "", example: "10001", desc: "内部服务调用用户ID"}]`
   - 免鉴权：不传 `req_headers`
   - 此 `req_headers` 在步骤 5 中自动注入每个接口，无需接口单独定义
   - 注意：Cookie（zw-authorization、zw-csrf-token）由浏览器自动携带，不写入 YApi req_headers

   统计进度：
   - 总接口数
   - 已完成（`- [x]`）
   - 剩余（`- [ ]`）

   如果全部已完成：提示"所有接口已同步！"并停止。

   显示进度："进度: N/M 个接口已同步。从第 #X 个接口继续。"

5. **同步接口（循环）**

   对每个未勾选的接口（`- [ ]`），按顺序执行：

   a. **提示**："同步中: [方法] [路径] — [接口名称]"

   b. **确定 YApi 分类 ID**：
      - 使用选定 MCP 的 `get_cat_menu` 查找与接口"分类"字段匹配的分类 ID
      - 如果分类不存在，使用 `add_cat` 创建
      - 禁止跳过分类确认：yapi.md 中未指定分类时必须中断并询问用户

   c. **从接口段落构建 MCP 参数**：
      - `method`：默认 `"POST"`（除非 yapi.md 明确指定其他方法）
      - `path`：直接使用 yapi.md 中已生成的路由路径（yapi-gen 阶段已按规则生成）
      - `title`：接口标题名称
      - `catid`：已解析的分类 ID
      - `req_body_type`：固定 `"json"`
      - `req_body_is_json_schema`：固定 `true`
      - `req_body_other`：将请求参数表转为 JSON Schema（含 `type: "object"` + `required` 数组 + `properties`）
      - `req_headers`：使用步骤 4 中从「公共请求头」解析的值，自动注入每个接口
      - `res_body_type`：固定 `"json"`
      - `res_body_is_json_schema`：固定 `true`
      - `res_body`：将返回数据表转为 JSON Schema（外层为 `{status_code, msg, data, extra}` 信封，四字段均 required，业务字段在 `data.properties` 内）
      - `status`："done"
      - `switch_notice`：false

   d. **调用选定 MCP 的 `save_interface`**，传入构建的参数

   e. **成功时**：
      1. 更新 yapi.md，将该接口的 `- [ ]` 改为 `- [x]`
      2. **立即回填接口地址（MUST）**：
         - 从 `save_interface` 响应中提取接口 ID；如果响应未包含，则通过 MCP `list_cat`（按 catid 查询该分类下所有接口列表）并按 `path` 字段匹配定位刚同步的接口，获取 `_id`（interface_id）和 `project_id`
         - 在 yapi.md 的「## 接口地址速查」中找到该接口对应的行：
           - 若为占位文本 `（新增接口 — 同步后回填地址）`：替换为实际 URL `https://doc.wozhangwan.com/project/{project_id}/interface/api/{interface_id}`
           - 若已有 URL：保持不变
         - 如果无法获取接口 ID（MCP 异常）：保留占位文本，输出警告但不中断流程

   f. **失败时**：报告错误，不更新复选框，暂停并询问用户操作

   g. **继续**处理下一个未勾选接口

6. **完成**

   当所有接口同步完毕：
   - 显示最终进度："全部 M/M 个接口同步成功。"
   - 扫描「## 接口地址速查」确认是否仍有未回填的占位文本，如有则列出并告知用户
   - 提示："YApi 同步完成。「接口地址速查」已更新，可复制发送给前端。"
   - 若尚未生成评审摘要，提示执行 `zwflow-review-doc-gen` Skill <change-name> 生成评审摘要。

**JSON Schema 转换规则**

将参数表转为 JSON Schema 时：

- `int` → `{"type": "integer"}`
- `string` → `{"type": "string"}`
- `float`/`double`/`decimal` → `{"type": "number"}`
- `bool`/`boolean` → `{"type": "boolean"}`
- `array` → `{"type": "array", "items": {...}}`
- `object` → `{"type": "object", "properties": {...}}`
- 点路径字段表示嵌套：`data.data[].id` → `data` 是 object，内层 `data` 是 array，items 含 `id`
- "是否必须" = "是" → 将字段名加入父级的 `required` 数组
- "备注" → schema 中的 `description` 字段
- **「变更」列处理**：该列仅供人工阅读，构建 JSON Schema 时完全忽略。标记为 🗑️ 删除 的字段不纳入 schema，其余字段（—/🆕 新增/✏️ 修改）全部正常纳入

响应转换示例：
```json
{
  "type": "object",
  "properties": {
    "status_code": {"type": "integer", "description": "状态码（1=成功）"},
    "msg": {"type": "string", "description": "提示信息"},
    "data": {
      "type": "object",
      "properties": {
        "id": {"type": "integer", "description": "记录ID"}
      },
      "required": ["id"]
    },
    "extra": {"type": "object", "description": "扩展信息"}
  },
  "required": ["status_code", "msg", "data", "extra"]
}
```

**护栏规则**
- 开始同步前必须检测并确认 MCP 服务
- 始终先读取 yapi.md 检查当前状态
- 不要重新同步已勾选的接口（尊重 `[x]`）
- 每次成功同步后立即更新复选框（检查点机制）
- MCP 调用出错时暂停并报告——不要静默跳过或重试
- 尊重操作类型：新增表示创建，更新表示修改（save_interface 通过路径匹配自动处理）
- 不要修改 yapi.md 中的接口定义内容，只更新复选框和「接口地址速查」区块
- 如果同步配置中的鉴权类型为空或无法识别，先询问用户再继续
- 一次同步会话中所有 MCP 工具调用必须使用同一个选定的 MCP 服务前缀
