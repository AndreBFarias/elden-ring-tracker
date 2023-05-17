#!/bin/bash
set -euo pipefail

INSTALL_DIR="/opt/elden-ring-tracker"
DESKTOP_FILE="/usr/share/applications/elden-ring-tracker.desktop"
PIXMAP_FILE="/usr/share/pixmaps/elden-ring-tracker.png"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { printf "${GREEN}[OK]${NC} %s\n" "$1"; }
fail() { printf "${RED}[FALHA]${NC} %s\n" "$1"; exit 1; }
warn() { printf "${YELLOW}[AVISO]${NC} %s\n" "$1"; }

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        fail "Este script requer root. Execute com: sudo bash install.sh"
    fi
}

do_uninstall() {
    require_root
    printf "\n=== Elden Ring Tracker - Desinstalação ===\n\n"

    pkill -f "streamlit run.*dashboard.py" 2>/dev/null && ok "Processo streamlit encerrado" || true
    pkill -f "python3.*tray.py" 2>/dev/null && ok "Processo tray encerrado" || true

    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        ok "Diretório removido: $INSTALL_DIR (incluindo .venv)"
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

    if command -v update-desktop-database > /dev/null 2>&1; then
        update-desktop-database /usr/share/applications 2>/dev/null || true
        ok "Desktop database atualizado"
    fi

    printf "\n${GREEN}Desinstalação concluída.${NC}\n"
    exit 0
}

do_install() {
    require_root
    printf "\n=== Elden Ring Tracker - Instalação ===\n\n"

    if ! command -v /usr/bin/python3 > /dev/null 2>&1; then
        fail "Python 3 não encontrado em /usr/bin/python3"
    fi

    PY_VERSION=$(/usr/bin/python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(/usr/bin/python3 -c "import sys; print(sys.version_info.major)")
    PY_MINOR=$(/usr/bin/python3 -c "import sys; print(sys.version_info.minor)")

    if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
        fail "Python 3.10+ necessário (encontrado: $PY_VERSION)"
    fi
    ok "Python $PY_VERSION detectado"

    install -d "$INSTALL_DIR"
    ok "Diretório criado: $INSTALL_DIR"

    cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
    cp -r "$SCRIPT_DIR/data" "$INSTALL_DIR/"
    cp -r "$SCRIPT_DIR/scripts" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/.python-version" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/pyproject.toml" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/run.sh" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/setup.sh" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/Makefile" "$INSTALL_DIR/"
    ok "Arquivos copiados para $INSTALL_DIR"

    if [ ! -d "$INSTALL_DIR/.venv" ]; then
        /usr/bin/python3 -m venv "$INSTALL_DIR/.venv"
        ok "Virtual env criado"
    fi
    "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
    "$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
    ok "Dependências instaladas"

    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$INSTALL_DIR/assets/icons"
    ok "Diretórios auxiliares criados"

    install -Dm644 "$SCRIPT_DIR/assets/icons/icon.png" "$PIXMAP_FILE"
    cp "$SCRIPT_DIR/assets/icons/icon.png" "$INSTALL_DIR/assets/icons/icon.png"
    ok "Ícone instalado"

    cat > "$DESKTOP_FILE" << DESKTOP
[Desktop Entry]
Type=Application
Name=Elden Ring Tracker
Comment=Dashboard interativo para rastrear progresso em Elden Ring
Exec=$INSTALL_DIR/.venv/bin/python3 $INSTALL_DIR/src/tray.py
Icon=elden-ring-tracker
Terminal=false
Categories=Game;Utility;
Keywords=elden;ring;tracker;souls;
StartupNotify=false
DESKTOP
    ok "Desktop entry instalado"

    if command -v update-desktop-database > /dev/null 2>&1; then
        update-desktop-database /usr/share/applications 2>/dev/null || true
        ok "Desktop database atualizado"
    fi

    printf "\n${GREEN}Instalação concluída.${NC}\n"
    printf "O Elden Ring Tracker foi instalado em: %s\n" "$INSTALL_DIR"
    printf "O aplicativo aparecerá no launcher do sistema.\n"
}

case "${1:-}" in
    --uninstall)
        do_uninstall
        ;;
    *)
        do_install
        ;;
esac

# "A propriedade privada nos fez tão estúpidos e parciais que um objeto só é nosso quando o temos." -- Karl Marx
