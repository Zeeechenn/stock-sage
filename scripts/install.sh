#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${STOCKSAGE_REPO_URL:-https://github.com/Zeeechenn/stock-sage.git}"
APP_DIR="${STOCKSAGE_APP_DIR:-$HOME/.stock-sage/app}"
BIN_DIR="${STOCKSAGE_BIN_DIR:-$HOME/.local/bin}"
LAUNCHER="$BIN_DIR/stocksage"

echo "== StockSage native Pi installer =="

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command git
require_command python3

if [[ ! -d "$APP_DIR/.git" ]]; then
  mkdir -p "$(dirname "$APP_DIR")"
  git clone "$REPO_URL" "$APP_DIR"
else
  echo "Using existing StockSage checkout: $APP_DIR"
fi

cd "$APP_DIR"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

PYTHON=".venv/bin/python"
"$PYTHON" -m pip install --upgrade pip >/dev/null
"$PYTHON" -m pip install -e ".[agent]" >/dev/null

if ! command -v pi >/dev/null 2>&1; then
  if command -v npm >/dev/null 2>&1; then
    printf "Install native Pi globally with npm now? [y/N]: "
    read -r install_pi
    if [[ "$install_pi" =~ ^[Yy]$ ]]; then
      npm install -g --ignore-scripts @earendil-works/pi-coding-agent
    else
      echo "Skipping Pi install. Install later with:"
      echo "  npm install -g --ignore-scripts @earendil-works/pi-coding-agent"
    fi
  else
    echo "npm was not found. Install native Pi later with the official installer:"
    echo "  curl -fsSL https://pi.dev/install.sh | sh"
  fi
fi

INSTALL_PI=0 bash scripts/agent_setup.sh

mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
export STOCKSAGE_APP_DIR="$APP_DIR"
exec bash "$APP_DIR/scripts/stocksage_launcher.sh" "\$@"
EOF
chmod +x "$LAUNCHER"

echo
echo "StockSage is installed."
echo "Launcher: $LAUNCHER"
echo
echo "Next:"
echo "  stocksage"
echo
echo "If your shell cannot find stocksage, add this to PATH:"
echo "  export PATH=\"$BIN_DIR:\$PATH\""
