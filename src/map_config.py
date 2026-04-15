from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
MAP_TILES_DIR = ASSETS_DIR / "map_tiles"
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"


@dataclass(frozen=True)
class TileConfig:
    map_id: str
    tileset_id: int
    tile_size: int = 256


@dataclass(frozen=True)
class MapRegion:
    name: str
    display_name: str
    tile_config: TileConfig
    default_zoom: int
    min_zoom: int
    max_zoom: int


SURFACE = MapRegion(
    name="surface",
    display_name="Superfície",
    tile_config=TileConfig(
        map_id="map-50be4728-3907-4f33-8857-7f063e0d24eb",
        tileset_id=3,
    ),
    default_zoom=3,
    min_zoom=0,
    max_zoom=7,
)

UNDERGROUND = MapRegion(
    name="underground",
    display_name="Subterrâneo",
    tile_config=TileConfig(
        map_id="map-c5431314-6159-4599-9668-0ccf4e1f8e9a",
        tileset_id=4,
    ),
    default_zoom=3,
    min_zoom=0,
    max_zoom=7,
)

DLC = MapRegion(
    name="dlc",
    display_name="DLC",
    tile_config=TileConfig(
        map_id="map-9d02bccc-081b-4a1d-b26e-a363f366fb40",
        tileset_id=3,
    ),
    default_zoom=3,
    min_zoom=0,
    max_zoom=7,
)

EXTRA = MapRegion(
    name="extra",
    display_name="Extra",
    tile_config=TileConfig(
        map_id="map-96747699-d8a3-44b4-b2d6-cf6b45c579c6",
        tileset_id=1,
    ),
    default_zoom=3,
    min_zoom=0,
    max_zoom=7,
)

REGIONS: dict[str, MapRegion] = {
    "surface": SURFACE,
    "underground": UNDERGROUND,
    "dlc": DLC,
    "extra": EXTRA,
}

FEXTRALIFE_TILE_URL = (
    "https://eldenring.wiki.fextralife.com/file/Elden-Ring"
    "/{map_id}/map-tiles.{tileset_id}/{z}/{x}/{y}.jpg"
)


@dataclass(frozen=True)
class CategoryConfig:
    key: str
    display_name: str
    color: str
    symbol: str
    icon_filename: str
    icon_size: tuple[int, int]
    reference_file: str
    filterable: bool = True


BOSS = CategoryConfig(
    key="boss",
    display_name="Bosses",
    color="#e74c3c",
    symbol="\u2620",
    icon_filename="boss.png",
    icon_size=(32, 32),
    reference_file="bosses.json",
)

GRACE = CategoryConfig(
    key="grace",
    display_name="Graças",
    color="#f1c40f",
    symbol="\u2605",
    icon_filename="grace.png",
    icon_size=(32, 32),
    reference_file="graces.json",
)

DUNGEON = CategoryConfig(
    key="dungeon",
    display_name="Dungeons",
    color="#95a5a6",
    symbol="\u26EA",
    icon_filename="dungeon.png",
    icon_size=(32, 32),
    reference_file="dungeons.json",
)

WEAPON = CategoryConfig(
    key="weapon",
    display_name="Armas",
    color="#e67e22",
    symbol="\u2694",
    icon_filename="weapon.png",
    icon_size=(28, 28),
    reference_file="items.json",
)

ARMOR = CategoryConfig(
    key="armor",
    display_name="Armaduras",
    color="#8e44ad",
    symbol="\u26E8",
    icon_filename="armor.png",
    icon_size=(28, 28),
    reference_file="items.json",
)

SHIELD = CategoryConfig(
    key="shield",
    display_name="Escudos",
    color="#2980b9",
    symbol="\u26E8",
    icon_filename="shield.png",
    icon_size=(28, 28),
    reference_file="items.json",
)

TALISMAN = CategoryConfig(
    key="talisman",
    display_name="Talismãs",
    color="#1abc9c",
    symbol="\u25C8",
    icon_filename="talisman.png",
    icon_size=(28, 28),
    reference_file="items.json",
)

ASH_OF_WAR = CategoryConfig(
    key="ash_of_war",
    display_name="Cinzas de Guerra",
    color="#d35400",
    symbol="\u2726",
    icon_filename="ash_of_war.png",
    icon_size=(28, 28),
    reference_file="items.json",
)

SPELL = CategoryConfig(
    key="spell",
    display_name="Feitiços",
    color="#9b59b6",
    symbol="\u2721",
    icon_filename="spell.png",
    icon_size=(28, 28),
    reference_file="items.json",
)

