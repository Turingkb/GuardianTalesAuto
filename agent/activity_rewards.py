"""Claim completed event goals without starting challenges or spending points."""

import re
import time
from collections.abc import Callable

from native import Screen


def goals_ready(screen: Screen) -> bool:
    return (screen.has([170, 40, 140, 60], "^活动目标$")
            and screen.has([350, 20, 180, 45], "^活动任务$")
            and bool(screen.recognize("ColorMatch", {
                "method": 4, "lower": [220, 220, 220], "upper": [255, 255, 255],
                "roi": [180, 45, 125, 45], "count": 150})))


def claim_available(screen: Screen) -> bool:
    return (goals_ready(screen)
            and screen.has([990, 630, 185, 65], "^一键领取$")
            and bool(screen.recognize("ColorMatch", {
                "method": 4, "lower": [240, 175, 0], "upper": [255, 230, 70],
                "roi": [1000, 640, 150, 40], "count": 2500})))


def points(screen: Screen) -> int:
    text = screen.text([425, 638, 120, 42]).replace(",", "").replace("，", "").strip()
    if not re.fullmatch(r"\d+", text):
        raise RuntimeError(f"Cannot read event points: {text!r}")
    return int(text)


def reward_popup(screen: Screen) -> bool:
    return (screen.has([510, 245, 270, 70], "^领取奖励$|^获得活动积分$")
            and screen.has([425, 635, 445, 68], "点击空白.*关闭弹窗"))


def wait_for(screen: Screen, predicate: Callable[[Screen], bool], message: str) -> None:
    deadline = time.monotonic() + 15
    while True:
        screen.capture()
        if predicate(screen):
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(message)
        screen.pause(0.3)


def claim_goals(screen: Screen) -> int:
    wait_for(screen, goals_ready, "Event goals did not open")
    total = 0
    for _ in range(3):
        screen.capture()
        if not goals_ready(screen):
            raise RuntimeError("Event goals are covered or changed")
        if not screen.has([990, 630, 185, 65], "^一键领取$"):
            raise RuntimeError("Event claim control is missing")
        if not claim_available(screen):
            if not screen.recognize("ColorMatch", {
                    "method": 4, "lower": [105, 110, 120], "upper": [145, 150, 165],
                    "roi": [1000, 640, 150, 40], "count": 2500}):
                raise RuntimeError("Event claim control has an unknown state")
            screen.log("activity_claim_checked", gained=total, reason="no_completed_goals")
            return total
        before = points(screen)
        screen.save("activity-before-claim")
        screen.tap(1078, 659, 0.7)
        deadline = time.monotonic() + 18
        while True:
            screen.capture()
            if reward_popup(screen):
                screen.save("activity-reward-received")
                screen.tap(640, 660, 0.5)
            elif goals_ready(screen):
                after = points(screen)
                if after > before:
                    total += after - before
                    screen.log("activity_claim_verified", before=before, after=after, gained=after-before)
                    break
            if time.monotonic() >= deadline:
                raise RuntimeError("Event claim was not verified; no further submission was made")
            screen.pause(0.3)
    screen.capture()
    if claim_available(screen):
        raise RuntimeError("Event claim button remained enabled after three submissions")
    return total


def activity_list(screen: Screen) -> bool:
    return screen.has([70, 12, 110, 44], "^活动$")


def bingo_page(screen: Screen) -> bool:
    return (screen.has([70, 12, 350, 48], "开心宾果乐")
            and screen.has([28, 185, 220, 50], "确认活动目标"))


def activity_rewards(screen: Screen, params: dict) -> bool:
    wait_for(screen, activity_list, "Activity list did not open")
    screen.act("Swipe", {"begin": [285, 155], "end": [285, 640], "duration": 300})
    screen.pause(0.4)
    banner = None
    for _ in range(6):
        screen.capture()
        if not activity_list(screen):
            raise RuntimeError("Activity list changed while searching banners")
        banner = screen.recognize("TemplateMatch", {
            "template": "activity_banner_bingo.png", "roi": [30, 120, 270, 560], "threshold": 0.88})
        if banner:
            break
        screen.act("Swipe", {"begin": [285, 630], "end": [285, 270], "duration": 300})
        screen.pause(0.4)
    if not banner:
        screen.log("activity_skipped", reason="supported_event_not_available")
        return True
    x, y, w, h = banner["box"]
    screen.tap(int(x + w / 2), int(y + h / 2), 0.7)
    screen.capture()
    if not bingo_page(screen):
        if not activity_list(screen):
            raise RuntimeError("Activity banner did not open a known page")
        # A selected banner may leave the sidebar open; toggle only in that state.
        screen.tap(350, 365, 0.7)
    wait_for(screen, bingo_page, "Supported event panel did not open")
    screen.tap(133, 214, 0.5)
    gained = claim_goals(screen)
    screen.tap(1237, 43, 0.5)
    wait_for(screen, bingo_page, "Event goals did not close")
    screen.tap(40, 360, 0.5)
    wait_for(screen, activity_list, "Activity list did not return")
    screen.log("activity_rewards_finished", gained=gained)
    return True
