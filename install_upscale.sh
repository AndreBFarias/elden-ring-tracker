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

printf "\n=== Elden Ring Tracker - Upscale Neural dos Mapas ===\n\n"

# 1. venv
if [ ! -d ".venv" ]; then
    fail "Virtual env nao encontrado. Execute setup.sh primeiro."
fi
source .venv/bin/activate
ok "Virtual env ativado: $(python3 --version)"

# 2. instalar torch + CUDA se necessario
if python3 -c "import torch" 2>/dev/null; then
    ok "torch ja instalado: $(python3 -c "import torch; print(torch.__version__)")"
else
    info "Instalando PyTorch com CUDA 12.8..."
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128 \
        || fail "Falha ao instalar PyTorch. Instale manualmente: https://pytorch.org/get-started/locally/"
    ok "PyTorch instalado"
fi

# 3. verificar CUDA
python3 -c "
import torch
if not torch.cuda.is_available():
    raise RuntimeError('sem CUDA')
gpu = torch.cuda.get_device_name(0)
vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
print(f'{gpu} ({vram:.2f} GB VRAM)')
" && ok "CUDA disponivel: $(python3 -c "import torch; print(torch.cuda.get_device_name(0))")" \
  || warn "CUDA nao disponivel. Upscale sera via CPU (lento) ou use --fallback para LANCZOS."

# 4. instalar spandrel
if python3 -c "import spandrel" 2>/dev/null; then
    ok "spandrel ja instalado"
else
    info "Instalando spandrel..."
    pip install -q -r requirements-upscale.txt || fail "Falha ao instalar spandrel"
    ok "spandrel instalado"
fi

# 5. verificar imagens de entrada
MAPS_OK=0
MAPS_TOTAL=3
[ -f "assets/map_tiles/base-underground.webp" ] && MAPS_OK=$((MAPS_OK + 1))
[ -f "assets/map_tiles/dlc.png" ] && MAPS_OK=$((MAPS_OK + 1))
[ -f "assets/map_tiles/base.png" ] && MAPS_OK=$((MAPS_OK + 1))

if [ "$MAPS_OK" -eq "$MAPS_TOTAL" ]; then
    ok "Imagens de entrada presentes ($MAPS_OK/$MAPS_TOTAL)"
else
    fail "Imagens de entrada faltando ($MAPS_OK/$MAPS_TOTAL). Verifique assets/map_tiles/"
fi

# 6. executar upscale
printf "\n${CYAN}Iniciando upscale neural...${NC}\n"
info "Ordem: underground (~1 min) -> dlc (~3-5 min) -> surface (~15-25 min)"
info "Argumentos extras sao repassados ao script (ex: --fallback, --tile-size 256, --force)"
printf "\n"

python3 src/upscale_maps.py "$@" || fail "Upscale falhou"

printf "\n"
ok "Upscale concluido"

# 7. limpar cache antigo
if [ -d "assets/cache" ]; then
    rm -rf assets/cache
    ok "Cache antigo removido"
fi

# 8. verificar saida
printf "\n${CYAN}Verificando imagens geradas...${NC}\n"
for img in underground_upscaled.png dlc_upscaled.png surface_upscaled.png; do
    path="assets/map_tiles/$img"
    if [ -f "$path" ]; then
        size=$(du -h "$path" | cut -f1)
        dims=$(python3 -c "from PIL import Image; i=Image.open('$path'); print(f'{i.width}x{i.height}')")
        ok "$img: $dims ($size)"
    else
        warn "$img nao gerado"
    fi
done

printf "\n${GREEN}=== Instalacao concluida ===${NC}\n"
printf "Proximo passo: recalibrar nas imagens HD\n"
printf "  ${CYAN}streamlit run src/calibration.py${NC}\n\n"

# "O que nao pode ser medido nao pode ser melhorado." -- Lord Kelvin
