import json
import logging
import math
import shutil
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CALIBRATION_FILE = PROJECT_ROOT / "data" / "calibration_points.json"
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"
BACKUP_DIR = PROJECT_ROOT / "data" / "references" / "backup"

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.recalibrate")
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

OLD_COORDS = {
    "surface": {
        "stranded_graveyard": (2269.5, 5691.5),
        "first_step": (2432.3, 5843.0),
        "church_elleh": (2206.0, 5617.8),
        "gatefront": (2247.3, 5379.3),
        "stormveil": (1715.5, 5189.0),
        "godrick": (1776.0, 5030.0),
        "raya_lucaria": (728.0, 3778.0),
        "volcano_manor": (1013.0, 2093.0),
        "leyndell": (2894.0, 2816.0),
        "radahn": (4257.9, 5296.0),
        "castle_sol": (4145.5, 1268.5),
        "fire_giant": (4689.0, 2199.0),
        "malenia": (3830.4, 571.9),
        "farum_azula": (6069.8, 3451.2),
        "weeping_peninsula": (2703.5, 6362.5),
    },
    "underground": {
        "siofra_river": (745.6, 512.1),
        "ainsel_river": (345.4, 481.6),
        "nokron": (637.5, 549.8),
        "deeproot_depths": (506.8, 133.9),
        "mohgwyn_palace": (907.0, 518.2),
        "lake_of_rot": (181.0, 631.9),
    },
    "dlc": {
        "gravesite_plain": (889.0, 1904.0),
        "castle_ensis": (1038.8, 1254.5),
        "shadow_keep": (1313.8, 659.7),
        "abyssal_woods": (1323.0, 2026.9),
        "enir_ilim": (324.0, 1181.3),
    },
}

DIRECT_MAPPINGS = {
    "surface": {
        "first_step": [("graces.json", "The First Step")],
        "church_elleh": [("graces.json", "Church of Elleh")],
        "gatefront": [("graces.json", "Gatefront")],
        "stormveil": [
            ("dungeons.json", "Stormveil Castle"),
            ("graces.json", "Stormveil Main Gate"),
        ],
        "godrick": [
            ("bosses.json", "Godrick the Grafted"),
            ("graces.json", "Godrick the Grafted"),
        ],
        "raya_lucaria": [
            ("dungeons.json", "Raya Lucaria Academy"),
            ("bosses.json", "Rennala, Queen of the Full Moon"),
        ],
        "volcano_manor": [("dungeons.json", "Volcano Manor")],
        "leyndell": [
            ("dungeons.json", "Leyndell, Royal Capital"),
            ("bosses.json", "Morgott, the Omen King"),
        ],
        "radahn": [("bosses.json", "Starscourge Radahn")],
        "fire_giant": [("bosses.json", "Fire Giant")],
        "malenia": [
            ("dungeons.json", "Miquella's Haligtree"),
            ("bosses.json", "Malenia, Blade of Miquella"),
        ],
        "farum_azula": [("bosses.json", "Dragonlord Placidusax")],
        "castle_sol": [("graces.json", "Church of the Eclipse")],
    },
    "underground": {
        "siofra_river": [("graces.json", "Siofra River Bank")],
        "ainsel_river": [("graces.json", "Ainsel River Main")],
        "mohgwyn_palace": [("bosses.json", "Mohg, Lord of Blood")],
        "deeproot_depths": [("bosses.json", "Lichdragon Fortissax")],
        "lake_of_rot": [("bosses.json", "Astel, Naturalborn of the Void")],
        "nokron": [("bosses.json", "Regal Ancestor Spirit")],
    },
    "dlc": {
        "gravesite_plain": [("graces.json", "Gravesite Plain")],
        "shadow_keep": [
            ("graces.json", "Shadow Keep"),
            ("bosses.json", "Messmer the Impaler"),
        ],
        "enir_ilim": [("bosses.json", "Promised Consort Radahn")],
    },
}

JSON_FILES = ["bosses.json", "graces.json", "dungeons.json"]


def _load_calibration() -> dict:
    if not CALIBRATION_FILE.exists():
        logger.error("Arquivo de calibracao nao encontrado: %s", CALIBRATION_FILE)
        return {}
    with open(str(CALIBRATION_FILE), encoding="utf-8") as f:
        return json.load(f)


def _load_json(filename: str) -> list[dict]:
    path = REFERENCES_DIR / filename
    if not path.exists():
        return []
    with open(str(path), encoding="utf-8") as f:
        return json.load(f)


