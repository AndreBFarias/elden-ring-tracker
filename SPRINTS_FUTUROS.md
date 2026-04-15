# Sprints Futuros -- Elden Ring Tracker

Documento de planejamento para sprints futuros identificados durante
a análise comparativa com CyberGiant7/Elden-Ring-Automatic-Checklist
e a auditoria de gaps do projeto (2026-04-14).

---

## Sprint 10: Localização e Coordenadas de Spirit Ashes

**Prioridade:** Alta
**Estimativa:** 1 semana
**Dependência:** Sprint 5 (Spirit Ashes já estão em item_ids.json e items.json)

### Contexto

Os 84 Spirit Ashes adicionados no Sprint 5 têm `lat: 0.0, lng: 0.0` porque
nenhuma fonte pública exporta coordenadas de mapa para eles. No mapa, eles
não aparecem em posição útil.

### Entregas

1. **Mapear coordenadas dos Spirit Ashes**
   - Fonte primária: mapeamento manual via Fextralife Interactive Map
     (coords visíveis na URL: `lat=-109.245&lng=59.690`)
   - Fonte alternativa: scraping das páginas de itens na wiki
   - Target: pelo menos os 64 base game (priorizar sobre DLC)
   - Atualizar `items.json` com lat/lng reais

2. **Script de auxílio** (`scripts/map_spirit_ash_coords.py`)
   - Recebe nome do spirit ash e coordenadas via CLI
   - Atualiza items.json automaticamente
   - Validação contra coordenadas existentes

### Fontes de dados identificadas

- Fextralife Interactive Map: coords na URL mas sem export JSON
- Nenhum projeto open-source exporta essas coords
- Alternativa: Phil25/erdb pode ter dados de localização (verificar)

---

## Sprint 11: NPC Questline Tracking Completo

**Prioridade:** Alta
**Estimativa:** 2 semanas
**Dependência:** Sprint 9 (skeleton npc_quests.json + QUEST_TRACKING_RESEARCH.md)

### Contexto

O `npc_quests.json` criado no Sprint 9 cobre apenas 5 NPCs (Ranni,
Alexander, Millicent, Blaidd, Nepheli) com `flag_id: null` em quase todos
os steps. O tracking real de quest steps requer conhecimento dos event flags
EMEVD, que são multi-byte e mal documentados publicamente.

### Entregas

1. **Expandir npc_quests.json para 30+ NPCs**
   - Fonte: mhogeveen/er-quest-tracker (35+ NPCs, quest steps estruturados)
   - Fonte: yosoyelfede/elden-ring-questline-map (grafo de dependências)
   - Converter para o schema do projeto (JSON com steps, rewards, loss_conditions)

2. **Validar NPC death flags** (50 pendentes)
   - Usar runtime flag diffing com `scripts/diagnose_flags.py`
   - Documentar flags confirmados vs rejeitados
   - Atualizar `npc_dead_flags.json` com status de cada flag

3. **Pesquisa de EMEVD quest flags**
   - Fonte: soulsmods/elden-ring-eventparam (referência de event flags)
   - Objetivo: mapear pelo menos 10 quest-step flags dos NPCs principais
   - Ferramenta: DarkScript3 para decompilação de EMEVD scripts

4. **UI de quest tracking** (`src/tabs/quests.py`)
   - Nova tab "Quests" no dashboard (ou sub-seção em Progresso)
   - Visualização de steps por NPC com status (pendente/completo/perdido)
   - Integração com event flags quando disponíveis

### Fontes de dados

| Fonte | URL | Dados | Formato |
|-------|-----|-------|---------|
| er-quest-tracker | github.com/mhogeveen/er-quest-tracker | 35+ NPCs, steps, rewards | TypeScript |
| elden-ring-questline-map | github.com/yosoyelfede/elden-ring-questline-map | Grafo de dependências | JS/HTML |
| elden-ring-eventparam | soulsmods.github.io/elden-ring-eventparam/ | Event flag IDs | Web reference |
| ERDB | github.com/EldenRingDatabase/erdb | Item metadata | JSON, MIT |

---

## Sprint 12: Eventos Perdíveis -- Melhoria de Auto-Detecção

**Prioridade:** Média
**Estimativa:** 1 semana
**Dependência:** Sprint 11 (dados de quest tracking)

### Contexto

Dos 20 eventos perdíveis em `missable_events.json`, apenas 9 têm
`loss_boss_flags` para auto-detecção. Os outros 11 dependem de tracking
manual. Com dados de quest progression do Sprint 11, podemos melhorar isso.

### Entregas

1. **Adicionar loss_boss_flags para 11 eventos sem auto-detecção**
   - Millicent: precisa de flag de Commander O'Neil ou estado de quest
   - Nepheli/Kenneth/Gostoc: precisa de flag de Morgott
   - Sellen: precisa de flag de progresso na Academy
   - Alexander: já tem death flag (7606), adicionar flag de boss triggers
   - DLC questlines (Thiollier, Ansbach, Hornsent): pesquisar boss triggers

2. **Adicionar itens perdíveis ao tracking**
   - Novo campo `missable_items` em `missable_events.json`
   - Listar recompensas específicas que se perdem com cada evento
   - Cross-reference com `item_ids.json` para matching automático

