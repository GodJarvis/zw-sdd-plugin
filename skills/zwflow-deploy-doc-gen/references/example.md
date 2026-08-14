# 标准输出示例

以下是一份符合规范的上线文档示例，生成时严格对标此格式。

---

```markdown
# 朱雀v1.6上线文档

上线时间：2026-06-12

* [ ] 上线文档审核：@谢富生

版本内容：

* 在调用中心新增「工具调用记录」页面，记录所有工具类服务的调用日志
* 在调用中心新增「计费配置」页面，支持运营自助维护各服务各档分辨率的官方价/折扣价
* 调用完成后按计费规则自动计算单次费用并写入调用记录

* [ ] 第一步：线上MySQL数据库执行SQL @姓名

​```text/x-sql
CREATE TABLE `tool_pricing_tier` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工具计费档位';
​```
​```text/x-sql
INSERT INTO tool_pricing_tier (...) VALUES (...);
​```

* [ ] 第二步：线上环境创建Kafka新的topic：phoenix_media_enhance_log @姓名

* [ ] 第三步：大数据创建线上环境hologres表 @姓名 @姓名

* [ ] 第四步：大数据启动消费者，将朱雀网关推送的数据填入holo表，将朱雀后端推送的价格回填入holo表 @姓名 @姓名

* [ ] 第五步：朱雀项目合并代码：

    * [ ] v1.6->release: @姓名
        {待填写 MR 链接}

    * [ ] release->master: @姓名
        {待填写 MR 链接}

* [ ] 第六步：前端项目合并代码：

    * [ ] v1.6->release 并配置线上菜单路由 @姓名

    * [ ] release->master: @姓名
        {待填写 MR 链接}

* [ ] 第七步：朱雀线上服务器新建kafka消费 @姓名

    | 任务名称 | 任务描述 | 任务命令 | 定时时间 | 相关队列 |
    | --- | --- | --- | --- | --- |
    | ToolCallPricingConsumer | 工具调用计费 Kafka 消费者 | php bin/hyperf.php kafka:consume -c ToolCallPricingConsumer -w 2 --coroutines 2 | 常驻 | topic: `phoenix_media_enhance_log` / group: `phoenix_media_enhance_pricing` |

* [ ] 第八步：启动ToolCallPricingConsumer消费 @姓名
```

---

## 格式要点

1. **步骤间无 `---` 分隔线** — 步骤直接紧跟
2. **无 `###` 子标题** — 所有内容在步骤 checkbox 层级下
3. **SQL 仅代码块** — 无"来源"、"说明"、"部署顺序"等注释
4. **版本内容** — 每条一个 `*` 开头的一句话，无编号无嵌套
5. **人员占位** — 统一 `@姓名`，不同步骤可有不同/多个负责人
6. **步骤描述具体** — "线上MySQL数据库执行SQL" 而非 "执行SQL"
7. **合并代码** — 嵌套 checkbox，含分支方向（version→release, release→master）
8. **文档末尾** — 最后一个步骤后即结束，无"上线后确认事项"等额外 section
