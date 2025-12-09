# Street Closure Notification Assistant

An intelligent agent that helps you create properly formatted street closure notification emails through conversational interaction.

## Overview

This tool uses an LLM-powered agent to:
- Guide you through gathering all necessary information
- Extract details from your natural language responses
- Generate professionally formatted notification emails
- Provide a preview before finalizing

## How to Use

### Start the Notification Assistant

```powershell
streamlit run notification_ui.py
```

The assistant will open in your browser at `http://localhost:8501`

### Example Conversation

```
🤖: Which street will be closed?
👤: Main Street

🤖: When will the closure start? (Please provide the date)
👤: December 10th, 2025

🤖: What time will the closure begin?
👤: 7 AM

🤖: When will the closure end? (Date)
👤: December 12th

🤖: What time will it reopen?
👤: 6 PM

🤖: What is the reason for this closure?
👤: Water main repairs

🤖: Which area or cross streets are affected?
👤: Between Oak Avenue and Elm Street

🤖: Is there a detour route or alternative route?
👤: Use Park Avenue as alternate route

🤖: Who should residents contact with questions?
👤: Public Works at 555-1234

🤖: Here's your street closure notification:

---
**STREET CLOSURE NOTIFICATION**

**Street:** Main Street
**Location:** Between Oak Avenue and Elm Street

**Closure Period:**
- **Start:** December 10th, 2025 at 7 AM
- **End:** December 12th at 6 PM

**Reason:** Water main repairs

**Detour Information:**
Use Park Avenue as alternate route

**Questions?** Contact: Public Works at 555-1234

We apologize for any inconvenience and appreciate your patience.
---

Does this look good?

👤: yes

🤖: Perfect! Your notification is ready.
```

## Features

### Information Extracted

**Required:**
- Street name
- Start date and time
- End date and time
- Reason for closure
- Affected area/cross streets

**Optional:**
- Detour information
- Contact information
- Additional details

### Output

The assistant generates:
1. **Formatted notification text** - Ready to copy/paste into email
2. **Email subject line** - Auto-generated based on street and date
3. **Download option** - Save as .txt file

## Integration with Ticket System

### Workflow

1. **Create ticket** using `chatbot_ui.py`:
   - Project: (Select your project)
   - Subject: "Street Closure - Notifications" (default)
   - Description: "Please Post Notifications" (default)

2. **When ready to post notifications**, run:
   ```powershell
   streamlit run notification_ui.py
   ```

3. **Agent helps format** the notification email

4. **Copy/download** the formatted notification

5. **Post to email** or notification system

## Files

- **`notification_agent.py`** - Core agent logic for information extraction and formatting
- **`notification_ui.py`** - Streamlit interface for the notification assistant
- **`llm.py`** - LLM integration (shared with other agents)

## Requirements

- Python 3.8+
- Streamlit
- OpenAI package
- LLM server (Ollama or OpenAI API)

Make sure your `.env` file has:
```env
OLLAMA_URL=http://localhost:11434/v1
LLM_MODEL=gpt-oss:20b
OPENAI_API_KEY=ollama
```

## Tips for Best Results

1. **Be specific** - Provide exact dates, times, and street names
2. **Include cross streets** - Helps residents understand the affected area
3. **Mention detours** - Reduces confusion and complaints
4. **Provide contact info** - Allows residents to ask questions

## Customization

You can modify the notification template in `notification_agent.py` in the `get_formatted_notification()` method to match your organization's style.

## Troubleshooting

**LLM Connection Error**: Make sure Ollama is running (`ollama serve`)

**Import Errors**: Ensure all dependencies are installed in your virtual environment

**Streamlit Version Issues**: The code is compatible with both old and new Streamlit versions
