import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingAssetTests(unittest.TestCase):
    def test_desktop_entry_uses_chinese_name_comment_and_icon(self):
        text = (ROOT / "packaging" / "kylin-gpu-control.desktop").read_text(encoding="utf-8")

        self.assertIn("Name=麒麟 GPU 兼容控制器", text)
        self.assertIn("Comment=管理指定 GLX 应用的 Mesa Zink 硬件加速白名单", text)
        self.assertIn("Icon=kylin-gpu-control", text)

    def test_svg_icon_asset_exists(self):
        text = (ROOT / "packaging" / "kylin-gpu-control.svg").read_text(encoding="utf-8")

        self.assertIn("<svg", text)
        self.assertIn("viewBox", text)

    def test_install_script_installs_gui_modules_and_icon(self):
        text = (ROOT / "install-gpu-control.sh").read_text(encoding="utf-8")

        for expected in [
            "app_catalog.py",
            "drirc_model.py",
            "kwin_model.py",
            "kylin_gpu_control.py",
            "kylin_gpu_control_apply.py",
            "kylin-gpu-control.svg",
            "desktop-file-validate",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_gui_source_uses_chinese_primary_labels(self):
        text = (ROOT / "src" / "kylin_gpu_control" / "kylin_gpu_control.py").read_text(encoding="utf-8")

        for expected in [
            "麒麟 GPU 兼容控制器",
            "GLX 状态",
            "桌面优化",
            "已安装应用",
            "Zink 白名单",
            "通过 Zink 启动",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        for legacy in ["GLX Status", "Run glxinfo -B", "Remove Selected", "Launch via Zink"]:
            with self.subTest(legacy=legacy):
                self.assertNotIn(legacy, text)


if __name__ == "__main__":
    unittest.main()
