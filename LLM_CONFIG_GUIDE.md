# LLM Configuration Guide

The system now supports both **OpenAI** and **Ollama** for LLM functionality. You can easily switch between them using environment variables in your `.env` file.

## Configuration Options

### Option 1: Use OpenAI (Recommended for Production)

Add/update these lines in your `.env` file:

```env
# LLM Provider Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
```

**Available Models:**
- `gpt-4o-mini` - Fast, cost-effective (recommended)
- `gpt-4o` - Most capable
- `gpt-4-turbo` - Previous generation, still powerful
- `gpt-3.5-turbo` - Fastest, cheapest

### Option 2: Use Ollama (Local/Free)

Add/update these lines in your `.env` file:

```env
# LLM Provider Configuration
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434/v1
LLM_MODEL=gpt-oss:20b
OPENAI_API_KEY=ollama
```

**Requirements:**
- Ollama must be running: `ollama serve`
- Model must be downloaded: `ollama pull gpt-oss:20b`

## Current Configuration

Your current `.env` has:
```env
OLLAMA_URL=http://localhost:11434/v1
LLM_MODEL=gpt-oss:20b
OPENAI_API_KEY=ollama
```

### To Switch to OpenAI:

1. **Uncomment your OpenAI API key** (line 1 in `.env`):
   ```env
   OPENAI_API_KEY=sk-your-openai-key-here
   ```

2. **Add the provider setting**:
   ```env
   LLM_PROVIDER=openai
   OPENAI_MODEL=gpt-4o-mini
   ```

3. **Restart your Streamlit apps** for changes to take effect

## Complete .env Example for OpenAI

```env
# LLM Configuration - OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4o-mini

# Salesforce Configuration
SF_USERNAME="your_username"
SF_PASSWORD='your_password'
SF_SECURITY_TOKEN=your_security_token
SF_DOMAIN=login
SF_ORG_ALIAS=clarit-org

# Redmine Configuration
RM_Username=your_username
RM_Password='your_password'
RM_Security_Token=your_api_token_here
RM_URL='https://redmine.scubeenterprise.com'
RM_VERIFY_SSL=true

# ... rest of your configuration
```

## Testing the Configuration

Test that the LLM is working:

```python
from llm import chat

response = chat(
    "You are a helpful assistant",
    "Say hello and confirm you're working"
)
print(response)
```

## Cost Comparison

### OpenAI (gpt-4o-mini)
- **Input**: $0.15 per 1M tokens
- **Output**: $0.60 per 1M tokens
- Very affordable for most use cases

### Ollama
- **Free** - runs locally
- Requires GPU for good performance
- No API costs

## Which Should You Use?

**Use OpenAI if:**
- You want the best quality responses
- You don't want to manage local infrastructure
- Cost is not a major concern ($5-20/month typical)

**Use Ollama if:**
- You want to keep everything local
- You have a good GPU (like your RTX 3090)
- You want zero API costs
- You're okay with slightly lower quality

## Switching Between Providers

You can easily switch by changing just one line in `.env`:

```env
LLM_PROVIDER=openai  # Use OpenAI
# or
LLM_PROVIDER=ollama  # Use Ollama
```

No code changes needed!
