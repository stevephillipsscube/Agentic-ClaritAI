# Agentic Requirements Chatbot for Redmine

An intelligent chatbot that conducts conversational requirements gathering before creating Redmine work tickets.

## Features

- 🤖 **Conversational Interface**: Natural dialogue instead of rigid forms
- 🧠 **Intelligent Extraction**: Uses LLM to extract structured information from free-form responses
- ✅ **Validation**: Ensures all required fields are collected and validates project names
- 📝 **Confirmation Step**: Reviews extracted information before ticket creation
- 🔄 **Iterative Refinement**: Asks clarifying questions for vague requirements

## Prerequisites

1. **Python 3.8+**
2. **Ollama** (or OpenAI API)
   - For Ollama: Install from https://ollama.ai
   - Start Ollama: `ollama serve`
   - Pull a model: `ollama pull gpt-oss:20b` (or your preferred model)
3. **Required Python packages**:
   ```bash
   pip install streamlit openai python-dotenv requests pyyaml
   ```

## Configuration

### Environment Variables (.env)

```env
# LLM Configuration
OLLAMA_URL=http://localhost:11434/v1
LLM_MODEL=gpt-oss:20b
OPENAI_API_KEY=ollama  # or your actual OpenAI key

# Redmine Configuration
RM_URL=https://your-redmine-instance.com
RM_USERNAME=your_username
RM_PASSWORD=your_password
RM_SECURITY_TOKEN=your_api_token
```

### Chatbot Configuration

Edit `config/chatbot_prompts.yml` to customize:
- Agent personality and behavior
- Required vs optional fields
- Validation rules
- Conversation prompts

## Usage

### Start the Chatbot

```bash
streamlit run chatbot_ui.py
```

The chatbot will:
1. Greet you and ask which project the ticket is for
2. Extract information from your responses
3. Ask follow-up questions for missing or vague details
4. Show a summary for confirmation
5. Create the Redmine ticket upon confirmation

### Example Conversation

```
🤖: Hello! I'm here to help you create a work ticket. Which project is this ticket for?

👤: I need a ticket for the Website Redesign project

🤖: Great! What should be the title or subject of this ticket?

👤: Fix the broken contact form

🤖: Can you provide more details about what needs to be done?

👤: The contact form on the homepage isn't submitting. Users click submit but nothing happens. 
    We need to debug the JavaScript and fix the form handler.

🤖: Here's a summary of the ticket:
    **Project:** Website Redesign
    **Subject:** Fix the broken contact form
    **Description:** The contact form on the homepage isn't submitting...
    
    Does this look correct?

👤: Yes

🤖: Perfect! Created Redmine Issue #1234: Fix the broken contact form
```

## Files

- **`chatbot_ui.py`**: Streamlit UI for the chatbot
- **`requirements_agent.py`**: Core agent logic for conversation management and information extraction
- **`llm.py`**: LLM integration (supports Ollama and OpenAI)
- **`tools/redmine_ops.py`**: Redmine API integration
- **`config/chatbot_prompts.yml`**: Configuration for agent behavior and prompts
- **`test_agent.py`**: Test script to verify agent functionality

## Testing

Run the test script to verify the agent works:

```bash
python test_agent.py
```

This will simulate a conversation and show the extracted information.

## Troubleshooting

### "Connection error" when running

**Problem**: The LLM server (Ollama) is not running.

**Solution**:
```bash
# Start Ollama
ollama serve

# In another terminal, verify it's running
curl http://localhost:11434/v1/models
```

### "Project not found"

**Problem**: The project name doesn't match exactly.

**Solution**: The agent uses fuzzy matching, but try using the exact project name from Redmine.

### Chatbot asks too many questions

**Solution**: Provide more details in your initial responses. The agent will ask fewer follow-ups if you're comprehensive upfront.

## Architecture

```
User Input
    ↓
RequirementsAgent.process_user_response()
    ↓
LLM extracts structured information
    ↓
Agent validates and checks completeness
    ↓
[Missing info?] → Ask next question → Loop
    ↓
[Complete?] → Generate summary → Confirm
    ↓
Create Redmine Ticket
```

## Customization

### Change Required Fields

Edit `requirements_agent.py`:

```python
def get_missing_required_fields(self) -> List[str]:
    required = ["project_id", "subject", "description", "priority"]  # Add fields
    # ...
```

### Modify Agent Personality

Edit `config/chatbot_prompts.yml`:

```yaml
agent:
  personality: "professional, thorough, and friendly"  # Change this
```

### Use OpenAI Instead of Ollama

Update `.env`:

```env
OLLAMA_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-your-actual-key-here
```

## License

MIT License - feel free to modify and use as needed.
