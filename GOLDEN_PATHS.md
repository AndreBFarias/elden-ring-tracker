# Golden Paths — Elden Ring Tracker

Cenários de teste para validação manual do dashboard. Cada cenário define pré-condições,
passos, resultado esperado e resultado em caso de falha.

---

## Cenário GP-01: Primeiro uso — setup, configurar save e sincronizar

### Pré-condições
- Repositório clonado, `.venv` não existe
- Steam/Proton instalado com Elden Ring jogado ao menos uma vez (arquivo `ER0000.sl2` existente)

### Passos
1. Executar `bash setup.sh`
2. Executar `bash run.sh`
3. No dashboard, clicar em "Configurar path do save" e informar o caminho até `ER0000.sl2`
4. Clicar em "Sincronizar Save"

### Resultado esperado
- Dashboard carrega sem erro
- Métricas de nível, runas e NG+ aparecem no topo
- Slot 0 selecionado por padrão

### Resultado em erro
- Mensagem de erro visível no dashboard descrevendo o problema (path inválido, arquivo corrompido, etc.)
- Nenhum crash silencioso

---

## Cenário GP-02: Mapa — visualizar região e alternar camadas

### Pré-condições
- Save sincronizado (GP-01 concluído)
- Tiles de mapa disponíveis em `assets/map_tiles/`

### Passos
1. Abrir aba **Mapa**
2. Na sidebar, selecionar região "Superfície"
3. Ativar camada "Bosses"
4. Verificar marcadores no mapa
5. Desativar "Bosses", ativar "Graças"
6. Trocar região para "Subterrâneo"

### Resultado esperado
- Mapa renderiza com marcadores correspondentes a cada camada ativa
- Troca de região recarrega o mapa sem erro de widget
- Tooltip dos marcadores exibe nome e status

### Resultado em erro
- Mapa em branco sem mensagem de erro
- Erro de chave duplicada no Streamlit (DuplicateWidgetID)

---

## Cenário GP-03: Filtro "A fazer" — mapa mostra só pendentes

### Pré-condições
- Save sincronizado com ao menos um boss morto e um boss vivo
- Camada "Bosses" ativada

### Passos
1. Na sidebar, selecionar filtro "A fazer"
2. Abrir aba **Mapa**
3. Verificar marcadores de bosses exibidos

### Resultado esperado
- Apenas bosses ainda vivos aparecem no mapa
- Bosses já mortos não exibem marcador

### Resultado em erro
- Todos os bosses aparecem (filtro ignorado)
- Mapa em branco mesmo havendo pendentes

---

## Cenário GP-04: Filtro "Feito" — mapa mostra só concluídos

### Pré-condições
- Save sincronizado com ao menos um boss morto

### Passos
1. Na sidebar, selecionar filtro "Feito"
2. Abrir aba **Mapa** com camada "Bosses" ativa

### Resultado esperado
- Apenas bosses mortos aparecem no mapa

### Resultado em erro
- Bosses vivos aparecem misturados
- Mapa em branco mesmo havendo bosses mortos

---

## Cenário GP-05: Filtro + "Nenhum" — mapa limpo sem erro de widget

### Pré-condições
- Filtro "A fazer" ou "Feito" ativo
- Ao menos uma camada ativa

### Passos
1. Clicar no botão "Nenhum" para desativar todas as camadas
2. Verificar que o mapa renderiza sem marcadores
3. Verificar que não há erro de widget no console

### Resultado esperado
- Mapa renderiza vazio (sem marcadores)
- Nenhum `DuplicateWidgetID` no log

### Resultado em erro
- Erro de chave duplicada ao clicar "Nenhum"
- Interface trava ou exige reload manual

---

## Cenário GP-06: Progresso — filtro "A fazer" mostra pendentes

### Pré-condições
- Save sincronizado
- Filtro "A fazer" selecionado na sidebar

### Passos
1. Abrir aba **Progresso**
2. Expandir categoria "Bosses"
3. Verificar itens listados

### Resultado esperado
- Apenas bosses pendentes aparecem nos expanders
- Contagem no cabeçalho da categoria reflete só os pendentes

### Resultado em erro
- Bosses concluídos aparecem misturados
- Contagem incorreta

---

