"""Validated game decisions that require reading counters before acting."""

import ctypes as ct
from functools import partial
import re
import time

from native import Screen
from shop import shop_purchase
from pass_rewards import pass_rewards


def integer_text(text: str) -> int:
    cleaned = text.strip().replace(",", "").replace("，", "")
    if not re.fullmatch(r"\d+", cleaned):
        raise ValueError(f"Ambiguous numeric value: {text!r}")
    return int(cleaned)


def finish_sweep(screen: Screen, expected_count: int, label: str = "sweep") -> None:
    deadline = time.monotonic() + max(90, expected_count * 3 + 30)
    while time.monotonic() < deadline:
        screen.capture()
        if screen.has([585, 84, 112, 39], "^扫荡$") and screen.has([240, 460, 270, 33], "扫荡结束"):
            progress = screen.text([242, 491, 150, 32]).replace(" ", "")
            if not re.fullmatch(rf"{expected_count}[/／]{expected_count}", progress):
                raise RuntimeError(f"Unexpected sweep completion count: {progress!r}")
            if not screen.has([560, 573, 161, 51], "^确认$"):
                raise RuntimeError("Sweep results have no confirmation button")
            screen.save(f"{label}-complete")
            screen.log("sweep_complete", completed=expected_count)
            screen.tap(640, 597, 0.6)
            return
        screen.pause(0.4)
    raise RuntimeError("Sweep results did not complete within the bounded wait")


def dialog_visible(screen: Screen) -> bool:
    return screen.has([500, 42, 275, 80], "自动战斗设置")


def counter(screen: Screen) -> int:
    return integer_text(screen.text([330, 385, 620, 40]))


def set_counter(screen: Screen, wanted: int) -> None:
    for _ in range(30):
        screen.capture()
        if not dialog_visible(screen):
            raise RuntimeError("Sweep dialog disappeared while setting count")
        current = counter(screen)
        if current == wanted:
            return
        x = 916 if current < wanted else 364
        for _ in range(min(abs(wanted - current), 5)):
            screen.tap(x, 454, 0.1)
    raise RuntimeError("Sweep counter did not reach configured value")


def stamina_cost(text: str) -> tuple[int, int]:
    normalized = text.replace("，", ",").replace("−", "-").replace("（", "(").replace("）", ")").replace(" ", "")
    match = re.fullmatch(r"([\d,]+)(?:\((-?\d+)\))?", normalized)
    if not match:
        raise ValueError(f"Ambiguous stamina cost: {text!r}")
    balance = int(match.group(1).replace(",", ""))
    delta = int(match.group(2) or "0")
    if delta > 0 or -delta > balance:
        raise ValueError(f"Invalid stamina deduction: {text!r}")
    return balance, -delta


def resource_sweep(screen: Screen, params: dict, *, kind: str | None = None) -> bool:
    kind = kind or params.get("kind")
    categories = {"gold": ("金币副本", 337, 395, [45, 260, 250, 68]),
                  "experience": ("经验副本", 737, 395, [445, 260, 250, 68]),
                  "items": ("道具副本", 1137, 395, [845, 260, 250, 68]),
                  "red": ("红色碎片副本", 737, 642, [445, 505, 350, 68])}
    if kind not in categories:
        raise ValueError("Unknown resource dungeon")
    requested = int(params.get("count", 10))
    if not 0 <= requested <= 100:
        raise ValueError("Sweep count must be between 0 and 100")
    if requested == 0:
        screen.log("resource_skipped", kind=kind, reason="configured_zero")
        return True
    boosted_only = params.get("boost_only", True)
    if not isinstance(boosted_only, bool):
        raise ValueError("boost_only must be a boolean")
    title, x, y, title_roi = categories[kind]
    screen.capture()
    if not dialog_visible(screen):
        if not screen.has(title_roi, title):
            raise RuntimeError(f"Dungeon category is not visible: {title}")
        screen.tap(x, y, 0.6)
        screen.capture()
    execute_stamina_sweep(screen, requested, boosted_only, kind)
    return True


