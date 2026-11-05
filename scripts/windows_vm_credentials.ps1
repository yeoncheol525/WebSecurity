$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$credentialFolder = Join-Path $projectRoot 'results\vm'
New-Item -ItemType Directory -Path $credentialFolder -Force | Out-Null
$credential = Get-Credential -Message 'MiniShop Ubuntu VM SSH login. Enter the existing Ubuntu username and password. Do not send passwords in chat.'
if ($null -eq $credential) { exit 1 }
$credential | Export-Clixml -LiteralPath (Join-Path $credentialFolder 'ubuntu-credential.clixml')
Write-Host 'Saved with Windows user encryption. This window will close.'
