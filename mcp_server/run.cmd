@echo off
rem Launch the CredVault MCP server on Windows (cmd.exe), bootstrapping a venv on first run.
rem Setup output goes to stderr: stdout is reserved for the MCP protocol.
setlocal
set "DIR=%~dp0"
set "VENV=%DIR%.venv"
if not exist "%VENV%\Scripts\credvault-mcp.exe" (
  where py >nul 2>nul && (py -3 -m venv "%VENV%" 1>&2) || (python -m venv "%VENV%" 1>&2)
  "%VENV%\Scripts\python.exe" -m pip install --quiet --upgrade pip 1>&2
  "%VENV%\Scripts\python.exe" -m pip install --quiet "%DIR%." 1>&2
)
"%VENV%\Scripts\credvault-mcp.exe" %*
