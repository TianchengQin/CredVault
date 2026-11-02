#!/bin/sh
# Launch the CredVault MCP server on Linux/macOS, bootstrapping a local venv on first run.
# All setup output goes to stderr: stdout is reserved for the MCP protocol.
set -eu
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV="$DIR/.venv"
PY=${PYTHON:-python3}

if [ ! -x "$VENV/bin/credvault-mcp" ]; then
  "$PY" -m venv "$VENV" >&2
  "$VENV/bin/python" -m pip install --quiet --upgrade pip >&2
  "$VENV/bin/python" -m pip install --quiet "$DIR" >&2
fi
exec "$VENV/bin/credvault-mcp" "$@"