## Cenário GP-07: Progresso — filtro "Feito" mostra concluídos

### Pré-condições
- Save sincronizado com ao menos um boss morto
- Filtro "Feito" selecionado na sidebar

### Passos
1. Abrir aba **Progresso**
2. Expandir categoria "Bosses"

### Resultado esperado
- Apenas bosses mortos aparecem
- Checklist manual de itens concluídos aparece marcado

### Resultado em erro
- Lista vazia mesmo com bosses mortos detectados
- Itens de checklist manual aparecem desmarcados

---

## Cenário GP-08: Conquistas — filtro por tipo e completion_mode

### Pré-condições
- Save sincronizado
- Ao menos uma conquista resolvida automaticamente

### Passos
1. Abrir aba **Conquistas**
2. Selecionar filtro "Feito" na sidebar (filtro global)
3. Verificar barra de progresso e lista de conquistas
4. Selecionar filtro "A fazer"
5. Verificar lista atualizada

### Resultado esperado
- "Feito": lista mostra apenas conquistas resolvidas, barra reflete porcentagem correta
- "A fazer": lista mostra conquistas pendentes sem sobreposição

### Resultado em erro
- Lista vazia em ambos os modos
- Barra de progresso não atualiza com o filtro

---

## Cenário GP-09: Eventos perdíveis — verificar evento crítico disponível

### Pré-condições
- Save sincronizado em NG (primeiro ciclo)

### Passos
1. Abrir aba **Eventos Perdíveis**
2. Localizar evento com severidade "critical"
3. Verificar status e condição de perda exibidos

### Resultado esperado
- Evento crítico exibe status "disponível" ou "perdido" de acordo com o save
- Condição de perda descrita em texto legível

### Resultado em erro
- Todos os eventos aparecem como "disponível" independente do save
- Coluna de severidade em branco

---

## Cenário GP-10: Busca de marcador no mapa + "Ver no Mapa" da aba Progresso

### Pré-condições
- Save sincronizado
- Aba Progresso com ao menos um item listado com coordenadas de mapa

### Passos
1. Na aba **Progresso**, localizar item com botão "Ver no Mapa"
2. Clicar em "Ver no Mapa"
3. Verificar se a aba Mapa é ativada e o marcador correspondente fica destacado ou visível

### Resultado esperado
- Navegação para aba Mapa centrada na posição do item
- Marcador visível na viewport inicial

### Resultado em erro
- Aba Mapa abre mas mapa não centraliza no item
- Botão não responde

---

## Cenário GP-11: Troca de slot de personagem

### Pré-condições
- Save com dois ou mais slots com personagens distintos

### Passos
1. Selecionar slot 0 na sidebar
2. Anotar nome do personagem e nível exibidos
3. Selecionar slot 1

### Resultado esperado
- Métricas, mapa e progresso atualizam para refletir o personagem do slot selecionado
- Nome do personagem muda no header

### Resultado em erro
- Dashboard exibe dados do slot anterior
- Erro de tipo ou KeyError no log

---

## Cenário GP-12: Sincronização manual via botão "Sincronizar Save"

### Pré-condições
- Dashboard aberto com save já sincronizado uma vez
- Elden Ring rodando em outra janela (ou arquivo de save modificado manualmente)

### Passos
1. Clicar em "Sincronizar Save" na sidebar
2. Aguardar mensagem de confirmação

### Resultado esperado
- Métricas atualizam refletindo o estado mais recente do save
- Log registra evento de sincronização com timestamp

### Resultado em erro
- Mensagem de sucesso exibida mas dados não atualizam
- Erro silencioso sem mensagem ao usuário

---

## Cenário GP-13: Diagnóstico de flags via CLI

### Pré-condições
- Save disponível em path conhecido
- `.venv` ativado

### Passos
1. Executar:
   ```bash
   python3 scripts/diagnose_flags.py --save /caminho/ER0000.sl2 --slot 0 --category boss
   ```
2. Verificar saída no terminal

### Resultado esperado
- Lista de flags ativos com ID e nome
- Contagem total ao final
- Sem traceback ou exceção não tratada

### Resultado em erro
- `FileNotFoundError` sem mensagem amigável
- Flags listados sem nome (IDs sem mapeamento)

---

*"Não existe teste sem critério de falha definido."*
