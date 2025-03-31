<div align="center">
<img src="assets/icons/icon.png" alt="Elden Ring Tracker" width="128">

# Elden Ring Tracker

**Dashboard interativo para rastrear progresso em Elden Ring**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.32-red)](https://streamlit.io/)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-green)](LICENSE)

</div>

---

Ferramenta de rastreamento de progresso para Elden Ring. Lê o arquivo de save do Steam/Proton
(`ER0000.sl2`), extrai stats, posição, event flags e inventário, persiste em SQLite e renderiza
um dashboard Streamlit com mapa interativo via Leaflet/Folium.

---

## Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| Mapa interativo | Quatro regiões (Superfície, Subterrâneo, DLC, Extra) com zoom e pan via Leaflet |
| Camadas toggláveis | Bosses, Graças, Dungeons, NPCs, itens e posição do jogador com ícones customizados |
| Auto-tracking expandido | Detecção automática de bosses, graças, dungeons, crystal tears, ashes of war, mapas, cookbooks, consumíveis, materiais, materiais de melhoria e inventário |
| Progresso detalhado | Tracking por categoria com abas Pendentes/Concluídos e checklist manual |
| Scan de inventário | Parsing binário do inventário para detectar armas, armaduras, escudos, talismãs e feitiços |
| Eventos perdíveis | 20 eventos críticos com severidade, status e condição de perda |
| Conquistas Steam | 42 conquistas offline com resolução automática e barra de progresso |
| Rastreamento de NPCs | 178 NPCs com checklist manual; auto-tracking via event flags para NPCs com flags documentados |
| Histórico de snapshots | Aba Sessões com nível, runas e atributos por sincronização |
| Indicador de NG+ | Ciclo do personagem exibido nos metrics do dashboard |
| Diagnóstico de flags | Script CLI `scripts/diagnose_flags.py` para listar event flags ativos com nomes |
| System tray | Integração desktop via pystray com autostart e controle de processo |
| Leitura de save | Parsing de ER0000.sl2 (BND4) com extração de stats, posição e event flags |
| Banco SQLite | Histórico de stats, kills, descobertas, itens coletados e progresso por slot |

---

## Requisitos

- Python 3.10+
- Linux (Steam/Proton para leitura automática de saves)
- GPU NVIDIA com CUDA (opcional, para upscale neural)

---

## Instalação

### Local (desenvolvimento)

```bash
bash setup.sh    # cria .venv, instala dependências, cria link simbólico para saves
bash run.sh      # inicia o dashboard
```

### Sistema (instalação em /opt)

```bash
sudo bash install.sh      # instala em /opt e configura o caminho do save
sudo bash uninstall.sh     # remove tudo (com opção de manter dados do usuário)
```

### Pacotes de distribuição

```bash
make deb        # gera pacote .deb via dpkg-buildpackage
make appimage   # gera AppImage
make flatpak    # gera Flatpak (org.freedesktop.Platform 23.08)
```

---

## Uso

```bash
bash run.sh          # dashboard direto no navegador (localhost:8501)
bash run.sh --tray   # system tray com controle de processo
```

Na sidebar do dashboard:

1. Selecione o **slot** do personagem (0-9)
2. Escolha a **região** do mapa
3. Toggle as **camadas** de interesse

Abas disponíveis:

- **Mapa**: visualização interativa com marcadores por categoria
- **Progresso**: tracking por categoria com checklist manual e paginação
- **Eventos Perdíveis**: 20 eventos críticos com status e severidade
- **Conquistas**: 42 conquistas Steam com resolução offline
- **Sessões**: histórico de snapshots de stats por sincronização

### Diagnóstico de flags

```bash
python3 scripts/diagnose_flags.py --save /caminho/ER0000.sl2 --slot 0 --category boss
```

Opções: `--category all | boss | grace`, `--slot 0-9`

Imprime cada flag ativo com ID e nome, mais contagem total. Útil para depurar se um boss
aparece como morto incorretamente ou verificar o estado real de um save.

---

## Infraestrutura

Esta seção documenta a arquitetura interna para desenvolvimento e manutenção.

### Fluxo de dados

```
ER0000.sl2 (binário BND4)
    └── save_parser.py          # lê slots, stats, posição, extrai event_flags
            ├── event_flags.py  # lê bits individuais usando BST map
            ├── inventory_parser.py  # parseia inventário binário do slot
            └── database.py     # persiste em SQLite (tracker.db)
                    └── progress_tracker.py  # API unificada de progresso
                            └── dashboard.py  # Streamlit + abas
```

### Formato do save (BND4)

O arquivo `ER0000.sl2` é um contêiner BND4 com 10 slots de personagem:

```
Offset 0x00: magic "BND4"
Offset N:    10x (checksum 0x10 bytes + slot_data 0x280000 bytes)
```

Cada slot contém:

- **PGD (Player Game Data)**: stats (vigor, mind, ...) em offsets fixos a partir de `0x34`, HP/FP/stamina em `0x08-0x24`, nível em `0x60`, runas em `0x64`, nome em `0x94` (UTF-16LE, 32 bytes).
- **Event flags**: região de `0x1BF99F` bytes que armazena o estado de todos os eventos do jogo como bits individuais. Localizada dinamicamente por `_find_event_flags()` usando um marcador de validação (flag 100).
- **Inventário**: parsing binário de seções por tipo de item (armas, armaduras, talismãs, feitiços, etc.).

### BST map (`data/eventflag_bst.txt`)

Mapeia `block_id` (= `flag_id // 1000`) para `offset_index` dentro da região de event flags.
Cada bloco tem 125 bytes (`BLOCK_SIZE`). Um bit específico dentro do bloco é calculado por:

```python
block_offset = bst_map[block_id] * BLOCK_SIZE
bit_pos      = flag_id % 1000
byte_index   = bit_pos // 8
bit_mask     = 1 << (bit_pos % 8)
active       = bool(event_data[block_offset + byte_index] & bit_mask)
```

Há dois tipos de flag relevantes:

| Tipo | Intervalo | Exemplo |
|------|-----------|---------|
| Reward (9xxx) | 9100 - 9190 | Boss principal morto / graça desbloqueada |
| Dead (3xxxxxxxx) | 30000800+ | Mini-boss de dungeon/caverna morto |

### Banco SQLite (`data/tracker.db`)

Localização em produção: `~/.local/share/elden-ring-tracker/tracker.db`
Localização em desenvolvimento: `data/tracker.db`

Tabelas principais:

| Tabela | Conteúdo |
|--------|----------|
| `player_stats` | Snapshot de nível, runas, atributos e posição por sincronização |
| `boss_kills` | Flags de boss confirmados mortos (sem duplicatas por slot) |
| `grace_discoveries` | Flags de graças ativadas |
| `map_progress` | Fragmentos de mapa revelados/adquiridos |
| `item_collection` | Itens do inventário por categoria |
| `manual_progress` | Checklist manual (NPCs, dungeons, eventos perdíveis) |
| `play_sessions` | Sessões abertas com nível/runas de início e fim |
| `endings` | Finais alcançados |

Todos os acessos passam por `database.py`. A conexão usa WAL mode, `foreign_keys=ON` e `busy_timeout=5000ms`.

### Módulos Python (`src/`)

| Módulo | Responsabilidade |
|--------|-----------------|
| `dashboard.py` | Ponto de entrada Streamlit: sidebar, métricas, tabs |
| `save_parser.py` | Parsing BND4: stats, posição, detecção do save |
| `event_flags.py` | Leitura de bits de event flags via BST map |
| `inventory_parser.py` | Parsing binário do inventário por tipo |
| `progress_tracker.py` | API unificada: carrega referências JSON + dados do banco |
| `database.py` | Schema SQLite, queries, inserções e histórico |
| `log.py` | Logger rotacionado; resolve dirs (dev vs /opt instalado) |
| `map_renderer.py` | Renderização Folium com camadas por categoria |
| `map_config.py` | Regiões, categorias, grupos e calibração de coordenadas |
| `achievement_resolver.py` | Resolução offline das 42 conquistas Steam |
| `missable_checker.py` | Avaliação dos 20 eventos perdíveis |
| `tray.py` | System tray via pystray (autostart, controle de processo) |
| `generate_icons.py` | Geração de ícones PNG para o mapa |
| `upscale_maps.py` | Upscale neural dos tiles via Real-ESRGAN (CUDA opcional) |

### Abas (`src/tabs/`)

| Módulo | Aba |
|--------|-----|
| `progress.py` | Progresso por categoria com paginação e checklist manual |
| `missable.py` | Eventos perdíveis com severidade e condição |
| `achievements.py` | Conquistas Steam com barra de progresso offline |
| `sessions.py` | Histórico de snapshots de stats por sincronização |

### Dados de referência (`data/references/`)

| Arquivo | Conteúdo |
|---------|----------|
| `bosses.json` | 244 bosses com nome, região, tipo e flag ID |
| `boss_flags.json` | 164 entradas: flag_id → {name, region, is_main, type} |
| `graces.json` | Graças com flag ID e região |
| `grace_flags.json` | flag_id → nome da graça |
| `dungeons.json` | 306 dungeons com nome, tipo, região e boss_flags para auto-tracking |
| `items.json` | Todos os itens coletáveis por categoria (loot map com coordenadas) |
| `item_ids.json` | Mapa de item_id → nome por categoria (weapon, armor, shield, talisman, spell, consumable, material, upgrade_material) |
| `npcs.json` | 178 NPCs com nome, região e categoria |
| `npc_dead_flags.json` | flag_id → nome de NPC para auto-tracking via event flags |
| `missable_events.json` | 20 eventos perdíveis com condição e severidade |
| `achievements.json` | 42 conquistas com condição de resolução |
| `crystal_tear_flags.json` | Flags de crystal tears (upgrades de frasco) |
| `ash_of_war_flags.json` | Flags de ashes of war |
| `map_fragment_flags.json` | Flags de fragmentos de mapa |
| `key_item_flags.json` | Flags de itens-chave |
| `story_flags.json` | Flags de progresso narrativo |
| `waygates.json` | Portais e waygates |

### Configuração (`data/config.json`)

Criado automaticamente pelo dashboard ou pelo `install.sh`. Campos:

```json
{
  "save_path": "/caminho/para/ER0000.sl2"
}
```

O path pode apontar para o arquivo diretamente ou para o diretório que o contém.
`find_save_file()` faz `.strip()` no valor antes de criar o `Path` — espaços trailing são ignorados.

Se `save_path` não estiver configurado ou for inválido, o parser busca automaticamente nos caminhos padrão do Steam/Proton.

### Scripts utilitários (`scripts/`)

| Script | Uso |
|--------|-----|
| `diagnose_flags.py` | CLI para listar event flags ativos com nomes (`--save`, `--slot`, `--category`) |
| `import_goods_ids.py` | Baixa CSV de itens do EldenRingTool e popula `item_ids.json` com IDs de consumíveis, materiais e materiais de melhoria |
| `link_dungeon_boss_flags.py` | Linka entradas de `dungeons.json` aos respectivos boss_flags para auto-tracking de conclusão |
| `download_tiles.py` | Download dos tiles de mapa do Fextralife |
| `enrich_references.py` | Enriquece JSONs de referência com flag IDs |
| `import_dataset.py` | Importação de datasets externos para os JSONs de referência |
| `install_desktop.sh` | Instala o atalho `.desktop` no menu do sistema |
| `stitch_tiles.py` | Une tiles de mapa em imagem única |

### CI/CD (`.github/workflows/`)

| Workflow | Gatilho | Jobs |
|----------|---------|------|
| `ci.yml` | push/PR em main | `lint`: ruff check em `src/` |
| `release.yml` | push de tag `v*` | `build-deb`, `build-appimage`, `build-flatpak`, `release` |

O workflow de release gera os três pacotes em paralelo e publica como GitHub Release com notas automáticas. Requer apenas uma tag semântica:

```bash
git tag v1.2.3
git push origin v1.2.3
```

### Linter e formatador

O projeto usa [ruff](https://docs.astral.sh/ruff/) para lint e formatação:

```bash
make lint      # ruff check src/
make format    # ruff format src/
```

Configuração em `pyproject.toml`: target Python 3.10, linha máxima 100, regras E/F/W/I/UP.
`dashboard.py` tem exceção para E402 (imports fora do topo, necessário pelo Streamlit path setup).

### Logging

Todos os módulos usam `log.get_logger(nome)`. Os logs são rotacionados (`RotatingFileHandler`) e salvos em:

- Desenvolvimento: `logs/`
- Instalado em `/opt`: `~/.local/share/elden-ring-tracker/logs/`

Nunca usar `print()` em código de produção — usar sempre o logger.

---

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
│   ├── achievement_resolver.py# Resolução de conquistas offline
│   ├── event_flags.py         # Leitura de event flags do save
│   ├── inventory_parser.py    # Parser de inventário do save
│   ├── tray.py                # Aplicação system tray (pystray)
│   ├── generate_icons.py      # Geração de ícones PNG
│   ├── upscale_maps.py        # Upscale neural via Real-ESRGAN
│   └── tabs/
│       ├── progress.py        # Aba de progresso detalhado
│       ├── missable.py        # Aba de eventos perdíveis
│       ├── achievements.py    # Aba de conquistas Steam
│       └── sessions.py        # Aba de histórico de sessões
├── data/
│   ├── references/            # JSONs de bosses, graças, dungeons, conquistas
│   ├── eventflag_bst.txt      # BST map: block_id → offset_index
│   ├── config.json            # Configuração do usuário (gitignore)
│   └── tracker.db             # Banco SQLite (gitignore)
├── assets/
│   ├── icons/                 # Ícones do mapa e app
│   └── map_tiles/             # Tiles dos mapas (baixados pelo usuário)
├── scripts/
│   ├── diagnose_flags.py      # CLI para listar event flags ativos com nomes
│   ├── import_goods_ids.py    # Popula item_ids.json com IDs de goods via CSV externo
│   ├── link_dungeon_boss_flags.py  # Linka dungeons.json a boss_flags para auto-tracking
│   ├── enrich_references.py   # Enriquecimento de JSONs com flags
│   ├── download_tiles.py      # Download de tiles
│   ├── stitch_tiles.py        # União de tiles
│   ├── import_dataset.py      # Importação de dados de referência
│   └── install_desktop.sh     # Instalador de .desktop
├── packaging/
│   ├── appimage/              # Build AppImage
│   └── flatpak/               # Manifesto Flatpak
├── debian/                    # Esqueleto para pacote .deb
├── .github/workflows/
│   ├── ci.yml                 # Lint em push/PR
│   └── release.yml            # Build e release em tag v*
├── pyproject.toml             # Configuração ruff e metadados do projeto
├── requirements.txt           # streamlit, Pillow, pystray, ruff
├── Makefile                   # Atalhos para setup, run, lint, build
├── setup.sh                   # Setup do ambiente (.venv + dependências)
├── run.sh                     # Verificação + inicialização (--tray)
├── install.sh                 # Instalação do sistema em /opt
└── uninstall.sh               # Desinstalação do sistema
```

---

## Aviso Legal

Projeto não oficial, sem afiliação com a FromSoftware Inc. ou Bandai Namco Entertainment Inc.
"Elden Ring" e "Shadow of the Erdtree" são marcas registradas de seus respectivos proprietários.
Consulte [LEGAL.md](LEGAL.md) para detalhes completos.

## Licença

[GPL-3.0](LICENSE)

---

*"A perfeição não é alcançada quando não há mais nada a acrescentar, mas quando não há mais nada a retirar."* -- Antoine de Saint-Exupéry
