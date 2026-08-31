#!/usr/bin/env sh
set -eu

ESB_VERSION="0.2.0"
ESB_HOME="${ESB_INSTALL_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/enhanced-second-brain}"
ESB_VAULT="${ESB_VAULT_PATH:-$HOME/SecondBrain}"

printf '\n%s\n' "Installing Enhanced Second Brain..."
case "$(uname -s)-$(uname -m)" in
    Darwin-arm64|Darwin-aarch64) ASSET="enhanced-second-brain-macos-arm64" ;;
    Darwin-x86_64) ASSET="enhanced-second-brain-macos-x64" ;;
    Linux-x86_64) ASSET="enhanced-second-brain-linux-x64" ;;
    *) printf '%s\n' "Unsupported operating system or processor: $(uname -s) $(uname -m)" >&2; exit 1 ;;
esac

mkdir -p "$ESB_HOME"
ENGINE="$ESB_HOME/enhanced-second-brain"
if [ -n "${ESB_ENGINE_OVERRIDE:-}" ]; then
    cp "$ESB_ENGINE_OVERRIDE" "$ENGINE"
else
    DOWNLOAD="$ENGINE.download.$$"
    curl -fsSL "https://github.com/buffalodebile/enhanced-second-brain/releases/download/v${ESB_VERSION}/${ASSET}" -o "$DOWNLOAD"
    mv "$DOWNLOAD" "$ENGINE"
fi
chmod +x "$ENGINE"

if [ "${ESB_INSTALL_DRY_RUN:-0}" = "1" ]; then
    CODEX_TEST_HOME="${CODEX_HOME:-$ESB_HOME/codex-test}"
    "$ENGINE" --vault "$ESB_VAULT" install --dry-run-automation --codex-home "$CODEX_TEST_HOME"
else
    "$ENGINE" --vault "$ESB_VAULT" install
fi

printf '\n%s\n' "Enhanced Second Brain is ready."
printf '%s\n' "Your notes live in: $ESB_VAULT"
printf '%s\n' "Restart your local AI agent once, then work normally."
