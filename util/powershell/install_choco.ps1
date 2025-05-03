# Installs choco to windows env

Write-Host "Removing any existing Chocolatey installation..."
Remove-Item -Recurse -Force "C:\ProgramData\chocolatey" -ErrorAction SilentlyContinue

Write-Host "Reinstalling Chocolatey from official source..."
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

Write-Host "Chocolatey installation complete. Please restart PowerShell."
