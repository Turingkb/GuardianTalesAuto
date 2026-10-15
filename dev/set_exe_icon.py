"""Embed an ICO in the Windows apphost without changing its .NET assembly name."""

import argparse
import ctypes as ct
from ctypes import wintypes as wt
from datetime import datetime
from pathlib import Path
import shutil
import struct
import tempfile


ROOT = Path(__file__).resolve().parents[1]
RT_ICON, RT_GROUP_ICON = 3, 14
NAME_CALLBACK = ct.WINFUNCTYPE(wt.BOOL, wt.HMODULE, ct.c_void_p, ct.c_void_p, ct.c_ssize_t)
LANG_CALLBACK = ct.WINFUNCTYPE(wt.BOOL, wt.HMODULE, ct.c_void_p, ct.c_void_p, wt.WORD, ct.c_ssize_t)


def resource_name(value):
    return ct.c_void_p(value) if isinstance(value, int) else ct.cast(ct.c_wchar_p(value), ct.c_void_p)


def windows_api():
    api = ct.WinDLL("kernel32", use_last_error=True)
    declarations = {
        "LoadLibraryExW": (wt.HMODULE, [wt.LPCWSTR, wt.HANDLE, wt.DWORD]),
        "FreeLibrary": (wt.BOOL, [wt.HMODULE]),
        "EnumResourceNamesW": (wt.BOOL, [wt.HMODULE, ct.c_void_p, NAME_CALLBACK, ct.c_ssize_t]),
        "EnumResourceLanguagesW": (wt.BOOL, [wt.HMODULE, ct.c_void_p, ct.c_void_p, LANG_CALLBACK, ct.c_ssize_t]),
        "BeginUpdateResourceW": (wt.HANDLE, [wt.LPCWSTR, wt.BOOL]),
        "UpdateResourceW": (wt.BOOL, [wt.HANDLE, ct.c_void_p, ct.c_void_p, wt.WORD, ct.c_void_p, wt.DWORD]),
        "EndUpdateResourceW": (wt.BOOL, [wt.HANDLE, wt.BOOL]),
        "FindResourceExW": (ct.c_void_p, [wt.HMODULE, ct.c_void_p, ct.c_void_p, wt.WORD]),
        "SizeofResource": (wt.DWORD, [wt.HMODULE, ct.c_void_p]),
        "LoadResource": (ct.c_void_p, [wt.HMODULE, ct.c_void_p]),
        "LockResource": (ct.c_void_p, [ct.c_void_p]),
    }
    for name, (result, arguments) in declarations.items():
        function = getattr(api, name)
        function.restype, function.argtypes = result, arguments
    return api


def icon_groups(api, executable: Path) -> list[tuple[int | str, list[int]]]:
    module = api.LoadLibraryExW(str(executable), None, 0x22)
    if not module:
        raise ct.WinError(ct.get_last_error())
    names, groups = [], []

    @NAME_CALLBACK
    def collect_name(_module, _kind, name, _data):
        names.append(name if name <= 65535 else ct.wstring_at(name))
        return True

    try:
        if not api.EnumResourceNamesW(module, resource_name(RT_GROUP_ICON), collect_name, 0):
            raise ct.WinError(ct.get_last_error())
        for name in names:
            languages = []

            @LANG_CALLBACK
            def collect_language(_module, _kind, _name, language, _data):
                languages.append(language)
                return True

            if not api.EnumResourceLanguagesW(module, resource_name(RT_GROUP_ICON),
                                             resource_name(name), collect_language, 0):
                raise ct.WinError(ct.get_last_error())
            groups.append((name, languages))
        return groups
    finally:
        api.FreeLibrary(module)


