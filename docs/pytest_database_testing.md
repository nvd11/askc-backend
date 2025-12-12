# 在 Pytest 中使用 SQLAlchemy 进行异步数据库测试

本文档详细解释了在 `pytest` 环境下，如何使用 SQLAlchemy 的异步功能来管理数据库连接和状态，以确保测试的隔离性和可靠性。

## 1. Pytest Fixture 核心概念：作用域 (Scope)

`@pytest.fixture` 是 `pytest` 中一个非常强大的功能，它用于为测试函数提供数据、对象或预备/清理环境。其中，`scope` 参数是控制 fixture生命周期的关键。

`scope` 参数决定了一个 fixture 实例会被创建和销毁的频率。它有以下几个选项，按从小到大的顺序排列：

| Scope         | 描述                                                               | 适用场景                                                     |
|---------------|--------------------------------------------------------------------|--------------------------------------------------------------|
| **`function`** (默认) | 每个测试**函数**运行一次。这是最高级别的隔离性。                   | 数据库事务、独立的测试数据、需要重置状态的 mock 对象。       |
| `class`       | 每个测试**类**只运行一次。                                         | 针对某个类的所有方法共享的、较昂贵的资源。                   |
| `module`      | 每个测试**文件 (.py)** 只运行一次。                               | 整个文件中的所有测试共享的、创建开销很大的资源（如数据库连接池）。 |
| `package`     | 每个测试**包 (目录)** 只运行一次。                                | 整个包中的所有测试共享的资源。                               |
| `session`     | 整个**测试会话** (即一次 `pytest` 命令的运行) 只运行一次。         | 全局配置、整个测试过程只需建立一次的连接（如数据库引擎）。     |

在我们的数据库测试策略中，我们组合使用了不同的 `scope`：
- `db_engine` 使用 `scope="module"`: 因为数据库引擎的创建开销较大，我们希望在一个测试文件中它只被创建一次。
- `db_session` 使用 `scope="function"`: 因为我们希望每个测试函数都在一个独立的、干净的事务中运行，测试结束后立即回滚，互不干扰。

## 2. 核心概念：MetaData 对象

`MetaData` 对象可以被看作是您数据库 schema 在 Python 代码中的一个“注册表”或“目录”。它是一个容器，用于存放所有与它关联的 `Table` 对象的定义。在我们的项目中，`src/models/tables.py` 中定义的所有 `Table` 对象都注册到了一个全局的 `metadata` 实例上。这使得我们可以执行强大的 schema 级别的操作，如 `metadata.create_all()` 和 `metadata.drop_all()`。

---

## 2. 测试隔离策略

为了确保每个单元测试都在一个独立、干净的环境中运行，不受其他测试的影响，我们需要实现一种“测试隔离”策略。主要有两种方法：

### 策略一：每次重建 (Recreation per Test) - 我们当前使用的方法

这是最直观、最健壮的方法，不依赖特定数据库的事务特性。

#### 示例代码

```python
# test/dao/test_user_dao.py
@pytest.mark.asyncio
async def test_create_user():
    # 1. 为此测试创建独立的引擎
    engine = create_async_engine(DATABASE_URL)
    
    # 2. 在测试开始时，物理删除并重建所有表
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)

    # 3. 执行测试逻辑 (包括 commit)
    async with AsyncSession(engine) as session:
        # ... DAO 调用 ...
    
    # 4. 在测试结束时，销毁引擎以关闭所有物理连接
    await engine.dispose()
```

#### 关键点解析

- **`metadata.drop_all()` / `create_all()`**:
    - **作用**: 实现测试隔离。
    - **原理**: 在每个测试函数开始时，物理地删除并重新创建所有数据库表。这保证了每个测试面对的都是一个全新的、空的数据库。
    - **DDL 与事务**: 您提出了一个很好的问题：`DROP`/`CREATE` 是 DDL，为何要放在 `engine.begin()` 事务块中？在 **PostgreSQL** 中，DDL 是事务性的，可以被包含在事务中。但在这里，使用 `engine.begin()` 的主要目的是为了**优雅地管理连接的生命周期**（获取连接、执行操作、释放连接），而不是为了 DDL 的原子性。

- **`engine.dispose()`**:
    - **作用**: 实现资源清理。
    - **原理**: 关闭并销毁 `engine` 内部维护的**整个连接池**中的所有物理数据库连接。
    - **与 `rollback` 的区别**: `dispose()` **不会**回滚任何已提交的事务。它只负责关闭网络连接。在我们的例子中，测试数据的清理是由下一个测试开始时的 `drop_all` 完成的。

- **优点**: 极其可靠，跨数据库兼容性好。
- **缺点**: 性能较低。对于每个测试都删除和创建表，开销很大。

---

### 策略二：事务回滚 (Transaction Rollback) - 更高效的策略

这是一种更高级、性能更好的方法，它利用了数据库的事务特性。

#### 理论代码

```python
# conftest.py - (这是一个理论上的例子，我们当前项目没有使用)

@pytest.fixture(scope="session")
async def engine():
    # 整个测试会话只创建一个引擎
    db_engine = create_async_engine(DATABASE_URL)
    yield db_engine
    await db_engine.dispose()

@pytest.fixture(scope="session", autouse=True)
async def setup_database(engine):
    # 在会话开始时创建一次表，结束时删除一次
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)

@pytest.fixture(scope="function")
async def db_session(engine) -> AsyncSession:
    # 为每个测试函数提供一个特殊的“回滚”会话
    async with engine.connect() as connection:
        async with connection.begin() as transaction: # 开始一个事务
            async with AsyncSession(bind=connection) as session:
                yield session
                # 测试结束后，回滚这个事务，撤销所有 DML 操作
                await transaction.rollback()
```

#### 关键点解析

- **`setup_database` Fixture**: 在整个测试会话开始时创建一次所有表，在会话结束时删除它们。
- **`db_session` Fixture**:
    - **`connection.begin()`**: 在每个测试函数开始时，它会启动一个事务（或者在支持的数据库上是一个嵌套事务/保存点）。
    - **`yield session`**: 测试函数在自己的这个“子事务”中运行，可以自由地 `COMMIT` 数据。
    - **`await transaction.rollback()`**: **这是核心**。当测试函数结束时，无论测试成功与否，也无论函数内部是否执行了 `commit`，这个 fixture 都会**强制回滚**最外层的事务。
- **效果**: `test_create_user` 中 `COMMIT` 的数据实际上只被提交到了一个未关闭的事务中。测试一结束，整个事务就被回滚，数据库瞬间恢复到测试开始前的状态。

- **优点**: **速度极快**。`ROLLBACK` 是一个非常轻量级的操作。
- **缺点**: 实现更复杂，且依赖于数据库对事务性 DDL 的支持。

### 总结

我们当前采用的**策略一（每次重建）**虽然性能稍低，但它更简单、直观，并且能 100% 保证每个测试的隔离性。对于大多数项目来说，这都是一个非常可靠和推荐的起点。
