#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { printf "${GREEN}[OK]${NC} %s\n" "$1"; }
fail() { printf "${RED}[FALHA]${NC} %s\n" "$1"; exit 1; }
warn() { printf "${YELLOW}[AVISO]${NC} %s\n" "$1"; }
info() { printf "${CYAN}[INFO]${NC} %s\n" "$1"; }

printf "\n=== Elden Ring Tracker - Verificação e Inicialização ===\n\n"

# ---------------------------------------------------------------------------
# 1. Ambiente virtual
#    Cria o .venv se não existir e ativa. Garante isolamento de dependências.
# ---------------------------------------------------------------------------
if [ ! -d ".venv" ]; then
    warn "Virtual env não encontrado, criando..."
    /usr/bin/python3 -m venv --system-site-packages .venv || fail "Não foi possível criar .venv"
fi
source .venv/bin/activate
PYTHON="$SCRIPT_DIR/.venv/bin/python3"
ok "Virtual env ativado: $($PYTHON --version)"

# ---------------------------------------------------------------------------
# 1.1 Verificação de sqlite3
#     O módulo _sqlite3 precisa estar disponível no Python do venv.
# ---------------------------------------------------------------------------
$PYTHON -c "import sqlite3" 2>/dev/null \
    || fail "Módulo sqlite3 indisponível no Python do venv. Reinstale o Python com suporte a SQLite."
ok "Módulo sqlite3 disponível"

# ---------------------------------------------------------------------------
# 2. Dependências (pip)
#    Verifica se todos os pacotes do requirements.txt estão instalados.
# ---------------------------------------------------------------------------
pip install -q -r requirements.txt || fail "Falha ao instalar dependências"
ok "Dependências verificadas"

# ---------------------------------------------------------------------------
# 3. Arquivos essenciais
#    Verifica se os fontes e dados de referência mínimos existem no projeto.
# ---------------------------------------------------------------------------
ESSENTIALS=(
    "src/dashboard.py"
    "src/map_renderer.py"
    "src/map_config.py"
    "src/database.py"
    "data/references/bosses.json"
    "data/references/graces.json"
    "data/references/dungeons.json"
)
for f in "${ESSENTIALS[@]}"; do
    [ -f "$f" ] || fail "Arquivo essencial não encontrado: $f"
done
ok "Arquivos essenciais presentes (${#ESSENTIALS[@]} verificados)"

# ---------------------------------------------------------------------------
# 4. Validação Python (imports + consistência dos JSONs)
#    Importa os módulos principais e valida que as regiões nos JSONs de
#    referência existem no mapa de REGIONS.
# ---------------------------------------------------------------------------
$PYTHON -c "
import sys, json
sys.path.insert(0, 'src')

from map_config import REGIONS, CATEGORIES
from map_renderer import build_map

erros = []
for ref_file in ['bosses.json', 'graces.json', 'dungeons.json']:
    path = f'data/references/{ref_file}'
    with open(path) as f:
        data = json.load(f)
    for entry in data:
        name = entry.get('name', '?')
        region = entry.get('region', '')
        if region not in REGIONS:
            erros.append(f'{ref_file}: {name} -> região desconhecida: {region}')

if erros:
    print('ERROS:')
    for e in erros:
        print(f'  - {e}')
    sys.exit(1)
else:
    print('OK')
" && ok "Validação Python: imports e JSONs consistentes" \
  || fail "Validação Python falhou (veja erros acima)"

# ---------------------------------------------------------------------------
# 5. Banco de dados
#    Inicializa o SQLite (cria tabelas se não existirem).
# ---------------------------------------------------------------------------
$PYTHON -c "
import sys
sys.path.insert(0, 'src')
from database import initialize_db
initialize_db()
" && ok "Banco de dados inicializado" \
  || fail "Falha ao inicializar banco de dados"

# ---------------------------------------------------------------------------
# 6. Tiles do mapa
#    Verifica o estado dos tiles locais por região usando --check:
#      - completo:   todos os tiles baixados com sucesso
#      - incompleto: download foi interrompido ou teve falhas parciais
#      - pendente:   nenhum tile baixado ainda
#
#    Se houver tiles faltando, inicia o download em background.
#    O download_tiles.py é idempotente: pula tiles já existentes, então
#    re-executar retoma de onde parou.
#
#    Enquanto o download roda, o dashboard usa tiles remotos do Fextralife.
#    Quando os tiles locais estiverem prontos, basta reiniciar o dashboard
#    para usar os tiles offline (melhor performance e funciona sem internet).
# ---------------------------------------------------------------------------
TILE_LOG="$SCRIPT_DIR/logs/tile_download.log"
mkdir -p "$SCRIPT_DIR/logs"

printf "\n  %-14s %7s  %s\n" "Região" "Tiles" "Estado"
printf "  %-14s %7s  %s\n" "--------------" "-------" "----------"

TILES_COMPLETE=true
while IFS= read -r line; do
    printf "%s\n" "$line"
    if echo "$line" | grep -qE '\[(pendente|incompleto)\]'; then
        TILES_COMPLETE=false
    fi
done < <($PYTHON scripts/download_tiles.py --check 2>&1)

printf "\n"

if [ "$TILES_COMPLETE" = true ]; then
    ok "Tiles do mapa: todas as regiões completas (modo offline disponível)"
else
    warn "Tiles incompletos ou pendentes"
    info "Iniciando download em background (log: logs/tile_download.log)"
    info "O dashboard usará tiles remotos até o download terminar"
    nohup $PYTHON scripts/download_tiles.py >> "$TILE_LOG" 2>&1 &
    TILE_PID=$!
    info "Download PID: $TILE_PID"
fi

# ---------------------------------------------------------------------------
# 7. Dashboard
#    Inicia o Streamlit na porta 8501. Se tiles locais não estiverem
#    disponíveis, o mapa carrega tiles remotos do Fextralife automaticamente.
# ---------------------------------------------------------------------------
printf "\n${GREEN}Todas as verificações passaram.${NC}\n"
printf "Iniciando dashboard...\n\n"

LOCAL_IP=$(hostname -I | awk '{print $1}')
info "Acesso local: http://${LOCAL_IP}:8501"

HEADLESS=false
TRAY=false

for arg in "$@"; do
    case "$arg" in
        --tray)     TRAY=true ;;
        --headless) HEADLESS=true ;;
    esac
done

if [ "$TRAY" = true ]; then
    info "Iniciando em modo system tray..."
    $PYTHON src/tray.py
else
    streamlit run src/dashboard.py \
        --server.address 0.0.0.0 \
        --server.port 8501 \
        --server.headless "$HEADLESS" \
        --browser.gatherUsageStats false
fi

# "Não é a consciência dos homens que determina o seu ser, mas, ao contrário, é o seu ser social que determina a sua consciência." -- Karl Marx
