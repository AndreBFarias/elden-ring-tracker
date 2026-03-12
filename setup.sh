#!/bin/bash

# #1
if ! command -v python3 &> /dev/null; then
    echo "Erro: Python3 nao encontrado. Instale-o para prosseguir."
    exit 1
fi

# #2
python3 -m venv .venv
source .venv/bin/activate

# #3
pip install --upgrade pip
pip install -r requirements.txt

# #4
mkdir -p data/references src assets/map_tiles docs logs

# #5
SAVE_PATH="$HOME/.steam/steam/steamapps/compatdata/1245620/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing"
if [ -d "$SAVE_PATH" ]; then
    ln -sf "$SAVE_PATH" ./data/raw_saves
    echo "Link simbolico para saves criado com sucesso."
else
    echo "Aviso: Diretorio de saves nao encontrado. Verifique o caminho do SteamID manualmente."
fi

echo "Setup concluido. Ambiente pronto."
