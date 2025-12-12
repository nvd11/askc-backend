# 课后作业：构建一个 ChatGPT 风格的应用

**目标**: 使用 **FastAPI** (后端) 和 **lit** (前端) 构建一个迷你的 ChatGPT 克隆，要求实现消息流式传输和持久化存储。

---

## 🧩 概览

- **后端**: FastAPI 服务器，提供流式聊天端点，并将对话历史记录存储在 PostgreSQL 中。
- **前端**: lit 应用，实时渲染和流式传输聊天消息，并支持对话选择。

---

## A. FastAPI 后端

### 代理式 AI 框架
使用 pydanticAI 框架 https://github.com/pydantic/pydantic-ai，你可以选择任何你喜欢的大语言模型（LLM）。

### 1. 流式聊天端点

- 必须使用 FastAPI 框架
- **端点**: `POST /api/v1/chat`
- **接收**: 对话历史 + 用户新消息
- 使用 OpenAI (或其他替代品) 并设置 `stream=True`
- 通过 **StreamingResponse** 或 **SSE** (服务器发送事件) 将助手的响应流式传输回客户端
- **请求头**: 例如 `Content-Type: text/event-stream`

### 2. 对话持久化

- **数据库**: 使用 PostgreSQL，并进行数据库迁移 (例如，使用 Alembic)
- **数据表结构**:
  - `conversations`: id, created_at (创建时间)
  - `messages`: id, conversation_id (对话ID), role (角色: user/assistant), content (内容), timestamp (时间戳)
- **端点**:
  - `GET /api/v1/conversations`: 列出所有对话
  - `GET /api/v1/conversations/{id}`: 获取指定对话的消息历史
  - `POST /api/v1/conversations`: 创建新对话 (或在 `/chat` 端点中自动创建)
- 将用户消息和整合后的助手响应存储在 `messages` 表中

#### 替代方案

如果你无法使用 PostgreSQL 进行数据库迁移，你也可以使用单个 JSON 文件。当然，这是一种更简单的实现方式，效果不如使用 PostgreSQL，仅在无法成功配置 PostgreSQL 时使用此方案。

### 3. 附加功能 (可选)

- 简单的**身份验证**或用户识别
- 为后端逻辑编写**单元测试**
- 为 API/数据库故障提供健壮的错误处理

---

## B. Lit 前端

### 1. 聊天界面

- **组件**:
  - 能够区分角色的聊天气泡列表
  - 输入框 + “发送” 按钮
- 点击发送时: 调用后端 `POST /api/v1/chat`
- 消费并**流式处理响应**，逐块追加助手返回的文本

### 2. 对话管理

- 通过 `GET /api/v1/conversations` 列出对话
- 允许选择或创建新对话
- 使用 `GET /api/v1/conversations/{id}` 加载历史记录

### 3. 流式用户体验

- 逐步显示助手的回复
- 为流式内容提供“打字”风格的渲染效果
- 平滑滚动和加载状态

### 4. 用户体验注意事项

- 加载指示器、自动滚动到底部、错误消息
- 适配移动端和桌面端的响应式布局

### 5. 附加功能

这些是附加功能，你应该在完成基本需求后再实现它们。

- 渲染助手消息中的 Markdown (例如代码块)
- 界面优化: 暗黑模式、时间戳、格式化
- 构建代理式 AI，并使用一个新框架来集成一个简单的 DuckDuckGo 搜索工具，以便从互联网上搜索更多结果
- 使用 [ag-ui](https://github.com/ag-ui-protocol/ag-ui) 协议
