[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

function Assert-LastExitCode {
    param([Parameter(Mandatory = $true)][string]$Step)

    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

Write-Host "[1/4] Verifying backend tests and lint..."
Push-Location (Join-Path $projectRoot "backend")
try {
    & uv run pytest
    Assert-LastExitCode "Backend tests"

    & uv run ruff check .
    Assert-LastExitCode "Backend lint"
}
finally {
    Pop-Location
}

Write-Host "[2/4] Verifying frontend build, tests, and lint..."
Push-Location (Join-Path $projectRoot "frontend")
try {
    & pnpm run build
    Assert-LastExitCode "Frontend build"

    & pnpm run test
    Assert-LastExitCode "Frontend tests"

    & pnpm run lint
    Assert-LastExitCode "Frontend lint"
}
finally {
    Pop-Location
}

Write-Host "[3/4] Verifying Docker Compose configuration and containers..."
Push-Location $projectRoot
try {
    & docker compose config --quiet
    Assert-LastExitCode "Docker Compose configuration"

    & docker compose ps
    Assert-LastExitCode "Docker Compose status"

    $redisResponse = & docker compose exec -T redis redis-cli ping
    Assert-LastExitCode "Redis connectivity"
    if ($redisResponse.Trim() -ne "PONG") {
        throw "Redis returned an unexpected response: $redisResponse"
    }

    $mysqlResponse = & docker compose exec -T mysql sh -c 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -Nse "SELECT 1;"'
    Assert-LastExitCode "MySQL connectivity"
    if ($mysqlResponse.Trim() -ne "1") {
        throw "MySQL returned an unexpected response: $mysqlResponse"
    }

    $testDatabaseGuard = & docker compose exec -T -e MYSQL_DATABASE=homepilot -e MYSQL_TEST_DATABASE=homepilot mysql sh /docker-entrypoint-initdb.d/10-create-test-database.sh 2>&1
    if ($LASTEXITCODE -eq 0) {
        throw "Test database guard accepted the business database name."
    }
    if (($testDatabaseGuard -join "`n") -notmatch "must differ") {
        throw "Test database guard returned an unexpected error: $testDatabaseGuard"
    }

    $qdrantStatus = (Invoke-WebRequest -Uri "http://127.0.0.1:6333/healthz").StatusCode
    if ($qdrantStatus -ne 200) {
        throw "Qdrant health check returned HTTP $qdrantStatus."
    }

    $minioStatus = (Invoke-WebRequest -Uri "http://127.0.0.1:9000/minio/health/live").StatusCode
    if ($minioStatus -ne 200) {
        throw "MinIO health check returned HTTP $minioStatus."
    }
}
finally {
    Pop-Location
}

Write-Host "[4/4] HomePilot scaffold verification passed."
