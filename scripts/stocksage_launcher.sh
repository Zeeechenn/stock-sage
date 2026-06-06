#!/usr/bin/env bash
set -euo pipefail

echo "stocksage is a legacy alias; use mingcang for new installs." >&2
DEFAULT_APP_DIR="$HOME/.mingcang/app"
if [[ ! -d "$DEFAULT_APP_DIR" && -d "$HOME/.stock-sage/app" ]]; then
  DEFAULT_APP_DIR="$HOME/.stock-sage/app"
fi
APP_DIR="${MINGCANG_APP_DIR:-${STOCKSAGE_APP_DIR:-$DEFAULT_APP_DIR}}"
exec bash "$APP_DIR/scripts/mingcang_launcher.sh" "$@"
