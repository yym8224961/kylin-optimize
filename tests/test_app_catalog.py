import tempfile
import unittest
from pathlib import Path

from src.kylin_gpu_control import app_catalog


class AppCatalogTests(unittest.TestCase):
    def test_parse_entry_prefers_chinese_name_and_extracts_basename(self):
        text = """[Desktop Entry]
Type=Application
Name=FreeCAD
Name[zh_CN]=FreeCAD 建模
Comment=Parametric modeler
Exec=/usr/bin/freecad %F
Icon=freecad
Categories=Graphics;Engineering;
"""

        app = app_catalog.parse_desktop_entry(text, Path("/usr/share/applications/freecad.desktop"))

        self.assertEqual(app.name, "FreeCAD 建模")
        self.assertEqual(app.executable, "freecad")
        self.assertEqual(app.desktop_file, Path("/usr/share/applications/freecad.desktop"))
        self.assertEqual(app.comment, "Parametric modeler")

    def test_parse_entry_ignores_hidden_no_display_and_non_app_entries(self):
        for text in [
            "[Desktop Entry]\nType=Link\nName=Docs\nExec=xdg-open https://example.com\n",
            "[Desktop Entry]\nType=Application\nNoDisplay=true\nName=Hidden\nExec=hidden\n",
            "[Desktop Entry]\nType=Application\nHidden=true\nName=Gone\nExec=gone\n",
        ]:
            with self.subTest(text=text):
                self.assertIsNone(app_catalog.parse_desktop_entry(text, Path("sample.desktop")))

    def test_extract_executable_handles_env_wrappers_and_desktop_field_codes(self):
        self.assertEqual(
            app_catalog.extract_executable("env MESA_LOADER_DRIVER_OVERRIDE=zink /opt/Foo/bin/foo %U"),
            "foo",
        )
        self.assertEqual(app_catalog.extract_executable("org.example.App --new-window %u"), "org.example.App")

    def test_load_desktop_apps_scans_directories_sorts_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "z.desktop").write_text(
                "[Desktop Entry]\nType=Application\nName=Zeta\nExec=/usr/bin/zeta %F\n",
                encoding="utf-8",
            )
            (root / "a.desktop").write_text(
                "[Desktop Entry]\nType=Application\nName=Alpha\nExec=alpha\n",
                encoding="utf-8",
            )
            (root / "duplicate.desktop").write_text(
                "[Desktop Entry]\nType=Application\nName=Alpha Copy\nExec=alpha %U\n",
                encoding="utf-8",
            )

            apps = app_catalog.load_desktop_apps([root])

        self.assertEqual([app.name for app in apps], ["Alpha", "Zeta"])
        self.assertEqual([app.executable for app in apps], ["alpha", "zeta"])


if __name__ == "__main__":
    unittest.main()
