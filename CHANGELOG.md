# Changelog

## [Não lançado]

## [1.4.0] - 2026-04-15

### Adicionado
- Subcategorização de itens: 38 tipos de arma, 4 slots de armadura (Head/Body/Arms/Legs), Sorcery/Incantation para feitiços, 13 afinidades para Ashes of War
- Spirit Ashes como nova categoria trackeável: 84 entradas (64 base + 20 DLC) com IDs extraídos do formato BND4
- Cards visuais na tab Progresso: thumbnails base64 inline, links para wiki Fextralife, tags de região
- `wiki_links.json` com 2072 links determinísticos para wiki Fextralife
- `scripts/fetch_item_images.py` para download de thumbnails .webp (fonte: CyberGiant7 GitHub)
- `scripts/enrich_subcategories.py` para enriquecimento automatizado de items.json
- Dropdown de subcategoria dentro de cada expander de equipamento (filtra por tipo específico)
- Toggle "Incluir DLC" na sidebar: filtra itens com `is_dlc` em todas as categorias
- Toggle "Incluir armaduras alteradas" na sidebar: filtra armaduras com `(Altered)` no nome
- Busca full-text na tab Progresso: filtra por nome cross-categoria com ocultação automática de categorias vazias
- Dropdown de ordenação (Padrão, A-Z, Região) na tab Progresso
- `npc_quests.json` com dados skeleton de 5 NPCs principais (Ranni, Alexander, Millicent, Blaidd, Nepheli)
- `QUEST_TRACKING_RESEARCH.md` documentando abordagens para extração de quest flags
- `SPRINTS_FUTUROS.md` com planejamento de 6 sprints futuros (10-15)
- Novos arquivos de referência: `weapon_types.json`, `armor_slots.json`, `spell_types.json`, `ash_of_war_types.json`

### Alterado
- `items.json` enriquecido com campos `subcategory`, `is_dlc`, `is_altered` para 3087 itens
- `item_ids.json` expandido com categoria `spirit_ash` (84 IDs)
- `inventory_parser.py` resolve Spirit Ashes na cadeia de goods
- `map_config.py` inclui SPIRIT_ASH como CategoryConfig em Equipamento
- `progress_tracker.py` propaga subcategory, is_dlc, is_altered nos dicts de progresso
- `tabs/progress.py` refatorado com subcategory_resolver, cards visuais, filtros e busca

## [1.3.0] - 2026-03-18

### Adicionado
- Integração de graças DLC: `graces.json` expandido para 423 entradas (105 DLC com flag)
- `grace_flags.json` expandido de 321 para 419 entradas (+98 DLC)
- `npc_dead_flags.json` expandido de 2 para 52 entradas para auto-tracking de mortes de NPC
- `boss_flags.json` expandido para 262 entradas com cobertura completa de flags
- `bosses.json` atualizado para 217 entradas com 206 vinculados a flags
- `story_flags.json` adicionado com 34 flags de progressão narrativa
- `item_ids.json` expandido de 1469 para 2012 IDs (+543) em 8 categorias
- `dungeons.json` auditado: 306 entradas com `dungeon_type` classificado
- Scripts de integração: `integrate_dlc_graces.py`, `integrate_npc_dead_flags.py`, `integrate_remaining_bosses.py`, `integrate_story_flags.py`, `audit_dungeons.py`, `expand_item_ids.py`
- Utilitário compartilhado `scripts/fetch_utils.py` para requisições HTTP com retry
- Script `scripts/validate_references.py` para validação cruzada de referências
- Script `scripts/cleanup_graces.py` para limpeza de duplicatas em graças

### Alterado
- Normalização de matching em `progress_tracker.py`: comparação case-insensitive e strip de nomes para reduzir falsos negativos

## [1.2.0] - 2026-03-17

### Adicionado
- Filtro global "A fazer / Feito" na sidebar afeta mapa, progresso e conquistas simultaneamente
- Parâmetro `completion_mode` propagado de `_render_sidebar()` até `build_map()`, `progress.render()` e `achievements.render()`
- `build_map()` recebe `completed_names: set[str]` para filtrar marcadores por nome

### Corrigido
- Conflito de chave Streamlit nos checkboxes de camada ao clicar "Nenhum": removido `value=True` hardcoded, session_state inicializado uma vez antes do widget
- `build_map()` não usava mais `progress_mode="total"` hardcoded — substituído por `completion_mode` + `completed_names`

### Alterado
- `st.radio(key="completion_mode")` movido da aba Progresso para a sidebar — controle global
- Assinatura de `_render_map()` expandida com `completion_mode: str`
- Assinatura de `achievements.render()` expandida com `completion_mode: str = "all"`

## [1.1.0] - 2026-03-16

### Adicionado
- Auto-tracking de NPCs via event flags
- Scripts de diagnóstico e aplicação de patches
- Enriquecimento de item_ids com IDs de goods
- Vinculação de dungeons a boss_flags
- Scripts: apply_patches.py, diagnose_block7.py, link_npc_graces.py, map_invader_boss_flags.py
- Screenshots de validação end-to-end

### Corrigido
- Tracking de dungeons, NPCs e invasores NPC

## [1.0.0] - 2024-01-01

### Adicionado
- Interface GTK4 para rastreamento de progresso no Elden Ring
- Abas: Progresso, Mapa, Eventos, Conquistas, Sessões, Feitiços
- Banco de dados SQLite local
- Packaging .deb e Flatpak
- Scripts de instalação e desinstalação
