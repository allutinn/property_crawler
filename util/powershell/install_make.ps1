# install_make.ps1
$env:Path += ";C:\ProgramData\chocolatey\bin"

Write-Host "📦 Installing make with Chocolatey..."
choco install make -y

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Make installed successfully."
    make --version
} else {
    Write-Host "❌ Make installation failed."
    exit 1
}
