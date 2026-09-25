"""
world.py
실제 맵 콘텐츠(장소, 장소 간 연결, 인카운터 몬스터, 보스 배치)를 정의합니다.
새로운 지역/던전을 추가할 때는 이 파일에 Location을 추가하고
build_world()의 리스트에 넣어주면 됩니다.
"""

from map import FlagRequirement, Location, GameMap
from shop import Shop
import data
import dialogues


TOWER_MAX_FLOOR = 100
TOWER_BOSS_INTERVAL = 5
TOWER_SUMMIT_ID = "tower_summit"


def tower_floor_id(floor: int) -> str:
    """100층은 구버전 저장 호환을 위해 기존 정상 ID를 유지한다."""
    if floor < 1 or floor > TOWER_MAX_FLOOR:
        raise ValueError(f"도전의 탑 층수는 1~{TOWER_MAX_FLOOR}여야 한다.")
    return TOWER_SUMMIT_ID if floor == TOWER_MAX_FLOOR else f"tower_floor_{floor}"


TOWER_LOCATION_IDS = tuple(tower_floor_id(floor) for floor in range(1, TOWER_MAX_FLOOR + 1))


def secret_dungeon_unlocked(flags: dict) -> bool:
    """공허의 관측자 처치와 심연 변이 던전 완주를 모두 요구한다."""
    try:
        abyss_clears = int(flags.get("dungeon_clear_count", 0))
    except (TypeError, ValueError):
        abyss_clears = 0
    return bool(flags.get("void_observer_defeated")) and abyss_clears >= 1


MAP_REGIONS = [
    {
        "id": "village", "name": "시작 마을", "description": "원정대의 거점과 지원 시설",
        "locations": ("village", "elder_armory"),
    },
    {
        "id": "forest", "name": "어둠의 숲과 봉인", "description": "폐허와 봉인의 방으로 이어지는 메인 경로",
        "locations": ("forest_entrance", "deep_forest", "shadow_valley", "ruins",
                      "seal_gate", "final_chamber", "ending"),
    },
    {
        "id": "twilight", "name": "황혼 교역로", "description": "그림자 골짜기와 오방의 장터를 잇는 상단 길",
        "locations": (
            "twilight_road", "twilight_village", "twilight_caravan_square",
            "red_reed_field", "twilight_hunter_camp", "windscar_ravine", "duskfang_den",
        ),
    },
    {
        "id": "marsh", "name": "안개 습지", "description": "달빛 샘과 가라앉은 기록실",
        "locations": ("mist_marsh", "sunken_boardwalk", "forgotten_shrine", "moonlit_spring",
                      "mist_village", "mist_herb_garden", "drowned_archive", "echo_vault"),
    },
    {
        "id": "cave", "name": "고대 동굴", "description": "골렘의 보물방과 잠긴 비밀 금고",
        "locations": ("cave", "cave_treasure", "cave_vault"),
    },
    {
        "id": "mine", "name": "버려진 폐광", "description": "광부의 원혼과 탄광 드레이크의 둥지",
        "locations": ("iron_village", "iron_forge_yard", "mine_entrance", "mine_deep", "mine_depths"),
    },
    {
        "id": "tower", "name": "도전의 탑", "description": "100층과 20개의 보스 관문으로 이루어진 반복 도전 지역",
        "locations": TOWER_LOCATION_IDS,
    },
    {
        "id": "fallen_star", "name": "검은 별 낙하지", "description": "마왕 처치 후 열리는 별의 균열",
        "locations": ("star_observatory", "star_village", "star_beacon", "fallen_star_field", "star_rift"),
        "unlock_flag": "demon_lord_defeated", "unlock_description": "봉인된 마왕 처치 필요",
    },
    {
        "id": "astral", "name": "별빛 항로", "description": "검은 별의 근원과 공허의 왕좌",
        "locations": ("astral_passage", "shattered_sanctum", "void_throne"),
        "unlock_flag": "star_rift_closed", "unlock_description": "별의 균열 봉쇄 필요",
    },
    {
        "id": "abyss", "name": "심연 변이 던전", "description": "위험 변이가 무작위로 겹치는 4층 반복 원정",
        "locations": ("abyss_dungeon",),
        "unlock_flag": "demon_lord_defeated", "unlock_description": "봉인된 마왕 처치 필요",
    },
    {
        "id": "secret_grave", "name": "잊힌 검총", "description": "이름 없는 검객들의 혼이 잠든 시크릿 던전",
        "locations": ("forgotten_sword_grave", "grave_depths", "nameless_sanctum"),
        "unlock_check": secret_dungeon_unlocked,
        "unlock_description": "공허의 관측자 처치 및 심연 변이 던전 1회 완주 필요",
    },
]
LOCATION_REGION = {
    location_id: region["id"]
    for region in MAP_REGIONS
    for location_id in region["locations"]
}


def region_for_location(location_id: str) -> dict:
    region_id = LOCATION_REGION[location_id]
    return next(region for region in MAP_REGIONS if region["id"] == region_id)


def star_chapter_epilogue(flags: dict) -> list[str]:
    """균열을 닫은 뒤 첫 처치 때만 보여줄 마을의 후일담."""
    lines = ["검은 별이 사라지고 낙하지 위로 새벽빛이 번진다."]
    if flags.get("star_signal_reported"):
        lines.append("장로가 밝힌 등불을 따라 마을 사람들은 균열의 밤을 무사히 넘겼다.")
    else:
        lines.append("마을이 잠든 사이 파티는 조용히 균열을 막고 돌아갈 길을 찾았다.")
    lines.append("리제: \"봉인은 끝났지만, 저 별은 어디에서 왔을까?\"")
    return lines


