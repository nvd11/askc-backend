# Database Testing in Pytest: Ensuring Isolation

When writing unit tests involving a database, the biggest challenge is **"Isolation"**. If Test A inserts a record, and Test B runs while that record is still there, Test B might fail because of that extra data.

This document records two strategies we explored for achieving perfect database isolation in `pytest`, and why we chose the current one.

## 1. Core Concepts

*   **Fixture**: Pytest's mechanism for handling "setup" and "teardown" for tests.
*   **Scope**:
    *   `function`: Runs once per test function (most common, best isolation).
    *   `session`: Runs once per entire test session (suitable for heavy operations like engine initialization).
*   **MetaData**: SQLAlchemy's "catalog" that holds all table definitions. We can use it to create or drop all tables in one go.

---

## 2. Strategy 1: The Brute Force Way (Recreation per Test)

This is the method **currently used** in our project. Its logic is straightforward: **Before each test starts, wipe the database clean and rebuild it.**

### Code Example

```python
# test/dao/test_user_dao.py

@pytest.mark.asyncio
async def test_create_user():
    # 1. Prepare engine
    engine = create_async_engine(DATABASE_URL)
    
    # 2. [CRITICAL] Clean slate: Drop all tables, then Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)

    # 3. Run test
    async with AsyncSession(engine) as session:
        # ... Insert data, Assert ...
    
    # 4. Clean up connection
    await engine.dispose()
```

### Deep Dive

*   **Why do this?**
    *   It guarantees that every test faces an **absolutely clean, empty** database.
    *   You don't need to worry about leftover garbage data from previous tests.
    *   It's very simple to implement and doesn't require deep knowledge of database transaction isolation levels.

*   **What does `engine.dispose()` do?**
    *   It **cuts off connections**.
    *   It does **not** roll back data. Data cleanup relies on the `drop_all` at the start of the *next* test (or the current test).
    *   Its purpose is to prevent the database connection pool from filling up if we run many tests.

*   **Pros**: Robust! Zero chance of data pollution.
*   **Cons**: Slow. Creating and dropping tables for every single test has overhead, though it's fast enough on local SQLite, it might be slower on a real PostgreSQL.

---

## 3. Strategy 2: Transaction Rollback

This is a more advanced technique, suitable for projects where speed is critical.

### Core Idea

Instead of physically deleting tables, we leverage the database's **Transaction** mechanism:
1.  Before a test starts, begin a transaction.
2.  During the test, insert/delete/update whatever you want.
3.  After the test ends, **force a ROLLBACK** of that transaction.

It's like writing a bunch of stuff in a document and then clicking "Don't Save". The database instantly reverts to its original state.

### Why not use it yet?
Although it's faster, it's more complex to implement correctly (requires carefully designed `conftest.py` fixtures). Given our current test volume is manageable, the simplicity of Strategy 1 offers a better tradeoff.

---
