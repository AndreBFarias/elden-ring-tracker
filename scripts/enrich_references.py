import json
import logging
import shutil
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"
BACKUP_DIR = REFERENCES_DIR / "backup"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.enrich")
if not logger.handlers:
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


BOSS_FLAGS = {
    "Margit, the Fell Omen": {"flag": 9100, "is_main": False, "type": "field", "missable": False},
    "Godrick the Grafted": {"flag": 9101, "is_main": True, "type": "legacy", "missable": False},
    "Grafted Scion": {"flag": 9103, "is_main": False, "type": "legacy", "missable": False},
    "Morgott, the Omen King": {"flag": 9104, "is_main": True, "type": "legacy", "missable": False},
    "Godfrey, First Elden Lord (Golden Shade)": {"flag": 9105, "is_main": False, "type": "legacy", "missable": False},
    "Sir Gideon Ofnir, the All-Knowing": {"flag": 9106, "is_main": False, "type": "legacy", "missable": False},
    "Hoarah Loux, Warrior": {"flag": 9107, "is_main": True, "type": "legacy", "missable": False},
    "Astel, Naturalborn of the Void": {"flag": 9108, "is_main": False, "type": "dungeon", "missable": False},
    "Dragonkin Soldier of Nokstella": {"flag": 9109, "is_main": False, "type": "dungeon", "missable": False},
    "Valiant Gargoyles": {"flag": 9110, "is_main": False, "type": "dungeon", "missable": False},
    "Valiant Gargoyle": {"flag": 9110, "is_main": False, "type": "dungeon", "missable": False},
    "Lichdragon Fortissax": {"flag": 9111, "is_main": False, "type": "dungeon", "missable": False},
    "Mohg, Lord of Blood": {"flag": 9112, "is_main": True, "type": "dungeon", "missable": False},
    "Godskin Duo": {"flag": 9114, "is_main": True, "type": "legacy", "missable": False},
    "Dragonlord Placidusax": {"flag": 9115, "is_main": False, "type": "dungeon", "missable": False},
    "Maliketh, the Black Blade": {"flag": 9116, "is_main": True, "type": "legacy", "missable": False},
    "Red Wolf of Radagon": {"flag": 9117, "is_main": False, "type": "legacy", "missable": False},
    "Rennala, Queen of the Full Moon": {"flag": 9118, "is_main": True, "type": "legacy", "missable": False},
    "Loretta, Knight of the Haligtree": {"flag": 9119, "is_main": False, "type": "legacy", "missable": False},
    "Malenia, Blade of Miquella": {"flag": 9120, "is_main": True, "type": "dungeon", "missable": False},
    "Godskin Noble (Volcano Manor)": {"flag": 9121, "is_main": False, "type": "legacy", "missable": False},
    "Rykard, Lord of Blasphemy": {"flag": 9122, "is_main": True, "type": "legacy", "missable": False},
    "Elden Beast": {"flag": 9123, "is_main": True, "type": "legacy", "missable": False},
    "Mohg, the Omen": {"flag": 9125, "is_main": False, "type": "dungeon", "missable": False},
    "Magma Wyrm Makar": {"flag": 9126, "is_main": False, "type": "dungeon", "missable": False},
    "Ulcerated Tree Spirit": {"flag": 9128, "is_main": False, "type": "dungeon", "missable": False},
    "Abductor Virgins": {"flag": 9129, "is_main": False, "type": "dungeon", "missable": False},
    "Starscourge Radahn": {"flag": 9130, "is_main": True, "type": "field", "missable": False},
    "Fire Giant": {"flag": 9131, "is_main": True, "type": "field", "missable": False},
    "Ancestor Spirit": {"flag": 9132, "is_main": False, "type": "dungeon", "missable": False},
    "Regal Ancestor Spirit": {"flag": 9133, "is_main": False, "type": "dungeon", "missable": False},
    "Mimic Tear": {"flag": 9134, "is_main": False, "type": "dungeon", "missable": False},
    "Fia's Champions": {"flag": 9135, "is_main": False, "type": "dungeon", "missable": False},
    "Divine Beast Dancing Lion": {"flag": 9140, "is_main": True, "type": "dlc", "missable": False},
    "Promised Consort Radahn": {"flag": 9143, "is_main": True, "type": "dlc", "missable": False},
    "Golden Hippopotamus": {"flag": 9144, "is_main": False, "type": "dlc", "missable": False},
    "Messmer the Impaler": {"flag": 9146, "is_main": True, "type": "dlc", "missable": False},
    "Putrescent Knight": {"flag": 9148, "is_main": False, "type": "dlc", "missable": False},
    "Metyr, Mother of Fingers": {"flag": 9155, "is_main": False, "type": "dlc", "missable": False},
    "Midra, Lord of Frenzied Flame": {"flag": 9156, "is_main": False, "type": "dlc", "missable": False},
    "Romina, Saint of the Bud": {"flag": 9160, "is_main": True, "type": "dlc", "missable": False},
    "Jori, Elder Inquisitor": {"flag": 9161, "is_main": False, "type": "dlc", "missable": False},
    "Scadutree Avatar": {"flag": 9162, "is_main": False, "type": "dlc", "missable": False},
    "Bayle, the Dread": {"flag": 9163, "is_main": True, "type": "dlc", "missable": False},
    "Bayle the Dread": {"flag": 9163, "is_main": True, "type": "dlc", "missable": False},
    "Commander Gaius": {"flag": 9164, "is_main": False, "type": "dlc", "missable": False},
    "Godskin Apostle (Dragonbarrow)": {"flag": 9173, "is_main": False, "type": "dungeon", "missable": False},
    "Fell Twins": {"flag": 9174, "is_main": False, "type": "dungeon", "missable": False},
    "Leonine Misbegotten": {"flag": 9180, "is_main": False, "type": "dungeon", "missable": False},
    "Royal Knight Loretta": {"flag": 9181, "is_main": False, "type": "dungeon", "missable": False},
    "Elemer of the Briar": {"flag": 9182, "is_main": False, "type": "dungeon", "missable": False},
    "Crucible Knight & Misbegotten Warrior": {"flag": 9183, "is_main": False, "type": "dungeon", "missable": False},
    "Commander Niall": {"flag": 9184, "is_main": False, "type": "dungeon", "missable": False},
    "Rellana, Twin Moon Knight": {"flag": 9190, "is_main": True, "type": "dlc", "missable": False},
}


