# Sprint 4 -- Completismo e Conquistas

## Dependencias

- Sprint 3 concluida: camadas de NPCs, eventos perdiveis e coletaveis criticos funcionais.
- Tabelas `npc_encounters` e `collectibles` no schema.
- Sistema de icones e camadas toggleaveis consolidado.

---

## Objetivo

Completar o rastreamento de todos os itens e locais relevantes para 100% do jogo,
adicionar tab de conquistas com mapeamento direto para as conquistas Steam (appid `1245620`)
e barra de progresso global. Esta sprint transforma o tracker de ferramenta de
acompanhamento em guia de completismo -- funcionando 100% offline via flags do save file.

---

## Camadas do Mapa

| Camada | Quantidade aprox. | Icone | Particularidade |
|--------|-------------------|-------|-----------------|
| Armas Lendarias | 9 base + DLC | Espada dourada | Obrigatorias para conquista |
| Magias Lendarias | 7 base + DLC | Grimorio roxo | Obrigatorias para conquista |
| Espiritros Invocaveis | ~60 Spirit Ashes | Fantasma azul | Localizacao fixa |
| Mercadores | ~20 fixos | Mochila marrom | Inventario unico por mercador |
| Cookbooks | ~60 receitas | Livro verde | Localizacao fixa |
| Fragmentos de Mapa | ~30 por jogo | Pergaminho bege | Revelam regioes do mapa |
| Pinturas | 7 puzzles | Quadro dourado | Localizacao fixa + local da recompensa |

---

## Armas e Magias Lendarias

Itens obrigatorios para as conquistas "Armas Lendarias" e "Feiticos/Encantamentos
Lendarios". Cada um tem localizacao fixa ou e obtido via questline especifica.

### Estrutura de dados -- `data/collectibles/legendary_weapons.json`

```json
[
  {
    "item_id": "grafted_blade_greatsword",
    "name": "Grafted Blade Greatsword",
    "category": "legendary_weapon",
    "flag": 67000,
    "pos_x": 1500.0,
    "pos_y": 4200.0,
    "region": "Limgrave",
    "acquisition": "Castle Morne - recompensa de boss",
    "achievement": "Legendary Armaments"
  }
]
```

Mesmo formato da tabela `collectibles` da Sprint 3. O campo `achievement` vincula
o item a conquista correspondente.

---

## Espiritros Invocaveis (Spirit Ashes)

Invocacoes coletaveis com localizacao fixa. Variam de drop de boss a itens em baus.

### Estrutura de dados -- `data/collectibles/spirit_ashes.json`

```json
[
  {
    "item_id": "mimic_tear",
    "name": "Mimic Tear Ashes",
    "category": "spirit_ash",
    "flag": 68000,
    "pos_x": 3800.0,
    "pos_y": 2100.0,
    "region": "Nokron",
    "acquisition": "Bau apos boss Mimic Tear"
  }
]
```

---

## Mercadores

Cada mercador tem localizacao fixa e inventario unico. O popup do mapa lista
os itens exclusivos disponiveis naquele mercador.

### Estrutura de dados -- `data/merchants.json`

```json
[
  {
    "merchant_id": "kale",
    "name": "Merchant Kale",
    "pos_x": 1050.0,
    "pos_y": 3150.0,
    "region": "Limgrave",
    "notable_items": [
      "Crafting Kit",
      "Telescope",
      "Torch"
    ]
  }
]
```

Mercadores nao usam a tabela `collectibles` (nao sao coletaveis). Sao exibidos
como pontos de interesse estaticos no mapa.

---

## Cookbooks, Fragmentos e Pinturas

Todos seguem o formato padrao de `collectibles` com suas respectivas categorias:
`cookbook`, `map_fragment`, `painting`.

Pinturas tem um campo adicional `reward_pos_x`/`reward_pos_y` indicando o local
onde a recompensa pode ser coletada apos encontrar a perspectiva correta.

---

## Tab de Conquistas + Mapeamento Steam

Nova tab no dashboard (via `st.tabs`) com lista completa das 42 conquistas do jogo,
mapeadas 1:1 para os achievements da Steam (appid `1245620`). O tracking e feito
inteiramente offline via flags do save file -- sem necessidade de API key ou perfil publico.

Cada conquista mostra:
- Nome (PT-BR) e nome Steam original (EN)
- Progresso (itens coletados / total necessario)
- Lista de itens faltantes com link para posicao no mapa
- Indicador de status: bloqueada, em progresso, desbloqueada

### Categorias de conquistas

| Tipo | Exemplos | Deteccao via flags |
|------|----------|--------------------|
| `collection` | Armas Lendarias, Magias Lendarias | Todas as flags de item ativas |
| `boss` | Shardbearers, Elden Beast | Flag de boss kill individual |
| `ending` | Age of Stars, Elden Lord | Flag de final na tabela `endings` |
| `progression` | Roundtable Hold, Erdtree aflame | Flag de progressao do jogo |
| `misc` | Prattling Pate, Spirit Steed | Flags diversas de evento |

### Estrutura de dados -- `data/achievements.json`