def astral_chapter_epilogue(flags: dict) -> list[str]:
    """공허의 관측자를 처음 처치한 뒤 선택에 맞춰 보여줄 결말."""
    lines = ["공허의 왕좌가 무너지자 검은 별을 보내던 통로가 닫히기 시작한다."]
    if flags.get("astral_beacon_lit"):
        lines.append("푸른 봉화가 마지막까지 빛나며 파티를 안전하게 마을로 이끈다.")
    else:
        lines.append("파티는 무너지는 별길을 돌파해 스스로 귀환로를 열어낸다.")
    lines.append("리제: \"관측은 끝났어. 이제 우리 세계의 운명은 우리가 정해.\"")
    return lines


def tower_clear_count(flags: dict) -> int:
    try:
        return max(0, int(flags.get("tower_clear_count", 0)))
    except (TypeError, ValueError):
        return 0


def tower_challenge_tier(flags: dict) -> int:
    """다음 탑 도전 단계. 최초 도전은 1단계다."""
    return tower_clear_count(flags) + 1


def tower_floor_number(location_id: str) -> int | None:
    """탑 장소 ID를 실제 층수로 변환한다."""
    if location_id == TOWER_SUMMIT_ID:
        return TOWER_MAX_FLOOR
    prefix = "tower_floor_"
    if not location_id.startswith(prefix):
        return None
    try:
        floor = int(location_id[len(prefix):])
    except ValueError:
        return None
    return floor if 1 <= floor < TOWER_MAX_FLOOR else None


def is_tower_boss_floor(floor: int) -> bool:
    return 1 <= floor <= TOWER_MAX_FLOOR and floor % TOWER_BOSS_INTERVAL == 0


