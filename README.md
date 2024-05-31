<div align="center">
<img src="assets/icons/icon.png" alt="Elden Ring Tracker" width="128">

# Elden Ring Tracker

**Dashboard interativo para rastrear progresso em Elden Ring**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.54-red)](https://streamlit.io/)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-green)](LICENSE)

</div>

---

Mapa interativo com camadas de bosses, graças e dungeons sobreposto aos tiles oficiais do jogo.
Lê saves do Steam/Proton, extrai coordenadas e estado de progresso, e renderiza tudo via Folium
dentro de um dashboard Streamlit.

## Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| Mapa interativo | Quatro regiões (Superfície, Subterrâneo, DLC, Extra) com zoom e pan via Leaflet |
| Camadas toggláveis | Bosses, Graças, Dungeons, NPCs, itens e posição do jogador com ícones customizados |
| Auto-tracking expandido | Detecção automática de bosses, graças, crystal tears, ashes of war, mapas, cookbooks, materiais de melhoria e inventário |
| Progresso detalhado | Tracking por categoria com abas Pendentes/Concluídos e checklist manual |
| Scan de inventário | Parsing binário do inventário para detectar armas, armaduras, escudos, talismãs e feitiços |
| Eventos perdíveis | 20 eventos críticos com severidade, status e condição de perda |
| Conquistas Steam | 42 conquistas offline com resolução automática e barra de progresso |
| Rastreamento de NPCs | 138 NPCs com checklist manual na aba Progresso |
| Histórico de snapshots | Aba Sessões com nível, runas e atributos por sincronização |
| Indicador de NG+ | Ciclo do personagem exibido nos metrics do dashboard |
| Diagnóstico de flags | Script CLI `scripts/diagnose_flags.py` para listar event flags ativos com nomes |
| System tray | Integração desktop via pystray com autostart e controle de processo |
| Leitura de save | Parsing de ER0000.sl2 (BND4) com extração de stats, posição e event flags |
| Banco SQLite | Histórico de stats, kills, descobertas, itens coletados e progresso por slot |

## Requisitos

- Python 3.10+
- Linux (Steam/Proton para leitura automática de saves)
- GPU NVIDIA com CUDA (opcional, para upscale neural)

## Instalação

### Local (desenvolvimento)

```bash
bash setup.sh    # venv + dependências + link simbólico para saves
bash run.sh      # iniciar dashboard
```

### Sistema (instalação em /opt)

```bash
sudo bash install.sh      # instala em /opt e pergunta o caminho do save
sudo bash uninstall.sh     # remove tudo (com opção de manter dados)
```

### Pacotes

```bash
make deb        # gera pacote .deb
make appimage   # gera AppImage
make flatpak    # gera Flatpak
```

## Estrutura

```
.
├── src/
│   ├── dashboard.py           # Entrada principal do Streamlit (abas)
│   ├── map_renderer.py        # Renderização Leaflet com camadas
│   ├── map_config.py          # Regiões, categorias e calibração
│   ├── database.py            # SQLite: schema, queries, histórico
│   ├── save_parser.py         # Parser de saves BND4/SL2
│   ├── progress_tracker.py    # API unificada de progresso
│   ├── missable_checker.py    # Avaliação de eventos perdíveis
│   ├── achievement_resolver.py # Resolução de conquistas offline
│   ├── event_flags.py         # Leitura de event flags do save (bosses, gracas, itens)
│   ├── inventory_parser.py    # Parser de inventário do save
│   ├── tray.py                # Aplicação system tray (pystray)
│   ├── generate_icons.py      # Geração de ícones PNG
│   ├── upscale_maps.py        # Upscale neural via Real-ESRGAN
│   └── tabs/
│       ├── progress.py        # Aba de progresso detalhado
│       ├── missable.py        # Aba de eventos perdiveis
│       ├── achievements.py    # Aba de conquistas Steam
│       └── sessions.py        # Aba de histórico de sessões
├── data/
│   └── references/            # JSONs de bosses, graças, dungeons, conquistas
├── assets/
│   ├── icons/                 # Ícones do mapa e app
│   └── map_tiles/             # Tiles dos mapas
├── scripts/
│   ├── diagnose_flags.py      # CLI para listar event flags ativos com nomes
│   ├── enrich_references.py   # Enriquecimento de JSONs com flags
│   ├── install_desktop.sh     # Instalador de .desktop
│   ├── download_tiles.py      # Download de tiles do Fextralife
│   └── import_dataset.py      # Importação de dados de referência
├── debian/                    # Esqueleto para pacote .deb
├── setup.sh                   # Setup do ambiente
├── run.sh                     # Verificação + inicialização (--tray)
├── install.sh                 # Instalação do sistema
└── uninstall.sh               # Desinstalação do sistema
```

## Uso

```bash
bash run.sh          # Dashboard direto no navegador
bash run.sh --tray   # System tray com controle de processo
```

O dashboard inicia em `localhost:8501`. Na sidebar:

1. Selecione o **slot** do personagem (0-9)
2. Escolha a **região** do mapa
3. Toggle as **camadas** de interesse

Nas abas superiores:

- **Mapa**: Visualização interativa com marcadores
- **Progresso**: Tracking por categoria com checklist manual
- **Eventos Perdíveis**: 20 eventos críticos com status e severidade
- **Conquistas**: 42 conquistas Steam com resolução offline
- **Sessões**: Histórico de snapshots de stats por sincronização

### Diagnóstico de flags

```bash
python3 scripts/diagnose_flags.py --save /caminho/ER0000.sl2 --slot 0 --category boss
```

Opções: `--category all | boss | grace`, `--slot 0-9`

## Aviso Legal

Este é um projeto não oficial, sem afiliação com a FromSoftware Inc. ou Bandai Namco
Entertainment Inc. "Elden Ring" é marca registrada de seus respectivos proprietários.
Consulte [LEGAL.md](LEGAL.md) para detalhes completos.

## Licença

[GPL-3.0](LICENSE)

---

*"A perfeição não é alcançada quando não há mais nada a acrescentar, mas quando não há mais nada a retirar."* -- Antoine de Saint-Exupery
