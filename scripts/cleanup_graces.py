"""Limpa e corrige graces.json.

1. Atribui flags a graças base game que estao sem flag (usando grace_flags.json)
2. Remove entradas duplicadas
3. Normaliza nomes com typos
"""

import json
from pathlib import Path

from log import get_logger

logger = get_logger("cleanup_graces")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"

MANUAL_FLAG_MAP: dict[str, int] = {
    "Academy Gate Town (Sites of Grace)": 76204,
    "Altus Plateau (Site of Grace)": 76301,
    "Altus Tunnel (Site of Grace)": 73205,
    "Behind the Castle": 76159,
    "Bellum Church (Site of Grace)": 76208,
    "Church of Repose (Site of Grace)": 76507,
    "Converted Tower (Site of Grace)": 76237,
    "Debate Hall Site of Grace": 71401,
    "Divine Tower of East Altus: Gate": 73450,
    "Divine Tower of West Altus Gate": 73432,
    "Dragonkin Soldier": 71210,
    "Fallen Ruins of the Lakes": 76236,
    "Fort Gael North Site": 76402,
    "Gael Tunnel (Site of Grace)": 73207,
    "Gatefront Ruins": 76111,
    "Giants' Gravepost": 76506,
    "Grand Lift of Rold (Site of Grace)": 76502,
    "Highroad Cave Site": 73117,
    "Isolated Merchant's Shack (Dragonbarrow)": 76451,
    "Isolated Merchant's Shack (Weeping Peninsula)": 76156,
    "Magma Wyrm Site of Grace": 73900,
    "Margit, the Fell Omen Site": 71001,
    "Road's End Catacombs (Site of Grace)": 73003,
    "Sainted Hero's Grave (Site of Grace)": 73008,
    "Schoolhouse Classroom Site": 71403,
    "Tombsward Cave (Site of Grace)": 73102,
    "Village of the Albinaurics (Site of Grace)": 76220,
    "Volcano Manor (Site of Grace)": 71602,
    "Yelough Anix Tunnel Site of Grace": 73211,
}

NAME_CORRECTIONS: dict[str, str] = {
    "Forbiden Lands": "Forbidden Lands",
    "Leyndell Catacomb": "Leyndell Catacombs",
    "Murkwaver Cave (Site of Grace)": "Murkwater Cave",
    "Lenne's Rise. (Site of Grace)": "Lenne's Rise",
    "Worshipper's Woods": "Worshippers' Woods",
    "Fallen Ruins of the Lakes": "Fallen Ruins of the Lake",
    "Debate Hall Site of Grace": "Debate Parlour",
    "Divine Tower of East Altus: Gate": "Divine Tower of the East Altus: Gate",
    "Divine Tower of West Altus Gate": "Divine Tower of West Altus: Gate",
    "Fort Gael North Site": "Fort Gael North",
    "Highroad Cave Site": "Highroad Cave",
    "Magma Wyrm Site of Grace": "Magma Wyrm",
    "Margit, the Fell Omen Site": "Margit, the Fell Omen",
    "Schoolhouse Classroom Site": "Schoolhouse Classroom",
    "Academy Gate Town (Sites of Grace)": "Academy Gate Town",
    "Altus Plateau (Site of Grace)": "Altus Plateau",
    "Altus Tunnel (Site of Grace)": "Altus Tunnel",
    "Bellum Church (Site of Grace)": "Bellum Church",
    "Church of Repose (Site of Grace)": "Church of Repose",
    "Converted Tower (Site of Grace)": "Converted Tower",
    "Gael Tunnel (Site of Grace)": "Gael Tunnel",
    "Grand Lift of Rold (Site of Grace)": "Grand Lift of Rold",
    "Road's End Catacombs (Site of Grace)": "Road's End Catacombs",
    "Sainted Hero's Grave (Site of Grace)": "Sainted Hero's Grave",
    "Tombsward Cave (Site of Grace)": "Tombsward Cave",
    "Village of the Albinaurics (Site of Grace)": "Village of the Albinaurics",
    "Volcano Manor (Site of Grace)": "Volcano Manor",
    "Yelough Anix Tunnel Site of Grace": "Yelough Anix Tunnel",
    "Elden Throne Site of Grace": "Elden Throne",
    "Gatefront Ruins": "Gatefront",
    "Dragonkin Soldier": "Dragonkin Soldier of Nokstella",
}