def execute_stamina_sweep(screen: Screen, requested: int, boosted_only: bool, kind: str) -> int:
    """Validate the shared normal/evolution dialog and return the completed count."""
    if not dialog_visible(screen):
        raise RuntimeError("Expected stamina sweep settings are missing")
    if not screen.has([365, 538, 170, 44], "每日焕发"):
        if boosted_only:
            screen.log("resource_skipped", kind=kind, reason="boost_not_available")
            screen.tap(536, 637, 0.5)
            return 0
        return execute_plain_sweep(screen, requested, kind)
    allowance = screen.text([853, 539, 88, 39]).replace(" ", "")
    match = re.fullmatch(r"(\d{1,2})[/／]10", allowance)
    if not match or not 0 <= int(match.group(1)) <= 10:
        raise RuntimeError(f"Cannot determine remaining boosted entries: {allowance!r}")
    remaining = int(match.group(1))
    wanted = min(requested, remaining) if boosted_only else requested
    if wanted == 0:
        screen.log("resource_skipped", kind=kind, reason="no_boosted_entries")
        screen.tap(536, 637, 0.5)
        return 0
    if boosted_only and not screen.recognize("ColorMatch", {"roi": [340, 546, 29, 27], "method": 4,
                                                           "lower": [70, 180, 0], "upper": [170, 255, 120], "count": 20}):
        screen.tap(353, 559, 0.3)
    set_counter(screen, wanted)
    screen.capture()
    if counter(screen) != wanted:
        raise RuntimeError("Sweep count changed unexpectedly")
    if boosted_only:
        if not screen.recognize("ColorMatch", {"roi": [340, 546, 29, 27], "method": 4,
                                               "lower": [70, 180, 0], "upper": [170, 255, 120], "count": 20}):
            raise RuntimeError("Daily boosted rewards are not enabled")
        if screen.text([853, 539, 88, 39]).replace(" ", "") != allowance:
            raise RuntimeError("Boosted allowance changed before confirmation")
    available, spend = stamina_cost(screen.text([623, 493, 121, 38]))
    reserve, reserve_spend = stamina_cost(screen.text([808, 493, 134, 38]))
    if spend + reserve_spend != wanted * 10:
        raise RuntimeError("Stamina cost does not match the selected count")
    if not screen.has([655, 612, 171, 54], "^扫荡$"):
        raise RuntimeError("Final sweep button is missing")
    screen.save(f"{kind}-before-confirm")
    screen.log("resource_confirm", kind=kind, count=wanted, boost_remaining=remaining,
               stamina=available, reserve=reserve, spend=spend, reserve_spend=reserve_spend)
    screen.tap(744, 637, 1.0)
    finish_sweep(screen, wanted, kind)
    screen.log("resource_verified", kind=kind, count=wanted)
    return wanted


def execute_plain_sweep(screen: Screen, wanted: int, kind: str, *, preview_only: bool = False) -> int:
    """The no-boost layout moves the counter and stamina row down by 47px."""
    for _ in range(30):
        screen.capture()
        if not dialog_visible(screen):
            raise RuntimeError("Plain sweep dialog disappeared")
        current = integer_text(screen.text([330, 435, 620, 40]))
        if current == wanted:
            break
        for _ in range(min(abs(wanted - current), 5)):
            screen.tap(916 if current < wanted else 364, 501, 0.1)
    else:
        raise RuntimeError("Plain sweep count did not reach configured value")
    available, spend = stamina_cost(screen.text([623, 539, 121, 38]))
    reserve, reserve_spend = stamina_cost(screen.text([808, 539, 134, 38]))
    if spend + reserve_spend != wanted * 10 or not screen.has([655, 612, 171, 54], "^扫荡$"):
        raise RuntimeError("Plain sweep count/cost/button could not be verified")
    screen.save(f"{kind}-before-confirm")
    screen.log("resource_confirm", kind=kind, count=wanted, stamina=available, reserve=reserve,
               spend=spend, reserve_spend=reserve_spend, boosted=False)
    if preview_only:
        screen.log("resource_preview", kind=kind, count=wanted)
        screen.tap(536, 637, 0.5)
        return 0
    screen.tap(744, 637, 1.0)
    finish_sweep(screen, wanted, kind)
    return wanted


