"""Exercise bundled Python, native libraries and OCR without a connected device."""

import ctypes as ct
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    # Native diagnostics must not become part of the distributable directory.
    work = ROOT.parent / ".checks" / ROOT.name
    work.mkdir(parents=True, exist_ok=True)
    os.chdir(work)
    sys.path.insert(0, str(ROOT / "agent"))
    from actions import HANDLERS
    from native import Native
    assert len(HANDLERS) == 13
    native = Native(ROOT)
    p, s, n = ct.c_void_p, ct.c_char_p, ct.c_int64
    resource = native.bind("MaaResourceCreate", p)()
    tasker = native.bind("MaaTaskerCreate", p)()
    image = native.create_image()
    callbacks = []
    results = []
    callback_type = ct.CFUNCTYPE(None, p, s, s, p)

    @callback_type
    def sink(_handle, message, details, _context):
        if message in (b"Node.Recognition.Succeeded", b"Node.Recognition.Failed"):
            results.append(json.loads(details))

    callbacks.append(sink)
    try:
        job = native.bind("MaaResourcePostBundle", n, p, s)(resource, str(ROOT / "resource").encode())
        if native.bind("MaaResourceWait", ct.c_int32, p, n)(resource, job) != 3000:
            raise RuntimeError("Bundled OCR models or task resources could not load")
        if not native.bind("MaaTaskerBindResource", ct.c_uint8, p, p)(tasker, resource):
            raise RuntimeError("Cannot bind bundled resources")
        native.bind("MaaTaskerAddContextSink", n, p, callback_type, p)(tasker, sink, None)
        png = (ROOT / "resource/image/daily_claim_all.png").read_bytes()
        if not native.bind("MaaImageBufferSetEncoded", ct.c_uint8, p, s, ct.c_uint64)(image, png, len(png)):
            raise RuntimeError("Cannot decode bundled recognition fixture")
        job = native.bind("MaaTaskerPostRecognition", n, p, s, s, p)(tasker, b"OCR",
                    json.dumps({"expected": ["全部领取"], "threshold": 0.65}).encode(), image)
        if native.bind("MaaTaskerWait", ct.c_int32, p, n)(tasker, job) != 3000:
            raise RuntimeError("Bundled OCR execution failed")
        if not results or not results[-1]["reco_details"].get("box"):
            raise RuntimeError("Bundled OCR did not recognize the expected game button")
        print("Portable smoke PASS: Python " + sys.version.split()[0] + "; 13 Agent actions; native resource load; Chinese OCR")
    finally:
        native.destroy_image(image)
        native.bind("MaaTaskerDestroy", None, p)(tasker)
        native.bind("MaaResourceDestroy", None, p)(resource)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
