# 异步流式服务中的取消处理与数据持久化一致性方案

## 1. 问题背景

在基于 FastAPI 和 Server-Sent Events (SSE) 的 LLM 流式对话服务中，观察到当客户端在生成过程中断开连接（Client Disconnection）或发生服务端超时（Server-side Timeout）时，已生成的 Assistant 响应内容未能持久化至 PostgreSQL 数据库。

**故障现象：**
- 数据库中存在用户提问记录，但对应的 Assistant 回复缺失。
- GKE 日志显示，在异常中断场景下，正常的 `Streaming finished` 和数据保存逻辑未被执行。

---

## 2. 初始分析

通过分析 `src/services/chat_service.py` 的原始代码，我们发现数据保存逻辑仅存在于流式生成完成之后：

```python
# 原始逻辑示意
try:
    llm_stream = llm_service.llm.astream(chat_history)
    async for chunk in llm_stream:
        full_response_content += chunk.content
        yield f"data: {chunk.content}\n\n"
    
    # 只有当循环正常结束，才会执行到这里
    logger.info("Streaming finished.")
    if full_response_content:
        # 保存到数据库
        await message_dao.create_message(db, ...)
except Exception as e:
    logger.exception(...)
```

**原因推断：**
如果客户端（前端 UI）在流式传输过程中断开连接（例如用户刷新页面、关闭标签页），或者 LLM 生成超时，FastAPI/Starlette 会抛出 `asyncio.CancelledError`，导致协程在 `async for` 循环中被立即中断。因此，代码永远无法执行到循环后的保存逻辑，导致已生成的部分内容丢失。

---

## 3. 第一次尝试：捕获 CancelledError

为了解决这个问题，我们尝试捕获 `asyncio.CancelledError` 并在捕获块中执行保存操作。

**修改后的代码结构：**

```python
except asyncio.CancelledError:
    logger.warning(f"Stream cancelled...")
    if full_response_content:
        # 尝试使用当前的 db session 保存
        await message_dao.create_message(db, ...)
    raise
```

**遇到的新问题：**
部署后，我们在日志中观察到了新的错误：
`sqlalchemy.dialects.postgresql.asyncpg.InterfaceError: cannot call Transaction.rollback(): the underlying connection is closed`

**原因分析：**
当 `CancelledError` 发生时，FastAPI 框架正在取消当前的请求处理任务（Task）。
1. 任务被取消导致与其关联的依赖资源（如通过 `Depends(get_db_session)` 获取的 `db` Session）开始清理或已经失效。
2. 此时在 `except` 块中尝试复用这个已经处于“半关闭”或“被取消”状态的 Session 进行数据库操作，会引发 `InterfaceError`。
3. 此外，在已取消的 Task 中直接 `await` 耗时操作本身就是不安全的，可能会被再次取消。

---

## 4. 最终解决方案：独立任务 + 新 Session + 重试机制

为了彻底解决问题，我们采取了以下策略：

1.  **使用后台任务 (`asyncio.create_task`)**：将保存操作从当前（正在被取消的）请求上下文中剥离，放入一个新的后台 Task 中执行。这确保了即使主请求结束，保存逻辑也能继续运行。
2.  **创建全新 Session**：不再复用请求级别的 `db` Session，而是使用 `AsyncSessionFactory()` 手动创建一个全新的、干净的数据库连接。
3.  **引入重试机制**：为了防止在这个时间窗口内连接池出现竞态条件（例如拿到了一个正好被 Engine 清理的连接），我们添加了简单的重试逻辑。

**最终代码实现 (`src/services/chat_service.py`)：**

```python
from sqlalchemy.exc import InterfaceError, OperationalError
from src.configs.db import AsyncSessionFactory

async def save_partial_response_task(conversation_id: int, content: str):
    """
    后台任务：在流被中断时保存部分回复。
    创建一个全新的 DB session，并包含重试机制以处理连接竞态条件。
    """
    for attempt in range(3):
        try:
            # 关键点：手动创建新 Session，与原请求隔离
            async with AsyncSessionFactory() as session:
                assistant_message_to_save = MessageCreateSchema(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=content,
                )
                await message_dao.create_message(session, message=assistant_message_to_save)
                logger.info(f"Saved partial assistant response in background task: conv={conversation_id} len={len(content)}")
                return  # 成功则退出
        except (InterfaceError, OperationalError, OSError) as e:
            # 如果遇到连接关闭等错误，进行重试
            if attempt < 2:
                logger.warning(f"Failed to save partial response (attempt {attempt + 1}), retrying: {e}")
                await asyncio.sleep(0.1)
            else:
                logger.error(f"Failed to save partial response after {attempt + 1} attempts: {e}")
        except Exception as e:
            logger.error(f"Failed to save partial response: {e}")
            break

async def stream_chat_response(request: ChatRequest, llm_service: LLMService, db: AsyncSession):
    # ... (初始化代码) ...
    full_response_content = ""
    response_saved = False
    
    try:
        # ... (流式生成循环) ...
        
    except asyncio.CancelledError:
        # 捕获客户端断开
        logger.warning(f"Stream cancelled (client disconnected)...")
        if full_response_content and not response_saved:
            # 关键点：将保存操作放入后台任务，不 await 它
            asyncio.create_task(save_partial_response_task(request.conversation_id, full_response_content))
        raise  # 重新抛出异常以让框架正确处理取消

    except asyncio.TimeoutError:
        # 处理 LLM 超时
        # ... 类似逻辑，使用后台任务保存 ...
```

## 5. 验证结果

部署修复版本后，我们在 GKE 日志中成功观察到了预期的行为：

1.  **触发断开**：日志显示 `Stream cancelled (client disconnected) for conversation 8...`
2.  **后台保存成功**：紧接着显示 `Saved partial assistant response in background task: conv=8 len=2007`

数据成功写入数据库，彻底解决了因网络中断或超时导致的消息丢失问题。