def create_scaled_tower_enemy(factory, floor: int):
    """일반층 적을 층수에 맞게 강화한다."""
    enemy = factory()
    step = max(0, (floor - 1) // 5)
    enemy.level += step
    enemy.max_hp = round(enemy.max_hp * (1 + 0.10 * step))
    enemy.hp = enemy.max_hp
    enemy.max_mp += 2 * step
    enemy.mp = enemy.max_mp
    enemy.attack += step
    enemy.defense += step // 2
    enemy.speed += min(step // 3, 6)
    enemy.exp_reward += 4 * step
    enemy.gold_reward += 3 * step
    return enemy


def tower_encounter_pool(floor: int):
    """20층 단위로 일반층 적 조합을 확장한다."""
    if floor <= 20:
        groups = ((data.create_goblin,), (data.create_wild_wolf,),
                  (data.create_orc_warrior, data.create_poison_spider))
    elif floor <= 40:
        groups = ((data.create_orc_warrior, data.create_goblin),
                  (data.create_forest_sprite, data.create_poison_spider),
                  (data.create_road_bandit, data.create_wild_wolf))
    elif floor <= 60:
        groups = ((data.create_skeleton_miner, data.create_ghost_miner),
                  (data.create_shadow_stalker, data.create_bat_swarm),
                  (data.create_canyon_hexer, data.create_road_bandit))
    elif floor <= 80:
        groups = ((data.create_marsh_hunter, data.create_will_o_wisp),
                  (data.create_cursed_wraith, data.create_shadow_stalker),
                  (data.create_star_remnant, data.create_canyon_hexer))
    else:
        groups = ((data.create_star_remnant, data.create_void_sentinel),
                  (data.create_cursed_wraith, data.create_void_sentinel),
                  (data.create_nebula_devourer, data.create_star_remnant))
    return [
        lambda group=group: [create_scaled_tower_enemy(factory, floor) for factory in group]
        for group in groups
    ]


def create_scaled_tower_boss(floor: int, flags: dict):
    """5층마다 등장하는 보스를 층수와 반복 도전 단계에 맞춰 강화한다."""
    if not is_tower_boss_floor(floor):
        raise ValueError("보스는 5층 단위로만 생성할 수 있다.")
    guardian = data.create_tower_guardian()
    floor_step = floor // TOWER_BOSS_INTERVAL - 1
    tier_step = tower_challenge_tier(flags) - 1
    guardian.name = (
        "탑의 수호자" if floor == TOWER_MAX_FLOOR
        else f"{floor}층 관문 수호자"
    )
    if tier_step:
        guardian.name += f" · {tier_step + 1}단계"
    guardian.level = 4 + floor // TOWER_BOSS_INTERVAL + tier_step
    guardian.max_hp = round(guardian.max_hp * (0.65 + 0.11 * floor_step) * (1 + 0.35 * tier_step))
    guardian.hp = guardian.max_hp
    guardian.max_mp += 3 * floor_step + 5 * tier_step
    guardian.mp = guardian.max_mp
    guardian.attack += floor_step + 3 * tier_step
    guardian.defense += floor_step // 2 + 2 * tier_step
    guardian.speed += min(floor_step // 3 + tier_step, 10)
    guardian.exp_reward += 12 * floor_step + 20 * tier_step
    guardian.gold_reward += 8 * floor_step + 12 * tier_step
    return guardian


def create_scaled_tower_guardian(flags: dict):
    """클리어 횟수에 따라 탑의 수호자를 점차 강화한다."""
    return create_scaled_tower_boss(TOWER_MAX_FLOOR, flags)


def grant_tower_boss_reward(flags: dict, floor: int, party, equipment_inventory: list):
    """보스층 보상을 회차당 한 번만 지급한다."""
    if not is_tower_boss_floor(floor):
        raise ValueError("보스층 보상은 5층 단위에서만 지급할 수 있다.")
    rewarded = flags.setdefault("tower_rewarded_floors", [])
    if floor in rewarded:
        return 0, None

    tier = tower_challenge_tier(flags)
    bonus_gold = 20 + floor * 2 + (tier - 1) * 15
    party.gold += bonus_gold
    equipment = None
    if floor % 10 == 0:
        party_level = max((member.level for member in party.members), default=1)
        reward_level = max(party_level, 2 + floor // 10 + tier - 1)
        equipment = data.generate_random_equipment(reward_level)
        equipment_inventory.append(equipment)

    rewarded.append(floor)
    flags["tower_highest_floor"] = max(int(flags.get("tower_highest_floor", 0)), floor)
    return bonus_gold, equipment


def reset_tower_challenge(game_map: GameMap, flags: dict) -> bool:
    """클리어한 탑 보스를 다음 단계로 초기화한다."""
    summit = game_map.locations[TOWER_SUMMIT_ID]
    if not summit.boss_defeated:
        return False
    # tower_clear_count 도입 전 저장 파일도 최초 클리어로 인정한다.
    if tower_clear_count(flags) == 0:
        flags["tower_clear_count"] = 1
    for floor in range(TOWER_BOSS_INTERVAL, TOWER_MAX_FLOOR + 1, TOWER_BOSS_INTERVAL):
        game_map.locations[tower_floor_id(floor)].boss_defeated = False
    flags["tower_rewarded_floors"] = []
    flags["tower_highest_floor"] = 0
    flags["tower_challenge_active"] = True
    return True


def complete_tower_challenge(flags: dict, party, equipment_inventory: list):
    """클리어 횟수를 기록하고 반복 도전 보상을 지급한다."""
    clear_count = tower_clear_count(flags) + 1
    flags["tower_clear_count"] = clear_count
    flags["tower_challenge_active"] = False
    if clear_count == 1:
        return clear_count, 0, None

    bonus_gold = 25 + 15 * clear_count
    party.gold += bonus_gold
    party_level = max((member.level for member in party.members), default=1)
    equipment = data.generate_random_equipment(max(party_level, clear_count + 2))
    equipment_inventory.append(equipment)
    return clear_count, bonus_gold, equipment


def build_world() -> GameMap:
    village = Location(
        loc_id="village",
        name="시작 마을",
        description="평화로운 마을. 저 너머로 어두운 숲이 보인다. 멀리 하늘을 찌를 듯한 탑도 보인다.",
        exits={
            "숲으로 향한다": "forest_entrance",
            "도전의 탑으로 향한다": "tower_floor_1",
            "장로의 비밀 무기고로 들어간다": "elder_armory",
            "북쪽 관측소로 향한다": "star_observatory",
            "별빛 항로로 향한다": "astral_passage",
            "심연 변이 던전에 도전한다": "abyss_dungeon",
            "검은 비석의 숨은 문을 연다": "forgotten_sword_grave",
        },
        flag_requirements={
            "북쪽 관측소로 향한다": FlagRequirement(
                flag="demon_lord_defeated",
                description="봉인된 마왕 처치 필요",
                failure_message="봉인의 방의 마왕을 처치한 뒤에만 북쪽의 신호를 조사할 수 있다.",
            ),
            "장로의 비밀 무기고로 들어간다": FlagRequirement(
                flag="promised_elder",
                description="장로의 신뢰 필요",
                failure_message="장로의 부탁을 맡은 이에게만 비밀 무기고가 열린다.",
            ),
            "별빛 항로로 향한다": FlagRequirement(
                flag="star_rift_closed",
                description="별의 균열 봉쇄 필요",
                failure_message="별의 균열을 먼저 닫아야 별빛 항로의 좌표를 고정할 수 있다.",
            ),
            "심연 변이 던전에 도전한다": FlagRequirement(
                flag="demon_lord_defeated",
                description="봉인된 마왕 처치 필요",
                failure_message="봉인된 마왕을 처치한 원정대만 심연의 입구를 견딜 수 있다.",
            ),
            "검은 비석의 숨은 문을 연다": FlagRequirement(
                flag="secret_dungeon_unlocked",
                predicate=secret_dungeon_unlocked,
                description="공허의 관측자 처치 및 심연 변이 던전 1회 완주 필요",
                failure_message=(
                    "검은 비석은 반응하지 않는다. 공허의 관측자를 쓰러뜨리고 "
                    "심연 변이 던전을 한 번 완주해야 한다."
                ),
            ),
        },
        dialogue=dialogues.village_intro_dialogue(),
        shops=[
            Shop(
                "여행자 잡화점",
                items=[data.POTION, data.ETHER, data.ANTIDOTE],
                description="회복약과 상태이상 치료제를 판매한다.",
            ),
            Shop(
                "바람칼 무기점",
                equipment=list(data.SHOP_WEAPONS),
                description="검·지팡이·단검·창·활·도끼·권갑, 일곱 계열의 무기를 취급한다.",
            ),
            Shop(
                "철벽 방어구점",
                equipment=[data.LEATHER_ARMOR, data.SWIFT_CHARM],
                description="방어구와 모험용 장신구를 판매한다.",
            ),
            Shop(
                "세아의 약초점",
                items=[data.ANTIDOTE, data.MOONLIGHT_TONIC],
                description="달빛 샘에서 구한 희귀 약초와 영약을 판매한다.",
                required_flag="found_herbalist",
                unlock_description="약초꾼 세아 구조 필요",
                discount_flag="escorted_herbalist",
                discount_rate=0.20,
                discount_description="호위 감사 전 상품 20% 할인",
            ),
        ],
        has_inn=True,
        is_village=True,
        quest_npc="길드 관리인 로아",
        services={"quest_board", "advancement", "blacksmith", "crafting"},
    )

    elder_armory = Location(
        loc_id="elder_armory",
        name="장로의 비밀 무기고",
        description="마을 수호자들이 사용하던 장비가 보관된 작은 지하실이다. 중앙 제단에 오래된 인장이 놓여 있다.",
        exits={"시작 마을로 돌아간다": "village"},
        loot_equipment=data.ELDER_GUARDIAN_SIGIL,
    )

    star_observatory = Location(
        loc_id="star_observatory", name="북쪽 관측소",
        description="마왕이 사라진 밤부터 오래된 관측 장치가 검은 별을 가리킨다.",
        exits={
            "낙하지로 내려간다": "fallen_star_field",
            "별바람 역참으로 향한다": "star_village",
            "마을로 돌아간다": "village",
        },
        dialogue=dialogues.star_observatory_dialogue(),
    )
    star_village = Location(
        loc_id="star_village", name="별바람 역참",
        description="낙하지를 오가는 관측자와 원정대가 별빛 천막 아래 모이는 국경의 역참이다.",
        exits={
            "북쪽 관측소로 돌아간다": "star_observatory",
            "유성 낙하지로 향한다": "fallen_star_field",
            "별바람 봉화대로 올라간다": "star_beacon",
        },
        shops=[
            Shop(
                "세라의 별빛 보급소",
                items=[data.ETHER, data.MOONLIGHT_TONIC, data.POTION],
                equipment=[data.OAK_STAFF, data.HUNTER_BOW, data.SWIFT_CHARM],
                description="별길 원정에 필요한 마력 회복품과 기동 장비를 판매한다.",
                discount_flag="star_beacon_aided", discount_rate=0.15,
                discount_description="봉화 수리 감사 전 상품 15% 할인",
            ),
        ],
        has_inn=True, is_village=True, quest_npc="별길 안내인 세라",
        services={"quest_board", "advancement", "blacksmith", "crafting"},
    )
    star_beacon = Location(
        loc_id="star_beacon", name="별바람 봉화대",
        description="낙하지와 별빛 항로의 귀환 신호를 맞추는 높은 봉화대다.",
        exits={"별바람 역참으로 내려간다": "star_village"},
        dialogue=dialogues.star_beacon_event_dialogue(),
        loot_item=data.ETHER,
    )
    fallen_star_field = Location(
        loc_id="fallen_star_field", name="유성 낙하지",
        description="검게 그을린 땅에 봉인의 문과 닮은 별의 문양이 새겨져 있다.",
        exits={"별의 균열로 들어간다": "star_rift", "관측소로 돌아간다": "star_observatory"},
        encounter_chance=0.45,
        encounter_pool=[lambda: [data.create_cursed_wraith()],
                        lambda: [data.create_shadow_stalker(), data.create_cursed_wraith()]],
        dialogue=dialogues.fallen_star_dialogue(),
    )
    star_rift = Location(
        loc_id="star_rift", name="별의 균열",
        description="별빛 아래 봉인의 찢어진 조각이 살아 있는 그림자로 뭉친다.",
        exits={"유성 낙하지로 돌아간다": "fallen_star_field"},
        boss=lambda: [data.create_star_remnant()],
        dialogue=dialogues.star_rift_dialogue(),
        loot_equipment=data.STARWARD_CHARM,
    )

    astral_passage = Location(
        loc_id="astral_passage", name="별빛 회랑",
        description="검은 별이 지나온 궤적이 길이 되어 공허 속으로 이어진다.",
        exits={
            "부서진 천문성소로 향한다": "shattered_sanctum",
            "별빛 문으로 마을에 돌아간다": "village",
        },
        encounter_chance=0.45,
        encounter_pool=[
            lambda: [data.create_nebula_devourer()],
            lambda: [data.create_nebula_devourer(), data.create_nebula_devourer()],
        ],
        dialogue=dialogues.astral_passage_dialogue(),
    )
    shattered_sanctum = Location(
        loc_id="shattered_sanctum", name="부서진 천문성소",
        description="금이 간 천문판과 꺼진 별들이 왕좌로 향하는 길을 가리킨다.",
        exits={
            "공허의 왕좌로 들어간다": "void_throne",
            "별빛 회랑으로 돌아간다": "astral_passage",
        },
        encounter_chance=0.60,
        encounter_pool=[
            lambda: [data.create_void_sentinel()],
            lambda: [data.create_void_sentinel(), data.create_nebula_devourer()],
        ],
        dialogue=dialogues.shattered_sanctum_dialogue(),
    )
    void_throne = Location(
        loc_id="void_throne", name="공허의 왕좌",
        description="검은 별의 신호를 내려보내던 존재가 별이 없는 왕좌에서 기다린다.",
        exits={"부서진 천문성소로 돌아간다": "shattered_sanctum"},
        boss=lambda: [data.create_void_observer()],
        dialogue=dialogues.void_throne_dialogue(),
        loot_equipment=data.CONSTELLATION_SPEAR,
    )

    forest_entrance = Location(
        loc_id="forest_entrance",
        name="숲 입구",
        description="나무 냄새가 짙게 풍긴다. 안쪽은 더 어두워 보인다. 한쪽에는 동굴 입구, 다른 한쪽에는 낡은 폐광 갱도 입구도 보인다.",
        exits={
            "더 깊은 숲으로 들어간다": "deep_forest",
            "동굴 쪽으로 향한다": "cave",
            "폐광 쪽으로 향한다": "mine_entrance",
            "마을로 돌아간다": "village",
        },
        encounter_chance=0.4,
        encounter_pool=[
            lambda: [data.create_slime()],
            lambda: [data.create_wild_wolf()],
            lambda: [data.create_bat_swarm()],
        ],
    )

    deep_forest = Location(
        loc_id="deep_forest",
        name="깊은 숲",
        description="빛이 거의 들지 않는다. 짐승의 울음소리가 들려온다.",
        exits={
            "그림자 골짜기로 향한다": "shadow_valley",
            "안개 습지로 들어간다": "mist_marsh",
            "숲 입구로 돌아간다": "forest_entrance",
        },
        encounter_chance=0.5,
        encounter_pool=[
            lambda: [data.create_slime()],
            lambda: [data.create_goblin()],
            lambda: [data.create_poison_spider()],
            lambda: [data.create_orc_warrior()],
            lambda: [data.create_forest_sprite()],
            lambda: [data.create_slime(), data.create_slime()],
            lambda: [data.create_goblin(), data.create_poison_spider()],
        ],
    )

    mist_marsh = Location(
        loc_id="mist_marsh",
        name="안개 습지",
        description="발목까지 차오른 물 위로 짙은 안개가 흐른다. 썩은 나무 사이에서 무언가 꿈틀거린다.",
        exits={
            "침수된 나무길로 향한다": "sunken_boardwalk",
            "깊은 숲으로 돌아간다": "deep_forest",
        },
        encounter_chance=0.5,
        encounter_pool=[
            lambda: [data.create_marsh_slime()],
            lambda: [data.create_marsh_hunter()],
            lambda: [data.create_poison_spider(), data.create_marsh_slime()],
        ],
    )

    sunken_boardwalk = Location(
        loc_id="sunken_boardwalk",
        name="침수된 나무길",
        description="반쯤 잠긴 널빤지 길 끝으로 오래된 석등이 희미하게 빛난다.",
        exits={
            "잊힌 사당으로 향한다": "forgotten_shrine",
            "안개 습지로 돌아간다": "mist_marsh",
        },
        encounter_chance=0.6,
        encounter_pool=[
            lambda: [data.create_will_o_wisp()],
            lambda: [data.create_marsh_hunter(), data.create_marsh_slime()],
            lambda: [data.create_will_o_wisp(), data.create_poison_spider()],
        ],
    )

    forgotten_shrine = Location(
        loc_id="forgotten_shrine",
        name="잊힌 사당",
        description="물에 잠긴 사당 중앙에서 안개의 여왕이 잠든 제단을 지키고 있다.",
        exits={
            "달빛 샘으로 들어간다": "moonlit_spring",
            "침수된 나무길로 돌아간다": "sunken_boardwalk",
        },
        boss=lambda: [data.create_mist_queen()],
        loot_equipment=data.MIST_CLOAK,
    )

    moonlit_spring = Location(
        loc_id="moonlit_spring",
        name="달빛 샘",
        description="안개가 걷힌 샘 위로 달빛이 쏟아진다. 고요한 물결이 긴 여정의 끝을 알린다.",
        exits={
            "잊힌 사당으로 돌아간다": "forgotten_shrine",
            "물안개 등불을 따라 안개나루로 간다": "mist_village",
            "세아가 알려준 수로로 들어간다": "drowned_archive",
        },
        flag_requirements={
            "세아가 알려준 수로로 들어간다": FlagRequirement(
                flag="found_herbalist",
                description="세아의 수로 안내 필요",
                failure_message="세아에게 수로의 위치를 듣기 전에는 들어갈 수 없다.",
            ),
        },
        dialogue=dialogues.moonlit_spring_dialogue(),
        loot_item=data.ETHER,
    )

    mist_village = Location(
        loc_id="mist_village", name="안개나루",
        description="달빛 샘의 물길 위에 세운 작은 수상 마을. 약초꾼과 뱃사공이 젖은 등불 곁을 지킨다.",
        exits={
            "달빛 샘으로 돌아간다": "moonlit_spring",
            "기록실 수로로 향한다": "drowned_archive",
            "달빛 약초밭으로 간다": "mist_herb_garden",
        },
        shops=[
            Shop(
                "나린의 수상 약방",
                items=[data.ANTIDOTE, data.POTION, data.ETHER, data.MOONLIGHT_TONIC],
                equipment=[data.SWIFT_CHARM],
                description="습지에서 채집한 약초와 가벼운 여행 장비를 판매한다.",
                discount_flag="mist_garden_aided", discount_rate=0.15,
                discount_description="약초밭 정화 감사 전 상품 15% 할인",
            ),
        ],
        has_inn=True, is_village=True, quest_npc="약초사 나린",
        services={"quest_board", "advancement", "blacksmith", "crafting"},
    )

    mist_herb_garden = Location(
        loc_id="mist_herb_garden", name="달빛 약초밭",
        description="안개나루의 물길 위에 조성된 약초밭. 달빛 영약의 재료가 자란다.",
        exits={"안개나루로 돌아간다": "mist_village"},
        dialogue=dialogues.mist_garden_event_dialogue(),
        loot_item=data.ANTIDOTE,
    )

    drowned_archive = Location(
        loc_id="drowned_archive",
        name="가라앉은 기록실",
        description="샘 아래 수로와 이어진 석실. 젖은 기록들이 봉인의 균열을 가리킨다.",
        exits={
            "메아리가 울리는 아래층으로 내려간다": "echo_vault",
            "달빛 샘으로 돌아간다": "moonlit_spring",
        },
        dialogue=dialogues.drowned_archive_dialogue(),
    )

    echo_vault = Location(
        loc_id="echo_vault",
        name="메아리의 석실",
        description="봉인의 틈에서 흘러나온 기억이 안개처럼 석실을 채우고 있다.",
        exits={"가라앉은 기록실로 돌아간다": "drowned_archive"},
        boss=lambda: [data.create_seal_echo()],
        dialogue=dialogues.echo_vault_dialogue(),
        loot_equipment=data.ARCHIVE_LANTERN,
    )

    shadow_valley = Location(
        loc_id="shadow_valley",
        name="그림자 골짜기",
        description="숲이 끝나고 나타나는 황량한 골짜기. 폐허로 가는 마지막 관문이다.",
        exits={
            "폐허로 향한다": "ruins",
            "황혼 교역로로 향한다": "twilight_road",
            "깊은 숲으로 돌아간다": "deep_forest",
        },
        encounter_chance=0.55,
        encounter_pool=[
            lambda: [data.create_shadow_stalker()],
            lambda: [data.create_cursed_wraith()],
            lambda: [data.create_orc_warrior()],
            lambda: [data.create_shadow_stalker(), data.create_cursed_wraith()],
        ],
        dialogue=dialogues.shadow_valley_dialogue(),
    )

    twilight_road = Location(
        loc_id="twilight_road", name="황혼 교역로",
        description="붉은 노을 아래 수레바퀴 자국이 황혼장터까지 이어진다.",
        exits={
            "황혼장터로 향한다": "twilight_village",
            "그림자 골짜기로 돌아간다": "shadow_valley",
        },
        encounter_chance=0.55,
        encounter_pool=[
            lambda: [data.create_road_bandit()],
            lambda: [data.create_dusk_hawk(), data.create_dusk_hawk()],
            lambda: [data.create_road_bandit(), data.create_dusk_hawk()],
        ],
    )

    twilight_village = Location(
        loc_id="twilight_village", name="황혼장터",
        description="다섯 지역의 상단과 무림인이 모이는 교역 마을. 해가 진 뒤에도 등불과 흥정 소리가 이어진다.",
        exits={
            "황혼 교역로로 나간다": "twilight_road",
            "황혼 상단 광장으로 간다": "twilight_caravan_square",
            "붉은 갈대 평원으로 사냥을 나간다": "red_reed_field",
        },
        shops=[
            Shop(
                "아라의 오방 보급소",
                items=[data.POTION, data.ETHER, data.ANTIDOTE, data.MOONLIGHT_TONIC],
                description="각지의 회복 물자와 희귀 영약을 한데 모아 판매한다.",
                discount_flag="twilight_trade_aided", discount_rate=0.15,
                discount_description="상단 수레 수리 감사 전 상품 15% 할인",
            ),
            Shop(
                "칠로 무기상",
                equipment=[data.IRON_DAGGER, data.HUNTER_BOW, data.GUARD_SPEAR, data.SWIFT_CHARM],
                description="먼 길에 적합한 빠른 무기와 기동 장비를 취급한다.",
                discount_flag="twilight_trade_aided", discount_rate=0.15,
                discount_description="상단 수레 수리 감사 전 상품 15% 할인",
            ),
        ],
        has_inn=True, is_village=True, quest_npc="상단주 아라",
        services={"quest_board", "advancement", "blacksmith", "crafting"},
    )

    twilight_caravan_square = Location(
        loc_id="twilight_caravan_square", name="황혼 상단 광장",
        description="오방에서 도착한 수레와 짐꾼이 모이는 황혼장터의 중심 광장이다.",
        exits={"황혼장터로 돌아간다": "twilight_village"},
        dialogue=dialogues.twilight_caravan_event_dialogue(),
        loot_item=data.POTION,
    )

    red_reed_field = Location(
        loc_id="red_reed_field", name="붉은 갈대 평원",
        description="노을빛 갈대가 사람 키보다 높게 자라 사냥감과 포식자의 움직임을 함께 감춘다.",
        exits={
            "황혼장터로 돌아간다": "twilight_village",
            "사냥꾼 전초막으로 향한다": "twilight_hunter_camp",
        },
        encounter_chance=0.62,
        encounter_pool=[
            lambda: [data.create_redmane_jackal()],
            lambda: [data.create_redmane_jackal(), data.create_redmane_jackal()],
            lambda: [data.create_road_bandit(), data.create_redmane_jackal()],
            lambda: [data.create_dusk_hawk(), data.create_redmane_jackal()],
        ],
    )

    twilight_hunter_camp = Location(
        loc_id="twilight_hunter_camp", name="갈대 사냥꾼 전초막",
        description="황혼장터의 사냥꾼들이 협곡 원정을 준비하는 작은 야영 거점이다.",
        exits={
            "붉은 갈대 평원으로 돌아간다": "red_reed_field",
            "바람흔적 협곡으로 진입한다": "windscar_ravine",
        },
        encounter_chance=0.35,
        encounter_pool=[
            lambda: [data.create_redmane_jackal()],
            lambda: [data.create_road_bandit(), data.create_dusk_hawk()],
        ],
        dialogue=dialogues.twilight_hunter_camp_dialogue(),
        loot_item=data.ANTIDOTE,
    )

    windscar_ravine = Location(
        loc_id="windscar_ravine", name="바람흔적 협곡",
        description="칼날 같은 바람과 도적술사의 매복이 원정대를 시험하는 상위 사냥터다.",
        exits={
            "사냥꾼 전초막으로 돌아간다": "twilight_hunter_camp",
            "황혼송곳니 소굴로 내려간다": "duskfang_den",
        },
        encounter_chance=0.68,
        encounter_pool=[
            lambda: [data.create_canyon_hexer()],
            lambda: [data.create_canyon_hexer(), data.create_road_bandit()],
            lambda: [data.create_canyon_hexer(), data.create_redmane_jackal()],
            lambda: [data.create_dusk_hawk(), data.create_dusk_hawk(), data.create_canyon_hexer()],
        ],
    )

    duskfang_den = Location(
        loc_id="duskfang_den", name="황혼송곳니 소굴",
        description="붉은 갈대와 짐승 뼈가 둥지를 이룬 협곡 최심부. 우두머리의 숨결이 바위를 울린다.",
        exits={"바람흔적 협곡으로 돌아간다": "windscar_ravine"},
        boss=lambda: [data.create_duskfang_alpha()],
        dialogue=dialogues.duskfang_den_dialogue(),
        loot_equipment=data.DUSKFANG_TALISMAN,
    )

    ruins = Location(
        loc_id="ruins",
        name="버려진 폐허",
        description="무너진 돌기둥 사이로 서늘한 기운이 감돈다.",
        exits={"바닥 아래로 내려간다": "seal_gate"},
        boss=lambda: [data.create_dark_knight()],
        dialogue=dialogues.ruins_approach_dialogue(),
    )

    seal_gate = Location(
        loc_id="seal_gate",
        name="봉인의 문",
        description="다크 나이트가 지키고 있던 자리, 바닥 아래로 이어지는 낡은 문이 드러나 있다.",
        exits={"문 안으로 들어간다": "final_chamber"},
        dialogue=dialogues.seal_gate_dialogue(),
    )

    final_chamber = Location(
        loc_id="final_chamber",
        name="봉인의 방",
        description="차갑고 거대한 공동. 봉인되어 있던 무언가가 서서히 깨어난다.",
        exits={"빛나는 문으로 들어간다": "ending"},
        boss=lambda: [data.create_sealed_demon_lord()],
        dialogue=dialogues.final_confrontation_dialogue(),
        loot_equipment=data.SEALBREAKER_BLADE,
    )
    abyss_dungeon = Location(
        loc_id="abyss_dungeon",
        name="심연 변이 던전",
        description="진입할 때마다 적 조합과 위험 변이가 달라진다. 층을 더 내려갈수록 누적 보상이 커진다.",
        exits={"누적 보상을 확정하고 마을로 귀환한다": "village"},
    )

    forgotten_sword_grave = Location(
        loc_id="forgotten_sword_grave",
        name="잊힌 검총 입구",
        description="검은 비석 아래 열린 계단 너머로 이름 없는 검들이 끝없이 꽂혀 있다.",
        exits={
            "검무덤 깊은 곳으로 내려간다": "grave_depths",
            "비석의 문으로 마을에 돌아간다": "village",
        },
        encounter_chance=0.55,
        encounter_pool=[
            lambda: [data.create_grave_sword()],
            lambda: [data.create_grave_sword(), data.create_grave_sword()],
        ],
    )

    grave_depths = Location(
        loc_id="grave_depths",
        name="검무덤 심층",
        description="부러진 검마다 주인을 잃은 맹세가 남아 있으며 가장 오래된 검이 안쪽 문을 가리킨다.",
        exits={
            "무명의 제단으로 들어간다": "nameless_sanctum",
            "검총 입구로 돌아간다": "forgotten_sword_grave",
        },
        encounter_chance=0.70,
        encounter_pool=[
            lambda: [data.create_oath_warden()],
            lambda: [data.create_grave_sword(), data.create_oath_warden()],
        ],
    )

    nameless_sanctum = Location(
        loc_id="nameless_sanctum",
        name="무명의 제단",
        description="어떤 기록에도 남지 못한 검객들의 이름이 하나의 검귀가 되어 제단을 지킨다.",
        exits={"검무덤 심층으로 돌아간다": "grave_depths"},
        boss=lambda: [data.create_nameless_swordmaster()],
        loot_equipment=data.NAMELESS_SOUL_CHARM,
    )

    cave = Location(
        loc_id="cave",
        name="동굴",
        description="축축하고 어두운 동굴이다. 안쪽에서 무언가 반짝이는 것이 보인다. 한쪽에는 굳게 닫힌 철문도 보인다.",
        exits={
            "동굴 깊은 곳으로": "cave_treasure",
            "굳게 닫힌 문 안으로": "cave_vault",
            "광부들의 지름길로 철광촌에 간다": "iron_village",
            "숲 입구로 돌아간다": "forest_entrance",
        },
        encounter_chance=0.5,
        encounter_pool=[
            lambda: [data.create_bat_swarm()],
            lambda: [data.create_orc_warrior()],
            lambda: [data.create_bat_swarm(), data.create_bat_swarm()],
        ],
        locked_exits={"굳게 닫힌 문 안으로": "녹슨 열쇠"},
    )

    cave_vault = Location(
        loc_id="cave_vault",
        name="동굴 비밀 금고",
        description="철문 안쪽, 오랫동안 아무도 손대지 않은 작은 금고가 놓여 있다.",
        exits={"동굴로 돌아간다": "cave"},
        loot_equipment=data.LUCKY_RING,
    )

    cave_treasure = Location(
        loc_id="cave_treasure",
        name="동굴 보물방",
        description="커다란 골렘이 낡은 보물상자를 지키고 서 있다.",
        exits={"동굴로 돌아간다": "cave"},
        boss=lambda: [data.create_cave_golem()],
        loot_equipment=data.MITHRIL_DAGGER,
    )

    ending = Location(
        loc_id="ending",
        name="빛나는 문 너머",
        description="눈부신 빛이 파티를 감싼다... (데모는 여기까지입니다)",
        is_ending=True,
        dialogue=dialogues.ending_dialogue(),
    )

    tower_locations = []
    for floor in range(1, TOWER_MAX_FLOOR + 1):
        loc_id = tower_floor_id(floor)
        boss_floor = is_tower_boss_floor(floor)
        exits = {}
        if floor < TOWER_MAX_FLOOR:
            exits[f"{floor + 1}층으로 올라간다"] = tower_floor_id(floor + 1)
        if floor == 1:
            exits["마을로 돌아간다"] = "village"
        else:
            exits[f"{floor - 1}층으로 내려간다"] = tower_floor_id(floor - 1)
        if floor == TOWER_MAX_FLOOR:
            exits = {
                "탑의 마법진으로 마을에 귀환한다": "village",
                f"{floor - 1}층으로 내려간다": tower_floor_id(floor - 1),
            }

        if floor == TOWER_MAX_FLOOR:
            description = "백 층의 시련 끝에 닿은 정상. 역대 수호자들의 기운이 마지막 관문에 모여 있다."
        elif boss_floor:
            description = f"도전의 탑 {floor}층. 계단을 봉쇄한 관문 수호자가 도전자를 기다린다."
        else:
            description = f"도전의 탑 {floor}층. 위층으로 갈수록 적의 기운과 탑의 압력이 강해진다."

        tower_locations.append(Location(
            loc_id=loc_id,
            name="도전의 탑 정상 · 100층" if floor == TOWER_MAX_FLOOR else f"도전의 탑 {floor}층",
            description=description,
            exits=exits,
            encounter_chance=0.0 if boss_floor else min(0.45 + floor * 0.004, 0.82),
            encounter_pool=[] if boss_floor else tower_encounter_pool(floor),
            boss=(lambda floor=floor: [create_scaled_tower_boss(floor, {})]) if boss_floor else None,
            dialogue=dialogues.tower_summit_dialogue() if floor == TOWER_MAX_FLOOR else None,
            loot_equipment=data.LEGENDARY_ARMOR if floor == TOWER_MAX_FLOOR else None,
        ))

    mine_entrance = Location(
        loc_id="mine_entrance",
        name="폐광 입구",
        description="오래전에 버려진 갱도. 곳곳에 녹슨 광차와 도구들이 나뒹굴고 있다.",
        exits={
            "더 깊이 들어간다": "mine_deep",
            "철광촌으로 향한다": "iron_village",
            "숲 입구로 돌아간다": "forest_entrance",
        },
        encounter_chance=0.5,
        encounter_pool=[
            lambda: [data.create_skeleton_miner()],
            lambda: [data.create_ghost_miner()],
        ],
    )

    iron_village = Location(
        loc_id="iron_village", name="철광촌",
        description="폐광과 고대 동굴 사이에 자리 잡은 광산 마을. 대장간의 불꽃이 밤새 꺼지지 않는다.",
        exits={
            "폐광 입구로 향한다": "mine_entrance",
            "광부들의 지름길로 동굴에 간다": "cave",
            "불꽃 대장간 마당으로 간다": "iron_forge_yard",
        },
        shops=[
            Shop(
                "브론의 광산 장비점",
                items=[data.POTION, data.ANTIDOTE],
                equipment=[data.GUARD_SPEAR, data.BATTLE_AXE, data.IRON_GAUNTLET, data.LEATHER_ARMOR],
                description="광산 작업과 근접 전투에 적합한 튼튼한 장비를 취급한다.",
                discount_flag="iron_forge_aided", discount_rate=0.15,
                discount_description="송풍 장치 수리 감사 전 상품 15% 할인",
            ),
        ],
        has_inn=True, is_village=True, quest_npc="광부 조합장 브론",
        services={"quest_board", "advancement", "blacksmith", "crafting"},
    )

    iron_forge_yard = Location(
        loc_id="iron_forge_yard", name="불꽃 대장간 마당",
        description="광석을 제련하는 거대한 용광로와 공동 송풍 장치가 있는 작업장이다.",
        exits={"철광촌으로 돌아간다": "iron_village"},
        dialogue=dialogues.iron_forge_event_dialogue(),
        loot_item=data.POTION,
    )

    mine_deep = Location(
        loc_id="mine_deep",
        name="폐광 깊은 곳",
        description="갱도가 점점 좁아진다. 벽 너머로 뜨거운 열기가 스며 나온다.",
        exits={
            "가장 깊은 곳으로": "mine_depths",
            "폐광 입구로 돌아간다": "mine_entrance",
        },
        encounter_chance=0.6,
        encounter_pool=[
            lambda: [data.create_skeleton_miner(), data.create_ghost_miner()],
            lambda: [data.create_skeleton_miner(), data.create_skeleton_miner()],
            lambda: [data.create_ghost_miner()],
        ],
        loot_item=data.RUSTY_KEY,
    )

    mine_depths = Location(
        loc_id="mine_depths",
        name="폐광 가장 깊은 곳",
        description="용암처럼 뜨거운 기운이 감도는 거대한 공동. 무언가 잠들어 있던 것이 눈을 뜬다.",
        exits={"폐광 깊은 곳으로 돌아간다": "mine_deep"},
        boss=lambda: [data.create_mine_drake()],
        dialogue=dialogues.mine_depths_dialogue(),
        loot_equipment=data.DRAKE_SCALE_ARMOR,
    )

    locations = [
        village, elder_armory, star_observatory, star_village, star_beacon, fallen_star_field, star_rift,
        astral_passage, shattered_sanctum, void_throne,
        forest_entrance, deep_forest,
        mist_marsh, sunken_boardwalk, forgotten_shrine, moonlit_spring, mist_village, mist_herb_garden,
        drowned_archive, echo_vault,
        shadow_valley, twilight_road, twilight_village, twilight_caravan_square,
        red_reed_field, twilight_hunter_camp, windscar_ravine, duskfang_den,
        ruins, seal_gate, final_chamber, abyss_dungeon,
        forgotten_sword_grave, grave_depths, nameless_sanctum,
        cave, cave_treasure, cave_vault, ending,
        *tower_locations,
        iron_village, iron_forge_yard, mine_entrance, mine_deep, mine_depths,
    ]
    for location in locations:
        if (
            location.id != "village"
            and not location.is_ending
            and "village" not in location.exits.values()
        ):
            location.exits["마을로 바로 이동한다"] = "village"

    return GameMap(locations=locations, start_id="village")
