# Launch the CredVault MCP server on Windows (PowerShell 5.1+ / pwsh), bootstrapping a venv on first run.
# All setup output goes to stderr: stdout is reserved for the MCP protocol.
$ErrorActionPreference = 'Stop'
$dir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $dir '.venv'
$exe  = Join-Path $venv 'Scripts\credvault-mcp.exe'

if (-not (Test-Path $exe)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { $out = & py -3 -m venv $venv 2>&1 }
    else { $out = & python -m venv $venv 2>&1 }
    $out | ForEach-Object { [Console]::Error.WriteLine($_) }
    $vpy = Join-Path $venv 'Scripts\python.exe'
    & $vpy -m pip install --quiet --upgrade pip 2>&1 | ForEach-Object { [Console]::Error.WriteLine($_) }
    & $vpy -m pip install --quiet $dir 2>&1 | ForEach-Object { [Console]::Error.WriteLine($_) }
}
& $exe @args
exit $LASTEXITCODE
