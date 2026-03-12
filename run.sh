#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { printf "${GREEN}[OK]${NC} %s\n" "$1"; }
fail() { printf "${RED}[FALHA]${NC} %s\n" "$1"; exit 1; }
warn() { printf "${YELLOW}[AVISO]${NC} %s\n" "$1"; }

printf "\n=== Elden Ring Tracker - Verificacao e Inicializacao ===\n\n"

# 1. venv
if [ ! -d ".venv" ]; then
    warn "Virtual env nao encontrado, criando..."
    python3 -m venv .venv || fail "Nao foi possivel criar .venv"
fi
source .venv/bin/activate
ok "Virtual env ativado: $(python3 --version)"

# 2. dependencias
MISSING_DEPS=0
while IFS= read -r pkg; do
    pkg_name=$(echo "$pkg" | cut -d'=' -f1 | tr '[:upper:]' '[:lower:]')
    if ! python3 -c "import importlib; importlib.import_module('${pkg_name}')" 2>/dev/null; then
        MISSING_DEPS=1
        break
    fi
done < <(grep -v '^\s*#' requirements.txt | grep -v '^\s*$')

if [ "$MISSING_DEPS" -eq 1 ]; then
    warn "Dependencias faltando, instalando..."
    pip install -q -r requirements.txt || fail "Falha ao instalar dependencias"
    ok "Dependencias instaladas"
else
    ok "Dependencias presentes"
fi

# 3. arquivos essenciais
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
    [ -f "$f" ] || fail "Arquivo essencial nao encontrado: $f"
done
ok "Arquivos essenciais presentes (${#ESSENTIALS[@]} verificados)"

# 4. imagens do mapa
MAP_IMAGES=("assets/map_tiles/base.png" "assets/map_tiles/base-underground.webp" "assets/map_tiles/dlc.png")
MAP_OK=0
for img in "${MAP_IMAGES[@]}"; do
    [ -f "$img" ] && MAP_OK=$((MAP_OK + 1))
done
if [ "$MAP_OK" -eq "${#MAP_IMAGES[@]}" ]; then
    ok "Imagens do mapa presentes ($MAP_OK/${#MAP_IMAGES[@]})"
else
    warn "Imagens do mapa: $MAP_OK/${#MAP_IMAGES[@]} encontradas (mapa pode nao renderizar)"
fi

# 5. validacao Python (imports + JSONs + coordenadas)
python3 -c "
import sys, json
sys.path.insert(0, 'src')

from map_config import REGIONS
from map_renderer import build_map

regions = REGIONS
erros = []

for ref_file in ['bosses.json', 'graces.json', 'dungeons.json']:
    path = f'data/references/{ref_file}'
    with open(path) as f:
        data = json.load(f)
    for entry in data:
        name = entry.get('name', '?')
        region = regions.get(entry.get('region'))
        if not region:
            erros.append(f'{ref_file}: {name} -> regiao desconhecida: {entry.get(\"region\")}')
            continue
        px, py = entry['pos_x'], entry['pos_y']
        if px < 0 or py < 0 or px > region.width or py > region.height:
            erros.append(f'{ref_file}: {name} fora dos limites ({px}, {py}) para {region.name} ({region.width}x{region.height})')

if erros:
    print('ERROS:')
    for e in erros:
        print(f'  - {e}')
    sys.exit(1)
else:
    print(f'OK')
" && ok "Validacao Python: imports, JSONs e coordenadas dentro dos limites" \
  || fail "Validacao Python falhou (veja erros acima)"

# 6. banco de dados
python3 -c "
import sys
sys.path.insert(0, 'src')
from database import initialize_db
initialize_db()
" && ok "Banco de dados inicializado" \
  || fail "Falha ao inicializar banco de dados"

printf "\n${GREEN}Todas as verificacoes passaram.${NC}\n"
printf "Iniciando dashboard...\n\n"

# 7. abrir no navegador e rodar streamlit
streamlit run src/dashboard.py \
    --server.address localhost \
    --server.port 8501 \
    --server.headless false \
    --browser.gatherUsageStats false

# "Nao e a consciencia dos homens que determina o seu ser, mas, ao contrario, e o seu ser social que determina a sua consciencia." -- Karl Marx