3. **Marcar bosses como perdíveis**
   - Atualizar campo `missable` e `missable_after` em `bosses.json`
   - Bosses que bloqueiam quests quando derrotados (Rykard, Morgott, etc.)
   - Usado pela UI para alertar o jogador antes de lutar

4. **Melhorar UI de eventos perdíveis**
   - Mostrar itens que serão perdidos com cada evento
   - Indicador visual de "risco" em bosses que bloqueiam quests
   - Link direto para quests afetadas

---

## Sprint 13: Download Completo de Imagens

**Prioridade:** Baixa
**Estimativa:** 0.5 semana
**Dependência:** Sprint 7 (script fetch_item_images.py já existe)

### Contexto

O Sprint 7 criou o `scripts/fetch_item_images.py` e baixou ~54 imagens
de teste. A fonte (CyberGiant7 GitHub) funciona para categorias que o
projeto referência cobre (weapon, armor, talisman, spell, spirit_ash).
Não cobre consumables, materials, upgrade_materials, key_items.

### Entregas

1. **Download completo das categorias cobertas**
   - `python scripts/fetch_item_images.py` (sem --limit)
   - Categorias: weapon (~399), armor (~717), talisman (~155), spell (~213),
     spirit_ash (~84), shield (~79)
   - Estimativa: ~1700 imagens, ~30 MB

2. **Fonte alternativa para categorias não cobertas**
   - Pesquisar Kaggle datasets (robikscube/elden-ring-ultimate-dataset)
   - Pesquisar Reddit post do u/Erigondo (imagens extraídas do jogo)
   - Avaliar viabilidade de scraping da wiki com headless browser

3. **Otimização de tamanho**
   - Converter para .webp se não estiver
   - Redimensionar para 80x80 (thumbnails)
   - Estimar tamanho final e decidir se inclui no .deb/.AppImage

---

## Sprint 14: Completude de Dados de Referência

**Prioridade:** Média
**Estimativa:** 1.5 semanas
**Dependência:** Nenhuma

### Contexto

Gaps identificados na auditoria de dados:

- Armas: 12/271 sem subcategoria (nomes com sufixo de localização)
- Armaduras: 50 "Sets" sem subcategoria (são conjuntos, não peças individuais)
- Feitiços: 5/119 sem subcategoria (nomes divergentes)
- Ashes of War: 10/95 sem afinidade mapeada

### Entregas

1. **Corrigir matching de nomes com localização**
   - Melhorar `_strip_location_suffix` no `enrich_subcategories.py`
   - Adicionar correções manuais para os 12 nomes divergentes de armas
   - Adicionar mapeamento de armor sets -> peças individuais

2. **Expandir item_ids.json com fontes externas**
   - ERDB (`pip install erdb`) para IDs completos
   - Kaggle datasets para consumables/materials faltantes
   - Target: de 2012 para 3000+ IDs

3. **Validação cruzada completa**
   - Rodar `scripts/validate_references.py` com verificações extras
   - Comparar contagens contra wiki oficial
   - Documentar discrepâncias conhecidas

---

## Sprint 15: Tradução de Nomes para PT-BR

**Prioridade:** Baixa
**Estimativa:** 1 semana
**Dependência:** Sprint 14 (dados completos)

### Contexto

Todos os nomes de itens, bosses, graças e NPCs estão em inglês. O jogo
tem localização oficial em PT-BR. A wiki Fextralife e o ERDB não fornecem
nomes localizados, mas o projeto elden-ring-data/msg tem dados de
localização extraídos diretamente do jogo.

### Entregas

1. **Obter nomes PT-BR do jogo**
   - Fonte: github.com/elden-ring-data/msg (JSON multilíngue)
   - Extrair mapeamento EN -> PT-BR para itens, bosses, graças
   - Criar `data/references/translations_ptbr.json`

2. **Toggle de idioma na sidebar**
   - Checkbox "Nomes em PT-BR" com fallback para inglês
   - Aplicar tradução na camada de apresentação (não alterar dados originais)

3. **Localizar UI labels fixos**
   - Nomes de subcategorias (Dagger -> Adaga, Straight Sword -> Espada Reta)
   - Nomes de regiões (Surface -> Superfície, já parcialmente feito)
   - Nomes de afinidades (Heavy -> Pesado, Keen -> Afiado, etc.)

### Fontes

- elden-ring-data/msg: github.com/elden-ring-data/msg (JSON do jogo)
- Licença: verificar compatibilidade com GPL-3.0

---

## Priorização e Dependências

```
Sprint 10 (Coords Spirit Ashes) ─────────── Independente
Sprint 11 (NPC Questlines) ──────────────── Independente
  |
  └── Sprint 12 (Missable Auto-Detection) ── Depende de 11
Sprint 13 (Download Imagens) ────────────── Independente
Sprint 14 (Completude de Dados) ─────────── Independente
  |
  └── Sprint 15 (Tradução PT-BR) ────────── Depende de 14
```

## Ordem Recomendada

1. Sprint 10 (coords) + Sprint 11 (quests) -- podem rodar em paralelo
2. Sprint 12 (missable) -- depende de 11
3. Sprint 14 (completude) -- independente, pode antecipar
4. Sprint 13 (imagens) -- baixa prioridade, rodar quando conveniente
5. Sprint 15 (tradução) -- depende de 14, última prioridade