```json
[
  {
    "achievement_id": "legendary_armaments",
    "steam_api_name": "ELDEN_RING_ACHIEVEMENT_0028",
    "name_pt": "Armamentos Lendarios",
    "name_en": "Legendary Armaments",
    "description": "Adquirir todas as armas lendarias",
    "type": "collection",
    "required_items": [
      "grafted_blade_greatsword",
      "sword_of_night_and_flame",
      "ruins_greatsword",
      "marais_executioners_sword",
      "dark_moon_greatsword",
      "bolt_of_gransax",
      "eclipse_shotel",
      "devourers_scepter",
      "golden_order_greatsword"
    ],
    "required_flags": null
  },
  {
    "achievement_id": "shardbearer_godrick",
    "steam_api_name": "ELDEN_RING_ACHIEVEMENT_0006",
    "name_pt": "Portador de Fragmento: Godrick",
    "name_en": "Shardbearer Godrick",
    "description": "Derrotar Godrick the Grafted",
    "type": "boss",
    "required_items": null,
    "required_flags": [10000]
  },
  {
    "achievement_id": "age_of_stars",
    "steam_api_name": "ELDEN_RING_ACHIEVEMENT_0040",
    "name_pt": "Era das Estrelas",
    "name_en": "Age of the Stars",
    "description": "Alcancar o final Era das Estrelas",
    "type": "ending",
    "required_items": null,
    "required_flags": [9200]
  }
]
```

### Logica de resolucao

O modulo `src/achievement_resolver.py` avalia cada conquista:

- **collection**: Verifica se todos os `required_items` existem na tabela `collectibles`
  para o slot ativo. Progresso parcial = contagem de itens encontrados / total.
- **boss**: Verifica se todas as `required_flags` existem na tabela `boss_kills`.
- **ending**: Verifica flags na tabela `endings`.
- **progression**: Verifica flags combinadas entre `boss_kills` e `grace_discoveries`.
- **misc**: Verifica flags na tabela `collectibles` ou flags genericas.

Retorna para cada conquista: `status` (locked/in_progress/unlocked), `progress` (0.0-1.0)
e `missing` (lista de itens/flags faltantes).

---

## Barra de Progresso Global

Painel no topo do dashboard com progresso percentual por categoria:

```
Bosses: 78/165 (47%) | Gracas: 120/300 (40%) | Talismas: 45/100 (45%)
Armas Lend.: 5/9 (55%) | Magias Lend.: 3/7 (42%) | Conquistas: 12/42 (28%)
```

O calculo usa contagem de registros na tabela `collectibles` agrupados por
`category` contra o total esperado nos JSONs de referencia.

---

## Schema -- alteracoes

Nenhuma tabela nova. Os novos coletaveis (armas lendarias, spirit ashes, cookbooks,
fragmentos, pinturas) usam a tabela `collectibles` da Sprint 3 com categorias distintas.

Mercadores sao dados estaticos (JSON), sem tabela no banco.

---

## Arquivos a criar/modificar

| Arquivo | Acao | Descricao |
|---------|------|-----------|
| `data/collectibles/legendary_weapons.json` | Criar | 9 armas lendarias + DLC |
| `data/collectibles/legendary_sorceries.json` | Criar | 7 magias lendarias + DLC |
| `data/collectibles/spirit_ashes.json` | Criar | Spirit Ashes com coordenadas |
| `data/collectibles/cookbooks.json` | Criar | Receitas coletaveis |
| `data/collectibles/map_fragments.json` | Criar | Fragmentos de mapa por regiao |
| `data/collectibles/paintings.json` | Criar | Pinturas com local de recompensa |
| `data/merchants.json` | Criar | Mercadores com inventario |
| `data/achievements.json` | Criar | 42 conquistas com mapeamento Steam |
| `src/achievement_resolver.py` | Criar | Resolucao de conquistas via flags locais |
| `src/map_config.py` | Modificar | Constantes das novas camadas |
| `src/map_renderer.py` | Modificar | FeatureGroups e popups de mercador |
| `src/generate_icons.py` | Modificar | Icones: espada, grimorio, fantasma, etc. |
| `src/dashboard.py` | Modificar | Tab de conquistas Steam e barra de progresso |

---

## Criterios de aceite

1. Todas as camadas novas renderizam corretamente com toggle independente
2. Tab de conquistas lista as 42 conquistas com nomes PT-BR e nomes Steam originais
3. Progresso por conquista calculado corretamente via flags locais (sem API externa)
4. Conquistas de tipo `collection` resolvem contra tabela `collectibles`
5. Conquistas de tipo `boss` e `ending` resolvem contra suas respectivas tabelas
6. Itens faltantes na tab de conquistas linkam para posicao no mapa
7. Barra de progresso global calcula percentuais por categoria
8. Popup de mercador lista itens notaveis disponiveis
9. Pinturas mostram tanto o local do quadro quanto o local da recompensa
10. Performance do mapa aceitavel com todas as camadas ativas simultaneamente
11. Nenhuma regressao nas camadas das sprints anteriores
