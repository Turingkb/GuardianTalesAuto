"""Shop plans with exact item, currency, quantity and balance checks."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
import time

from native import Screen

PRODUCTS = json.loads(Path(__file__).with_name("shop_products.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Product:
    key: str
    category: str
    name: str
    currency: str
    count: int
    budget: int


def number(text: str) -> int:
    value = text.strip().replace(",", "").replace("，", "")
    if not re.fullmatch(r"\d+", value):
        raise ValueError(f"Cannot read shop number: {text!r}")
    return int(value)


def plans(params: dict, *, event_only: bool | None = None) -> list[Product]:
    result = []
    definitions = PRODUCTS + [{"key": "diamond_other", "category": "钻石商店", "name": "", "currency": "diamond"},
                              {"key": "event", "category": "活动商店", "name": "", "currency": "diamond"}]
    for definition in definitions:
        key, category, name, currency = (definition[field] for field in ("key", "category", "name", "currency"))
        if event_only is not None and (category == "活动商店") != event_only:
            continue
        count, budget = params.get(key + "_count", 0), params.get(key + "_budget", 0)
        if type(count) is not int or type(budget) is not int or not 0 <= count <= 100 or not 0 <= budget <= 100000000:
            raise ValueError(f"Invalid quantity/budget for {key}")
        if not count or not budget:
            continue
        # Preset names cannot be replaced by stale custom input from the GUI.
        name = params.get(key + "_name", name).strip() if key in ("event", "diamond_other") else name
        currency = params.get(key + "_currency", currency)
        if not name or len(name) > 40 or re.search("召唤|抽卡|付费|人民币|礼包", name):
            raise ValueError(f"Unsupported product name: {name!r}")
        if currency not in ("gold", "diamond", "hero_crystal"):
            raise ValueError("Unsupported shop currency")
        result.append(Product(key, category, name, currency, count, budget))
    return result


def center(item: dict) -> tuple[int, int]:
    x, y, w, h = item["box"]
    return int(x + w / 2), int(y + h / 2)


def item_name(text: str) -> str:
    return re.sub(r"\s+", "", text).replace("（", "(").replace("）", ")")


def require_shop(screen: Screen):
    # Opening the shop can download resources; a fixed post-delay is too short.
    deadline = time.monotonic() + 30
    while True:
        if screen.recognize("TemplateMatch", {"template": "shop_title.png", "roi": [20, 5, 160, 65], "threshold": 0.9}):
            return
        if time.monotonic() >= deadline:
            raise RuntimeError("Shop page did not become visible within thirty seconds")
        screen.pause(0.5)
        screen.capture()


def select_category(screen: Screen, name: str) -> bool:
    screen.capture()
    require_shop(screen)
    # The sidebar remembers its scroll position; never select a fixed row number.
    screen.act("Swipe", {"begin": [220, 225], "end": [220, 650], "duration": 350})
    screen.pause(0.4)
    for _ in range(4):
        screen.capture()
        matches = screen.ocr([20, 126, 218, 570], "^" + re.escape(name) + "$")
        if matches:
            screen.tap(*center(matches[0]), 0.6)
            screen.capture()
            require_shop(screen)
            return True
        screen.act("Swipe", {"begin": [220, 632], "end": [220, 265], "duration": 350})
        screen.pause(0.4)
    screen.log("shop_skipped", category=name, reason="category_not_available")
    return False


def find_product(screen: Screen, name: str, free: bool = False) -> tuple[int, int] | None:
    for _ in range(3):
        screen.act("Swipe", {"begin": [1230, 230], "end": [1230, 660], "duration": 300})
    screen.pause(0.4)
    previous = None
    for _ in range(12):
        screen.capture()
        require_shop(screen)
        items = screen.ocr([278, 190, 980, 504])
        for item in items:
            text = item_name(item["text"])
            if free:
                if re.fullmatch(r"每日免费商品[!！]?", text):
                    x, y = center(item)
                    column = min((394, 642, 890, 1138), key=lambda value: abs(x - value))
                    return column, max(195, y - 90)
                continue
            aliases = (name, "传说觉醒石") if name == "传说中的觉醒石" else (name,)
            if text in tuple(item_name(alias) for alias in aliases):
                x, y = center(item)
                # The price and sold-out label belong to the same card column.
                column = min((394, 642, 890, 1138), key=lambda value: abs(x - value))
                if screen.has([column - 110, y + 20, 220, min(100, 720 - y - 20)], "售罄"):
                    screen.log("shop_skipped", item=name, reason="sold_out")
                    return None
                return x, y
        fingerprint = tuple((item["text"], tuple(item["box"])) for item in items)
        if fingerprint == previous:
            break
        previous = fingerprint
        screen.act("Swipe", {"begin": [1230, 642], "end": [1230, 278], "duration": 350})
        screen.pause(0.5)
    screen.log("shop_skipped", item=name, reason="product_not_available")
    return None


def cancel(screen: Screen):
    buttons = screen.ocr([390, 540, 250, 110], "^取消$")
    if not buttons:
        raise RuntimeError("Purchase dialog has no recognized cancel button")
    screen.tap(*center(buttons[0]), 0.4)


def inspect_purchase(screen: Screen, product: Product) -> tuple[int, tuple[int, int]]:
    if not screen.has([550, 65, 180, 85], "^购买$"):
        raise RuntimeError("Purchase dialog is missing")
    aliases = (product.name, "传说觉醒石") if product.key == "legendary" else (product.name,)
    # Match the title line exactly, excluding the material-description subtitle.
    lines = [item_name(item["text"]) for item in screen.ocr([435, 270, 410, 80])]
    if not any(item_name(alias) in lines for alias in aliases):
        raise RuntimeError(f"Unexpected product: {lines!r}")
    buttons = screen.ocr([390, 540, 250, 110], "^取消$")
    if len(buttons) != 1:
        raise RuntimeError("Ambiguous purchase dialog layout")
    _, y = center(buttons[0])
    button_roi = [660, y - 24, 200, 48]
    label = screen.text(button_roi)
    if re.search(r"付费|人民币|[¥￥]", label):
        raise RuntimeError("Paid-gem and cash purchases are unsupported")
    if product.currency == "free":
        if not screen.has(button_roi, "^免费$") or not screen.has([590, 249, 115, 43], "^2[,，.]?000$"):
            raise RuntimeError("Free coins must be exactly 2000 with a free confirmation")
        return 0, (752, y)
    templates = [f"shop_currency_{product.currency}.png"]
    if product.currency == "diamond":
        templates.append("shop_currency_diamond_compact.png")
    if not any(screen.recognize("TemplateMatch", {"template": template, "roi": [686, y - 24, 72, 48],
                                                   "threshold": 0.94}) for template in templates):
        raise RuntimeError("Purchase currency does not match configured currency")
    price = number(screen.text([746, y - 21, 100, 42]))
    if not price:
        raise RuntimeError("Paid item has an unexpected zero price")
    slider = screen.recognize("TemplateMatch", {"template": "shop_quantity_minus.png",
                                               "roi": [350, 475, 95, 90], "threshold": 0.94})
    if slider and number(screen.text([375, 460, 548, 39])) != 1:
        raise RuntimeError("Purchase quantity must remain one per transaction")
    return price, (752, y)


def balance(screen: Screen, currency: str) -> int:
    rois = {"gold": [745, 16, 112, 38], "diamond": [940, 15, 90, 42], "hero_crystal": [1150, 75, 70, 35]}
    return number(screen.text(rois[currency]))


def settle(screen: Screen):
    for _ in range(12):
        screen.capture()
        if screen.has([500, 245, 280, 75], "奖励|已购买|已接受"):
            if screen.has([420, 620, 450, 90], "点击|关闭"):
                screen.tap(640, 680, 0.5)
                continue
        if screen.recognize("TemplateMatch", {"template": "shop_title.png", "roi": [20, 5, 160, 65], "threshold": 0.9}) and not screen.has([550, 65, 180, 85], "^购买$"):
            return
        screen.pause(0.5)
    raise RuntimeError("Shop transaction result is ambiguous; no retry was submitted")


def purchase(screen: Screen, product: Product, preview: bool) -> None:
    spent = 0
    for _ in range(product.count):
        location = find_product(screen, product.name, product.currency == "free")
        if location is None:
            return
        before = balance(screen, product.currency) if product.currency != "free" else None
        screen.tap(*location, 0.5)
        screen.capture()
        try:
            price, target = inspect_purchase(screen, product)
            if price > product.budget - spent or (before is not None and price > before):
                screen.log("shop_skipped", item=product.name, reason="budget_or_balance", price=price)
                cancel(screen)
                return
            screen.save("shop-before-confirm")
            screen.log("shop_preview" if preview else "shop_confirm", item=product.name,
                       currency=product.currency, price=price, spent=spent, budget=product.budget)
            if preview:
                cancel(screen)
                return
        except (RuntimeError, ValueError):
            cancel(screen)
            raise
        screen.tap(*target, 0.7)
        settle(screen)
        if before is not None and balance(screen, product.currency) != before - price:
            raise RuntimeError("Balance change does not match the purchase; stopping")
        spent += price
        screen.log("shop_verified", item=product.name, spent=spent)


def shop_purchase(screen: Screen, params: dict, *, event_only: bool = False) -> bool:
    products = plans(params, event_only=event_only)
    preview = params.get("preview_only", False)
    free = params.get("free_coins", not event_only)
    if type(preview) is not bool or type(free) is not bool:
        raise ValueError("Shop switches must be boolean")
    if free and not event_only:
        products.insert(0, Product("free", "资源", "金币", "free", 1, 0))
    for product in products:
        if select_category(screen, product.category):
            purchase(screen, product, preview)
    return True
