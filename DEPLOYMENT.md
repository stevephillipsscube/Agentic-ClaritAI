# Deployment Guide - Copy to Another Machine

## Option 1: Using Git (Recommended)

### On Current Machine:
```powershell
# Navigate to project directory
cd C:\Users\mrjum\clariti_flow_agent

# Initialize git if not already done
git init

# Add all files
git add .

# Commit
git commit -m "Working Redmine ticket creation app"

# Push to GitHub/GitLab (replace with your repo URL)
git remote add origin https://github.com/yourusername/clariti_flow_agent.git
git push -u origin main
```

### On New Machine:
```powershell
# Clone the repository
git clone https://github.com/yourusername/clariti_flow_agent.git
cd clariti_flow_agent

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy your .env file (see below)
# Create .env with your credentials
```

---

## Option 2: Manual Copy (Simple but less organized)

### Steps:
1. **Copy the entire folder** `C:\Users\mrjum\clariti_flow_agent` to a USB drive or network location
2. **On new machine**, paste the folder
3. **Recreate virtual environment**:
   ```powershell
   cd clariti_flow_agent
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
4. **Update .env file** with new machine's settings if needed

---

## Option 3: Create Deployment Package

### Create a deployment script:
```powershell
# On current machine, create a deployment package
# Exclude unnecessary files

$exclude = @('.venv', '__pycache__', '*.pyc', '.git', '.gemini')
$source = "C:\Users\mrjum\clariti_flow_agent"
$dest = "C:\Users\mrjum\Desktop\clariti_flow_agent_deploy.zip"

# Create zip excluding files
Compress-Archive -Path $source\* -DestinationPath $dest -Force
```

---

## Important Files to Handle

### ⚠️ **DO NOT COPY (recreate on new machine):**
- `.venv\` - Virtual environment (recreate with `python -m venv .venv`)
- `__pycache__\` - Python cache
- `.gemini\` - Local AI conversation data
- `test_notifications.tsv` - Test files

### ✅ **MUST COPY:**
- All `.py` files
- `requirements.txt`
- `.env` file (⚠️ **contains secrets - handle securely**)
- `README.md` (if exists)

### 🔒 **Handle Securely (.env file):**
```
# Don't commit .env to git
# Manually copy or recreate on new machine with:
RM_URL=your_redmine_url
RM_USERNAME=your_username
RM_PASSWORD=your_password
RM_SECURITY_TOKEN=your_api_key
```

---

## Quick Setup on New Machine

```powershell
# 1. Copy or clone project
cd clariti_flow_agent

# 2. Create virtual environment
python -m venv .venv

# 3. Activate
.\.venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create/copy .env file
# Add your Redmine credentials

# 6. Test
streamlit run chatbot_ui.py
```

---

## Recommended Approach

**For version control and collaboration:** Use Git (Option 1)
**For quick one-time copy:** Use manual copy (Option 2)
**For creating a portable package:** Use deployment package (Option 3)

All three work, but Git is best for long-term maintenance and team collaboration.
