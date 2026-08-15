import importlib.util
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
    fake_config.VAULT_DIR = Path(tempfile.gettempdir()) / "secureguard_test_vault"
    fake_config.USER_PASSWORD = "test-password"
    sys.modules["config"] = fake_config

    spec = importlib.util.spec_from_file_location("file_protector", ROOT / "file_protector.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DecoyBuilderTests(unittest.TestCase):
    def test_build_launcher_script_contains_trigger_and_path(self):
        module = load_file_protector_module()
        protector = module.FileProtector.__new__(module.FileProtector)

        content = protector._build_decoy_launcher_script(
            "C:/Users/Test/Documents/secret.txt",
            "C:/Windows/System32/pythonw.exe",
            "C:/SecureGuard/main.py",
        )

        self.assertIn("--trigger", content)
        self.assertIn("secret.txt", content)
        self.assertIn("pythonw.exe", content)


if __name__ == "__main__":
    unittest.main()