GRACE_FLAGS = {
    "Godrick the Grafted": 71000,
    "Margit, the Fell Omen": 71001,
    "Castleward Tunnel": 71002,
    "Gateside Chamber": 71003,
    "Stormveil Cliffside": 71004,
    "Rampart Tower": 71005,
    "Liftside Chamber": 71006,
    "Secluded Cell": 71007,
    "Stormveil Main Gate": 71008,
    "Elden Throne": 71100,
    "Erdtree Sanctuary": 71101,
    "East Capital Rampart": 71102,
    "Lower Capital Church": 71103,
    "Avenue Balcony": 71104,
    "West Capital Rampart": 71105,
    "Queen's Bedchamber": 71107,
    "Fortified Manor, First Floor": 71108,
    "Divine Bridge": 71109,
    "Elden Throne (Ashen)": 71120,
    "Erdtree Sanctuary (Ashen)": 71121,
    "East Capital Rampart (Ashen)": 71122,
    "Leyndell, Capital of Ash": 71123,
    "Queen's Bedchamber (Ashen)": 71124,
    "Divine Bridge (Ashen)": 71125,
    "Table of Lost Grace": 71190,
    "Dragonkin Soldier of Nokstella": 71210,
    "Ainsel River Well Depths": 71211,
    "Ainsel River Sluice Gate": 71212,
    "Ainsel River Downstream": 71213,
    "Ainsel River Main": 71214,
    "Nokstella, Eternal City": 71215,
    "Lake of Rot Shoreside": 71216,
    "Grand Cloister": 71218,
    "Nokstella Waterfall Basin": 71219,
    "Great Waterfall Basin": 71220,
    "Mimic Tear": 71221,
    "Siofra River Bank": 71222,
    "Worshippers' Woods": 71223,
    "Ancestral Woods": 71224,
    "Aqueduct-Facing Cliffs": 71225,
    "Night's Sacred Ground": 71226,
    "Below the Well": 71227,
    "Prince of Death's Throne": 71230,
    "Root-Facing Cliffs": 71231,
    "Great Waterfall Crest": 71232,
    "Deeproot Depths": 71233,
    "The Nameless Eternal City": 71234,
    "Across the Roots": 71235,
    "Astel, Naturalborn of the Void": 71240,
    "Cocoon of the Empyrean": 71250,
    "Palace Approach Ledge-Road": 71251,
    "Dynasty Mausoleum Entrance": 71252,
    "Dynasty Mausoleum Midpoint": 71253,
    "Siofra River Well Depths": 71270,
    "Nokron, Eternal City": 71271,
    "Maliketh, the Black Blade": 71300,
    "Dragonlord Placidusax": 71301,
    "Dragon Temple Altar": 71302,
    "Crumbling Beast Grave": 71303,
    "Crumbling Beast Grave Depths": 71304,
    "Tempest-Facing Balcony": 71305,
    "Dragon Temple": 71306,
    "Dragon Temple Transept": 71307,
    "Dragon Temple Lift": 71308,
    "Dragon Temple Rooftop": 71309,
    "Beside the Great Bridge": 71310,
    "Raya Lucaria Grand Library": 71400,
    "Debate Parlour": 71401,
    "Church of the Cuckoo": 71402,
    "Schoolhouse Classroom": 71403,
    "Malenia, Goddess of Rot": 71500,
    "Prayer Room": 71501,
    "Elphael Inner Wall": 71502,
    "Drainage Channel": 71503,
    "Haligtree Roots": 71504,
    "Haligtree Promenade": 71505,
    "Haligtree Canopy": 71506,
    "Haligtree Town": 71507,
    "Haligtree Town Plaza": 71508,
    "Rykard, Lord of Blasphemy": 71600,
    "Temple of Eiglay": 71601,
    "Volcano Manor": 71602,
    "Prison Town Church": 71603,
    "Guest Hall": 71604,
    "Audience Pathway": 71605,
    "Abductor Virgin": 71606,
    "Subterranean Inquisition Chamber": 71607,
    "Cave of Knowledge": 71800,
    "Stranded Graveyard": 71801,
    "Fractured Marika": 71900,
    "Divine Beast Dancing Lion": 72000,
    "Promised Consort Radahn": 72010,
    "Golden Hippopotamus": 72101,
    "Messmer the Impaler": 72110,
    "Putrescent Knight": 72200,
    "Metyr, Mother of Fingers": 72500,
    "Midra, Lord of Frenzied Flame": 72800,
    "Tombsward Catacombs": 73000,
    "Impaler's Catacombs": 73001,
    "Stormfoot Catacombs": 73002,
    "Road's End Catacombs": 73003,
    "Murkwater Catacombs": 73004,
    "Black Knife Catacombs": 73005,
    "Cliffbottom Catacombs": 73006,
    "Wyndham Catacombs": 73007,
    "Sainted Hero's Grave": 73008,
    "Gelmir Hero's Grave": 73009,
    "Auriza Hero's Grave": 73010,
    "Deathtouched Catacombs": 73011,
    "Unsightly Catacombs": 73012,
    "Auriza Side Tomb": 73013,
    "Minor Erdtree Catacombs": 73014,
    "Caelid Catacombs": 73015,
    "War-Dead Catacombs": 73016,
    "Giant-Conquering Hero's Grave": 73017,
    "Giant's Mountaintop Catacombs": 73018,
    "Consecrated Snowfield Catacombs": 73019,
    "Hidden Path to the Haligtree": 73020,
    "Murkwater Cave": 73100,
    "Earthbore Cave": 73101,
    "Tombsward Cave": 73102,
    "Groveside Cave": 73103,
    "Stillwater Cave": 73104,
    "Lakeside Crystal Cave": 73105,
    "Academy Crystal Cave": 73106,
    "Seethewater Cave": 73107,
    "Volcano Cave": 73109,
    "Dragonbarrow Cave": 73110,
    "Sellia Hideaway": 73111,
    "Cave of the Forlorn": 73112,
    "Coastal Cave": 73115,
    "Highroad Cave": 73117,
    "Perfumer's Grotto": 73118,
    "Sage's Cave": 73119,
    "Abandoned Cave": 73120,
    "Gaol Cave": 73121,
    "Spiritcaller's Cave": 73122,
    "Morne Tunnel": 73200,
    "Limgrave Tunnels": 73201,
    "Raya Lucaria Crystal Tunnel": 73202,
    "Old Altus Tunnel": 73204,
    "Altus Tunnel": 73205,
    "Gael Tunnel": 73207,
    "Sellia Crystal Tunnel": 73208,
    "Yelough Anix Tunnel": 73211,
    "Rear Gael Tunnel Entrance": 73257,
    "Limgrave Tower Bridge": 73410,
    "Divine Tower of Limgrave": 73412,
    "Study Hall Entrance": 73420,
    "Liurnia Tower Bridge": 73421,
    "Divine Tower of Liurnia": 73422,
    "Divine Tower of West Altus": 73430,
    "Sealed Tunnel": 73431,
    "Divine Tower of West Altus: Gate": 73432,
    "Divine Tower of Caelid: Basement": 73440,
    "Divine Tower of Caelid: Center": 73441,
    "Divine Tower of the East Altus: Gate": 73450,
    "Divine Tower of the East Altus": 73451,
    "Isolated Divine Tower": 73460,
    "Cathedral of the Forsaken": 73500,
    "Underground Roadside": 73501,
    "Forsaken Depths": 73502,
    "Leyndell Catacombs": 73503,
    "Frenzied Flame Proscription": 73504,
    "Magma Wyrm": 73900,
    "Ruin-Strewn Precipice": 73901,
    "Ruin-Strewn Precipice Overlook": 73902,
    "Church of Elleh": 76100,
    "The First Step": 76101,
    "Stormhill Shack": 76102,
    "Artist's Shack (Limgrave)": 76103,
    "Third Church of Marika": 76104,
    "Fort Haight West": 76105,
    "Agheel Lake South": 76106,
    "Agheel Lake North": 76108,
    "Church of Dragon Communion": 76110,
    "Gatefront": 76111,
    "Seaside Ruins": 76113,
    "Mistwood Outskirts": 76114,
    "Murkwater Coast": 76116,
    "Saintsbridge": 76117,
    "Warmaster's Shack": 76118,
    "Summonwater Village Outskirts": 76119,
    "Waypoint Ruins Cellar": 76120,
    "Church of Pilgrimage": 76150,
    "Castle Morne Rampart": 76151,
    "Tombsward": 76152,
    "South of the Lookout Tower": 76153,
    "Ailing Village Outskirts": 76154,
    "Beside the Crater-Pocked Glade": 76155,
    "Isolated Merchant's Shack (Limgrave)": 76156,
    "Bridge of Sacrifice": 76157,
    "Castle Morne Lift": 76158,
    "Behind The Castle": 76159,
    "Beside the Rampart Gaol": 76160,
    "Morne Moangrave": 76161,
    "Fourth Church of Marika": 76162,
    "Lake-Facing Cliffs": 76200,
    "Liurnia Lake Shore": 76201,
    "Laskyar Ruins": 76202,
    "Scenic Isle": 76203,
    "Academy Gate Town": 76204,
    "South Raya Lucaria Gate": 76205,
    "Main Academy Gate": 76206,
    "East Raya Lucaria Gate": 76207,
    "Bellum Church": 76208,
    "Grand Lift of Dectus": 76209,
    "Foot of the Four Belfries": 76210,
    "Sorcerer's Isle": 76211,
    "Northern Liurnia Lake Shore": 76212,
    "Road to the Manor": 76213,
    "Main Caria Manor Gate": 76214,
    "Slumbering Wolf's Shack": 76215,
    "Boilprawn Shack": 76216,
    "Artist's Shack (Liurnia)": 76217,
    "Revenger's Shack": 76218,
    "Folly on the Lake": 76219,
    "Village of the Albinaurics": 76220,
    "Liurnia Highway North": 76221,
    "Gate Town Bridge": 76222,
    "Eastern Liurnia Lake Shore": 76223,
    "Church of Vows": 76224,
    "Ruined Labyrinth": 76225,
    "Mausoleum Compound": 76226,
    "The Four Belfries": 76227,
    "Ranni's Rise": 76228,
    "Ravine-Veiled Village": 76229,
    "Manor Upper Level": 76230,
    "Manor Lower Level": 76231,
    "Royal Moongazing Grounds": 76232,
    "Gate Town North": 76233,
    "Eastern Tableland": 76234,
    "The Ravine": 76235,
    "Fallen Ruins of the Lake": 76236,
    "Converted Tower": 76237,
    "Behind Caria Manor": 76238,
    "Frenzied Flame Village Outskirts": 76239,
    "Church of Inhibition": 76240,
    "Temple Quarter": 76241,
    "East Gate Bridge Trestle": 76242,
    "Crystalline Woods": 76243,
    "Liurnia Highway South": 76244,
    "Jarburg": 76245,
    "Ranni's Chamber": 76247,
    "Moonlight Altar": 76250,
    "Cathedral of Manus Celes": 76251,
    "Altar South": 76252,
    "Abandoned Coffin": 76300,
    "Altus Plateau": 76301,
    "Erdtree-Gazing Hill": 76302,
    "Altus Highway Junction": 76303,
    "Forest-Spanning Greatbridge": 76304,
    "Rampartside Path": 76305,
    "Bower of Bounty": 76306,
    "Road of Iniquity Side Path": 76307,
    "Windmill Village": 76308,
    "Outer Wall Phantom Tree": 76309,
    "Minor Erdtree Church": 76310,
    "Hermit Merchant's Shack": 76311,
    "Outer Wall Battleground": 76312,
    "Windmill Heights": 76313,
    "Capital Rampart": 76314,
    "Shaded Castle Ramparts": 76320,
    "Shaded Castle Inner Gate": 76321,
    "Castellan's Hall": 76322,
    "Bridge of Iniquity": 76350,
    "First Mt. Gelmir Campsite": 76351,
    "Ninth Mt. Gelmir Campsite": 76352,
    "Road of Iniquity": 76353,
    "Seethewater River": 76354,
    "Seethewater Terminus": 76355,
    "Craftsman's Shack": 76356,
    "Primeval Sorcerer Azur": 76357,
    "Smoldering Church": 76400,
    "Rotview Balcony": 76401,
    "Fort Gael North": 76402,
    "Caelem Ruins": 76403,
    "Cathedral of Dragon Communion": 76404,
    "Caelid Highway South": 76405,
    "Aeonia Swamp Shore": 76406,
    "Astray from Caelid Highway North": 76407,
    "Smoldering Wall": 76409,
    "Deep Siofra Well": 76410,
    "Southern Aeonia Swamp Bank": 76411,
    "Heart of Aeonia": 76412,
    "Inner Aeonia": 76413,
    "Sellia Backstreets": 76414,
    "Chair-Crypt of Sellia": 76415,
    "Sellia Under-Stair": 76416,
    "Impassable Greatbridge": 76417,
    "Church of the Plague": 76418,
    "Redmane Castle Plaza": 76419,
    "Chamber Outside the Plaza": 76420,
    "Starscourge Radahn": 76422,
    "Dragonbarrow West": 76450,
    "Isolated Merchant's Shack": 76451,
    "Dragonbarrow Fork": 76452,
    "Fort Faroth": 76453,
    "Bestial Sanctum": 76454,
    "Lenne's Rise": 76455,
    "Farum Greatbridge": 76456,
    "Forbidden Lands": 76500,
    "Zamor Ruins": 76501,
    "Grand Lift of Rold": 76502,
    "Ancient Snow Valley Ruins": 76503,
    "Freezing Lake": 76504,
    "First Church of Marika": 76505,
    "Giant's Gravepost": 76506,
    "Church of Repose": 76507,
    "Foot of the Forge": 76508,
    "Fire Giant": 76509,
    "Forge of the Giants": 76510,
    "Whiteridge Road": 76520,
    "Snow Valley Ruins Overlook": 76521,
    "Castle Sol Main Gate": 76522,
    "Church of the Eclipse": 76523,
    "Castle Sol Rooftop": 76524,
    "Consecrated Snowfield": 76550,
    "Inner Consecrated Snowfield": 76551,
    "Ordina, Liturgical Town": 76652,
    "Apostate Derelict": 76653,
}


