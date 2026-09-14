"""
world.py
실제 맵 콘텐츠(장소, 장소 간 연결, 인카운터 몬스터, 보스 배치)를 정의합니다.
새로운 지역/던전을 추가할 때는 이 파일에 Location을 추가하고
build_world()의 리스트에 넣어주면 됩니다.
"""

from map import Location, GameMap
import data
import dialogues


def build_world() -> GameMap:
    village = Location(
        loc_id="village",
        name="시작 마을",
        description="평화로운 마을. 저 너머로 어두운 숲이 보인다. 멀리 하늘을 찌를 듯한 탑도 보인다.",
        exits={
            "숲으로 향한다": "forest_entrance",
            "도전의 탑으로 향한다": "tower_floor_1",
        },
        dialogue=dialogues.village_intro_dialogue(),
        shop_items=[data.POTION, data.ETHER, data.ANTIDOTE],
        shop_equipment=[data.IRON_SWORD, data.OAK_STAFF, data.LEATHER_ARMOR, data.SWIFT_CHARM],
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

    shadow_valley = Location(
        loc_id="shadow_valley",
        name="그림자 골짜기",
        description="숲이 끝나고 나타나는 황량한 골짜기. 폐허로 가는 마지막 관문이다.",
        exits={
            "폐허로 향한다": "ruins",
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

    cave = Location(
        loc_id="cave",
        name="동굴",
        description="축축하고 어두운 동굴이다. 안쪽에서 무언가 반짝이는 것이 보인다. 한쪽에는 굳게 닫힌 철문도 보인다.",
        exits={
            "동굴 깊은 곳으로": "cave_treasure",
            "굳게 닫힌 문 안으로": "cave_vault",
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

    tower_floor_1 = Location(
        loc_id="tower_floor_1",
        name="도전의 탑 1층",
        description="차가운 돌계단이 위로 이어져 있다. 여기서부터가 시작이다.",
        exits={
            "2층으로 올라간다": "tower_floor_2",
            "마을로 돌아간다": "village",
        },
        encounter_chance=0.5,
        encounter_pool=[
            lambda: [data.create_goblin()],
            lambda: [data.create_wild_wolf()],
            lambda: [data.create_orc_warrior()],
        ],
    )

    tower_floor_2 = Location(
        loc_id="tower_floor_2",
        name="도전의 탑 2층",
        description="위로 올라갈수록 공기가 무거워진다. 이곳의 몬스터들은 한층 더 사납다.",
        exits={
            "3층으로 올라간다": "tower_floor_3",
            "1층으로 내려간다": "tower_floor_1",
        },
        encounter_chance=0.6,
        encounter_pool=[
            lambda: [data.create_orc_warrior()],
            lambda: [data.create_forest_sprite()],
            lambda: [data.create_goblin(), data.create_poison_spider()],
        ],
    )

    tower_floor_3 = Location(
        loc_id="tower_floor_3",
        name="도전의 탑 3층",
        description="탑의 정상이 가까워졌다. 강력한 기운이 위층에서부터 느껴진다.",
        exits={
            "정상으로 올라간다": "tower_summit",
            "2층으로 내려간다": "tower_floor_2",
        },
        encounter_chance=0.7,
        encounter_pool=[
            lambda: [data.create_orc_warrior(), data.create_goblin()],
            lambda: [data.create_poison_spider(), data.create_bat_swarm()],
            lambda: [data.create_orc_warrior(), data.create_orc_warrior()],
        ],
    )

    tower_summit = Location(
        loc_id="tower_summit",
        name="도전의 탑 정상",
        description="탑의 가장 높은 곳. 구름 위로 솟아 있어 사방이 훤히 내려다보인다.",
        exits={"3층으로 내려간다": "tower_floor_3"},
        boss=lambda: [data.create_tower_guardian()],
        dialogue=dialogues.tower_summit_dialogue(),
        loot_equipment=data.LEGENDARY_ARMOR,
    )

    mine_entrance = Location(
        loc_id="mine_entrance",
        name="폐광 입구",
        description="오래전에 버려진 갱도. 곳곳에 녹슨 광차와 도구들이 나뒹굴고 있다.",
        exits={
            "더 깊이 들어간다": "mine_deep",
            "숲 입구로 돌아간다": "forest_entrance",
        },
        encounter_chance=0.5,
        encounter_pool=[
            lambda: [data.create_skeleton_miner()],
            lambda: [data.create_ghost_miner()],
        ],
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

    return GameMap(
        locations=[
            village, forest_entrance, deep_forest, shadow_valley, ruins, seal_gate, final_chamber,
            cave, cave_treasure, cave_vault, ending,
            tower_floor_1, tower_floor_2, tower_floor_3, tower_summit,
            mine_entrance, mine_deep, mine_depths,
        ],
        start_id="village",
    )
