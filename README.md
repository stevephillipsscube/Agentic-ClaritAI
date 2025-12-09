# Agentic ClaritAI - Redmine Ticket Creation

Streamlit application for creating Redmine tickets with AI-powered notification parsing and validation.

## Features

- ✅ AI-powered notification data parsing
- ✅ Interactive table editing with validation
- ✅ HTML table rendering in Redmine (with text wrapping)
- ✅ Tab-delimited TSV file attachment for scripts
- ✅ Automatic edit saving before ticket creation
- ✅ Feature type (ID: 2) and Normal priority (ID: 2) metadata

## Setup

### 1. Clone the Repository
```bash
git clone https://github.com/stevephillipsscube/Agentic-ClaritAI.git
cd Agentic-ClaritAI
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# or
source .venv/bin/activate     # Mac/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```
RM_URL=https://your-redmine-instance.com
RM_USERNAME=your_username
RM_PASSWORD=your_password
RM_SECURITY_TOKEN=your_api_key
```

**⚠️ Never commit the `.env` file to Git!**

### 5. Run the Application
```bash
streamlit run chatbot_ui.py
```

## Usage

1. Paste your notification data into the chat
2. Review and edit the parsed table
3. Click "Confirm & Continue"
4. Click "Post to Redmine"
5. Result: Ticket created with HTML table + TSV attachment

## Project Structure

```
clariti_flow_agent/
├── chatbot_ui.py              # Main Streamlit app
├── notification_agent.py      # Notification parsing & validation
├── requirements_agent.py      # Requirements extraction (if used)
├── llm.py                     # LLM configuration
├── tools/
│   └── redmine_ops.py         # Redmine API operations
├── .env                       # Environment variables (DO NOT COMMIT)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Key Features

### HTML Table Rendering
Tickets are created with a properly formatted HTML table that:
- Wraps text automatically
- Uses proper column widths (20% / 30% / 50%)
- Preserves multi-line email content with `<br/>` tags

### TSV File Attachment
Every ticket includes a `notifications.tsv` attachment with perfect tab-delimited data for:
- Excel import
- Script processing
- Data analysis

### Edit Saving
Changes made in the UI are automatically captured in session state and saved before posting to Redmine.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