ENTRIES_TO_REMOVE: set[str] = {
    "Elden Throne Site of Grace",
    "Forbiden Lands",
    "Leyndell Catacomb",
    "Divine Tower of East Altus: Gates",
}


def resolve_artist_shack(graces: list[dict]) -> None:
    """Resolve a ambiguidade do Artist's Shack verificando coordenadas."""
    for g in graces:
        if g["name"] == "Artist's Shack" and g.get("flag") is None:
            lat = g.get("lat", 0)
            lng = g.get("lng", 0)
            limgrave_lat, limgrave_lng = -83.5, 167.6
            liurnia_lat, liurnia_lng = -58.0, 142.0
            dist_lim = ((lat - limgrave_lat)**2 + (lng - limgrave_lng)**2)**0.5
            dist_lir = ((lat - liurnia_lat)**2 + (lng - liurnia_lng)**2)**0.5
            if dist_lir < dist_lim:
                g["flag"] = 76217
                g["name"] = "Artist's Shack (Liurnia)"
                logger.info("Artist's Shack resolvido como Liurnia (flag=76217)")
            else:
                g["flag"] = 76103
                g["name"] = "Artist's Shack (Limgrave)"
                logger.info("Artist's Shack resolvido como Limgrave (flag=76103)")


def find_divine_tower_duplicate(graces: list[dict]) -> str | None:
    """Encontra a segunda entrada duplicada de 'Divine Tower of East Altus'."""
    seen = False
    for g in graces:
        if g["name"] == "Divine Tower of East Altus" and g.get("flag") is None:
            if seen:
                return g["name"]
            seen = True
    return None


def main() -> None:
    graces_path = REFERENCES_DIR / "graces.json"
    with open(graces_path, encoding="utf-8") as f:
        graces = json.load(f)

    logger.info("graces.json atual: %d entradas", len(graces))

    resolve_artist_shack(graces)

    divine_tower_dup_indices: list[int] = []
    divine_tower_first_seen = False
    for i, g in enumerate(graces):
        if g["name"] == "Divine Tower of East Altus" and g.get("flag") is None:
            if divine_tower_first_seen:
                divine_tower_dup_indices.append(i)
            else:
                divine_tower_first_seen = True
                g["flag"] = 73451
                g["name"] = "Divine Tower of the East Altus"
                logger.info("Divine Tower of East Altus -> flag 73451")

    flags_assigned = 0
    names_corrected = 0
    to_remove_indices: set[int] = set(divine_tower_dup_indices)

    for i, g in enumerate(graces):
        name = g["name"]

        if name in ENTRIES_TO_REMOVE:
            to_remove_indices.add(i)
            logger.info("Removendo duplicata: %s", name)
            continue

        if g.get("flag") is None and name in MANUAL_FLAG_MAP:
            g["flag"] = MANUAL_FLAG_MAP[name]
            flags_assigned += 1

        if name in NAME_CORRECTIONS:
            corrected = NAME_CORRECTIONS[name]
            existing = [
                eg for eg in graces
                if eg["name"] == corrected and eg.get("flag") is not None
            ]
            if existing and g.get("flag") == existing[0].get("flag"):
                to_remove_indices.add(i)
                logger.info("Removendo duplicata corrigida: %s -> %s", name, corrected)
                continue
            g["name"] = corrected
            names_corrected += 1

    updated = [g for i, g in enumerate(graces) if i not in to_remove_indices]

    updated.sort(key=lambda x: (x.get("region", ""), x.get("name", "")))

    with open(graces_path, "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)
        f.write("\n")

    removed = len(graces) - len(updated)
    logger.info("graces.json salvo: %d entradas", len(updated))
    logger.info("  Flags atribuidos: %d", flags_assigned)
    logger.info("  Nomes corrigidos: %d", names_corrected)
    logger.info("  Entradas removidas: %d", removed)

    null_base = sum(
        1 for g in updated
        if g.get("flag") is None and g.get("region") != "dlc"
    )
    null_dlc = sum(
        1 for g in updated
        if g.get("flag") is None and g.get("region") == "dlc"
    )
    logger.info("  Base game sem flag: %d", null_base)
    logger.info("  DLC sem flag: %d", null_dlc)


if __name__ == "__main__":
    main()


# "Ordem e progresso nao sao apenas um lema." -- Auguste Comte
