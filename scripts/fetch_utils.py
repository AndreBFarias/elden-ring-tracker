"""Utilitarios compartilhados para scripts de integracao de fontes externas.

Funcoes de download (GitHub raw), backup e salvamento padronizado de JSON.
"""

import json
import shutil
import ssl
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"
BACKUP_DIR = REFERENCES_DIR / "backup"


def fetch_raw_github(owner: str, repo: str, branch: str, path: str) -> str:
    """Download de arquivo cru do GitHub via raw.githubusercontent.com."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "elden-ring-tracker/1.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return resp.read().decode("utf-8")


def backup_file(path: Path) -> Path | None:
    """Cria copia timestamped em data/references/backup/. Retorna path do backup."""
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"{path.stem}_{ts}{path.suffix}"
    shutil.copy2(path, dest)
    return dest


def save_json(path: Path, data: dict | list) -> None:
    """Escrita padronizada de JSON (indent=2, ensure_ascii=False, newline final)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_json(filename: str) -> dict | list:
    """Carrega JSON do diretorio de referencias."""
    path = REFERENCES_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_bst_blocks() -> set[int]:
    """Retorna conjunto de block IDs presentes no eventflag_bst.txt."""
    bst_path = PROJECT_ROOT / "data" / "eventflag_bst.txt"
    blocks: set[int] = set()
    with open(bst_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) == 2:
                blocks.add(int(parts[0]))
    return blocks


def normalize_name(name: str) -> str:
    """Normaliza nome para comparacao: lowercase, sem pontuacao, sem espacos extras."""
    import re
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


# "Quem controla o passado controla o futuro." -- George Orwell
