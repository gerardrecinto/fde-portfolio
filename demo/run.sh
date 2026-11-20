#!/usr/bin/env bash
# Runs the whole customer visit against the real Joltrin barrier server.
# Needs: Go 1.21+ (it fetches the Go version Joltrin needs), Python 3.9+, curl. Takes about 2 minutes the
# first time because it builds the server, then under 10 seconds.
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=versions.env
. ./versions.env
BIN="${SOP_MCP_SERVER:-$PWD/.bin/sop-mcp-server}"
if [ ! -x "$BIN" ]; then
  echo "building sop-mcp-server at ${JOLTRIN_REF:0:7} (first run only)..." >&2
  GOBIN="$PWD/.bin" go install "github.com/sharedcode/joltrin/v5/cmd/sop-mcp-server@${JOLTRIN_REF}"
fi
exec python3 fde_demo.py "$BIN" "$@"
