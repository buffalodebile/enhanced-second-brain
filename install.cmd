@echo off
setlocal EnableExtensions

set "ESB_VERSION=0.1.2"
set "ESB_UV_VERSION=0.12.7"
set "ESB_PACKAGE=https://github.com/buffalodebile/enhanced-second-brain/releases/download/v%ESB_VERSION%/enhanced_second_brain-%ESB_VERSION%-py3-none-any.whl"
if defined ESB_PACKAGE_OVERRIDE set "ESB_PACKAGE=%ESB_PACKAGE_OVERRIDE%"

if defined ESB_INSTALL_HOME (
  set "ESB_HOME=%ESB_INSTALL_HOME%"
) else (
  set "ESB_HOME=%LOCALAPPDATA%\EnhancedSecondBrain"
)

if defined ESB_VAULT_PATH (
  set "ESB_VAULT=%ESB_VAULT_PATH%"
) else (
  set "ESB_VAULT=%USERPROFILE%\SecondBrain"
)

echo.
echo Installing Enhanced Second Brain...
if defined ESB_UV_OVERRIDE (
  set "UV_EXE=%ESB_UV_OVERRIDE%"
) else (
  set "UV_EXE=%ESB_HOME%\bootstrap\uv.exe"
  if not exist "%ESB_HOME%\bootstrap\uv.exe" (
    mkdir "%ESB_HOME%\bootstrap" >nul 2>&1
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$env:UV_UNMANAGED_INSTALL='%ESB_HOME%\bootstrap'; $env:UV_NO_MODIFY_PATH='1'; irm https://astral.sh/uv/%ESB_UV_VERSION%/install.ps1 | iex"
    if errorlevel 1 goto :failed
  )
)

if not exist "%ESB_HOME%\runtime\Scripts\python.exe" (
  "%UV_EXE%" venv --python 3.13 "%ESB_HOME%\runtime"
  if errorlevel 1 goto :failed
)

"%UV_EXE%" pip install --python "%ESB_HOME%\runtime\Scripts\python.exe" --upgrade "%ESB_PACKAGE%"
if errorlevel 1 goto :failed

if /I "%ESB_INSTALL_DRY_RUN%"=="1" (
  if not defined CODEX_HOME set "CODEX_HOME=%ESB_HOME%\codex-test"
  "%ESB_HOME%\runtime\Scripts\esb.exe" --vault "%ESB_VAULT%" install --dry-run-automation --codex-home "%CODEX_HOME%"
) else (
  "%ESB_HOME%\runtime\Scripts\esb.exe" --vault "%ESB_VAULT%" install
)
if errorlevel 1 goto :failed

echo.
echo Enhanced Second Brain is ready.
echo Your notes live in: %ESB_VAULT%
echo Restart Codex once, then work normally.
if not defined ESB_INSTALL_NONINTERACTIVE explorer "%ESB_VAULT%"
if not defined ESB_INSTALL_NONINTERACTIVE pause
exit /b 0

:failed
echo.
echo Installation failed. Nothing in your existing notes was deleted.
echo See: https://github.com/buffalodebile/enhanced-second-brain/blob/main/docs/troubleshooting.md
if not defined ESB_INSTALL_NONINTERACTIVE pause
exit /b 1
