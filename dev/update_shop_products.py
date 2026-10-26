"""Generate selectable product options from the Agent's shared shop catalog."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def product_option(product: dict, node: str) -> dict:
    key = product["key"]
    return {"type": "input", "label": product["label"], "inputs": [
        {"name": "count", "label": "购买次数（0为跳过）", "default": "0", "pipeline_type": "int",
         "verify": "^(?:[0-9]|[1-9][0-9]|100)$"}],
        "pipeline_override": {node: {"custom_action_param": {key + "_count": "{count}"}}}}


def currency_option(key: str, currency: str, node: str) -> dict:
    labels = {"gold": "金币", "diamond": "钻石（不含付费钻石）", "hero_crystal": "英雄水晶"}
    return {"type": "select", "label": "购买货币", "default_case": currency, "cases": [
        {"name": value, "label": label,
         "pipeline_override": {node: {"custom_action_param": {key + "_currency": value}}}}
        for value, label in labels.items()]}


def update(interface: dict, products: list[dict]) -> None:
    options = interface["option"]
    diamond, event = [], []
    for product in products:
        key, category = product["key"], product["category"]
        option = "ShopItem_" + key
        node = "GT_EventShop_Run" if category == "活动商店" else "GT_Shop_PurchaseRun"
        options[option] = product_option(product, node)
        options[option + "Currency"] = currency_option(key, product["currency"], node)
        case = {"name": key, "label": product["label"], "option": [option, option + "Currency"]}
        if category == "活动商店": event.append(case)
        elif category == "钻石商店": diamond.append(case)
    options["ShopItem_diamond_otherCurrency"] = currency_option("diamond_other", "diamond", "GT_Shop_PurchaseRun")
    options["ShopItem_eventCurrency"] = currency_option("event", "diamond", "GT_EventShop_Run")
    diamond.append({"name": "diamond_other", "label": "未收录商品（高级）", "option": ["ShopItem_diamond_other", "ShopItem_diamond_otherCurrency"]})
    event.append({"name": "event", "label": "未收录商品（高级）", "option": ["ShopItem_event", "ShopItem_eventCurrency"]})
    options["ShopDiamondProducts"] = {"type": "checkbox", "label": "勾选要购买的商品", "default_case": [], "cases": diamond}
    options["EventShopProducts"] = {"type": "checkbox", "label": "勾选活动商品", "default_case": [], "cases": event}
    options["ShopItem_diamond_other"]["label"] = "未收录的钻石商品"
    options["ShopItem_event"]["label"] = "未收录的活动商品"
    options["ShopItem_event"]["description"] = "仅未收录商品需要填写游戏中的完整名称；常见商品直接勾选即可。"
    for name, option in options.items():
        if name.startswith("ShopItem_"):
            if "inputs" in option:
                option["inputs"] = [item for item in option["inputs"] if item["name"] != "budget"]
            for override in option.get("pipeline_override", {}).values():
                params = override.get("custom_action_param", {})
                for key in list(params):
                    if key.endswith("_budget"): del params[key]
        # Existing resource/growth/equipment groups also expose a currency selector.
        for source in [option] + option.get("cases", []):
            children = source.get("option", [])
            for child in list(children):
                currency = child + "Currency"
                if child.startswith("ShopItem_") and currency in options and currency not in children:
                    children.append(currency)
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
