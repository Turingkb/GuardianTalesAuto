"""MaaFramework Agent server entry point; uses only Python standard-library modules."""

import ctypes as ct
import json
import os
from pathlib import Path
import sys
import traceback

from actions import HANDLERS
from native import ACTION_CALLBACK, Native, Screen
from settings import resolve_task_settings


ROOT = Path(__file__).resolve().parents[1]


def register(native: Native, register_action):
    for name, handler in HANDLERS.items():
        def invoke(context, _task_id, _node, action_name, parameters, _reco_id, _box, _user_data,
                   handler=handler):
            screen = Screen(native, context)
            try:
                params = resolve_task_settings(screen, json.loads(parameters or b"{}"))
                return int(handler(screen, params))
            except Exception as error:
                # Never let a Python exception unwind through a native callback.
                screen.log("action_failed", action=action_name.decode(), error=str(error))
                try:
                    screen.capture().save("action-failed")
                except (RuntimeError, OSError):
                    pass
                traceback.print_exc()
                return 0
            finally:
                screen.close()
        callback = ACTION_CALLBACK(invoke)
        native.callbacks.append(callback)
        if not register_action(name.encode(), callback, None):
            raise RuntimeError(f"Cannot register action: {name}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python agent/main.py <Maa Agent identifier>")
    os.chdir(ROOT)
    native = Native(ROOT)
    server = ct.CDLL(str(ROOT / "runtimes/win-x64/native/MaaAgentServer.dll"))
    server.MaaAgentServerRegisterCustomAction.restype = ct.c_uint8
    server.MaaAgentServerRegisterCustomAction.argtypes = [ct.c_char_p, ACTION_CALLBACK, ct.c_void_p]
    server.MaaAgentServerStartUp.restype = ct.c_uint8
    server.MaaAgentServerStartUp.argtypes = [ct.c_char_p]
    server.MaaAgentServerJoin.restype = None
    server.MaaAgentServerJoin.argtypes = []
    server.MaaAgentServerShutDown.restype = None
    server.MaaAgentServerShutDown.argtypes = []
    register(native, server.MaaAgentServerRegisterCustomAction)
    if not server.MaaAgentServerStartUp(sys.argv[1].encode()):
        raise RuntimeError("Agent server startup failed")
    print("GuardianTales Agent ready", flush=True)
    try:
        server.MaaAgentServerJoin()
    finally:
        server.MaaAgentServerShutDown()


if __name__ == "__main__":
    main()
