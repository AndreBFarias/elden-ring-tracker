# Sprint 2 -- Dashboard + Mapa Base

## Dependencias

- Sprint 1 concluida: `src/database.py`, schema SQLite com 6 tabelas, boilerplate do projeto.

---

## Objetivo

Construir o dashboard Streamlit com painel de estatisticas e mapa interativo.
O mapa usa projecao plana (CRS.Simple) com a imagem do mapa do jogo como tile layer,
exibindo camadas toggleaveis para as quatro categorias base.

---

## Camadas do Mapa

| Camada | Fonte de dados | Icone | Toggle padrao |
|--------|---------------|-------|---------------|
| Bosses | `boss_kills` | Caveira vermelha | Ativo |
| Gracas | `grace_discoveries` | Chama dourada | Ativo |
| Dungeons | `data/dungeons.json` | Porta cinza | Ativo |
| Player | `player_stats` (pos_x, pos_y) | Marcador azul | Ativo |

---

## Arquivos a criar

### `src/generate_icons.py`

Gera icones PNG via Pillow para cada categoria do mapa. Os icones sao salvos
em `assets/icons/` e referenciados pelo renderer. Dimensao padrao: 32x32 pixels
com fundo transparente.

### `src/map_config.py`

Constantes de configuracao do mapa:
- Bounds da imagem (coordenadas min/max do tile layer)
- Mapeamento de coordenadas do jogo para pixels do mapa
- Cores e tamanhos por categoria
- Paths dos icones

### `src/map_renderer.py`

Modulo que monta o objeto `folium.Map` com:
- Tile layer usando a imagem do mapa de Elden Ring
- `FeatureGroup` por categoria com toggle via `LayerControl`
- Marcadores com popup contendo nome, timestamp de descoberta e flag ID
- Posicao do jogador como marcador diferenciado (pulsa ou destaque)

### `src/dashboard.py`

Ponto de entrada Streamlit (`streamlit run src/dashboard.py`):
- Header com sessao ativa e ultima atualizacao
- Sidebar com seletor de slot (0-9) e filtros de camada
- Painel superior: nivel, runas, horas jogadas, bosses derrotados (metricas)
- Mapa interativo centralizado via `st_folium`
- Graficos de progressao: nivel ao longo do tempo, runas acumuladas

---

## Dados estaticos necessarios

### `data/dungeons.json`

Lista de dungeons com coordenadas do mapa. Estrutura:

```json
[
  {
    "name": "Stormveil Castle",
    "type": "legacy_dungeon",
    "pos_x": 1234.5,
    "pos_y": 5678.9,
    "region": "Limgrave"
  }
]
```

Tipos: `legacy_dungeon`, `minor_dungeon`, `cave`, `tunnel`, `catacomb`, `evergaol`.

---

## Schema -- alteracoes

Nenhuma alteracao no schema da Sprint 1. As tabelas `boss_kills`, `grace_discoveries`,
`player_stats` e `map_progress` ja cobrem todas as camadas desta sprint.

---

## Criterios de aceite

1. Dashboard abre sem erros com `streamlit run src/dashboard.py`
2. Mapa renderiza com imagem base e quatro camadas toggleaveis
3. Metricas do painel refletem dados do banco corretamente
4. Graficos de progressao temporal funcionam com dados reais
5. Seletor de slot filtra todos os componentes simultaneamente
6. Icones gerados em `assets/icons/` com fundo transparente
7. Logging rotacionado em todos os modulos novos
