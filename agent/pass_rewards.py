"""Claim completed invitational goals and unlocked pass rewards, without upgrades."""

import time

from native import Screen

BANNERS = (("guardian", "pass_banner_guardian.png"),
           ("celebration", "pass_banner_celebration.png"),
           ("world", "pass_banner_world.png"))


def page_ready(screen: Screen) -> bool:
    return (screen.has([70, 12, 110, 44], "^邀请赛$")
            and (screen.has([350, 146, 150, 42], "邀请函等级") or world_page(screen))
            and bool(screen.recognize("ColorMatch", {"method": 4, "lower": [220, 220, 220],
                                                     "upper": [255, 255, 255],
                                                     "roi": [30, 16, 150, 44], "count": 200})))


def world_page(screen: Screen) -> bool:
    return (screen.has([350, 90, 420, 80], "通关世界挑战赛")
            and screen.has([350, 365, 190, 55], "^公主的礼物$"))


def claim_available(screen: Screen) -> bool:
    return (page_ready(screen)
            and screen.has([1068, 628, 166, 53], "^全部领取$")
            and bool(screen.recognize("ColorMatch", {"method": 4, "lower": [240, 175, 0],
                                                     "upper": [255, 230, 70],
                                                     "roi": [1076, 635, 148, 36], "count": 2500})))


def reward_popup(screen: Screen) -> bool:
    return (screen.has([510, 245, 270, 70], "^领取奖励$")
            and screen.has([425, 635, 445, 68], "点击空白.*关闭弹窗"))


def settle_claim(screen: Screen) -> None:
    deadline, stable, dismissed = time.monotonic() + 18, 0, False
    while time.monotonic() < deadline:
        screen.capture()
        if reward_popup(screen):
            screen.save("pass-reward-received")
            screen.tap(640, 660, 0.5)
            stable, dismissed = 0, True
            continue
        if page_ready(screen):
            if dismissed:
                return
            # An animation may finish before the next capture. The disabled
            # claim button must remain disabled across multiple observations.
            stable = stable + 1 if not claim_available(screen) else 0
            if stable >= 3:
                return
        screen.pause(0.3)
    raise RuntimeError("Pass claim result is unknown; no further input was submitted")


def claim_all(screen: Screen, kind: str, phase: str) -> int:
    for count in range(3):
        screen.capture()
        if not page_ready(screen):
            raise RuntimeError("Invitational page is covered or has changed")
        if not claim_available(screen):
            screen.log("pass_claim_checked", kind=kind, phase=phase, claims=count)
            return count
        screen.save("pass-before-claim")
        screen.tap(1150, 651, 0.7)
        settle_claim(screen)
        screen.log("pass_claim_verified", kind=kind, phase=phase)
    screen.capture()
    if claim_available(screen):
        raise RuntimeError("Pass claim button remained enabled after three submissions")
    return 3


def select_tab(screen: Screen, phase: str):
    if phase not in ("goals", "rewards"):
        raise ValueError("Unknown pass tab")
    screen.capture()
    if not page_ready(screen):
        raise RuntimeError("Invitational page is not ready")
    x, label = (1000, "邀请函目标") if phase == "goals" else (556, "邀请函奖励")
    if not screen.has([x - 160, 75, 320, 48], label):
        raise RuntimeError(f"Pass tab is missing: {phase}")
    screen.tap(x, 98, 0.5)
    screen.capture()
    if not page_ready(screen) or not screen.recognize("ColorMatch", {
            "method": 4, "lower": [0, 140, 200], "upper": [100, 220, 255],
            "roi": [800 if phase == "goals" else 335, 80, 435, 38], "count": 6000}):
        raise RuntimeError(f"Pass tab did not become active: {phase}")


def pass_rewards(screen: Screen, params: dict) -> bool:
    screen.capture()
    if not page_ready(screen):
        raise RuntimeError("Invitational page is not visible")
    screen.act("Swipe", {"begin": [285, 160], "end": [285, 640], "duration": 300})
    screen.pause(0.3)
    for kind, template in BANNERS:
        screen.capture()
        if not page_ready(screen):
            raise RuntimeError("Invitational page changed while selecting a pass")
        banner = screen.recognize("TemplateMatch", {"template": template, "roi": [30, 120, 270, 560],
                                                     "threshold": 0.88})
        if not banner:
            screen.log("pass_skipped", kind=kind, reason="banner_not_available")
            continue
        x, y, w, h = banner["box"]
        screen.tap(int(x + w / 2), int(y + h / 2), 0.6)
        if kind == "world":
            screen.capture()
            if not world_page(screen):
                raise RuntimeError("World challenge reward page did not open")
            claim_all(screen, kind, "rewards")
            continue
        select_tab(screen, "goals")
        # The all-claim control includes completed daily/weekly/season goals.
        claim_all(screen, kind, "goals")
        select_tab(screen, "rewards")
        claim_all(screen, kind, "rewards")
    screen.log("pass_rewards_finished")
    return True
