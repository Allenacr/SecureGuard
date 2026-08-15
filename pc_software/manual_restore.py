import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from file_protector import FileProtector


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python manual_restore.py \"C:\\path\\to\\file.jpg\"")
        return 1

    file_path = os.path.normpath(sys.argv[1])
    protector = FileProtector()

    if not protector.is_protected(file_path):
        print(f"{file_path} is not currently protected. Nothing to restore.")
        return 0

    if protector.restore_file(file_path):
        print(f"Restored: {file_path}")
        return 0

    print(f"Restore failed: {file_path}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
