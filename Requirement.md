# Take‑Home Assignment: ChatGPT‑Style App

**Goal**: Build a minimal ChatGPT clone using **FastAPI** (backend) and **Lit** (frontend) with message streaming and persistence.

---

## 🧩 Overview

- **Backend**: FastAPI server exposing streaming chat endpoint + conversation history storage in PostgreSQL.
- **Frontend**: lit app that renders and streams chat messages live, with conversation selection.

---

## A. FastAPI Backend

### Agentic AI Framework
Use the pydanticAI framework https://github.com/pydantic/pydantic-ai , you may use any LLM of your choice

### 1. Streaming Chat Endpoint

- Must use FastAPI framework
- **Endpoint**: `POST /api/v1/chat`
- Accepts: conversation history + new user message
- Uses OpenAI (or alternative) with `stream=True`
- Streams assistant response back to client via **StreamingResponse** or **SSE**
- Headers: e.g. `Content-Type: text/event-stream`

### 2. Conversation Persistence

- **Database**: PostgreSQL with migrations (e.g. using Alembic)
- **Schema**:
  - `conversations`: id, created_at
  - `messages`: id, conversation_id, role (user/assistant), content, timestamp
- **Endpoints**:
  - `GET /api/v1/conversations`: list conversations
  - `GET /api/v1/conversations/{id}`: fetch message history
  - `POST /api/v1/conversations`: create new (or auto-create in `/chat`)
- Store user messages and assembled assistant response in `messages`

#### Alternative

If you are not able to use PostgresSQL to do the migrations, you can also use a single json file. Of course, this is a much simplier implementation, and will not be as good as using a PostgresSQL method, only use this if you are unable to get it to work with PostgresSQL. 

### 3. Bonus (Optional)

- Simple **authentication** or identification
- **Unit tests** for backend logic
- Robust error handling for API/DB failures

---

## B. Lit Frontend

### 1. Chat UI

- **Components**:
  - Chat bubble list distinguishing roles
  - Input field + “Send” button
- On send: call backend `POST /api/v1/chat`
- Consume and **stream response**, appending assistant text chunk by chunk

### 2. Conversation Management

- List conversations via `GET /api/v1/conversations`
- Allow selection or creation of a new conversation
- Load history with `GET /api/v1/conversations/{id}`

### 3. Streaming UX

- Display assistant replies progressively
- Provide “typing”-style rendering of streamed content
- Smooth scrolling and loading states

### 4. UX Considerations

- Loading indicators, scroll-to-bottom, error messages
- Responsive layout for mobile + desktop

### 5. Bonus Features

These are bonus features that you should impement only when you have fulfilled the basic requirements.

- Markdown rendering of assistant messages (e.g. code blocks)
- UI polish: dark mode, timestamps, formatting
- Build agentic AI, and use a new framework to use a simple duckduckgo search tool to search the internet for more results
- Use the [ag-ui](https://github.com/ag-ui-protocol/ag-ui) protocol
