# 后端 API 文档 (供前端参考)

本文档为前端开发人员提供了与聊天应用后端进行交互所需的所有 API 端点的详细信息。

## 1. 基础 URL

所有 API 端点的基础路径都是 `/api/v1`。

---

## 2. 用户 (Users)

### 2.1. 创建新用户

创建一个新的用户账户。

- **端点**: `POST /users/`
- **请求体 (Request Body)**:
  ```json
  {
    "username": "string",
    "email": "string (optional)"
  }
  ```
- **成功响应 (200 OK)**:
  ```json
  {
    "username": "string",
    "email": "string (optional)",
    "id": integer,
    "created_at": "string (datetime)"
  }
  ```
- **错误响应 (400 Bad Request)**:
  - 如果 `username` 已经存在，会返回：
    ```json
    {
      "detail": "Username already registered"
    }
    ```
- **数据库影响**:
  - 在 `users` 表中插入一条新记录。

### 2.2. 获取用户信息

根据用户名获取单个用户的详细信息。

- **端点**: `GET /users/{username}`
- **路径参数**:
  - `username` (string): 要查询的用户名。
- **成功响应 (200 OK)**:
  ```json
  {
    "username": "string",
    "email": "string (optional)",
    "id": integer,
    "created_at": "string (datetime)"
  }
  ```
- **错误响应 (404 Not Found)**:
  - 如果用户不存在，会返回：
    ```json
    {
      "detail": "User not found"
    }
    ```
- **数据库影响**:
  - 在 `users` 表中执行一次 `SELECT` 查询。

---

## 3. 对话 (Conversations)

### 3.1. 创建新对话

为一个指定的用户创建一个新的空对话。

- **端点**: `POST /conversations/`
- **请求体 (Request Body)**:
  ```json
  {
    "user_id": integer,
    "name": "string (optional)"
  }
  ```
- **成功响应 (200 OK)**:
  - 返回新创建的对话对象，其中最重要的字段是 `id`，前端需要保存它用于后续的聊天。
  ```json
  {
    "user_id": integer,
    "name": "string (nullable)",
    "id": integer,
    "created_at": "string (datetime)"
  }
  ```
- **数据库影响**:
  - 在 `conversations` 表中插入一条新记录。

### 3.2. 获取用户的所有对话

获取指定用户的所有对话列表。

- **端点**: `GET /users/{user_id}/conversations`
- **路径参数**:
  - `user_id` (integer): 用户的 ID。
- **查询参数 (Query Parameters)**:
  - `skip` (integer, optional, default: 0): 跳过的记录数，用于分页。
  - `limit` (integer, optional, default: 10): 返回的最大记录数，用于分页。
- **成功响应 (200 OK)**:
  - 返回一个对话对象的列表。
  ```json
  [
    {
      "user_id": integer,
      "name": "string (nullable)",
      "id": integer,
      "created_at": "string (datetime)"
    },
    ...
  ]
  ```
- **数据库影响**:
  - 在 `conversations` 表中执行一次带 `WHERE`, `OFFSET`, `LIMIT` 的 `SELECT` 查询。

### 3.3. 获取单个对话及其所有消息

获取一个指定的对话，并包含该对话下的所有历史消息。

- **端点**: `GET /conversations/{conversation_id}`
- **路径参数**:
  - `conversation_id` (integer): 对话的 ID。
- **成功响应 (200 OK)**:
  ```json
  {
    "user_id": integer,
    "name": "string (nullable)",
    "id": integer,
    "created_at": "string (datetime)",
    "messages": [
      {
        "role": "string ('user' or 'assistant')",
        "content": "string",
        "id": integer,
        "conversation_id": integer,
        "created_at": "string (datetime)"
      },
      ...
    ]
  }
  ```
- **错误响应 (404 Not Found)**:
  - 如果对话不存在，会返回：
    ```json
    {
      "detail": "Conversation not found"
    }
    ```
- **数据库影响**:
  - 在 `conversations` 表中执行一次 `SELECT`。
  - 在 `messages` 表中执行一次 `SELECT`。

---

## 4. 聊天 (Chat)

### 4.1. 发送消息并获取流式响应

在一个指定的对话中发送一条新消息，并以流式方式接收助手的回复。

- **端点**: `POST /chat`
- **请求体 (Request Body)**:
  ```json
  {
    "conversation_id": integer,
    "message": "string"
  }
  ```
- **成功响应 (200 OK)**:
  - 这是一个**流式响应 (Server-Sent Events)**，`Content-Type` 是 `text/event-stream`。
  - 前端需要监听这个流，并逐块接收数据。每一块数据的格式都是 `data: <content>\n\n`。
  - **示例流**:
    ```
    data: The

    data:  sky

    data:  is

    data:  blue...

    ...
    ```
- **数据库影响**:
  1.  **立即**: 在 `messages` 表中插入一条用户的消息记录。
  2.  **流式响应结束后**: 在 `messages` 表中插入一条助手的完整回复记录。
