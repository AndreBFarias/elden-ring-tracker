# Pesquisa: NPC Quest Tracking via Event Flags

## Contexto

O tracking de progressao de quests NPC requer conhecimento dos event flags
internos do Elden Ring. Diferente de bosses e gracas (que usam flags simples
de bit unico), quests NPC usam flags multi-byte no sistema EMEVD (Event
Meta-Variable Data).

## Estado Atual

### Flags Confirmados

Apenas 2 NPC death flags foram confirmados via testes:

| NPC | Flag ID | Status |
|-----|---------|--------|
| Iron Fist Alexander | 7606 | Confirmado |
| Millicent | 7611 | Confirmado |

### Flags Nao Confirmados

Os 50 NPC death flags restantes em `npc_dead_flags.json` precisam de
validacao. Os IDs foram extraidos de fontes comunitarias mas nao
foram testados contra saves reais.

## Abordagens para Extracao de Flags

### 1. EMEVD Decompilation (DarkScript3)

**Ferramenta:** DarkScript3 (https://github.com/JKAnderson/DarkScript3)

**Processo:**
1. Extrair EMEVD scripts do jogo via Yabber/UXM
2. Decompilar para formato legivel
3. Identificar event IDs associados a NPCs
4. Mapear condicoes de trigger para quest steps

**Vantagem:** Fonte de verdade completa
**Desvantagem:** Requer copia do jogo e ferramentas de modding

### 2. Runtime Flag Diffing

**Processo:**
1. Criar save backup antes de interacao com NPC
2. Executar acao no jogo (falar, entregar item, etc.)
3. Comparar event flags do save antes vs depois
4. Registrar flags que mudaram

**Ferramenta recomendada:** `scripts/diagnose_flags.py --save <path> --slot 0`

**Vantagem:** Nao requer ferramentas de modding
**Desvantagem:** Trabalhoso, requer playthrough manual

### 3. Referencia Comunitaria

**Fontes:**
- soulsmods/elden-ring-eventparam (https://soulsmods.github.io/elden-ring-eventparam/)
- mhogeveen/er-quest-tracker (quest steps estruturados, sem flag IDs)
- yosoyelfede/elden-ring-questline-map (grafo visual de quests)

**Vantagem:** Disponivel imediatamente
**Desvantagem:** Incompleto, sem flag IDs mapeados

## Proximos Passos

1. Validar os 50 NPC dead flags restantes via runtime diffing
2. Pesquisar EMEVD scripts decompilados publicados pela comunidade
3. Expandir `npc_quests.json` com mais NPCs e quest steps
4. Implementar UI de quest tracking quando dados suficientes existirem

## Estrutura de Dados

O arquivo `data/references/npc_quests.json` segue o schema:

```json
{
  "npc": "Nome do NPC",
  "questline": "Nome da Questline",
  "region": "surface|underground|dlc",
  "steps": [
    {"step": "Descricao do passo", "flag_id": null}
  ],
  "reward": "Recompensa final",
  "missable": true,
  "loss_condition": "Condicao de perda ou null"
}
```

Campos `flag_id` sao `null` ate serem confirmados via testes.
