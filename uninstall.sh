#!/bin/bash
set -euo pipefail

INSTALL_DIR="/opt/elden-ring-tracker"
DESKTOP_FILE="/usr/share/applications/elden-ring-tracker.desktop"
PIXMAP_FILE="/usr/share/pixmaps/elden-ring-tracker.png"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { printf "${GREEN}[OK]${NC} %s\n" "$1"; }
fail() { printf "${RED}[FALHA]${NC} %s\n" "$1"; exit 1; }
warn() { printf "${YELLOW}[AVISO]${NC} %s\n" "$1"; }

if [ "$(id -u)" -ne 0 ]; then
    fail "Este script requer root. Execute com: sudo bash uninstall.sh"
fi

printf "\n=== Elden Ring Tracker - Desinstalação ===\n\n"

pkill -f "streamlit run.*dashboard.py" 2>/dev/null && ok "Processo streamlit encerrado" || true
pkill -f "python3.*tray.py" 2>/dev/null && ok "Processo tray encerrado" || true

if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    ok "Diretório removido: $INSTALL_DIR (incluindo .venv, logs e dados)"
else
    warn "Diretório não encontrado: $INSTALL_DIR"
fi

rm -f "$DESKTOP_FILE" && ok "Desktop entry removido"
rm -f "$PIXMAP_FILE" && ok "Ícone removido"

REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")
AUTOSTART_FILE="$REAL_HOME/.config/autostart/elden-ring-tracker.desktop"
if [ -f "$AUTOSTART_FILE" ]; then
    rm -f "$AUTOSTART_FILE"
    ok "Autostart removido"
fi

DATA_DIR="$REAL_HOME/.local/share/elden-ring-tracker"
if [ -d "$DATA_DIR" ]; then
    printf "\nDados do usuário encontrados em: %s\n" "$DATA_DIR"
    printf "  (contém: logs, banco de dados, configuração)\n"
    printf "Deseja remover? [s/N]: "
    read -r REMOVE_DATA
    if [ "$REMOVE_DATA" = "s" ] || [ "$REMOVE_DATA" = "S" ]; then
        rm -rf "$DATA_DIR"
        ok "Dados do usuário removidos: $DATA_DIR"
    else
        warn "Dados do usuário mantidos: $DATA_DIR"
    fi
fi

if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
    ok "Desktop database atualizado"
fi

printf "\n${GREEN}Desinstalação concluída.${NC}\n"

# "Destruir é também criar." -- Mikhail Bakunin
