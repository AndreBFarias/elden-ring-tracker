import logging
import sqlite3
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# #1
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tracker.db"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.database")
logger.setLevel(logging.DEBUG)

_handler = RotatingFileHandler(
    LOG_DIR / "tracker.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
logger.addHandler(_handler)

# #2
SCHEMA = """
CREATE TABLE IF NOT EXISTS player_stats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_index  INTEGER NOT NULL CHECK (slot_index BETWEEN 0 AND 9),
    level       INTEGER NOT NULL,
    runes_held  INTEGER NOT NULL DEFAULT 0,
    vigor       INTEGER NOT NULL DEFAULT 0,
    mind        INTEGER NOT NULL DEFAULT 0,
    endurance   INTEGER NOT NULL DEFAULT 0,
    strength    INTEGER NOT NULL DEFAULT 0,
    dexterity   INTEGER NOT NULL DEFAULT 0,
    intelligence INTEGER NOT NULL DEFAULT 0,
    faith       INTEGER NOT NULL DEFAULT 0,
    arcane      INTEGER NOT NULL DEFAULT 0,
    hp          INTEGER NOT NULL DEFAULT 0,
    fp          INTEGER NOT NULL DEFAULT 0,
    stamina     INTEGER NOT NULL DEFAULT 0,
    pos_x       REAL,
    pos_y       REAL,
    pos_z       REAL,
    ng_plus     INTEGER NOT NULL DEFAULT 0,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS boss_kills (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_index  INTEGER NOT NULL CHECK (slot_index BETWEEN 0 AND 9),
    boss_flag   INTEGER NOT NULL,
    defeated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (slot_index, boss_flag)
);

CREATE TABLE IF NOT EXISTS grace_discoveries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_index    INTEGER NOT NULL CHECK (slot_index BETWEEN 0 AND 9),
    grace_flag    INTEGER NOT NULL,
    discovered_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (slot_index, grace_flag)
);

CREATE TABLE IF NOT EXISTS map_progress (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_index  INTEGER NOT NULL CHECK (slot_index BETWEEN 0 AND 9),
    map_flag    INTEGER NOT NULL,
    flag_type   TEXT NOT NULL CHECK (flag_type IN ('reveal', 'acquire')),
    unlocked_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (slot_index, map_flag)
);

CREATE TABLE IF NOT EXISTS play_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_index  INTEGER NOT NULL CHECK (slot_index BETWEEN 0 AND 9),
    started_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    ended_at    TEXT,
    level_start INTEGER,
    level_end   INTEGER,
    runes_start INTEGER,
    runes_end   INTEGER
);

CREATE TABLE IF NOT EXISTS endings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_index  INTEGER NOT NULL CHECK (slot_index BETWEEN 0 AND 9),
    ending_flag INTEGER NOT NULL,
    achieved_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (slot_index, ending_flag)
);

CREATE INDEX IF NOT EXISTS idx_stats_slot_time
    ON player_stats (slot_index, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_boss_slot
    ON boss_kills (slot_index);
CREATE INDEX IF NOT EXISTS idx_grace_slot
    ON grace_discoveries (slot_index);
CREATE INDEX IF NOT EXISTS idx_sessions_slot
    ON play_sessions (slot_index, started_at DESC);
"""


# #3
def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


# #4
def initialize_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        logger.info("Banco de dados inicializado: %s", DB_PATH)
    finally:
        conn.close()


# --- Escritas (commit atomico via context manager) ---

# #5
def insert_player_stats(slot_index: int, stats: dict) -> None:
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO player_stats (
                    slot_index, level, runes_held,
                    vigor, mind, endurance, strength, dexterity,
                    intelligence, faith, arcane,
                    hp, fp, stamina, pos_x, pos_y, pos_z, ng_plus
                ) VALUES (
                    :slot_index, :level, :runes_held,
                    :vigor, :mind, :endurance, :strength, :dexterity,
                    :intelligence, :faith, :arcane,
                    :hp, :fp, :stamina, :pos_x, :pos_y, :pos_z, :ng_plus
                )
                """,
                {"slot_index": slot_index, **stats},
            )
        logger.debug("Snapshot de stats inserido para slot %d", slot_index)
    finally:
        conn.close()


# #6
def insert_boss_kill(slot_index: int, boss_flag: int) -> None:
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO boss_kills (slot_index, boss_flag) VALUES (?, ?)",
                (slot_index, boss_flag),
            )
        logger.debug("Boss flag %d registrada para slot %d", boss_flag, slot_index)
    finally:
        conn.close()


def insert_grace_discovery(slot_index: int, grace_flag: int) -> None:
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO grace_discoveries (slot_index, grace_flag) VALUES (?, ?)",
                (slot_index, grace_flag),
            )
        logger.debug("Grace flag %d registrada para slot %d", grace_flag, slot_index)
    finally:
        conn.close()


def insert_map_progress(slot_index: int, map_flag: int, flag_type: str) -> None:
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO map_progress (slot_index, map_flag, flag_type) VALUES (?, ?, ?)",
                (slot_index, map_flag, flag_type),
            )
        logger.debug(
            "Map flag %d (%s) registrada para slot %d",
            map_flag,
            flag_type,
            slot_index,
        )
    finally:
        conn.close()


def insert_ending(slot_index: int, ending_flag: int) -> None:
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO endings (slot_index, ending_flag) VALUES (?, ?)",
                (slot_index, ending_flag),
            )
        logger.debug("Ending flag %d registrada para slot %d", ending_flag, slot_index)
    finally:
        conn.close()


# #7
def start_session(slot_index: int, level: int, runes: int) -> int:
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO play_sessions (slot_index, level_start, runes_start)
                VALUES (?, ?, ?)
                """,
                (slot_index, level, runes),
            )
        session_id = cursor.lastrowid
        logger.info("Sessao %d iniciada para slot %d", session_id, slot_index)
        return session_id
    finally:
        conn.close()


def end_session(session_id: int, level: int, runes: int) -> None:
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE play_sessions
                SET ended_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                    level_end = ?,
                    runes_end = ?
                WHERE id = ?
                """,
                (level, runes, session_id),
            )
        logger.info("Sessao %d encerrada", session_id)
    finally:
        conn.close()


# --- Leituras ---

# #8
def get_latest_stats(slot_index: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT * FROM player_stats
            WHERE slot_index = ?
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (slot_index,),
        ).fetchone()
        return row
    finally:
        conn.close()


def get_boss_kills(slot_index: int) -> list[sqlite3.Row]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM boss_kills WHERE slot_index = ? ORDER BY defeated_at",
            (slot_index,),
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_grace_discoveries(slot_index: int) -> list[sqlite3.Row]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM grace_discoveries WHERE slot_index = ? ORDER BY discovered_at",
            (slot_index,),
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_stats_history(slot_index: int, limit: int = 100) -> list[sqlite3.Row]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM player_stats
            WHERE slot_index = ?
            ORDER BY recorded_at DESC
            LIMIT ?
            """,
            (slot_index, limit),
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_active_session(slot_index: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT * FROM play_sessions
            WHERE slot_index = ? AND ended_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (slot_index,),
        ).fetchone()
        return row
    finally:
        conn.close()


# #9
if __name__ == "__main__":
    initialize_db()
    logger.info("Modulo database executado diretamente -- banco inicializado.")


# "O segredo da liberdade esta na coragem." -- Pericles
