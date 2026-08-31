#!/usr/bin/env sh
set -eu

ESB_VERSION="0.1.2"
ESB_UV_VERSION="0.12.7"
ESB_PACKAGE_DEFAULT="https://github.com/buffalodebile/enhanced-second-brain/releases/download/v${ESB_VERSION}/enhanced_second_brain-${ESB_VERSION}-py3-none-any.whl"
ESB_PACKAGE="${ESB_PACKAGE_OVERRIDE:-$ESB_PACKAGE_DEFAULT}"
ESB_HOME="${ESB_INSTALL_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/enhanced-second-brain}"
ESB_VAULT="${ESB_VAULT_PATH:-$HOME/SecondBrain}"

printf '\n%s\n' "Installing Enhanced Second Brain..."
if [ -n "${ESB_UV_OVERRIDE:-}" ]; then
    UV="$ESB_UV_OVERRIDE"
else
    UV="$ESB_HOME/bootstrap/uv"
    if [ ! -x "$UV" ]; then
        mkdir -p "$ESB_HOME/bootstrap"
        curl -LsSf "https://astral.sh/uv/${ESB_UV_VERSION}/install.sh" | env UV_UNMANAGED_INSTALL="$ESB_HOME/bootstrap" UV_NO_MODIFY_PATH=1 sh
    fi
fi

if [ ! -x "$ESB_HOME/runtime/bin/python" ]; then
    "$UV" venv --python 3.13 "$ESB_HOME/runtime"
fi

"$UV" pip install --python "$ESB_HOME/runtime/bin/python" --upgrade "$ESB_PACKAGE"

if [ "${ESB_INSTALL_DRY_RUN:-0}" = "1" ]; then
    CODEX_TEST_HOME="${CODEX_HOME:-$ESB_HOME/codex-test}"
    "$ESB_HOME/runtime/bin/esb" --vault "$ESB_VAULT" install --dry-run-automation --codex-home "$CODEX_TEST_HOME"
else
    "$ESB_HOME/runtime/bin/esb" --vault "$ESB_VAULT" install
fi

printf '\n%s\n' "Enhanced Second Brain is ready."
printf '%s\n' "Your notes live in: $ESB_VAULT"
printf '%s\n' "Restart your local AI agent once, then work normally."
