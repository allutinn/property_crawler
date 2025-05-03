# setup.ps1

Write-Host "🛠️ Running full system setup..."

& "./install_choco.ps1"
& "./install_make.ps1"
& "./setup_env.ps1"

Write-Host "`n✅ All components installed and ready."
