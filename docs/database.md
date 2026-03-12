# database.py -- Documentacao Pareada

Modulo de persistencia temporal para o Elden Ring Progress Tracker.
Cada marcador `#N` abaixo corresponde ao mesmo marcador no codigo-fonte.

---

## #1 Configuracao e Logging

O `DB_PATH` e calculado relativamente ao proprio modulo para funcionar
independente do diretorio de execucao. O logger usa `RotatingFileHandler`
com limite de 5 MB e 3 backups, evitando crescimento descontrolado de logs.

---

## #2 Schema -- 6 tabelas

### player_stats (append-only)

Cada leitura do save file gera um novo registro com timestamp. Isso permite
construir series temporais de nivel, runas e atributos para graficos de
progressao no dashboard. O campo `slot_index` identifica qual dos 10 slots
de personagem do `ER0000.sl2` foi lido (0 a 9).

Campos de posicao (`pos_x`, `pos_y`, `pos_z`) sao REAL porque o jogo
armazena coordenadas como float32.

### boss_kills, grace_discoveries, endings (UNIQUE + INSERT OR IGNORE)

Tabelas de eventos unicos por slot. A constraint `UNIQUE(slot_index, flag)`
combinada com `INSERT OR IGNORE` garante idempotencia: o watcher pode
processar o mesmo save file varias vezes sem duplicar registros. O timestamp
captura o momento da primeira deteccao.

### map_progress

Similar as tabelas de eventos, mas com `flag_type` distinguindo entre
revelacao do mapa (fog of war) e aquisicao do fragmento fisico.

Faixas de referencia (de `Elden_ring_research.md`):
- Revelacao: flags `62000-62099`
- Aquisicao: flags `63000-63099`

### play_sessions

Registra sessoes de jogo com timestamps de inicio e fim. Uma sessao
com `ended_at IS NULL` indica que o jogador esta ativo. O delta entre
`level_start`/`level_end` e `runes_start`/`runes_end` permite calcular
eficiencia de farm por sessao.

### Indices

- `idx_stats_slot_time`: Otimiza a query mais frequente do dashboard
  (ultimo snapshot de um slot, ORDER BY recorded_at DESC).
- `idx_boss_slot`, `idx_grace_slot`: Filtros por slot nas listas de progresso.
- `idx_sessions_slot`: Busca de sessao ativa e historico recente.

---

## #3 get_connection()

Configura a conexao com tres PRAGMAs criticos:

- **WAL (Write-Ahead Logging)**: Permite leituras concorrentes durante
  escritas. Essencial porque o watcher escreve enquanto o Streamlit le.
- **foreign_keys=ON**: Ativado explicitamente porque o SQLite desabilita
  por padrao em cada nova conexao.
- **busy_timeout=5000**: Espera ate 5 segundos em caso de lock, evitando
  erros de `database is locked` durante picos de escrita.

O `row_factory = sqlite3.Row` permite acessar colunas por nome nas leituras.

---

## #4 initialize_db()

Executa o schema completo via `executescript()`, que roda todas as
instrucoes DDL em uma unica transacao implicita. Seguro para re-execucao
gracas ao `IF NOT EXISTS` em todas as tabelas e indices.

---

## #5 insert_player_stats()

Recebe um dicionario `stats` com as chaves correspondentes aos atributos
do personagem. O unpacking `{"slot_index": slot_index, **stats}` permite
que o parser binario passe os dados diretamente sem transformacao.

---

## #6 Insercoes de eventos (boss, grace, map, ending)

Todas usam `INSERT OR IGNORE` para que flags ja registradas sejam
silenciosamente ignoradas. O padrao e:

```sql
INSERT OR IGNORE INTO tabela (slot_index, flag) VALUES (?, ?)
```

O timestamp de deteccao e preenchido pelo DEFAULT da coluna.

---

## #7 Sessoes de jogo (start/end)

`start_session()` retorna o `id` da sessao criada para que o watcher
possa referencia-lo ao chamar `end_session()` quando detectar inatividade
ou fechamento do jogo.

---

## #8 Queries de leitura

Todas retornam `sqlite3.Row` (acesso por nome de coluna). O dashboard
consome essas funcoes para:

- `get_latest_stats()`: Painel principal com nivel, runas e atributos atuais.
- `get_boss_kills()`: Lista de chefes derrotados com timestamps.
- `get_grace_discoveries()`: Lista de gracas descobertas.
- `get_stats_history()`: Serie temporal para graficos de progressao.
- `get_active_session()`: Indicador de sessao ativa no header do dashboard.

### Queries comuns do dashboard

```sql
-- Progressao de nivel nas ultimas 24h
SELECT level, recorded_at FROM player_stats
WHERE slot_index = 0
  AND recorded_at >= datetime('now', '-1 day')
ORDER BY recorded_at;

-- Total de chefes derrotados por slot
SELECT slot_index, COUNT(*) as total
FROM boss_kills GROUP BY slot_index;

-- Duracao media de sessoes
SELECT slot_index,
       AVG(julianday(ended_at) - julianday(started_at)) * 24 as avg_hours
FROM play_sessions
WHERE ended_at IS NOT NULL
GROUP BY slot_index;
```

---

## #9 Execucao direta

`python3 src/database.py` inicializa o banco, criando `data/tracker.db`
com todas as tabelas e indices. Util para verificacao rapida do schema.