def flower_sweep(screen: Screen, params: dict) -> bool:
    count = params.get("count", 10)
    attributes = {"neutral": ("虚", 337, 395, 45, 260), "light": ("光", 737, 395, 445, 260),
                  "dark": ("暗", 1137, 395, 845, 260), "earth": ("土", 337, 642, 45, 505),
                  "fire": ("火", 737, 642, 445, 505), "water": ("水", 1137, 642, 845, 505)}
    attribute = params.get("attribute", "neutral")
    preview = params.get("preview_only", False)
    if type(count) is not int or not 0 <= count <= 100 or attribute not in attributes or type(preview) is not bool:
        raise ValueError("Invalid flowering-stone sweep settings")
    if not count:
        screen.log("resource_skipped", kind="flower", reason="configured_zero")
        return True
    label, x, y, title_x, title_y = attributes[attribute]
    screen.capture()
    if not screen.has([title_x, title_y, 350, 68], label + "属性开花石副本"):
        raise RuntimeError("Selected flowering-stone dungeon is not visible")
    if not screen.has([x - 35, y - 22, 110, 44], "^扫荡$"):
        raise RuntimeError("Flowering-stone sweep is not unlocked")
    screen.tap(x, y, 0.6)
    screen.capture()
    if not dialog_visible(screen) or screen.has([365, 538, 170, 44], "每日焕发"):
        raise RuntimeError("Unexpected flowering-stone sweep layout")
    execute_plain_sweep(screen, count, "flower", preview_only=preview)
    return True


def tethys_free(screen: Screen, params: dict) -> bool:
    screen.capture()
    if not screen.has([65, 5, 340, 60], "忒提斯英雄传"):
        raise RuntimeError("Thetis page is not visible")
    # The ticket icon immediately to the left can be OCR'd as a Chinese prefix.
    value = screen.text([1070, 564, 60, 44]).replace(" ", "")
    match = re.fullmatch(r"([0-3])[/／]3", value)
    if not match:
        raise RuntimeError(f"Cannot determine Thetis free entries: {value!r}")
    remaining = int(match.group(1))
    if not remaining:
        screen.log("tethys_skipped", reason="no_free_entries")
        return True
    if not dialog_visible(screen):
        screen.tap(1065, 644, 0.6)
        screen.capture()
    if not dialog_visible(screen) or not screen.has([530, 325, 240, 44], "剩余免费进入次数"):
        raise RuntimeError("Thetis free-entry setting is missing")
    count = counter(screen)
    diamonds = integer_text(screen.text([870, 492, 75, 40]))
    vouchers = screen.text([870, 540, 75, 40]).replace(" ", "")
    if count != remaining or diamonds != 0 or not re.fullmatch(r"0[/／]3", vouchers):
        raise RuntimeError(f"Refusing non-free Thetis sweep: count={count}, diamonds={diamonds}, vouchers={vouchers!r}")
    if not screen.has([680, 612, 140, 50], "^扫荡$"):
        raise RuntimeError("Thetis sweep confirmation button is missing")
    screen.save("tethys-before-confirm")
    screen.log("tethys_confirm", count=count, diamonds=diamonds, vouchers=vouchers)
    screen.tap(765, 637, 1.0)
    finish_sweep(screen, count, "tethys")
    screen.log("tethys_verified", count=count)
    return True


