-- SQL script to create the initial database schema for the chat application.
-- This script is designed for PostgreSQL and is idempotent (re-runnable).

-- Create the users table if it does not exist
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create the conversations table if it does not exist
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create an index on conversations.user_id if it does not exist
CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations (user_id);

-- Create the messages table if it does not exist
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    role VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create an index on messages.conversation_id if it does not exist
CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages (conversation_id);

-- Optional: Add comments to describe the tables and columns
COMMENT ON TABLE users IS 'Stores user information.';
COMMENT ON COLUMN users.username IS 'Unique username for each user.';
COMMENT ON COLUMN users.email IS 'Optional, but unique email address for each user.';

COMMENT ON TABLE conversations IS 'Stores individual conversation sessions.';
COMMENT ON COLUMN conversations.user_id IS 'The ID of the user who owns this conversation (soft reference).';

COMMENT ON TABLE messages IS 'Stores individual messages within a conversation.';
COMMENT ON COLUMN messages.conversation_id IS 'The ID of the conversation this message belongs to (soft reference).';
COMMENT ON COLUMN messages.role IS 'The role of the message sender, e.g., ''user'' or ''assistant''.';
