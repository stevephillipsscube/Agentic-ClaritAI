# =========================== llm.py =============================
import os

# Handle both old and new openai package versions
try:
    from openai import OpenAI  # New version (1.0+)
    OPENAI_NEW_VERSION = True
except ImportError:
    try:
        import openai  # Old version (pre-1.0)
        OPENAI_NEW_VERSION = False
    except ImportError:
        raise RuntimeError("openai python package not installed. Run: pip install --upgrade openai")


def _get_llm_config():
    """Get LLM configuration from environment variables."""
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()  # 'openai' or 'ollama'
    
    if provider == "openai":
        # OpenAI configuration
        return {
            "provider": "openai",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": None,  # Use default OpenAI endpoint
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),  # Default to gpt-4o-mini
        }
    else:
        # Ollama configuration (default)
        return {
            "provider": "ollama",
            "api_key": os.getenv("OPENAI_API_KEY", "ollama"),  # Dummy key for Ollama
            "base_url": os.getenv("OLLAMA_URL", "http://localhost:11434/v1"),
            "model": os.getenv("LLM_MODEL", "gpt-oss:20b"),
        }


def chat(system_prompt: str, user_prompt: str) -> str:
    """
    Send a chat request to the configured LLM (OpenAI or Ollama).
    
    Configuration via .env:
    - LLM_PROVIDER: 'openai' or 'ollama' (default: 'ollama')
    - OPENAI_API_KEY: Your OpenAI API key (required for OpenAI)
    - OPENAI_MODEL: Model to use (default: 'gpt-4o-mini')
    - OLLAMA_URL: Ollama server URL (default: 'http://localhost:11434/v1')
    - LLM_MODEL: Ollama model name (default: 'gpt-oss:20b')
    """
    config = _get_llm_config()
    
    if OPENAI_NEW_VERSION:
        # New OpenAI API (1.0+)
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        resp = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        txt = resp.choices[0].message.content or "{}"
    else:
        # Old OpenAI API (pre-1.0)
        openai.api_key = config["api_key"]
        if config["base_url"]:
            openai.api_base = config["base_url"]
        
        resp = openai.ChatCompletion.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        txt = resp.choices[0].message.content or "{}"

    # Return just the JSON if present
    start, end = txt.find("{"), txt.rfind("}")
    return txt[start : end + 1] if 0 <= start < end else txt


def chat_with_history(system_prompt: str, conversation_history: list) -> str:
    """
    Chat with conversation history for multi-turn dialogues.
    
    Args:
        system_prompt: System instructions for the LLM
        conversation_history: List of message dicts with 'role' and 'content' keys
                             Example: [{"role": "user", "content": "Hello"}, 
                                      {"role": "assistant", "content": "Hi!"}]
    
    Returns:
        The assistant's response as a string
    """
    config = _get_llm_config()
    
    # Build messages with system prompt first, then history
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)

    if OPENAI_NEW_VERSION:
        # New OpenAI API (1.0+)
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        resp = client.chat.completions.create(
            model=config["model"],
            messages=messages,
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""
    else:
        # Old OpenAI API (pre-1.0)
        openai.api_key = config["api_key"]
        if config["base_url"]:
            openai.api_base = config["base_url"]
        
        resp = openai.ChatCompletion.create(
            model=config["model"],
            messages=messages,
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""