def _save_json(filename: str, data: list[dict]) -> None:
    path = REFERENCES_DIR / filename
    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _backup_jsons() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for filename in JSON_FILES:
        source = REFERENCES_DIR / filename
        if source.exists():
            dest = BACKUP_DIR / f"{source.stem}_{timestamp}{source.suffix}"
            shutil.copy2(str(source), str(dest))
            logger.info("Backup criado: %s", dest.name)


def _idw_interpolate(
    point: tuple[float, float],
    anchors_old: list[tuple[float, float]],
    anchors_new: list[tuple[float, float]],
    power: float = 2.0,
) -> tuple[float, float]:
    weights = []
    deltas_x = []
    deltas_y = []

    for (ox, oy), (nx, ny) in zip(anchors_old, anchors_new):
        dist = math.sqrt((point[0] - ox) ** 2 + (point[1] - oy) ** 2)

        if dist < 1.0:
            return (nx, ny)

        w = 1.0 / (dist ** power)
        weights.append(w)
        deltas_x.append(nx - ox)
        deltas_y.append(ny - oy)

    total_w = sum(weights)
    avg_dx = sum(w * dx for w, dx in zip(weights, deltas_x)) / total_w
    avg_dy = sum(w * dy for w, dy in zip(weights, deltas_y)) / total_w

    return (point[0] + avg_dx, point[1] + avg_dy)


def _build_direct_map(
    region: str,
    calibration: dict,
) -> dict[str, dict[str, tuple[float, float]]]:
    result = {}
    mappings = DIRECT_MAPPINGS.get(region, {})
    region_cal = calibration.get(region, {})

    for cal_id, entries in mappings.items():
        if cal_id not in region_cal:
            continue
        new_x = region_cal[cal_id]["pos_x"]
        new_y = region_cal[cal_id]["pos_y"]

        for filename, entry_name in entries:
            if filename not in result:
                result[filename] = {}
            result[filename][entry_name] = (new_x, new_y)

    return result


def _build_anchors(
    region: str,
    calibration: dict,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    old_coords = OLD_COORDS.get(region, {})
    region_cal = calibration.get(region, {})

    anchors_old = []
    anchors_new = []

    for cal_id, (ox, oy) in old_coords.items():
        if cal_id in region_cal:
            anchors_old.append((ox, oy))
            anchors_new.append((region_cal[cal_id]["pos_x"], region_cal[cal_id]["pos_y"]))

    return anchors_old, anchors_new


def recalibrate() -> None:
    calibration = _load_calibration()
    if not calibration:
        logger.error("Calibracao vazia ou nao encontrada. Execute a pagina de calibracao primeiro.")
        return

    _backup_jsons()

    json_data = {}
    for filename in JSON_FILES:
        json_data[filename] = _load_json(filename)

    total_direct = 0
    total_interpolated = 0

    for region in OLD_COORDS:
        region_cal = calibration.get(region, {})
        if not region_cal:
            logger.info("Regiao '%s' sem pontos calibrados, pulando.", region)
            continue

        cal_count = len(region_cal)
        logger.info("Processando regiao '%s' com %d pontos calibrados.", region, cal_count)

        direct_map = _build_direct_map(region, calibration)
        anchors_old, anchors_new = _build_anchors(region, calibration)

        for filename in JSON_FILES:
            entries = json_data[filename]
            file_directs = direct_map.get(filename, {})

            for entry in entries:
                if entry.get("region") != region:
                    continue

                name = entry["name"]

                if name in file_directs:
                    new_x, new_y = file_directs[name]
                    entry["pos_x"] = round(new_x, 1)
                    entry["pos_y"] = round(new_y, 1)
                    total_direct += 1
                    logger.info(
                        "  [direto] %s -> (%.1f, %.1f)",
                        name, new_x, new_y,
                    )
                elif len(anchors_old) >= 3:
                    old_point = (entry["pos_x"], entry["pos_y"])
                    new_x, new_y = _idw_interpolate(old_point, anchors_old, anchors_new)
                    entry["pos_x"] = round(new_x, 1)
                    entry["pos_y"] = round(new_y, 1)
                    total_interpolated += 1
                    logger.info(
                        "  [interpolado] %s: (%.1f, %.1f) -> (%.1f, %.1f)",
                        name, old_point[0], old_point[1], new_x, new_y,
                    )
                else:
                    logger.warning(
                        "  [ignorado] %s: menos de 3 ancoras para interpolacao na regiao '%s'",
                        name, region,
                    )

    for filename in JSON_FILES:
        _save_json(filename, json_data[filename])
        logger.info("Salvo: %s", filename)

    logger.info(
        "Recalibracao concluida: %d diretos, %d interpolados.",
        total_direct, total_interpolated,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(console)

    recalibrate()


# "Medir o que e mensuravel e tornar mensuravel o que nao e." -- Galileu Galilei
