# setup_env.ps1

# Navigate to project root (one level up from script location)
Set-Location "$PSScriptRoot/../.."

Write-Host "🐍 Creating Python virtual environment in project root..."
python -m venv .venv

if (-Not (Test-Path ".venv/Scripts/Activate.ps1")) {
    Write-Host "❌ Failed to create virtual environment"
    exit 1
}

Write-Host "⬆️  Installing requirements..."
. .\.venv\Scripts\Activate.ps1
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt

Write-Host "`n✅ Environment setup complete."
