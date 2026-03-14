import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_user_dirs() -> tuple[Path, Path]:
    if str(_PROJECT_ROOT).startswith("/opt/"):
        base = Path(os.environ.get(
            "XDG_DATA_HOME",
            Path.home() / ".local" / "share",
        )) / "elden-ring-tracker"
        return base / "logs", base
    return _PROJECT_ROOT / "logs", _PROJECT_ROOT / "data"


LOG_DIR, DB_DIR = _resolve_user_dirs()
LOG_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = DB_DIR / "config.json"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"elden_tracker.{name}")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(
            LOG_DIR / "tracker.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    return logger

# "O segredo da liberdade reside na coragem." -- Pericles
