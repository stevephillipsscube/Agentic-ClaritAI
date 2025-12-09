# Run Chatbot - Quick Start Script
# This ensures the chatbot runs with the correct Python environment

Write-Host "🤖 Starting Redmine Requirements Chatbot..." -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
$venvPaths = @(
    ".\claritAI\Scripts\Activate.ps1",
    ".\.venv\Scripts\Activate.ps1",
    ".\venv\Scripts\Activate.ps1"
)

$venvFound = $false
foreach ($venvPath in $venvPaths) {
    if (Test-Path $venvPath) {
        Write-Host "✓ Activating virtual environment: $venvPath" -ForegroundColor Green
        & $venvPath
        $venvFound = $true
        break
    }
}

if (-not $venvFound) {
    Write-Host "⚠ No virtual environment found. Using system Python." -ForegroundColor Yellow
}

# Check if Streamlit is installed
try {
    $streamlitVersion = & python -m streamlit --version 2>&1
    Write-Host "✓ Streamlit is installed" -ForegroundColor Green
} catch {
    Write-Host "✗ Streamlit not found. Installing..." -ForegroundColor Red
    & python -m pip install streamlit
}

# Check if openai is installed with correct version
try {
    $openaiCheck = & python -c "from openai import OpenAI; print('OK')" 2>&1
    if ($openaiCheck -like "*OK*") {
        Write-Host "✓ OpenAI package is correctly installed" -ForegroundColor Green
    } else {
        Write-Host "⚠ Upgrading OpenAI package..." -ForegroundColor Yellow
        & python -m pip install --upgrade openai
    }
} catch {
    Write-Host "✗ OpenAI package issue. Installing..." -ForegroundColor Red
    & python -m pip install --upgrade openai
}

Write-Host ""
Write-Host "🚀 Launching chatbot..." -ForegroundColor Cyan
Write-Host "   The chatbot will open in your browser at http://localhost:8501" -ForegroundColor Gray
Write-Host "   Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Run Streamlit
& streamlit run chatbot_ui.py
