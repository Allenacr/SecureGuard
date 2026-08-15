import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_photo_capture_module():
    fake_config = types.ModuleType("config")
    fake_config.DATA_DIR = Path(tempfile.gettempdir()) / "secureguard_test_data"
    sys.modules["config"] = fake_config

    spec = importlib.util.spec_from_file_location("photo_capture", ROOT / "photo_capture.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PhotoCaptureMediaTests(unittest.TestCase):
    def test_build_media_paths_use_distinct_extensions(self):
        module = load_photo_capture_module()
        capture = module.PhotoCapture.__new__(module.PhotoCapture)
        capture.photos_dir = Path(tempfile.gettempdir()) / "secureguard_test_media"

        photo_path = capture._build_media_path("photo")
        video_path = capture._build_media_path("video")

        self.assertTrue(str(photo_path).endswith(".jpg"))
        self.assertTrue(str(video_path).endswith(".mp4"))
        self.assertNotEqual(photo_path, video_path)


if __name__ == "__main__":
    unittest.main()
