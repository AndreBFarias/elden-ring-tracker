# Sprint 3 -- NPCs, Eventos e Coletaveis Criticos

## Dependencias

- Sprint 2 concluida: dashboard funcional, mapa com camadas base (Bosses, Gracas, Dungeons, Player).
- Infraestrutura de camadas (`map_renderer.py`, `map_config.py`, `generate_icons.py`) operacional.

---

## Objetivo

Adicionar camadas de rastreamento para NPCs com questlines, eventos perdiveis e
coletaveis criticos (talismas, sementes, lagrimas). Essas categorias sao as que mais
impactam a experiencia de jogo quando perdidas.

---

## Camadas do Mapa

| Camada | Quantidade aprox. | Icone | Particularidade |
|--------|-------------------|-------|-----------------|
| NPCs | ~40 questlines | Silhueta roxa | Posicao muda por fase da quest |
| Eventos perdiveis | ~15 criticos | Triangulo vermelho | Alerta visual pulsante |
| Talismas | ~100 base + DLC | Medalha verde | Localizacao fixa |
| Sementes Douradas | 30 base + DLC | Semente amarela | Localizacao fixa |
| Lagrimas Sagradas | 12 base + DLC | Gota azul | Localizacao fixa |
| Lagrimas de Larva | 18 total | Larva laranja | Recurso limitado (respec) |

---

## NPCs e Questlines

O sistema de NPCs e o mais complexo desta sprint. Cada NPC tem uma sequencia de
encontros em locais diferentes, condicionados por flags do jogo.

### Estrutura de dados -- `data/npcs.json`

```json
[
  {
    "npc_id": "ranni",
    "name": "Ranni the Witch",
    "questline": "Age of Stars",
    "encounters": [
      {
        "phase": 1,
        "location": "Church of Elleh",
        "pos_x": 1100.0,
        "pos_y": 3200.0,
        "trigger_flag": 71000,
        "description": "Encontro inicial, recebe Spirit Calling Bell"
      },
      {
        "phase": 2,
        "location": "Ranni's Rise",
        "pos_x": 2400.0,
        "pos_y": 1800.0,
        "trigger_flag": 71010,
        "description": "Inicio da questline principal"
      }
    ]
  }
]
```

O mapa exibe apenas a fase atual do NPC (baseado nas flags detectadas), com popup
mostrando o historico de fases anteriores.

---

## Eventos Perdiveis

Eventos que se tornam inacessiveis apos certos triggers do jogo. O sistema precisa
de duas flags: a flag de trigger (evento disponivel) e a flag de perda (ponto sem retorno).

### Estrutura de dados -- `data/missable_events.json`

```json
[
  {
    "event_id": "goldmask_law",
    "name": "Goldmask - Lei da Regressao",
    "trigger_flag": 74200,
    "loss_flag": 74250,
    "loss_condition": "Queimar a Erdtree",
    "pos_x": 3100.0,
    "pos_y": 2900.0,
    "severity": "critical"
  }
]
```

Severidade: `critical` (afeta conquistas/finais), `moderate` (perde item unico), `minor` (perde dialogo).

No mapa, eventos perdiveis com `loss_flag` ja ativada sao exibidos com opacidade
reduzida e marcacao de "perdido".

---

## Coletaveis com Localizacao Fixa

Talismas, sementes, lagrimas sagradas e lagrimas de larva compartilham o mesmo
formato de dados. Cada um tem localizacao fixa e flag de aquisicao.

### Estrutura de dados -- `data/collectibles/`

Diretorio com um JSON por categoria: `talismans.json`, `golden_seeds.json`,
`sacred_tears.json`, `larval_tears.json`.

```json
[
  {
    "item_id": "erdtrees_favor",
    "name": "Erdtree's Favor",
    "category": "talisman",
    "flag": 65100,
    "pos_x": 2200.0,
    "pos_y": 3400.0,
    "region": "Limgrave",
    "description": "Aumenta HP, stamina e equip load"
  }
]
```

---

## Schema -- novas tabelas

### npc_encounters

```sql
CREATE TABLE IF NOT EXISTS npc_encounters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_index INTEGER NOT NULL,
    npc_id TEXT NOT NULL,
    phase INTEGER NOT NULL,
    flag INTEGER NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(slot_index, npc_id, phase)
);

CREATE INDEX IF NOT EXISTS idx_npc_slot ON npc_encounters(slot_index);
```

### collectibles

```sql
CREATE TABLE IF NOT EXISTS collectibles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_index INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    category TEXT NOT NULL,
    flag INTEGER NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(slot_index, item_id)
);

CREATE INDEX IF NOT EXISTS idx_collectibles_slot_cat
    ON collectibles(slot_index, category);
```

---

## Arquivos a criar/modificar

| Arquivo | Acao | Descricao |
|---------|------|-----------|
| `data/npcs.json` | Criar | Catalogo de NPCs com fases e coordenadas |
| `data/missable_events.json` | Criar | Eventos perdiveis com flags de trigger/perda |
| `data/collectibles/*.json` | Criar | JSONs por categoria de coletavel |
| `src/database.py` | Modificar | Adicionar tabelas `npc_encounters` e `collectibles` |
| `src/map_config.py` | Modificar | Novas constantes de camada e cores |
| `src/map_renderer.py` | Modificar | Novas FeatureGroups e logica de fase NPC |
| `src/generate_icons.py` | Modificar | Novos icones: npc, talisman, seed, tear, larva |
| `src/dashboard.py` | Modificar | Novos filtros na sidebar e metricas de coletaveis |

---

## Criterios de aceite

1. NPCs exibidos na fase correta com historico de fases anteriores no popup
2. Eventos perdiveis com alerta visual diferenciado por severidade
3. Eventos ja perdidos marcados com opacidade reduzida
4. Talismas, sementes e lagrimas como camadas toggleaveis independentes
5. Contadores de progresso por categoria no painel de metricas
6. Novas tabelas criadas sem quebrar schema existente (migracao aditiva)
7. Todos os JSONs de dados validados contra schema esperado
