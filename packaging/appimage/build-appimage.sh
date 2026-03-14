#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
BUILD_DIR="$SCRIPT_DIR/build"
APPDIR="$BUILD_DIR/EldenRingTracker.AppDir"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { printf "${GREEN}[OK]${NC} %s\n" "$1"; }
fail() { printf "${RED}[FALHA]${NC} %s\n" "$1"; exit 1; }
info() { printf "${CYAN}[INFO]${NC} %s\n" "$1"; }

info "Construindo AppImage do Elden Ring Tracker"

rm -rf "$BUILD_DIR"
mkdir -p "$APPDIR/opt/elden-ring-tracker"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

info "Copiando arquivos do projeto..."
for item in src data assets scripts requirements.txt .python-version pyproject.toml run.sh setup.sh Makefile; do
    if [ -e "$PROJECT_DIR/$item" ]; then
        cp -r "$PROJECT_DIR/$item" "$APPDIR/opt/elden-ring-tracker/"
    fi
done

cp "$SCRIPT_DIR/AppRun" "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"

cp "$PROJECT_DIR/assets/icons/icon.png" "$APPDIR/elden-ring-tracker.png"
cp "$PROJECT_DIR/assets/icons/icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/elden-ring-tracker.png"

cat > "$APPDIR/elden-ring-tracker.desktop" << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=Elden Ring Tracker
Comment=Dashboard interativo para rastrear progresso em Elden Ring
Exec=AppRun
Icon=elden-ring-tracker
Terminal=false
Categories=Game;Utility;
Keywords=elden;ring;tracker;souls;
StartupNotify=false
DESKTOP

cp "$APPDIR/elden-ring-tracker.desktop" "$APPDIR/usr/share/applications/"

if ! command -v appimagetool &> /dev/null; then
    info "appimagetool não encontrado. Baixando..."
    ARCH=$(uname -m)
    TOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage"
    TOOL_PATH="$BUILD_DIR/appimagetool"
    curl -fsSL "$TOOL_URL" -o "$TOOL_PATH" || fail "Falha ao baixar appimagetool"
    chmod +x "$TOOL_PATH"
    APPIMAGETOOL="$TOOL_PATH"
else
    APPIMAGETOOL="appimagetool"
fi

info "Gerando AppImage..."
ARCH=$(uname -m) "$APPIMAGETOOL" "$APPDIR" "$BUILD_DIR/EldenRingTracker-${ARCH}.AppImage" \
    || fail "Falha ao gerar AppImage"

ok "AppImage gerado: $BUILD_DIR/EldenRingTracker-${ARCH}.AppImage"

# "A tecnologia é uma coisa maravilhosa, desde que não nos controle." -- Karl Marx
