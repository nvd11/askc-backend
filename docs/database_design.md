# Database Design: The Data Foundation for High-Concurrency Chat

This document records our PostgreSQL database design philosophy. Our goal was to build a lightweight architecture that supports high-concurrency writes while remaining flexible enough for rapid iteration.

## 1. Design Philosophy: Simplicity First, Efficiency Priority

At the outset, we established several core principles:

*   **Async First**: Since the entire application layer is fully asynchronous (FastAPI + Asyncio), our database layer must also fully embrace async (SQLAlchemy Async ORM + asyncpg) to ensure database I/O never becomes a bottleneck in high-concurrency scenarios.
*   **Soft Relations**: We made a bold decision—**not to enforce foreign key constraints at the database level**.
    *   *Why?* This significantly improves write performance (the database doesn't need to check foreign key integrity) and offers greater flexibility for sharding or data migration in the future.
    *   *What's the cost?* Data consistency (e.g., ensuring `messages.conversation_id` corresponds to a real conversation) is entirely guaranteed by our application logic. This places higher demands on code quality but trades off for better performance and flexibility.
*   **Auto-increment Primary Keys**: We chose the simplest integer auto-increment ID (`Integer`, `autoincrement`). Compared to UUIDs, it offers significant advantages in indexing efficiency and storage space, which is crucial for massive data like chat logs.

---

## 2. Table Structure Overview

We designed only three core tables, keeping it simple and clear.

### 2.1. `users` Table: User Center

Think of this as our user roster.

| Field Name  | Type                     | Key Attributes        | Role                                                                 |
|-------------|--------------------------|-----------------------|----------------------------------------------------------------------|
| `id`        | `Integer`                | **PK**, Auto-inc      | Unique user ID.                                                      |
| `username`  | `String`                 | Not Null, **Unique**  | User's login name, our primary lookup key.                           |
| `email`     | `String`                 | Nullable, **Unique**  | User's email. Nullable because some third-party logins might not provide it. |
| `created_at`| `DateTime(timezone=True)`| Default: Server Time  | Timestamp of when the user joined.                                   |

### 2.2. `conversations` Table: Chat Containers

Every new dialogue, short or long, gets a record here.

| Field Name  | Type                     | Key Attributes        | Role                                                                 |
|-------------|--------------------------|-----------------------|----------------------------------------------------------------------|
| `id`        | `Integer`                | **PK**, Auto-inc      | Unique conversation ID.                                              |
| `user_id`   | `Integer`                | Not Null, **Indexed** | Marks which user this conversation belongs to. Indexed for fast retrieval of a user's history. |
| `name`      | `String`                 | Nullable              | Title of the conversation (e.g., "Discussion about Python").         |
| `created_at`| `DateTime(timezone=True)`| Default: Server Time  | Timestamp of when the conversation started.                          |

### 2.3. `messages` Table: Chat Logs

This is the largest table, storing all chat content.

| Field Name        | Type                     | Key Attributes        | Role                                                                 |
|-------------------|--------------------------|-----------------------|----------------------------------------------------------------------|
| `id`              | `Integer`                | **PK**, Auto-inc      | Unique message ID.                                                   |
| `conversation_id` | `Integer`                | Not Null, **Indexed** | Marks which conversation this message belongs to. The core index for querying chat history. |
| `role`            | `String`                 | Not Null              | Only two values: `user` (human) or `assistant` (AI).                 |
| `content`         | `Text`                   | Not Null              | The actual message text. Using `Text` type to support long content.  |
| `created_at`      | `DateTime(timezone=True)`| Default: Server Time  | Timestamp sent, used to reconstruct the dialogue sequence chronologically. |
