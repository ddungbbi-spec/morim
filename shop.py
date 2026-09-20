"""
shop.py
골드로 아이템/장비를 사고파는 상점 UI입니다.
각 상점의 이름과 독립 재고는 world.py에서 Shop으로 만들어 Location에 연결합니다.
판매가는 정가의 절반으로 고정되어 있습니다.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from models import Item, Equipment, Party
from input_utils import prompt_index

SELL_RATIO = 0.5


@dataclass(frozen=True)
class Shop:
    """한 상점의 이름과 독립적인 판매 재고."""

    name: str
    items: List[Item] = field(default_factory=list)
    equipment: List[Equipment] = field(default_factory=list)
    description: str = ""
    required_flag: Optional[str] = None
    unlock_description: str = ""
    discount_flag: Optional[str] = None
    discount_rate: float = 0.0
    discount_description: str = ""

    def is_available(self, flags: Optional[dict] = None) -> bool:
        return self.required_flag is None or bool((flags or {}).get(self.required_flag))

    def active_discount(self, flags: Optional[dict] = None) -> float:
        if self.discount_flag and (flags or {}).get(self.discount_flag):
            return max(0.0, min(0.9, self.discount_rate))
        return 0.0

    def price_for(self, product, flags: Optional[dict] = None) -> int:
        return max(1, int(product.price * (1.0 - self.active_discount(flags))))


def run_shop(
    party: Party,
    inventory: List[Item],
    equipment_inventory: List[Equipment],
    shop_items: List[Item],
    shop_equipment: List[Equipment],
    shop_name: str = "상점",
    discount_rate: float = 0.0,
    discount_description: str = "",
) -> None:
    """상점 메뉴 루프. 구매/판매 모두 여기서 처리합니다."""
    shop_items = shop_items or []
    shop_equipment = shop_equipment or []

    while True:
        print(f"\n=== {shop_name} ===")
        print(f"보유 골드: {party.gold} G")
        if discount_rate:
            label = discount_description or f"전 상품 {discount_rate:.0%} 할인"
            print(f"혜택: {label}")

        print("\n[구매 - 아이템]")
        for i, it in enumerate(shop_items, 1):
            price = _discounted_price(it.price, discount_rate)
            print(f"  {i}) {it.name}  {price} G  - {it.description}")

        item_count = len(shop_items)
        print("\n[구매 - 장비]")
        for i, eq in enumerate(shop_equipment, 1):
            price = _discounted_price(eq.price, discount_rate)
            print(f"  {item_count + i}) {eq.display_name}  {price} G  - {eq.display_description}")

        equip_count = len(shop_equipment)
        sell_option = item_count + equip_count + 1
        leave_option = sell_option + 1
        print(f"\n  {sell_option}) 아이템/장비 팔기")
        print(f"  {leave_option}) 나가기")

        num = prompt_index("> ", leave_option) + 1

        if num == leave_option:
            return

        if num == sell_option:
            _sell_menu(party, inventory, equipment_inventory)
            continue

        if 1 <= num <= item_count:
            item = shop_items[num - 1]
            _buy_item(party, inventory, item, _discounted_price(item.price, discount_rate))
            continue

        if item_count < num <= item_count + equip_count:
            equipment = shop_equipment[num - item_count - 1]
            _buy_equipment(
                party, equipment_inventory, equipment,
                _discounted_price(equipment.price, discount_rate),
            )
            continue

        print("잘못된 입력입니다.")


def _discounted_price(price: int, discount_rate: float) -> int:
    return max(1, int(price * (1.0 - max(0.0, min(0.9, discount_rate)))))


def _buy_item(party: Party, inventory: List[Item], item: Item, price: Optional[int] = None) -> None:
    price = item.price if price is None else price
    if party.gold < price:
        print("골드가 부족합니다.")
        return
    party.gold -= price
    inventory.append(item)
    print(f"{item.name}을(를) 구매했다! (남은 골드: {party.gold} G)")


def _buy_equipment(
    party: Party, equipment_inventory: List[Equipment], eq: Equipment,
    price: Optional[int] = None,
) -> None:
    price = eq.price if price is None else price
    if party.gold < price:
        print("골드가 부족합니다.")
        return
    party.gold -= price
    equipment_inventory.append(eq)
    print(f"{eq.display_name}을(를) 구매했다! (남은 골드: {party.gold} G)")


def _sell_menu(party: Party, inventory: List[Item], equipment_inventory: List[Equipment]) -> None:
    combined = [("item", it) for it in inventory if it.sellable] + [
        ("equipment", eq) for eq in equipment_inventory
    ]

    print(f"\n[판매] (정가의 {int(SELL_RATIO * 100)}%로 판매)")
    if not combined:
        print("판매할 아이템/장비가 없습니다.")
        return

    for i, (kind, obj) in enumerate(combined, 1):
        sell_price = int(obj.price * SELL_RATIO)
        display_name = obj.display_name if kind == "equipment" else obj.name
        print(f"  {i}) {display_name}  판매가 {sell_price} G")
    cancel_option = len(combined) + 1
    print(f"  {cancel_option}) 취소")

    idx = prompt_index("> ", cancel_option)

    if idx == cancel_option - 1:
        return
    if not (0 <= idx < len(combined)):
        print("잘못된 입력입니다.")
        return

    kind, obj = combined[idx]
    sell_price = int(obj.price * SELL_RATIO)
    party.gold += sell_price
    if kind == "item":
        inventory.remove(obj)
    else:
        equipment_inventory.remove(obj)
    display_name = obj.display_name if kind == "equipment" else obj.name
    print(f"{display_name}을(를) 판매해서 {sell_price} G를 받았다.")
