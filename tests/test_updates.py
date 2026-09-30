import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktoptools import updates


class UpdateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.package = b"MZ" + b"test executable" * 100
        self.manifest = {
            "version": "10.0.0", "size": len(self.package),
            "sha256": hashlib.sha256(self.package).hexdigest(),
        }

    def test_valid_download_and_cache(self):
        requests = []
        def opener(request, *, timeout):
            requests.append(request)
            return io.BytesIO(json.dumps(self.manifest).encode() if request.full_url.endswith("json") else self.package)
        client = updates.UpdateClient(self.directory, opener=opener, app_version="9.0.0")
        latest = client.latest()
        destination = client.download(latest)
        self.assertEqual(destination.read_bytes(), self.package)
        self.assertEqual(client.download(latest), destination)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0].get_header("User-agent"), "DesktopTools/9.0.0")

    def test_corrupt_download_never_installed(self):
        for data in (b"<html>error</html>", self.package + b"extra", self.package[:-1], b"MZ" + b"x" * (len(self.package)-2)):
            with self.subTest(size=len(data)):
                client = updates.UpdateClient(self.directory, opener=lambda *args, **kwargs: io.BytesIO(data))
                with self.assertRaises(updates.UpdateError):
                    client.download(self.manifest)
                self.assertEqual(list(self.directory.iterdir()), [])

    def test_invalid_manifest_is_rejected(self):
        for changed in ({"size": True}, {"version": "../bad"}, {"sha256": "broken"}):
            client = updates.UpdateClient(self.directory, opener=lambda *args, **kwargs: io.BytesIO(json.dumps(self.manifest | changed).encode()))
            with self.assertRaises(updates.UpdateError):
                client.latest()

    def test_installer_result_is_logged(self):
        with patch.object(updates, "_install_staged_update", return_value=4):
            with self.assertLogs("desktoptools", level="ERROR") as captured:
                self.assertEqual(updates._apply_staged_update([]), 4)
        self.assertIn("exit code 4", captured.output[0])

    def test_verified_staged_update_replaces_target(self):
        staged = self.directory / "staged.exe"
        target = self.directory / "target.exe"
        staged.write_bytes(self.package)
        target.write_bytes(b"previous")
        with patch.object(updates.sys, "frozen", True, create=True), patch.object(updates.sys, "executable", str(staged)):
            result = updates._apply_staged_update([str(target), self.manifest["sha256"], "no-restart"])
        self.assertEqual(result, 0)
        self.assertEqual(target.read_bytes(), self.package)
        self.assertFalse(list(self.directory.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
