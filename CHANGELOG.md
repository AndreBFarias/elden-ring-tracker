# Changelog

## [Não lançado]

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
