# 后端开发计划：基于 FastAPI 的 ChatGPT 风格应用

本文档根据需求，为后端开发制定详细的计划。

---

## 数据库表设计 (Database Schema)

根据项目需求，数据库将包含 `conversations` 和 `messages` 两张核心表。

详细的表结构、字段定义、数据类型和关系请参考独立的 **[数据库设计文档](docs/database_design.md)**。

---

## 1. 项目初始化与环境设置 (Phase 1)

- **目标**: 搭建项目基础架构，完成数据库配置和初始化。
- **任务**:
    - **1.1. 项目结构**: 创建标准的 FastAPI 项目目录结构 (例如，包含 `app`, `models`, `schemas`, `api` 等模块)。
    - **1.2. 依赖安装**: 初始化 Python 虚拟环境，并在 `requirements.txt` 中添加以下核心依赖：
        - `fastapi`: Web 框架。
        - `uvicorn[standard]`: ASGI 服务器。
        - `sqlalchemy`: ORM 工具。
        - `psycopg2-binary`: PostgreSQL 驱动。
        - `alembic`: 数据库迁移工具。
        - `pydantic-ai`: AI 代理框架。
        - `openai`: (或其他 LLM) SDK。
        - `python-dotenv`: 环境变量管理。
    - **1.3. 数据库配置**:
        - 使用 SQLAlchemy 定义数据库连接 URL。
        - 定义 `conversations` 和 `messages` 数据表模型 (使用 SQLAlchemy ORM)。
    - **1.4. 数据库迁移**:
        - 初始化 Alembic，配置其指向正确的数据库和模型。
        - 生成初始迁移脚本，并在数据库中执行，以创建数据表。
- **产出**:
    - 一个可以成功运行并连接到数据库的 FastAPI 基础应用。
    - 数据库中已创建 `conversations` 和 `messages` 表。

---

## 2. 对话持久化 API 开发 (Phase 2)

- **目标**: 实现管理对话历史记录的 RESTful API。
- **任务**:
    - **2.1. Pydantic 模型**: 为 API 请求和响应创建 Pydantic 模型 (`schemas`)，以实现数据校验和序列化。
    - **2.2. 数据库交互层 (DAO)**: 创建一个 `dao` 或 `crud` 模块，封装所有与数据库表的交互逻辑 (增、删、改、查)。API 端点将通过调用此层来操作数据，实现业务逻辑与数据访问的解耦。
    - **2.3. 创建对话**: 实现 `POST /api/v1/conversations` 端点，调用 DAO 层创建一个新的空对话。
    - **2.4. 列出对话**: 实现 `GET /api/v1/conversations` 端点，调用 DAO 层查询并返回所有对话的列表。
    - **2.5. 获取对话历史**: 实现 `GET /api/v1/conversations/{id}` 端点，调用 DAO 层获取指定对话的所有历史消息。
- **产出**:
    - 一套完整的 CRUD API，用于前端管理对话。
    - API 通过 Swagger UI 进行了自记录。

---

## 3. 核心流式聊天 API 开发 (Phase 3)

- **目标**: 实现核心的流式聊天功能，并与持久化层集成。
- **任务**:
    - **3.1. LLM 集成**: 集成 `pydantic-ai` 框架，并配置一个 LLM (例如 OpenAI GPT-4)。
    - **3.2. 实现聊天端点**: 创建 `POST /api/v1/chat` 端点。
    - **3.3. 端点逻辑**:
        1.  接收请求体，包含 `conversation_id` 和用户新消息 `content`。
        2.  将用户的消息立即存入 `messages` 表。
        3.  从数据库加载该 `conversation_id` 的所有历史消息。
        4.  调用 `pydantic-ai` 的流式接口 (`stream=True`)，将历史消息和新消息传递给 LLM。
        5.  使用 FastAPI 的 `StreamingResponse` 并设置 `Content-Type: text/event-stream`，将 LLM 返回的数据块通过 SSE (服务器发送事件) 格式实时推送给客户端。
        6.  在数据流传输完成后，将 LLM 返回的完整响应聚合成一条消息，并存入 `messages` 表。
- **产出**:
    - 一个功能完备、支持流式响应和持久化存储的聊天 API。

---

## 4. 测试与完善 (Phase 4)

- **目标**: 确保后端服务的稳定性和可靠性。
- **任务**:
    - **4.1. 单元测试**: 使用 `pytest` 和 `httpx` 为所有 API 端点编写单元测试和集成测试。
    - **4.2. 错误处理**: 创建一个 FastAPI 中间件，用于捕获全局异常，并返回统一格式的错误响应 (例如，HTTP 500 或 404)。
    - **4.3. (可选) 用户隔离**: 实现一个简单的用户识别机制。例如，要求客户端在请求头中传递 `X-User-ID`，并在所有数据库查询中加入该条件，以隔离不同用户的对话数据。
- **产出**:
    - 一套高代码覆盖率的测试用例。
    - 一个更加健壮和可靠的后端服务。

---

## 5. 文档与部署 (Phase 5)

- **目标**: 方便他人理解、使用和部署此项目。
- **任务**:
    - **5.1. API 文档**: 检查并完善 FastAPI 自动生成的 OpenAPI (Swagger) 文档，确保所有端点、模型和字段都有清晰的描述。
    - **5.2. 项目文档**: 编写 `README.md`，详细说明：
        - 项目功能。
        - 如何设置 `.env` 文件 (环境变量)。
        - 如何安装依赖、运行数据库迁移和启动本地服务。
        - API 的使用示例。
    - **5.3. 容器化**:
        - 编写 `Dockerfile` 来构建后端应用的镜像。
        - 编写 `docker-compose.yml` 来一键启动后端服务、PostgreSQL 数据库和（可选的）前端应用。
- **产出**:
    - 清晰的 API 文档和项目说明文档。
    - 一套完整的容器化部署方案，实现一键启动。