def _backup_file(filepath: Path) -> None:
    if not filepath.exists():
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{filepath.stem}_{timestamp}{filepath.suffix}"
    shutil.copy2(str(filepath), str(BACKUP_DIR / backup_name))
    logger.info("Backup criado: %s", backup_name)


def enrich_bosses() -> int:
    path = REFERENCES_DIR / "bosses.json"
    if not path.exists():
        logger.error("bosses.json nao encontrado")
        return 0

    _backup_file(path)

    with open(str(path), encoding="utf-8") as f:
        bosses = json.load(f)

    enriched = 0
    for boss in bosses:
        name = boss["name"]
        if name in BOSS_FLAGS:
            meta = BOSS_FLAGS[name]
            boss["flag"] = meta["flag"]
            boss["is_main"] = meta["is_main"]
            boss["type"] = meta["type"]
            boss["missable"] = meta["missable"]
            boss["missable_after"] = None
            enriched += 1
        else:
            boss.setdefault("flag", None)
            boss.setdefault("is_main", False)
            boss.setdefault("type", "field")
            boss.setdefault("missable", False)
            boss.setdefault("missable_after", None)

    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(bosses, f, ensure_ascii=False, indent=2)

    logger.info("Bosses enriquecidos: %d/%d", enriched, len(bosses))
    return enriched


