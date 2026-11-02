"""Backward-compatible launcher: `python server.py` (any OS).

Prefer installing the package (`pip install ./mcp_server`, `pipx install ./mcp_server`
or `uvx --from ./mcp_server credvault-mcp`) and running `credvault-mcp`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from credvault_mcp.server import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
