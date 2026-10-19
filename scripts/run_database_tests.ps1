param(
    [string]$DatabaseHost = $(if ($env:PGHOST) { $env:PGHOST } else { '127.0.0.1' }),
    [int]$DatabasePort = $(if ($env:PGPORT) { [int]$env:PGPORT } else { 5432 }),
    [string]$DatabaseName = $(if ($env:PGDATABASE) { $env:PGDATABASE } else { 'banking_fraud' }),
    [string]$DatabaseUser = $(if ($env:PGUSER) { $env:PGUSER } else { 'postgres' }),
    [string]$PsqlPath = ''
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

if ([string]::IsNullOrWhiteSpace($PsqlPath)) {
    $localPsql = Join-Path $root 'tools\postgresql16-bin\pgsql\bin\psql.exe'
    if (Test-Path -LiteralPath $localPsql) {
        $PsqlPath = $localPsql
    } else {
        $command = Get-Command psql -ErrorAction SilentlyContinue
        if ($command) {
            $PsqlPath = $command.Source
        }
    }
}

if ([string]::IsNullOrWhiteSpace($PsqlPath) -or -not (Test-Path -LiteralPath $PsqlPath)) {
    throw 'psql was not found. Install PostgreSQL or pass -PsqlPath explicitly.'
}

$testFile = Join-Path $root 'tests\integration\database_smoke.sql'
& $PsqlPath -h $DatabaseHost -p $DatabasePort -U $DatabaseUser -d $DatabaseName -v ON_ERROR_STOP=1 -f $testFile
if ($LASTEXITCODE -ne 0) {
    throw "Database integration tests failed with exit code $LASTEXITCODE."
}

Write-Output 'Database integration tests passed.'
