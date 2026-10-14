"""Benchmark native screenshot jobs without performing game input."""

import ctypes as ct
import json
import os
from pathlib import Path
import statistics
import time


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    native = root / "runtimes/win-x64/native"
    output = root / "dev/2026-10-14"
    directory = os.add_dll_directory(str(native))
    fw = ct.CDLL(str(native / "MaaFramework.dll"))

    def bind(name, restype, *argtypes):
        function = getattr(fw, name)
        function.restype, function.argtypes = restype, argtypes
        return function

    ptr, string, identifier = ct.c_void_p, ct.c_char_p, ct.c_int64
    create = bind("MaaAdbControllerCreate", ptr, string, string, ct.c_uint64, ct.c_uint64, string, string)
    connect = bind("MaaControllerPostConnection", identifier, ptr)
    wait = bind("MaaControllerWait", ct.c_int32, ptr, identifier)
    capture = bind("MaaControllerPostScreencap", identifier, ptr)
    cached = bind("MaaControllerCachedImage", ct.c_uint8, ptr, ptr)
    create_image = bind("MaaImageBufferCreate", ptr)
    destroy_image = bind("MaaImageBufferDestroy", None, ptr)
    destroy = bind("MaaControllerDestroy", None, ptr)
    width = bind("MaaImageBufferWidth", ct.c_int32, ptr)
    height = bind("MaaImageBufferHeight", ct.c_int32, ptr)
    encoded = bind("MaaImageBufferGetEncoded", ptr, ptr)
    encoded_size = bind("MaaImageBufferGetEncodedSize", ct.c_uint64, ptr)
    config = {"extras": {"mumu": {"enable": True, "index": 0, "path": "D:/Software/Game/Mumu12/MuMuPlayer"}}}
    adb = json.loads((root / "config/maa_pi_config.json").read_text(encoding="utf-8"))["adb"]
    results = []
    for name, method in (("Encode", 2), ("EmulatorExtras", 64)):
        controller = image = None
        try:
            controller = create(adb["adb_path"].encode(), adb["address"].encode(), method, 1,
                                json.dumps(config).encode(), str(root / "libs/MaaAgentBinary").encode())
            if not controller or wait(controller, connect(controller)) != 3000:
                raise RuntimeError("Connection failed")
            image = create_image()
            measurements = []
            for iteration in range(22):
                started = time.perf_counter()
                if wait(controller, capture(controller)) != 3000:
                    raise RuntimeError("Capture failed")
                milliseconds = (time.perf_counter() - started) * 1000
                if iteration >= 2:
                    measurements.append(milliseconds)
            if not cached(controller, image) or width(image) < 100:
                raise RuntimeError("No valid image")
            size = encoded_size(image)
            (output / f"capture-{name}.png").write_bytes(ct.string_at(encoded(image), size))
            result = {"method": name, "resolution": [width(image), height(image)],
                      "samples": len(measurements), "median_ms": statistics.median(measurements),
                      "min_ms": min(measurements), "max_ms": max(measurements)}
        except RuntimeError as error:
            result = {"method": name, "error": str(error)}
        finally:
            if image:
                destroy_image(image)
            if controller:
                destroy(controller)
        results.append(result)
        print(json.dumps(result), flush=True)
    (output / "capture-benchmark.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    directory.close()


if __name__ == "__main__":
    main()
