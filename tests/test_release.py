import json
import tempfile
import unittest
from pathlib import Path

from build_release import sha256, verify_release


class ReleaseTests(unittest.TestCase):
    def test_source_manifest_tag_and_binary_must_agree(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "source.pyw"
            source.write_text('APP_VERSION = "9.8.7"', encoding="utf-8")
            executable = directory / "DesktopTools.exe"
            executable.write_bytes(b"MZtest")
            manifest = {"version": "9.8.7", "size": 6, "sha256": sha256(executable)}
            index = directory / "update.json"
            index.write_text(json.dumps(manifest), encoding="utf-8")
            verify_release(directory, source=source, tag="v9.8.7")
            for changed in ({"version": "9.8.6"}, {"size": 7}, {"sha256": "0" * 64}):
                with self.subTest(changed=changed):
                    index.write_text(json.dumps(manifest | changed), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        verify_release(directory, source=source)
            index.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_release(directory, source=source, tag="v9.8.6")


if __name__ == "__main__":
    unittest.main()
