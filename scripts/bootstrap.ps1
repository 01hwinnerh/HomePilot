[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name. Install it, then try again."
    }
}

Require-Command uv
Require-Command node
Require-Command pnpm
Require-Command docker

$pythonPath = uv python find 3.12
if ($LASTEXITCODE -ne 0) {
    throw "uv cannot find Python 3.12. Run: uv python install 3.12"
}

Write-Host "uv: $(& uv --version)"
Write-Host "Python 3.12: $pythonPath"
Write-Host "Node: $(& node --version)"
Write-Host "pnpm: $(& pnpm --version)"
Write-Host "Docker Compose: $(& docker compose version)"
Write-Host "Environment command check passed. This script does not install software."
