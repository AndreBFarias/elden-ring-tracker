# Guia de Contribuição -- GraceMap

## Como Contribuir

1. Fork → branch feature → PR contra `main`
2. Commits em PT-BR (Conventional Commits)

## Padrão

- PT-BR com acentuação correta
- Zero emojis, zero menção IA
- Type hints sempre
- `logging` (nunca print em produção)

## Testes

```bash
pytest tests/ -v
```

## Lint

```bash
ruff check src tests
```

## Save File Format

O parser binário em `src/save_parser.py` decodifica o formato de save do jogo. Qualquer alteração deve preservar compatibilidade com slots existentes e ser testada contra fixtures de múltiplos patches do jogo.
