#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { printf "${GREEN}[OK]${NC} %s\n" "$1"; }
fail() { printf "${RED}[FALHA]${NC} %s\n" "$1"; exit 1; }
warn() { printf "${YELLOW}[AVISO]${NC} %s\n" "$1"; }
info() { printf "${CYAN}[INFO]${NC} %s\n" "$1"; }

printf "\n=== Elden Ring Tracker - Setup ===\n\n"

# 1. Verificar Python
if ! command -v /usr/bin/python3 &> /dev/null; then
    fail "Python3 não encontrado em /usr/bin/python3. Instale-o para prosseguir."
fi
ok "Python3 encontrado: $(/usr/bin/python3 --version)"

# 2. Criar venv com Python do sistema
/usr/bin/python3 -m venv .venv || fail "Falha ao criar .venv"
source .venv/bin/activate
ok "Virtual env criado e ativado"

# 3. Verificar sqlite3
.venv/bin/python3 -c "import sqlite3" 2>/dev/null \
    || fail "Módulo sqlite3 indisponível. Reinstale o Python com suporte a SQLite."
ok "Módulo sqlite3 disponível"

# 4. Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt
ok "Dependências instaladas"

# 5. Criar diretórios necessários
mkdir -p data/references src/tabs assets/map_tiles assets/icons logs debian
ok "Diretórios criados"

# 6. Criar link simbólico para saves
SAVE_PATH="$HOME/.steam/steam/steamapps/compatdata/1245620/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing"
if [ -d "$SAVE_PATH" ]; then
    ln -sf "$SAVE_PATH" ./data/raw_saves
    ok "Link simbólico para saves criado"
else
    warn "Diretório de saves não encontrado. Verifique o caminho do SteamID manualmente."
fi

# 7. Verificar libappindicator (necessário para system tray no GNOME)
if command -v dpkg &> /dev/null; then
    if ! dpkg -l libappindicator3-1 &> /dev/null 2>&1; then
        warn "libappindicator3-1 não instalado. Necessário para system tray no GNOME."
        info "Instale com: sudo apt install libappindicator3-1"
    else
        ok "libappindicator3-1 disponível"
    fi
fi

# 8. Instalar .desktop (opcional)
if [ -f "scripts/install_desktop.sh" ]; then
    bash scripts/install_desktop.sh 2>/dev/null && ok "Atalho .desktop instalado" \
        || warn "Falha ao instalar .desktop (não crítico)"
fi

printf "\n${GREEN}Setup concluído. Ambiente pronto.${NC}\n"
printf "Execute: ${CYAN}bash run.sh${NC}\n\n"

# "A dúvida é o princípio da sabedoria." -- Aristóteles
