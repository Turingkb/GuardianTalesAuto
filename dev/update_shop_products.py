"""Generate selectable product options from the Agent's shared shop catalog."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def product_option(product: dict, node: str) -> dict:
    key = product["key"]
    return {"type": "input", "label": product["label"], "inputs": [
        {"name": "count", "label": "购买次数（0为跳过）", "default": "0", "pipeline_type": "int",
         "verify": "^(?:[0-9]|[1-9][0-9]|100)$"},
        {"name": "budget", "label": "本次总预算（钻石，0为跳过）", "default": "0", "pipeline_type": "int",
         "verify": "^(?:0|[1-9][0-9]{0,7}|100000000)$"}],
        "pipeline_override": {node: {"custom_action_param": {key + "_count": "{count}", key + "_budget": "{budget}"}}}}


def update(interface: dict, products: list[dict]) -> None:
    options = interface["option"]
    diamond, event = [], []
    for product in products:
        key, category = product["key"], product["category"]
        if category not in ("钻石商店", "活动商店"):
            continue
        option = "ShopItem_" + key
        node = "GT_EventShop_Run" if category == "活动商店" else "GT_Shop_PurchaseRun"
        options[option] = product_option(product, node)
        case = {"name": key, "label": product["label"], "option": [option]}
        (event if category == "活动商店" else diamond).append(case)
    diamond.append({"name": "diamond_other", "label": "未收录商品（高级）", "option": ["ShopItem_diamond_other"]})
    event.append({"name": "event", "label": "未收录商品（高级）", "option": ["ShopItem_event", "ShopItem_eventCurrency"]})
    options["ShopDiamondProducts"] = {"type": "checkbox", "label": "勾选要购买的商品", "default_case": [], "cases": diamond}
    options["EventShopProducts"] = {"type": "checkbox", "label": "勾选活动商品", "default_case": [], "cases": event}
    options["ShopItem_diamond_other"]["label"] = "未收录的钻石商品"
    options["ShopItem_event"]["label"] = "未收录的活动商品"
    options["ShopItem_event"]["description"] = "仅未收录商品需要填写游戏中的完整名称；常见商品直接勾选即可。"
    for name in ("ShopItem_event", "ShopItem_eventCurrency"):
        option = options[name]
        targets = [option] + option.get("cases", [])
        for target in targets:
            override = target.get("pipeline_override", {})
            if "GT_Shop_PurchaseRun" in override:
                override["GT_EventShop_Run"] = override.pop("GT_Shop_PurchaseRun")


def main():
    path = ROOT / "interface.json"
    interface = json.loads(path.read_text(encoding="utf-8"))
    products = json.loads((ROOT / "agent/shop_products.json").read_text(encoding="utf-8"))
    update(interface, products)
    path.write_text(json.dumps(interface, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
