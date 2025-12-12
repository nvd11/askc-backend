from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    MetaData,
    func,
)

# Create a MetaData instance
metadata = MetaData()

# Define the 'users' table
users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String, nullable=False, unique=True),
    Column("email", String, nullable=True, unique=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

# Define the 'conversations' table
conversations_table = Table(
    "conversations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("name", String, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

# Define the 'messages' table
messages_table = Table(
    "messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("conversation_id", Integer, nullable=False, index=True),
    Column("role", String, nullable=False),
    Column("content", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)
