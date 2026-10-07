#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

fastmcp run "$SCRIPT_DIR/finbank-mcp/server.py" \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8765
