# 数据库设计文档

本文档详细描述了聊天应用后端所使用的 PostgreSQL 数据库的表结构。

---

## 1. 核心设计理念

- **多用户支持**: 系统支持多用户，每个对话都与一个用户关联。
- **异步支持**: 所有表的设计都与 SQLAlchemy 的异步 ORM 兼容。
- **自增主键**: 使用整数自增 (`Integer`, `autoincrement=True`) 作为主键，以获得最佳的索引性能。
- **软关联**: 表之间通过 ID 进行关联，但不在数据库层面强制建立外键约束，以获得更高的灵活性和写入性能。数据一致性由应用层保证。
- **时间戳**: 所有表都包含一个 `created_at` 字段，并由数据库服务器自动填充，以记录创建时间。

---

## 2. 表结构详情

### 2.1. `users` 表

该表存储应用的用户信息。

| 字段名      | 数据类型                 | 约束/默认值        | 描述                               |
|-------------|--------------------------|--------------------|------------------------------------|
| `id`        | `Integer`                | **主键**, `autoincrement` | 用户的唯一标识符。                 |
| `username`  | `String`                 | `nullable=False`, `unique=True` | 用户的唯一名称。                   |
| `email`     | `String`                 | `nullable=True`, `unique=True` | 用户的可选邮箱地址，如果提供则必须唯一。 |
| `created_at`| `DateTime(timezone=True)`| `server_default=func.now()` | 用户的创建时间（带时区）。         |

---

### 2.2. `conversations` 表

该表存储每一个独立的对话会话。

| 字段名      | 数据类型                 | 约束/默认值        | 描述                               |
|-------------|--------------------------|--------------------|------------------------------------|
| `id`        | `Integer`                | **主键**, `autoincrement` | 对话的唯一标识符。                 |
| `user_id`   | `Integer`                | `nullable=False`, `index=True` | 关联的用户ID (软关联)。            |
| `name`      | `String`                 | `nullable=True`    | 用户为对话指定的名称，用于UI显示。 |
| `created_at`| `DateTime(timezone=True)`| `server_default=func.now()` | 对话的创建时间（带时区）。         |

---

### 2.3. `messages` 表

该表存储在一次对话中，用户与助手之间的每一条消息。

| 字段名            | 数据类型                 | 约束/默认值        | 描述                               |
|-------------------|--------------------------|--------------------|------------------------------------|
| `id`              | `Integer`                | **主键**, `autoincrement` | 消息的唯一标识符。                 |
| `conversation_id` | `Integer`                | `nullable=False`, `index=True` | 关联的对话ID (软关联)。            |
| `role`            | `String`                 | `nullable=False`   | 消息发送者的角色 (`user` 或 `assistant`)。 |
| `content`         | `Text`                   | `nullable=False`   | 消息的具体文本内容。               |
| `created_at`      | `DateTime(timezone=True)`| `server_default=func.now()` | 消息的创建时间（带时区）。         |