SPIRIT_ASH = CategoryConfig(
    key="spirit_ash",
    display_name="Espíritos Invocáveis",
    color="#5dade2",
    symbol="\u2727",
    icon_filename="spirit_ash.png",
    icon_size=(28, 28),
    reference_file="items.json",
)

CONSUMABLE = CategoryConfig(
    key="consumable",
    display_name="Consumíveis",
    color="#27ae60",
    symbol="\u25CF",
    icon_filename="consumable.png",
    icon_size=(24, 24),
    reference_file="items.json",
)

MATERIAL = CategoryConfig(
    key="material",
    display_name="Materiais",
    color="#7f8c8d",
    symbol="\u25A0",
    icon_filename="material.png",
    icon_size=(24, 24),
    reference_file="items.json",
)

UPGRADE_MATERIAL = CategoryConfig(
    key="upgrade_material",
    display_name="Materiais de Melhoria",
    color="#f39c12",
    symbol="\u25B2",
    icon_filename="upgrade_material.png",
    icon_size=(24, 24),
    reference_file="items.json",
)

FLASK_UPGRADE = CategoryConfig(
    key="flask_upgrade",
    display_name="Melhorias de Frasco",
    color="#e74c3c",
    symbol="\u25C7",
    icon_filename="flask_upgrade.png",
    icon_size=(28, 28),
    reference_file="items.json",
)

KEY_ITEM = CategoryConfig(
    key="key_item",
    display_name="Itens Chave",
    color="#f1c40f",
    symbol="\u2606",
    icon_filename="key_item.png",
    icon_size=(28, 28),
    reference_file="items.json",
)

NPC = CategoryConfig(
    key="npc",
    display_name="NPCs",
    color="#3498db",
    symbol="\u263A",
    icon_filename="npc.png",
    icon_size=(32, 32),
    reference_file="npcs.json",
)

NPC_INVADER = CategoryConfig(
    key="npc_invader",
    display_name="Invasores NPC",
    color="#c0392b",
    symbol="\u2623",
    icon_filename="npc_invader.png",
    icon_size=(32, 32),
    reference_file="npcs.json",
)

WAYGATE = CategoryConfig(
    key="waygate",
    display_name="Portais",
    color="#2ecc71",
    symbol="\u29BF",
    icon_filename="waygate.png",
    icon_size=(32, 32),
    reference_file="waygates.json",
)

MAP_FRAGMENT = CategoryConfig(
    key="map_fragment",
    display_name="Fragmentos de Mapa",
    color="#ecf0f1",
    symbol="\u2637",
    icon_filename="map_fragment.png",
    icon_size=(28, 28),
    reference_file="items.json",
)

PLAYER = CategoryConfig(
    key="player",
    display_name="Jogador",
    color="#3498db",
    symbol="\u25C6",
    icon_filename="player.png",
    icon_size=(36, 36),
    reference_file="",
    filterable=False,
)

CATEGORIES: dict[str, CategoryConfig] = {
    "boss": BOSS,
    "grace": GRACE,
    "dungeon": DUNGEON,
    "weapon": WEAPON,
    "armor": ARMOR,
    "shield": SHIELD,
    "talisman": TALISMAN,
    "ash_of_war": ASH_OF_WAR,
    "spirit_ash": SPIRIT_ASH,
    "spell": SPELL,
    "consumable": CONSUMABLE,
    "material": MATERIAL,
    "upgrade_material": UPGRADE_MATERIAL,
    "flask_upgrade": FLASK_UPGRADE,
    "key_item": KEY_ITEM,
    "npc": NPC,
    "npc_invader": NPC_INVADER,
    "waygate": WAYGATE,
    "map_fragment": MAP_FRAGMENT,
    "player": PLAYER,
}

ITEM_CATEGORIES = {
    "weapon", "armor", "shield", "talisman", "ash_of_war",
    "spirit_ash", "spell", "consumable", "material", "upgrade_material",
    "flask_upgrade", "key_item", "map_fragment",
}

CATEGORY_GROUPS: dict[str, list[str]] = {
    "Locais": ["boss", "grace", "dungeon", "waygate"],
    "Personagens": ["npc", "npc_invader"],
    "Equipamento": ["weapon", "armor", "shield", "talisman", "ash_of_war", "spirit_ash"],
    "Magias e Consumíveis": ["spell", "consumable", "flask_upgrade"],
    "Materiais": ["material", "upgrade_material", "key_item", "map_fragment"],
}


# "A felicidade é o significado da vida, todo o objetivo e finalidade da existência humana." -- Aristóteles