def ico_resources(icon: Path) -> tuple[bytes, list[bytes]]:
    data = icon.read_bytes()
    reserved, kind, count = struct.unpack_from("<HHH", data)
    if reserved != 0 or kind != 1 or not 1 <= count <= 256 or len(data) < 6 + count * 16:
        raise ValueError("Invalid ICO directory")
    group, images = bytearray(struct.pack("<HHH", 0, 1, count)), []
    for index in range(count):
        width, height, colors, unused, planes, depth, size, offset = struct.unpack_from("<BBBBHHII", data, 6 + index * 16)
        if size == 0 or offset < 6 + count * 16 or offset + size > len(data):
            raise ValueError("ICO image is outside the file")
        group.extend(struct.pack("<BBBBHHIH", width, height, colors, unused, planes, depth, size, index + 1))
        images.append(data[offset:offset + size])
    return bytes(group), images


def embed_icon(executable: Path, icon: Path) -> Path:
    executable, icon = executable.resolve(strict=True), icon.resolve(strict=True)
    group, images = ico_resources(icon)
    api = windows_api()
    groups = icon_groups(api, executable)
    if not groups:
        raise ValueError("Executable has no icon groups")
    backup_dir = ROOT / "backup"
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / f"{executable.stem}-before-icon-{datetime.now():%Y%m%d-%H%M%S-%f}.exe"
    shutil.copy2(executable, backup)
    # Patch a sibling copy first. A failure leaves the original executable intact.
    with tempfile.NamedTemporaryFile(prefix=".GTAssistant-icon-", suffix=".exe", dir=executable.parent, delete=False) as file:
        temporary = Path(file.name)
    handle = None
    try:
        shutil.copy2(executable, temporary)
        handle = api.BeginUpdateResourceW(str(temporary), False)
        if not handle:
            raise ct.WinError(ct.get_last_error())

        def update(kind, name, language, payload):
            buffer = ct.create_string_buffer(payload)
            if not api.UpdateResourceW(handle, resource_name(kind), resource_name(name), language, buffer, len(payload)):
                raise ct.WinError(ct.get_last_error())

        for language in {language for _, languages in groups for language in languages}:
            for index, image in enumerate(images, 1):
                update(RT_ICON, index, language, image)
        for name, languages in groups:
            for language in languages:
                update(RT_GROUP_ICON, name, language, group)
        completed, handle = handle, None
        if not api.EndUpdateResourceW(completed, False):
            raise ct.WinError(ct.get_last_error())
        verify_icon(temporary, icon)
        temporary.replace(executable)
        return backup
    finally:
        if handle:
            api.EndUpdateResourceW(handle, True)
        temporary.unlink(missing_ok=True)


def verify_icon(executable: Path, icon: Path):
    group, images = ico_resources(icon)
    api = windows_api()
    groups = icon_groups(api, executable)
    module = api.LoadLibraryExW(str(executable), None, 0x22)
    if not module:
        raise ct.WinError(ct.get_last_error())
    try:
        for name, languages in groups:
            for language in languages:
                resources = [(RT_GROUP_ICON, name, group)] + [(RT_ICON, index, data) for index, data in enumerate(images, 1)]
                for kind, resource_id, expected in resources:
                    resource = api.FindResourceExW(module, resource_name(kind), resource_name(resource_id), language)
                    if not resource:
                        raise ct.WinError(ct.get_last_error())
                    size = api.SizeofResource(module, resource)
                    memory = api.LockResource(api.LoadResource(module, resource))
                    if not memory or ct.string_at(memory, size) != expected:
                        raise ValueError(f"Embedded icon mismatch: resource {kind}/{resource_id}, language {language}")
    finally:
        api.FreeLibrary(module)
    if not groups:
        raise ValueError("Executable has no icon groups")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=ROOT / "GTAssistant.exe")
    parser.add_argument("--icon", type=Path, default=ROOT / "logo-v2.ico")
    parser.add_argument("--verify", action="store_true", help="Verify embedded resources without changing the EXE")
    args = parser.parse_args()
    if args.verify:
        verify_icon(args.exe.resolve(strict=True), args.icon.resolve(strict=True))
        print("All embedded icon sizes match the selected ICO")
        return
    backup = embed_icon(args.exe, args.icon)
    print(f"Embedded icon: {args.exe.name}; backup: {backup}")


if __name__ == "__main__":
    main()