def awake_free(screen: Screen, params: dict) -> bool:
    """Only submit up to three verified free entries, with zero diamond/voucher cost."""
    screen.capture()
    if not screen.has([500, 66, 275, 50], "自动战斗设置"):
        if not screen.has([45, 505, 350, 68], "觉醒副本"):
            raise RuntimeError("Awakening category is not visible")
        button = screen.text([244, 616, 184, 52])
        if "挑战券兑换" in button:
            screen.log("awakening_skipped", reason="no_free_entries")
            return True
        match = re.search(r"[（(]([0-3])\s*[/／]\s*3[)）]", button)
        if not match:
            raise RuntimeError(f"Cannot determine remaining free entries: {button!r}")
        remaining = int(match.group(1))
        if remaining == 0:
            screen.log("awakening_skipped", reason="no_free_entries")
            return True
        screen.tap(337, 642, 0.6)
        screen.capture()
    if not screen.has([500, 66, 275, 50], "自动战斗设置"):
        raise RuntimeError("Awakening sweep dialog did not open")
    if not screen.has([530, 317, 240, 46], "剩余免费进入次数"):
        raise RuntimeError("Free-entry setting is missing")
    count = integer_text(screen.text([330, 365, 620, 39]))
    diamonds = integer_text(screen.text([870, 468, 73, 40]))
    vouchers = integer_text(screen.text([870, 519, 73, 40]))
    if not 1 <= count <= 3 or diamonds != 0 or vouchers != 0:
        raise RuntimeError(f"Refusing non-free awakening sweep: count={count}, diamonds={diamonds}, vouchers={vouchers}")
    if not screen.has([680, 585, 139, 54], "^扫荡$"):
        raise RuntimeError("Sweep confirmation button is missing")
    screen.save("awakening-before-confirm")
    screen.log("awakening_confirm", count=count, diamonds=diamonds, vouchers=vouchers)
    screen.tap(744, 611, 1.0)
    finish_sweep(screen, count, "awakening")
    screen.capture().save("awakening-after-confirm")
    screen.log("awakening_verified", count=count)
    return True


def evolution_candidate(screen: Screen) -> tuple[int, int] | None:
    """Only owned, incomplete cards with both progress fields visible qualify."""
    statuses = screen.ocr([336, 187, 609, 385], r"\d+[/／]\d+")
    for item in sorted(statuses, key=lambda item: (item["box"][1], item["box"][0])):
        text = item["text"].replace(" ", "")
        match = re.fullmatch(r"(\d+)[/／](\d+)", text)
        if not match or int(match.group(2)) == 1160:
            continue
        x, y, w, h = item["box"]
        center = min((385, 487, 589, 691, 793, 895), key=lambda value: abs(value - (x + w / 2)))
        # Bottom progress belongs to an owned hero. Unowned cards say 未持有.
        total = screen.text([center - 44, y - 119, 89, 30]).replace(" ", "")
        cumulative = re.fullmatch(r"(\d+)[/／]1160", total)
        if cumulative and int(cumulative.group(1)) < 1160 and y - 60 >= 197:
            return center, y - 60
    return None


def wait_evolution_page(screen: Screen) -> None:
    """Dismiss known sweep rewards before clicking the next hero's settings."""
    deadline = time.monotonic() + 12
    while True:
        screen.capture()
        if (screen.has([510, 245, 270, 70], "^获得活动积分$|^领取奖励$|^获得活跃度$")
                and screen.has([425, 635, 445, 68], "点击空白.*关闭弹窗")):
            screen.tap(640, 660, 0.5)
        elif (screen.has([45, 260, 350, 65], "虚属性进化石副本")
              and screen.recognize("ColorMatch", {"method": 4, "lower": [220, 220, 220],
                  "upper": [255, 255, 255], "roi": [30, 16, 200, 44], "count": 200})):
            return
        if time.monotonic() >= deadline:
            raise RuntimeError("Evolution page is still covered after sweep rewards")
        screen.pause(0.3)


