"""Protect archive boundaries, configuration privacy and prerequisite checks."""

import hashlib
import io
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import zipfile

import build_portable as package
import launch_gui
import migrate_gui_tasks


class PortablePackage(unittest.TestCase):
    def setUp(self):
        directory = Path(__file__).resolve().parent / "runtime"
        directory.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_archive_cannot_escape_destination_or_use_windows_streams(self):
        for name in ("../config.json", "/absolute", "C:/settings", "safe/../../escape", "safe\\..\\escape", "file:stream"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                package.destination(self.root, name)

    def test_symlink_archive_is_rejected_before_writing(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            info = zipfile.ZipInfo("link")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "../outside")
        with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive, self.assertRaises(ValueError):
            package.extract(archive, self.root, lambda name: name)
        self.assertFalse((self.root / "link").exists())

    def test_poisoned_cache_stops_without_executing_or_redownloading(self):
        (self.root / "input.zip").write_bytes(b"unexpected")
        component = {"file": "input.zip", "url": "https://github.com/example/archive.zip",
                     "sha256": hashlib.sha256(b"expected").hexdigest()}
        with patch.object(package.urllib.request, "urlopen") as network, self.assertRaises(ValueError):
            package.fetch(component, self.root)
        network.assert_not_called()

    def test_personal_configuration_cannot_enter_package(self):
        (self.root / "config").mkdir()
        (self.root / "config/default.json").write_text('{"device":"private"}')
        with self.assertRaises(ValueError):
            package.check_package(self.root)

    def test_missing_dotnet_gives_official_install_link(self):
        with patch.object(launch_gui, "find_dotnet", return_value=None), \
                patch.object(launch_gui.subprocess, "run") as run:
            problems = launch_gui.check_environment(self.root)
        self.assertTrue(any(launch_gui.DOTNET_URL in problem for problem in problems))
        run.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows startup integration")
    def test_gui_process_check_does_not_depend_on_powershell_in_path(self):
        with patch.dict(os.environ, {"PATH": ""}), \
                patch.object(migrate_gui_tasks.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="1")) as run:
            self.assertEqual(migrate_gui_tasks.main(), 0)
        executable = Path(run.call_args.args[0][0])
        self.assertTrue(executable.is_absolute())
        self.assertTrue(executable.is_file())


if __name__ == "__main__": unittest.main()
