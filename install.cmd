@echo off
setlocal EnableExtensions

set "ESB_VERSION=0.2.0"
set "ESB_ENGINE_URL=https://github.com/buffalodebile/enhanced-second-brain/releases/download/v%ESB_VERSION%/enhanced-second-brain-windows-x64.exe"

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
mkdir "%ESB_HOME%" >nul 2>&1
set "ESB_ENGINE=%ESB_HOME%\enhanced-second-brain.exe"
if defined ESB_ENGINE_OVERRIDE (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Copy-Item -LiteralPath $env:ESB_ENGINE_OVERRIDE -Destination $env:ESB_ENGINE -Force"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$target=$env:ESB_ENGINE + '.download'; Invoke-WebRequest -Uri $env:ESB_ENGINE_URL -OutFile $target -UseBasicParsing; Move-Item -LiteralPath $target -Destination $env:ESB_ENGINE -Force"
)
if errorlevel 1 goto :failed

if /I "%ESB_INSTALL_DRY_RUN%"=="1" (
  if not defined CODEX_HOME set "CODEX_HOME=%ESB_HOME%\codex-test"
  "%ESB_ENGINE%" --vault "%ESB_VAULT%" install --dry-run-automation --codex-home "%CODEX_HOME%"
) else (
  "%ESB_ENGINE%" --vault "%ESB_VAULT%" install
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
