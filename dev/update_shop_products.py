"""Generate selectable product options from the Agent's shared shop catalog."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_PRODUCTS = json.loads((ROOT / "agent/shop_custom_products.json").read_text(encoding="utf-8"))


def settings_override(node: str, params: dict) -> dict:
    # MaaFramework replaces custom_action_param as a whole, rather than merging
    # its fields. Each independently selected GUI field needs its own node.
    return {node + "_" + key: {"custom_action_param": {key: value}}
            for key, value in params.items()}


def product_option(product: dict, node: str, *, custom: bool = False) -> dict:
    key = product["key"]
    option = {"type": "input", "label": product["label"], "inputs": [
        {"name": "count", "label": "购买次数（0为跳过）", "default": "0", "pipeline_type": "int",
         "verify": "^(?:[0-9]|[1-9][0-9]|100)$", "pattern_msg": "请输入0到100的整数"}],
        "pipeline_override": settings_override(node, {key + "_count": "{count}"})}
    if custom:
        option["inputs"].insert(0, {"name": "name", "label": "商品名称（与游戏显示一致）", "default": "", "verify": "^.{1,40}$", "pattern_msg": "请检查输入格式"})
        option["pipeline_override"].update(settings_override(node, {key + "_name": "{name}"}))
    return option


def currency_option(key: str, currency: str, node: str) -> dict:
    labels = {"gold": "金币", "diamond": "钻石（不含付费钻石）",
              "hero_crystal": "英雄水晶（暂未适配）", "star_piece": "星片"}
    return {"type": "select", "label": "购买货币", "default_case": currency, "cases": [
        {"name": value, "label": label,
         "pipeline_override": settings_override(node, {key + "_currency": value})}
        for value, label in labels.items()]}


def update(interface: dict, products: list[dict]) -> None:
    options = interface["option"]
    groups = {category: [] for category in ("资源", "钻石商店", "英雄成长", "装备", "活动商店")}
    for product in products + CUSTOM_PRODUCTS:
        key, category = product["key"], product["category"]
        option = "ShopItem_" + key
        node = "GT_EventShop_Run" if category == "活动商店" else "GT_Shop_PurchaseRun"
        custom = not product["name"]
        options[option] = product_option(product, node, custom=custom)
        options[option + "Currency"] = currency_option(key, product["currency"], node)
        case = {"name": key, "label": "自定义商品（备用）" if custom else product["label"], "option": [option, option + "Currency"]}
        groups[category].append(case)
    groups["资源"].append({"name": "free_coins", "label": "金币（每日免费）",
                          "pipeline_override": settings_override("GT_Shop_PurchaseRun", {"free_coins": True})})
    specs = [("资源", "ShopResourceProducts", "ShopResources", ["free_coins"]),
             ("钻石商店", "ShopDiamondProducts", "ShopDiamonds", []),
             ("英雄成长", "ShopGrowthProducts", "ShopGrowth", ["legendary"]),
             ("装备", "ShopEquipmentProducts", "ShopEquipment", ["hammer"]),
             ("活动商店", "EventShopProducts", None, [])]
    for category, name, parent, defaults in specs:
        options[name] = {"type": "checkbox", "label": "勾选要购买的商品", "default_case": defaults, "cases": groups[category]}
        if parent:
            enabled = next(case for case in options[parent]["cases"] if case["name"] == "Yes")
            enabled["option"] = [name]
    options["ShopResources"]["default_case"] = "Yes"
    # The free coin checkbox now lives alongside stamina in the resource list.
    for task in interface["task"]:
        if task["entry"] == "GT_ShopPurchase":
            task["option"] = [name for name in task["option"] if name != "ShopFree"]
    options.pop("ShopFree", None)
    # Drop stale generated entries from the abandoned bulk catalog.
    valid_keys = {product["key"] for product in products + CUSTOM_PRODUCTS}
    for name in list(options):
        if name.startswith("ShopItem_"):
            key = name[len("ShopItem_"):]
            if key.endswith("Currency"): key = key[:-len("Currency")]
            if key not in valid_keys: del options[name]
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
    settings = {}
    for product in products + CUSTOM_PRODUCTS:
        node = "GT_EventShop_Run" if product["category"] == "活动商店" else "GT_Shop_PurchaseRun"
        defaults = {product["key"] + "_count": 0, product["key"] + "_currency": product["currency"]}
        if not product["name"]: defaults[product["key"] + "_name"] = ""
        for target, override in settings_override(node, defaults).items():
            settings[target] = {"action": "Custom", "custom_action": "GT_ShopPurchase", **override}
    for node in ("GT_Shop_PurchaseRun", "GT_EventShop_Run"):
        settings[node + "_free_coins"] = {"action": "Custom", "custom_action": "GT_ShopPurchase",
                                         "custom_action_param": {"free_coins": False}}
    (ROOT / "resource/pipeline/shop_settings.json").write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