def choose_evolution_hero(screen: Screen, gear: tuple[int, int]) -> bool:
    wait_evolution_page(screen)
    screen.tap(*gear, 0.5)
    screen.capture()
    if not screen.has([526, 48, 230, 40], "奖励设置"):
        raise RuntimeError("Evolution reward settings did not open")
    # Always restore the top first. Scan bounded pages inside the card viewport.
    screen.act("Swipe", {"begin": [933, 218], "end": [933, 545], "duration": 350})
    screen.pause(0.4)
    for _ in range(8):
        screen.capture()
        candidate = evolution_candidate(screen)
        if candidate:
            screen.tap(*candidate, 0.25)
            screen.capture().save("evolution-hero-selected")
            screen.log("evolution_hero_selected", position=candidate)
            screen.tap(754, 631, 0.5)
            return True
        # Detect the end using exact pixels, not an arbitrary OCR text order.
        before = hero_viewport(screen)
        screen.act("Swipe", {"begin": [933, 532], "end": [933, 320], "duration": 350})
        screen.pause(0.4)
        screen.capture()
        after = hero_viewport(screen)
        if before == after:
            break
    screen.log("evolution_attribute_finished", reason="no_owned_incomplete_candidate")
    screen.tap(526, 631, 0.4)
    return False


def hero_viewport(screen: Screen) -> bytes:
    channels = screen.native.image_channels(screen.image)
    pixels = ct.string_at(screen.native.raw(screen.image), 1280 * 720 * channels)
    return b"".join(pixels[(y * 1280 + 326) * channels:(y * 1280 + 954) * channels]
                    for y in range(185, 580))


def evolution_sweep(screen: Screen, params: dict) -> bool:
    requested = int(params.get("count", 10))
    if not 0 <= requested <= 100:
        raise ValueError("Evolution count must be between 0 and 100")
    if not requested:
        screen.log("evolution_skipped", reason="configured_zero")
        return True
    attributes = ["neutral", "light", "dark", "earth", "fire", "water"]
    selected = params.get("attribute", "neutral")
    mode = params.get("mode", "auto")
    if selected not in attributes or mode not in ("auto", "selected"):
        raise ValueError("Invalid evolution attribute or target mode")
    boosted_only = params.get("boost_only", True)
    if not isinstance(boosted_only, bool):
        raise ValueError("boost_only must be a boolean")
    screen.capture()
    if not screen.has([45, 260, 350, 65], "虚属性进化石副本"):
        raise RuntimeError("Evolution category is not visible")
    start = attributes.index(selected)
    order = attributes[start:] + attributes[:start] if mode == "auto" else [selected]
    completed = 0
    for attribute in order:
        index = attributes.index(attribute)
        gear = (404 + (index % 3) * 400, 333 if index < 3 else 578)
        button = (337 + (index % 3) * 400, 395 if index < 3 else 642)
        while completed < requested:
            if mode == "auto" and not choose_evolution_hero(screen, gear):
                break
            screen.tap(*button, 0.6)
            screen.capture()
            # One run at a time allows a completed hero to be replaced immediately.
            count = execute_stamina_sweep(screen, 1 if mode == "auto" else requested - completed,
                                          boosted_only, "evolution")
            if not count:
                return True
            completed += count
            screen.log("evolution_progress", attribute=attribute, completed=completed, requested=requested)
        if completed >= requested:
            return True
    screen.log("evolution_finished", completed=completed, reason="no_more_owned_targets")
    return True


def probe(screen: Screen, params: dict) -> bool:
    screen.capture().save("agent-probe")
    screen.log("agent_probe", resolution=[1280, 720])
    return True



HANDLERS = {"GT_AwakeningFree": awake_free,
            "GT_GoldResourceSweep": partial(resource_sweep, kind="gold"),
            "GT_ExperienceResourceSweep": partial(resource_sweep, kind="experience"),
            "GT_ItemsResourceSweep": partial(resource_sweep, kind="items"),
            "GT_RedResourceSweep": partial(resource_sweep, kind="red"),
            "GT_FlowerSweep": flower_sweep,
            "GT_ShopPurchase": shop_purchase, "GT_TethysFree": tethys_free,
            "GT_EventShopPurchase": partial(shop_purchase, event_only=True),
            "GT_PassRewards": pass_rewards,
            "GT_EvolutionSweep": evolution_sweep, "GT_AgentProbe": probe}
