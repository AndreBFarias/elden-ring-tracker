<div align="center">

# Elden Ring Tracker

**Dashboard interativo para rastrear progresso em Elden Ring**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.32-red)](https://streamlit.io/)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-green)](LICENSE)

</div>

---

Mapa interativo com camadas de bosses, gracas e dungeons sobreposto aos tiles oficiais do jogo.
Le saves do Steam/Proton, extrai coordenadas e estado de progresso, e renderiza tudo via Folium
dentro de um dashboard Streamlit.

## Funcionalidades

| Funcionalidade | Descricao |
|---|---|
| Mapa interativo | Tres regioes (Superficie, Subterraneo, DLC) com zoom e pan via Folium |
| Camadas togglaveis | Bosses, Gracas, Dungeons e posicao do jogador com icones customizados |
| Progresso em tempo real | Leitura de save files do Steam/Proton com deteccao de sessao ativa |
| Metricas | Nivel, runas, bosses derrotados, gracas descobertas com historico temporal |
| Upscale neural | Real-ESRGAN via spandrel para mapas em alta resolucao (GPU ou fallback LANCZOS) |
| Calibracao | Ferramenta de recalibracao de coordenadas game-to-pixel |
| Banco SQLite | Historico de stats, kills e descobertas por slot |

## Requisitos

- Python 3.10+
- Linux (Steam/Proton para leitura automatica de saves)
- GPU NVIDIA com CUDA (opcional, para upscale neural)

## Instalacao

```bash
# Setup inicial (venv + dependencias + link simbolico para saves)
bash setup.sh

# Iniciar dashboard
bash run.sh
```

### Upscale neural (opcional)

```bash
# Instala PyTorch + CUDA, spandrel e executa o upscale
bash install_upscale.sh

# Opcoes: --fallback (LANCZOS), --tile-size 256, --force, --regions underground dlc
bash install_upscale.sh --fallback
```

## Estrutura

```
.
├── src/
│   ├── dashboard.py        # Entrada principal do Streamlit
│   ├── map_renderer.py     # Renderizacao Folium com camadas
│   ├── map_config.py       # Regioes, categorias e calibracao
│   ├── database.py         # SQLite: schema, queries, historico
│   ├── calibration.py      # Ferramenta de recalibracao
│   ├── recalibrate.py      # Logica de recalibracao game-to-pixel
│   ├── generate_icons.py   # Geracao de icones SVG/PNG
│   └── upscale_maps.py     # Upscale neural via Real-ESRGAN
├── data/
│   └── references/         # JSONs de bosses, gracas, dungeons
├── assets/
│   └── map_tiles/          # Tiles originais dos mapas
├── setup.sh                # Setup do ambiente
├── run.sh                  # Verificacao + inicializacao
└── install_upscale.sh      # Setup do upscale neural
```

## Uso

O dashboard inicia em `localhost:8501`. Na sidebar:

1. Selecione o **slot** do personagem (0-9)
2. Escolha a **regiao** do mapa
3. Toggle as **camadas** de interesse
4. Acompanhe **progresso** e **metricas** em tempo real

## Licenca

[GPL-3.0](LICENSE)

---

*"A perfeicao nao e alcancada quando nao ha mais nada a acrescentar, mas quando nao ha mais nada a retirar."* -- Antoine de Saint-Exupery
