# Post-Mortem: Why Did Chat Interruption Lead to Data Loss?

This document records a severe data consistency issue we encountered in our streaming chat service: when the network was interrupted or timed out, the user could see partial responses, but this partial content was not saved to the database.

## 1. What Happened?

Our chat feature is streaming. This means the AI sends characters to the frontend one by one as they are generated.

**The Symptom:**
While a user was chatting with the AI, if:
*   The user closed the browser/refreshed the page (connection disconnected).
*   Or the AI took too long to think and timed out.

The result was: The database only contained the user's question, but **none of the AI's answer**. Even if the AI had generated most of the content, it was lost as if it never happened.

---

## 2. Why Did It Get Lost?

We dug into the code of `chat_service.py` and found the culprit:

```python
# Original Logic (Simplified)
try:
    async for chunk in llm_stream:
        # Generate and send to frontend simultaneously
        full_response += chunk
        yield chunk
    
    # Save to DB only after the loop finishes
    save_to_db(full_response)

except Exception:
    # Error handling
```

**Root Cause:**
When the connection is disconnected, FastAPI raises an `asyncio.CancelledError` exception exactly when the code executes the `yield` line.
This exception **immediately interrupts** the execution of the entire function. The code jumps out directly, never having a chance to execute `save_to_db` below. So, the `full_response` that was already generated disappears with memory reclamation.

---

## 3. Pitfall Record: First Attempt

Our initial thought was simple: since it throws an exception, why not save it in `except`?

```python
except asyncio.CancelledError:
    # Attempt to salvage: save generated content
    if full_response:
        await save_to_db(full_response)
    raise
```

**Result: Failed.**
Log error: `InterfaceError: cannot call Transaction.rollback(): the underlying connection is closed`.

**Why didn't it work?**
Because when the request is cancelled, the database Session (`db`) injected by FastAPI also enters a "cleanup" state. We were trying to reuse a **closing** database connection to write data within a **dying** request context, which naturally caused an error.

---

## 4. Final Solution: The Escape Plan

To completely solve this problem, we needed the save operation to "escape" the current request context that was destined to fail.

**Strategy:**
1.  **Background Task**: Use `asyncio.create_task` to start a new asynchronous task. It's like sending a clone to do the work; if the main body dies, the clone is unaffected.
2.  **Fresh Connection**: The clone cannot use the main body's database connection (because it's closing). It must request a new, clean database connection for itself.

**Code Implementation:**

```python
# src/services/chat_service.py

# Dedicated background save task
async def save_partial_response_task(conversation_id, content):
    # Request a fresh Session, independent of the original request
    async with AsyncSessionFactory() as session:
        await message_dao.create_message(session, ...)

# Main flow
async def stream_chat_response(...):
    try:
        # ... streaming generation ...
    except asyncio.CancelledError:
        logger.warning("Client disconnected!")
        # Start background task to save data, don't await it, let it run
        asyncio.create_task(save_partial_response_task(cid, full_response))
        raise
```

## 5. Verification

After deploying the fix, we simulated a network disconnection scenario.
**GKE Logs showed:**
1.  `Stream cancelled (client disconnected)...` (Main request detected disconnection)
2.  `Saved partial assistant response in background task...` (Background task successfully took over and saved the data)

The problem is perfectly solved. Now, no matter when the conversation is interrupted, the generated content will be safely recorded.
