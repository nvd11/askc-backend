import os
from langchain_deepseek import ChatDeepSeek
from src.configs.config import yaml_configs
from loguru import logger

def get_deepseek_llm():
    """
    Initializes and returns a ChatDeepSeek instance.
    It resolves the API key from an environment variable just-in-time.
    """
    # Get the placeholder value from the config, which should be the env var name
    api_key_env_var = yaml_configs["deepseek"]["api-key"]
    base_url = yaml_configs["deepseek"]["base-url"]

    # Resolve the key from the environment at the moment it's needed.
    resolved_api_key = os.getenv(api_key_env_var)
    
    if not resolved_api_key:
        logger.error(f"CRITICAL: Environment variable '{api_key_env_var}' for DeepSeek not found!")
        # Fallback to using the placeholder, which will cause an auth error, but prevents a crash.
        resolved_api_key = api_key_env_var

    llm = ChatDeepSeek(
        model="deepseek-chat",
        temperature=0.2,
        max_tokens=None,
        api_key=resolved_api_key,
        base_url=base_url,
    )
    return llm
