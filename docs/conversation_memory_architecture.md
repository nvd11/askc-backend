# Deep Dive: Implementing LLM Conversation Memory

## 1. Introduction: Giving LLMs "Memory"

Large Language Models (LLMs) are inherently **stateless**. This means that when you send a new message, the model doesn't "remember" anything you said before. Every interaction is a fresh start.

However, we want to provide users with a "continuous conversation" experience. To achieve this, we implemented an **external memory system**. This document details how we built this system, specifically how we handle independent conversation histories for each user and the optimizations we made for performance.

## 2. Core Implementation Flow

Our conversation memory logic is straightforward and can be summarized in four steps:

1.  **Receive**: The API layer receives the user's new message and the current `conversation_id`.
2.  **Load**: The business layer uses the `conversation_id` to fetch recent history from the database.
3.  **Construct**: The history and the new message are stitched together into a complete "context".
4.  **Invoke**: This "context" is sent to the LLM, enabling it to generate a response based on the conversation history.

Let's dive into the code to see the implementation details.

---

### Step 1: API Interface Layer (`chat_router.py`)

First is the FastAPI router layer, responsible for receiving frontend requests.

**Code Snippet:**
```python
# File: src/routers/chat_router.py

@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
    # ...
):
    # ...
    return StreamingResponse(
        chat_service.stream_chat_response(request, llm_service, db),
        media_type="text/event-stream"
    )
```

Here we receive a `ChatRequest` containing the most critical `conversation_id`. This ID is the key to distinguishing different conversations. The Router layer doesn't handle complex logic; it delegates the task directly to the Service layer.

---

### Step 2: Business Logic Layer (`chat_service.py`)

This is where the core logic resides.

**Code Snippet:**
```python
# File: src/services/chat_service.py

# Define maximum history length
MAX_HISTORY_LENGTH = 20

async def stream_chat_response(
    request: ChatRequest, llm_service: LLMService, db: AsyncSession
):
    # 1. Save the user's new message to the database first
    user_message_to_save = MessageCreateSchema(...)
    await message_dao.create_message(db, message=user_message_to_save)

    # 2. Load conversation history from the database
    # Note: We pass limit=MAX_HISTORY_LENGTH here
    history_from_db = await message_dao.get_messages_by_conversation(
        db, conversation_id=request.conversation_id, limit=MAX_HISTORY_LENGTH
    )
    
    # The database returns the latest messages (descending order) for efficiency.
    # But the LLM needs chronological order (old -> new), so we reverse it.
    history_from_db.reverse()

    # ...
```

**Key Points:**
*   **Save New Message**: Must be saved to the database first so it becomes part of the history.
*   **`MAX_HISTORY_LENGTH`**: We defined a constant here (e.g., 20). This prevents the context from growing indefinitely. Without a limit, as the conversation gets longer, token consumption would explode, potentially exceeding the LLM's context window.
*   **Reverse List**: The database query returns `[Newest Message, 2nd Newest, ...]`, we need to turn it into `[Oldest Message, ..., Newest Message]` for the conversation logic to make sense.

---

### Step 3: Data Access Layer (`message_dao.py`)

The DAO layer handles the dirty work—writing SQL queries.

**Code Snippet:**
```python
# File: src/dao/message_dao.py

async def get_messages_by_conversation(
    db: AsyncSession, 
    conversation_id: int, 
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    
    # Base query: only fetch messages for the current conversation_id
    query = select(messages_table).where(
        messages_table.c.conversation_id == conversation_id
    )
    
    if limit:
        # If there is a limit, sort by time descending and take the latest N
        query = query.order_by(messages_table.c.created_at.desc()).limit(limit)
    else:
        # Otherwise, sort by time ascending (usually for exporting or viewing full history)
        query = query.order_by(messages_table.c.created_at)
    
    # ...
```

**Performance Optimization:**
*   We pushed the `limit` logic down to the database query.
*   **Why?** Imagine a conversation with 1000 messages. If we truncated at the application layer (fetching 1000 messages then `list[-20:]`), it would vastly waste database I/O and network bandwidth.
*   The current approach tells the database directly: "Just give me the latest 20 messages." The database only scans and returns these 20 records, which is highly efficient and memory-friendly.

---

### Step 4: Context Construction & LLM Invocation

After getting the data, the final step is assembling it for the LLM.

**Code Snippet:**
```python
# File: src/services/chat_service.py

    # ... (continuing from Step 2) ...

    # Convert database records into LangChain message objects
    chat_history = []
    for msg in history_from_db:
        if msg['role'] == 'user':
            chat_history.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            chat_history.append(AIMessage(content=msg['content']))

    # Pass the entire history list to the LLM
    llm_stream = llm_service.llm.astream(chat_history)
```

LangChain uses `HumanMessage` and `AIMessage` to distinguish who is speaking. We send this chain of messages to the LLM, and it understands: "Oh, so this is the conversation so far," and generates the next response based on it.

## 3. Summary

The core of this solution lies in:
1.  **Database Persistence**: Ensures no conversation is lost.
2.  **Database-level Limit**: Key to performance, preventing the system from slowing down as conversations grow.
3.  **Dynamic Context Construction**: Assembling "memory" in real-time for each request, making the stateless LLM appear to have memory.
