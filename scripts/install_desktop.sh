#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

ok()   { printf "${GREEN}[OK]${NC} %s\n" "$1"; }
fail() { printf "${RED}[FALHA]${NC} %s\n" "$1"; exit 1; }

ICON_PATH="$PROJECT_DIR/assets/icons/icon.png"
TRAY_SCRIPT="$PROJECT_DIR/src/tray.py"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="elden-ring-tracker.desktop"

[ -f "$ICON_PATH" ] || fail "Ícone não encontrado: $ICON_PATH"
[ -f "$TRAY_SCRIPT" ] || fail "tray.py não encontrado: $TRAY_SCRIPT"
[ -f "$VENV_PYTHON" ] || fail "venv não encontrado: $VENV_PYTHON"

mkdir -p "$DESKTOP_DIR"

cat > "$PROJECT_DIR/$DESKTOP_FILE" << DESKTOP
[Desktop Entry]
Type=Application
Name=Elden Ring Tracker
Comment=Dashboard interativo para rastrear progresso em Elden Ring
Exec=$VENV_PYTHON $TRAY_SCRIPT
Icon=$ICON_PATH
Terminal=false
Categories=Game;Utility;
Keywords=elden;ring;tracker;souls;
StartupNotify=false
DESKTOP

ok "Arquivo .desktop gerado: $PROJECT_DIR/$DESKTOP_FILE"

cp "$PROJECT_DIR/$DESKTOP_FILE" "$DESKTOP_DIR/$DESKTOP_FILE"
ok "Copiado para: $DESKTOP_DIR/$DESKTOP_FILE"

if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    ok "Desktop database atualizado"
fi

printf "\n${GREEN}Instalação concluída.${NC}\n"
printf "O Elden Ring Tracker aparecerá no launcher do sistema.\n"

# "A liberdade consiste em poder fazer tudo aquilo que não prejudique outrem." -- Declaração dos Direitos do Homem
