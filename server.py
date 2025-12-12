from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import text
from contextlib import asynccontextmanager
import os

# Import the routers
from src.routers import chat_router, user_router, conversation_router
from src.configs.db import get_async_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Testing database connection...")
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful!")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    yield
    # Clean up code here if needed

# Get root_path from an environment variable. Defaults to "/chat-api-svc" if not set.
root_path = os.getenv("ROOT_PATH", "/chat-api-svc")

# Initialize the FastAPI app
app = FastAPI(
    title="ChatGPT-style Streaming API",
    description="A simple API to demonstrate streaming chat responses.",
    version="1.0.0",
    root_path=root_path,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include the routers
app.include_router(chat_router.router)
app.include_router(user_router.router)
app.include_router(conversation_router.router)

@app.get("/")
def read_root():
    """A simple root endpoint to confirm the server is running."""
    # logger.debug("Root endpoint was hit.")
    return {"message": "Welcome to the Streaming API. See /docs for details."}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server...")
    # Disable Uvicorn's default logging to let Loguru take full control
    # uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
    uvicorn.run(app, host="0.0.0.0", port=8000)
