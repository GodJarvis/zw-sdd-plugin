---
author: <操作人姓名>
version: <标准版本号，如 v2.1.0，对应目录版本标识 v2-1-0；非版本开发填"项目维护"，对应 maintenance>
created: YYYY-MM-DD
updated: YYYY-MM-DD
branch: <当前分支名>
depends_on: []
---

## 背景（Why）

<!-- 解释变更动机，解决什么问题？为什么现在做？ -->

## 变更内容（What Changes）

<!-- 描述变更内容，具体说明新功能、修改或删除的内容。破坏性变更标注 **BREAKING** -->

## 能力（Capabilities）

### 新增能力（New Capabilities）
<!-- 引入的新能力，使用 kebab-case 命名（例如 user-auth、data-export、api-rate-limiting），每个创建 specs/<name>/spec.md -->
- `<name>`: <此能力的简要描述>

### 修改能力（Modified Capabilities）
<!-- 现有能力的需求正在变更（不仅仅是实现细节）。
     仅当规范级行为变更时在此列出。每个需要 delta 规范文件。
     使用 openspec/specs/ 中的现有规范名称。如果没有需求变更，请留空。 -->
- `<existing-name>`: <变更的需求内容>

## 影响面（Impact）

<!-- 受影响的代码、API、依赖、系统。涉及第三方服务时须说明降级方案 -->
