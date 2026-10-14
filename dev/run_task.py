"""Run a local pipeline against the configured device using bundled MaaFramework.

Development tool only; no Python SDK download is required. The event transcript
records task and node results, so validation is based on runtime observations.
"""

import argparse
import ctypes as ct
import json
import os
from pathlib import Path
import time
import sys
import subprocess
import uuid


def recognition_input(recognition: dict) -> dict:
    """Convert exported composite children back to the pipeline input format."""
    result = {"type": recognition["type"], "param": dict(recognition["param"])}
    for field in ("all_of", "any_of"):
        if field in result["param"]:
            result["param"][field] = [
                {"recognition": recognition_input(child), "sub_name": child.get("sub_name", "")}
                if isinstance(child, dict) else child
                for child in result["param"][field]
            ]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("entries", nargs="+")
    parser.add_argument("--override", type=Path)
    parser.add_argument("--limit", type=int, default=180)
    parser.add_argument("--image", type=Path, help="Recognize each node on this saved screenshot without device input")
    parser.add_argument("--expect-miss", action="store_true")
    parser.add_argument("--remote-agent", action="store_true", help="Exercise the GUI-style Agent IPC path")
    args = parser.parse_args()
    if args.override:
        args.override = args.override.resolve()
    if args.image:
        args.image = args.image.resolve()
    root = Path(__file__).resolve().parents[1]
    native = root / "runtimes/win-x64/native"
    os.chdir(root)
    dll_directory = os.add_dll_directory(str(native))
    fw = ct.CDLL(str(native / "MaaFramework.dll"))
    toolkit = ct.CDLL(str(native / "MaaToolkit.dll"))
    pointer, string, number = ct.c_void_p, ct.c_char_p, ct.c_int64

    def bind(library, name, restype, *argtypes):
        function = getattr(library, name)
        function.restype = restype
        function.argtypes = argtypes
        return function

    init = bind(toolkit, "MaaToolkitConfigInitOption", ct.c_uint8, string, string)
    create_controller = bind(fw, "MaaAdbControllerCreate", pointer, string, string,
                             ct.c_uint64, ct.c_uint64, string, string)
    connect = bind(fw, "MaaControllerPostConnection", number, pointer)
    wait_controller = bind(fw, "MaaControllerWait", ct.c_int32, pointer, number)
    set_option = bind(fw, "MaaControllerSetOption", ct.c_uint8, pointer,
                      ct.c_int32, pointer, ct.c_uint64)
    create_resource = bind(fw, "MaaResourceCreate", pointer)
    load = bind(fw, "MaaResourcePostBundle", number, pointer, string)
    wait_resource = bind(fw, "MaaResourceWait", ct.c_int32, pointer, number)
    create_tasker = bind(fw, "MaaTaskerCreate", pointer)
    bind_resource = bind(fw, "MaaTaskerBindResource", ct.c_uint8, pointer, pointer)
    bind_controller = bind(fw, "MaaTaskerBindController", ct.c_uint8, pointer, pointer)
    post_task = bind(fw, "MaaTaskerPostTask", number, pointer, string, string)
    status = bind(fw, "MaaTaskerStatus", ct.c_int32, pointer, number)
    stop = bind(fw, "MaaTaskerPostStop", number, pointer)
    wait_task = bind(fw, "MaaTaskerWait", ct.c_int32, pointer, number)
    post_recognition = bind(fw, "MaaTaskerPostRecognition", number, pointer, string, string, pointer)
    get_node = bind(fw, "MaaResourceGetNodeData", ct.c_uint8, pointer, string, pointer)
    create_string = bind(fw, "MaaStringBufferCreate", pointer)
    read_string = bind(fw, "MaaStringBufferGet", string, pointer)
    destroy_string = bind(fw, "MaaStringBufferDestroy", None, pointer)
    create_image = bind(fw, "MaaImageBufferCreate", pointer)
    set_image = bind(fw, "MaaImageBufferSetEncoded", ct.c_uint8, pointer, pointer, ct.c_uint64)
    destroy_image = bind(fw, "MaaImageBufferDestroy", None, pointer)
    callback_type = ct.CFUNCTYPE(None, pointer, string, string, pointer)
    add_sink = bind(fw, "MaaTaskerAddSink", number, pointer, callback_type, pointer)
    add_context_sink = bind(fw, "MaaTaskerAddContextSink", number, pointer, callback_type, pointer)
    destroy_tasker = bind(fw, "MaaTaskerDestroy", None, pointer)
    destroy_resource = bind(fw, "MaaResourceDestroy", None, pointer)
    destroy_controller = bind(fw, "MaaControllerDestroy", None, pointer)
    init(str(root / "dev/runtime").encode(), b'{"logging":true,"save_on_error":true,"stdout_level":2}')
    adb = json.loads((root / "config/maa_pi_config.json").read_text(encoding="utf-8"))["adb"]
    controller = resource = tasker = image = client = None
    agent_process = agent_log = None
    recognition_events = []

    @callback_type
    def event(_handle, message, details, _context):
        label = message.decode()
        if args.image and label in ("Node.Recognition.Succeeded", "Node.Recognition.Failed"):
            recognition_events.append((label, json.loads(details)))
            print(label, "box=", json.loads(details).get("reco_details", {}).get("box"), flush=True)
        if label.endswith(("Succeeded", "Failed")) and label.startswith(("Tasker.Task", "Node.Action")):
            print(label, details.decode(), flush=True)

    try:
        # Use the same capture mode/config as the GUI so development tests agree.
        if not args.image:
            settings = json.loads((root / "config/instances/default.json").read_text(encoding="utf-8"))
            capture_method = 64 if settings.get("AdbControlScreenCapType") == "EmulatorExtras" else 2
            capture_config = settings.get("AdbDevice", {}).get("Config", "{}")
            controller = create_controller(adb["adb_path"].encode(), adb["address"].encode(),
                                           capture_method, 1, capture_config.encode(), str(root / "libs/MaaAgentBinary").encode())
            if not controller or wait_controller(controller, connect(controller)) != 3000:
                raise RuntimeError("ADB connection failed")
            short_side = ct.c_int32(720)
            if not set_option(controller, 2, ct.byref(short_side), ct.sizeof(short_side)):
                raise RuntimeError("Cannot configure 720p screenshots")
        resource = create_resource()
        if not resource or wait_resource(resource, load(resource, str(root / "resource").encode())) != 3000:
            raise RuntimeError("Resource loading failed")
        # Register the same custom actions locally that the GUI obtains via Agent.
        sys.path.insert(0, str(root / "agent"))
        from main import register
        from native import ACTION_CALLBACK, Native
        agent_native = Native(root)
        if args.remote_agent:
            client_dll = ct.CDLL(str(native / "MaaAgentClient.dll"))
            make_client = bind(client_dll, "MaaAgentClientCreateV2", pointer, pointer)
            bind_client = bind(client_dll, "MaaAgentClientBindResource", ct.c_uint8, pointer, pointer)
            connect_client = bind(client_dll, "MaaAgentClientConnect", ct.c_uint8, pointer)
            disconnect_client = bind(client_dll, "MaaAgentClientDisconnect", ct.c_uint8, pointer)
            destroy_client = bind(client_dll, "MaaAgentClientDestroy", None, pointer)
            set_string = bind(fw, "MaaStringBufferSet", ct.c_uint8, pointer, string)
            identifier = "gt" + uuid.uuid4().hex[:12]
            buffer = create_string()
            try:
                set_string(buffer, identifier.encode())
                client = make_client(buffer)
            finally:
                destroy_string(buffer)
            if not client or not bind_client(client, resource):
                raise RuntimeError("Cannot create or bind Agent client")
            agent_log = (root / "dev/2026-10-14/remote-agent-server.log").open("w", encoding="utf-8")
            agent_process = subprocess.Popen([sys.executable, "-u", str(root / "agent/main.py"), identifier],
                                             cwd=root, stdout=agent_log, stderr=subprocess.STDOUT)
            if not connect_client(client):
                raise RuntimeError("Agent IPC connection failed")
            print("REMOTE AGENT CONNECTED", flush=True)
        else:
            register_custom = bind(fw, "MaaResourceRegisterCustomAction", ct.c_uint8,
                                   pointer, string, ACTION_CALLBACK, pointer)
            register(agent_native, lambda name, callback, data: register_custom(resource, name, callback, data))
        tasker = create_tasker()
        if not bind_resource(tasker, resource) or (controller and not bind_controller(tasker, controller)):
            raise RuntimeError("Tasker binding failed")
        add_sink(tasker, event, None)
        add_context_sink(tasker, event, None)
        override = args.override.read_bytes() if args.override else b"{}"
        if args.image:
            image = create_image()
            encoded = args.image.read_bytes()
            if not set_image(image, encoded, len(encoded)):
                raise RuntimeError("Cannot decode screenshot")
        result = 0
        for entry in args.entries:
            recognition_events.clear()
            if args.image:
                buffer = create_string()
                try:
                    if not get_node(resource, entry.encode(), buffer):
                        raise RuntimeError(f"Unknown node: {entry}")
                    node = json.loads(read_string(buffer))
                finally:
                    destroy_string(buffer)
                recognition = recognition_input(node["recognition"])
                task_id = post_recognition(tasker, recognition["type"].encode(),
                                          json.dumps(recognition["param"]).encode(), image)
            else:
                task_id = post_task(tasker, entry.encode(), override)
            deadline = time.monotonic() + args.limit
            while status(tasker, task_id) in (1000, 2000):
                if time.monotonic() > deadline:
                    wait_task(tasker, stop(tasker))
                    print(f"External time limit reached: {entry}", flush=True)
                    return 1
                time.sleep(0.2)
            task_status = status(tasker, task_id)
            print(f"RESULT {entry}: {task_status}", flush=True)
            passed = task_status == 3000
            if args.image:
                hit = any(label == "Node.Recognition.Succeeded" for label, _ in recognition_events)
                passed = hit != args.expect_miss
                print(f"RECOGNITION {entry}: hit={hit} expected={not args.expect_miss}", flush=True)
            if not passed:
                result = 1
                break
        return result
    finally:
        if client:
            disconnect_client(client)
            destroy_client(client)
        if agent_process:
            try:
                agent_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                agent_process.terminate()
                agent_process.wait(timeout=5)
        if agent_log:
            agent_log.close()
        if image:
            destroy_image(image)
        if tasker:
            destroy_tasker(tasker)
        if resource:
            destroy_resource(resource)
        if controller:
            destroy_controller(controller)
        dll_directory.close()


if __name__ == "__main__":
    raise SystemExit(main())
