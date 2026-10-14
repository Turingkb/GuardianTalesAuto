"""Small C ABI adapter shared by the GUI Agent and local development tests.

Uses the project's pinned MaaFramework runtime. Screenshots, recognition and
input remain in MaaFramework so GUI cancellation and controller selection apply.
"""

import ctypes as ct
import json
import os
from pathlib import Path
import time


class Rect(ct.Structure):
    _fields_ = [("x", ct.c_int32), ("y", ct.c_int32), ("w", ct.c_int32), ("h", ct.c_int32)]


ACTION_CALLBACK = ct.CFUNCTYPE(ct.c_uint8, ct.c_void_p, ct.c_int64, ct.c_char_p,
                              ct.c_char_p, ct.c_char_p, ct.c_int64, ct.POINTER(Rect), ct.c_void_p)


class Native:
    def __init__(self, root: Path):
        self.root = root
        runtime = root / "runtimes/win-x64/native"
        self.directory = os.add_dll_directory(str(runtime))
        self.fw = ct.CDLL(str(runtime / "MaaFramework.dll"))
        p, s, n = ct.c_void_p, ct.c_char_p, ct.c_int64
        self.context_tasker = self.bind("MaaContextGetTasker", p, p)
        self.controller = self.bind("MaaTaskerGetController", p, p)
        self.stopping = self.bind("MaaTaskerStopping", ct.c_uint8, p)
        self.post_capture = self.bind("MaaControllerPostScreencap", n, p)
        self.wait = self.bind("MaaControllerWait", ct.c_int32, p, n)
        self.cached = self.bind("MaaControllerCachedImage", ct.c_uint8, p, p)
        self.create_image = self.bind("MaaImageBufferCreate", p)
        self.destroy_image = self.bind("MaaImageBufferDestroy", None, p)
        self.image_width = self.bind("MaaImageBufferWidth", ct.c_int32, p)
        self.image_height = self.bind("MaaImageBufferHeight", ct.c_int32, p)
        self.image_channels = self.bind("MaaImageBufferChannels", ct.c_int32, p)
        self.raw = self.bind("MaaImageBufferGetRawData", p, p)
        self.encoded = self.bind("MaaImageBufferGetEncoded", p, p)
        self.encoded_size = self.bind("MaaImageBufferGetEncodedSize", ct.c_uint64, p)
        self.create_string = self.bind("MaaStringBufferCreate", p)
        self.destroy_string = self.bind("MaaStringBufferDestroy", None, p)
        self.read_string = self.bind("MaaStringBufferGet", s, p)
        self.run_recognition = self.bind("MaaContextRunRecognitionDirect", n, p, s, s, p)
        self.run_action = self.bind("MaaContextRunActionDirect", n, p, s, s, ct.POINTER(Rect), s)
        self.reco_detail = self.bind("MaaTaskerGetRecognitionDetail", ct.c_uint8,
                                    p, n, p, p, ct.POINTER(ct.c_uint8), ct.POINTER(Rect), p, p, p)
        self.action_detail = self.bind("MaaTaskerGetActionDetail", ct.c_uint8,
                                      p, n, p, p, ct.POINTER(Rect), ct.POINTER(ct.c_uint8), p)
        self.callbacks = []

    def bind(self, name, restype, *argtypes):
        function = getattr(self.fw, name)
        function.restype, function.argtypes = restype, argtypes
        return function


class Screen:
    def __init__(self, native: Native, context):
        self.native, self.context = native, context
        self.tasker = native.context_tasker(context)
        self.controller = native.controller(self.tasker)
        self.image = native.create_image()
        self.started = time.monotonic()

    def close(self):
        if self.image:
            self.native.destroy_image(self.image)
            self.image = None

    def check_cancelled(self):
        if self.native.stopping(self.tasker):
            raise RuntimeError("Task cancelled")
        if time.monotonic() - self.started > 1200:
            raise RuntimeError("Agent operation exceeded twenty-minute limit")

    def capture(self):
        self.check_cancelled()
        if self.native.wait(self.controller, self.native.post_capture(self.controller)) != 3000:
            raise RuntimeError("Screenshot job failed")
        if not self.native.cached(self.controller, self.image):
            raise RuntimeError("Screenshot is empty")
        dimensions = (self.native.image_width(self.image), self.native.image_height(self.image))
        if dimensions != (1280, 720):
            raise RuntimeError(f"Unexpected screenshot resolution: {dimensions}")
        return self

    def recognize(self, kind: str, params: dict) -> dict | None:
        self.check_cancelled()
        reco_id = self.native.run_recognition(self.context, kind.encode(),
                                             json.dumps(params, ensure_ascii=False).encode(), self.image)
        hit, box = ct.c_uint8(), Rect()
        buffer = self.native.create_string()
        try:
            if not self.native.reco_detail(self.tasker, reco_id, None, None, ct.byref(hit),
                                           ct.byref(box), buffer, None, None):
                raise RuntimeError("Cannot retrieve recognition result")
            if not hit.value:
                return None
            detail = json.loads(self.native.read_string(buffer) or b"null")
            return {"box": [box.x, box.y, box.w, box.h], "detail": detail}
        finally:
            self.native.destroy_string(buffer)

    def ocr(self, roi: list[int], expected: str | list[str] | None = None) -> list[dict]:
        params = {"roi": roi, "threshold": 0.65}
        if expected is not None:
            params["expected"] = expected
        result = self.recognize("OCR", params)
        return result["detail"].get("filtered", []) if result else []

    def has(self, roi: list[int], expected: str | list[str]) -> bool:
        return bool(self.ocr(roi, expected))

    def text(self, roi: list[int]) -> str:
        return " ".join(item["text"] for item in self.ocr(roi))

    def act(self, kind: str, params: dict):
        self.check_cancelled()
        box = Rect(0, 0, 1280, 720)
        action_id = self.native.run_action(self.context, kind.encode(), json.dumps(params).encode(), ct.byref(box), b"{}")
        success = ct.c_uint8()
        if not self.native.action_detail(self.tasker, action_id, None, None, ct.byref(box), ct.byref(success), None) or not success.value:
            raise RuntimeError(f"{kind} action failed")

    def tap(self, x: int, y: int, delay: float = 0.35):
        if not (0 <= x < 1280 and 0 <= y < 720):
            raise ValueError("Tap is outside the game screen")
        self.act("LongPress", {"target": [x, y], "duration": 50})
        self.pause(delay)

    def pause(self, seconds: float):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            self.check_cancelled()
            time.sleep(min(0.1, max(0, until - time.monotonic())))

    def save(self, name: str):
        directory = self.native.root / "debug/agent"
        directory.mkdir(parents=True, exist_ok=True)
        size = self.native.encoded_size(self.image)
        (directory / f"{name}.png").write_bytes(ct.string_at(self.native.encoded(self.image), size))

    def log(self, event: str, **details):
        record = {"event": event, **details}
        print(json.dumps(record, ensure_ascii=False), flush=True)
        directory = self.native.root / "debug/agent"
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "actions.jsonl").open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
