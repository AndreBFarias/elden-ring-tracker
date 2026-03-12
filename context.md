1. Requisitos do Sistema (requirements.txt)
Estes são os componentes vitais. Sem eles, seu dashboard é apenas um código inerte.

Plaintext
streamlit==1.32.0
watchdog==4.0.0
folium==0.16.0
streamlit-folium==0.18.0
pandas==2.2.0
cryptography==42.0.0
2. O Ritual de Inicialização (setup.sh)
docs/setup.md
#1 Verifica se o Python 3 está instalado no sistema.
#2 Cria o ambiente virtual (.venv) para isolar as dependências e não poluir o seu Pop!_OS.
#3 Atualiza o pip e instala todas as bibliotecas listadas no requirements.txt.
#4 Cria a estrutura de pastas necessária (data/references, src, assets).
#5 Localiza o diretório de saves do Elden Ring no Proton e cria um link simbólico para facilitar o acesso do script.

setup.sh
Bash
#!/bin/bash
#1
if ! command -v python3 &> /dev/null; then
    echo "Erro: Python3 não encontrado. Instale-o para prosseguir."
    exit 1
fi

#2
python3 -m venv .venv
source .venv/bin/activate

#3
pip install --upgrade pip
pip install -r requirements.txt

#4
mkdir -p data/references src assets docs

#5
SAVE_PATH="$HOME/.steam/steam/steamapps/compatdata/1245620/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing"
if [ -d "$SAVE_PATH" ]; then
    ln -s "$SAVE_PATH" ./data/raw_saves
    echo "Link simbólico para saves criado com sucesso."
else
    echo "Aviso: Diretório de saves não encontrado. Verifique o caminho do SteamID manualmente."
fi

echo "Setup concluído. O ambiente está pronto para a sua obsessão."
3. O Gatilho de Execução (run.sh)
docs/run.md
#1 Ativa o ambiente virtual criado anteriormente.
#2 Inicia o processo watcher.py em segundo plano para monitorar o arquivo .sl2.
#3 Lança o dashboard do Streamlit.
#4 Garante que, ao fechar o terminal, o processo do monitor de arquivos também seja encerrado.

run.sh
Bash
#!/bin/bash
#1
source .venv/bin/activate

#2
python3 src/watcher.py &
WATCHER_PID=$!

#3
streamlit run src/dashboard.py --server.address 0.0.0.0

#4
trap "kill $WATCHER_PID" EXIT
Nota de Sistema: Configurei o run.sh para rodar no endereço 0.0.0.0. Isso permitirá que seu celular ou tablet acesse o dashboard apenas digitando o IP do seu Nitro 5 na rede local. Ver o seu progresso em tempo real é uma eficiência deliciosa, embora eu ainda prefira monitorar seus erros de segmentação.
