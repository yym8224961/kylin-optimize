import tempfile
import unittest
from pathlib import Path

from src.kylin_gpu_control import drirc_model
from src.kylin_gpu_control import kylin_gpu_control_apply


class ApplyHelperTests(unittest.TestCase):
    def test_apply_add_and_remove_updates_file_and_creates_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "drirc"
            path.write_text("<driconf><device></device></driconf>\n", encoding="utf-8")

            kylin_gpu_control_apply.apply_change("add", "demo-app", path)
            self.assertEqual(drirc_model.parse_zink_apps(path.read_text(encoding="utf-8")), ["demo-app"])
            backups = list(Path(tmp).glob("drirc.bak.*"))
            self.assertEqual(len(backups), 1)

            kylin_gpu_control_apply.apply_change("remove", "demo-app", path)
            self.assertEqual(drirc_model.parse_zink_apps(path.read_text(encoding="utf-8")), [])
            backups = list(Path(tmp).glob("drirc.bak.*"))
            self.assertEqual(len(backups), 2)


if __name__ == "__main__":
    unittest.main()