def enrich_graces() -> int:
    path = REFERENCES_DIR / "graces.json"
    if not path.exists():
        logger.error("graces.json nao encontrado")
        return 0

    _backup_file(path)

    with open(str(path), encoding="utf-8") as f:
        graces = json.load(f)

    enriched = 0
    for grace in graces:
        name = grace["name"]
        if name in GRACE_FLAGS:
            grace["flag"] = GRACE_FLAGS[name]
            enriched += 1
        else:
            grace.setdefault("flag", None)

    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(graces, f, ensure_ascii=False, indent=2)

    logger.info("Gracas enriquecidas: %d/%d", enriched, len(graces))
    return enriched


def enrich_npcs() -> int:
    path = REFERENCES_DIR / "npcs.json"
    if not path.exists():
        logger.error("npcs.json nao encontrado")
        return 0

    _backup_file(path)

    with open(str(path), encoding="utf-8") as f:
        npcs = json.load(f)

    for npc in npcs:
        npc.setdefault("npc_id", None)
        npc.setdefault("questline", None)
        npc.setdefault("missable", False)

    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(npcs, f, ensure_ascii=False, indent=2)

    logger.info("NPCs processados: %d", len(npcs))
    return len(npcs)


def enrich_dungeons() -> int:
    path = REFERENCES_DIR / "dungeons.json"
    if not path.exists():
        logger.error("dungeons.json nao encontrado")
        return 0

    _backup_file(path)

    with open(str(path), encoding="utf-8") as f:
        dungeons = json.load(f)

    for dungeon in dungeons:
        dungeon.setdefault("type", "dungeon")

    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(dungeons, f, ensure_ascii=False, indent=2)

    logger.info("Dungeons processadas: %d", len(dungeons))
    return len(dungeons)


def main() -> None:
    logger.info("Iniciando enriquecimento de referencias")

    boss_count = enrich_bosses()
    grace_count = enrich_graces()
    npc_count = enrich_npcs()
    dungeon_count = enrich_dungeons()

    logger.info(
        "Enriquecimento concluido: bosses=%d, gracas=%d, npcs=%d, dungeons=%d",
        boss_count, grace_count, npc_count, dungeon_count,
    )


if __name__ == "__main__":
    main()


# "Os dados estão lançados." -- Júlio César
