import importlib.util
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_file_protector_module():
    fake_config = types.ModuleType("config")
    fake_config.VAULT_DIR = Path(tempfile.gettempdir()) / "secureguard_test_vault_shutdown"
    fake_config.USER_PASSWORD = "test-password"
    sys.modules["config"] = fake_config

    shutil.rmtree(fake_config.VAULT_DIR, ignore_errors=True)
    fake_config.VAULT_DIR.mkdir(parents=True, exist_ok=True)

    spec = importlib.util.spec_from_file_location("file_protector", ROOT / "file_protector.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ShutdownRestorationTests(unittest.TestCase):
    def test_restore_protected_files_restores_file_and_removes_decoy(self):
        module = load_file_protector_module()
        protector = module.FileProtector()

        def fake_create_decoy(self, original_path):
            if os.path.exists(original_path):
                os.remove(original_path)
            with open(original_path, "w", encoding="utf-8") as f:
                f.write("decoy")

        protector._create_decoy = fake_create_decoy.__get__(protector, module.FileProtector)

        with tempfile.TemporaryDirectory() as tmpdir:
            original = Path(tmpdir) / "sample.jpg"
            original.write_bytes(b"secret-image")

            self.assertTrue(protector.protect_file(str(original)))
            self.assertTrue(original.exists())
            self.assertEqual(original.read_text(encoding="utf-8"), "decoy")
            self.assertTrue(protector.is_protected(str(original)))

            restored = protector.restore_protected_files([str(original)])

            self.assertEqual(restored, [str(original)])
            self.assertTrue(original.exists())
            self.assertEqual(original.read_bytes(), b"secret-image")
            self.assertFalse((Path(tmpdir) / "sample.jpg.cmd").exists())
            self.assertFalse((Path(tmpdir) / "sample.jpg.lnk").exists())


if __name__ == "__main__":
    unittest.main()
