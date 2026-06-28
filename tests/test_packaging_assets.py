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
            "kylin-zink-run",
            "kylin-gpu-control.svg",
            "desktop-file-validate",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_zink_launcher_asset_exists(self):
        text = (ROOT / "packaging" / "kylin-zink-run").read_text(encoding="utf-8")

        self.assertIn("MESA_LOADER_DRIVER_OVERRIDE", text)
        self.assertIn("VK_ICD_FILENAMES", text)
        self.assertIn("/usr/lib/aarch64-linux-gnu/maleoon", text)

    def test_gui_source_uses_chinese_primary_labels(self):
        text = (ROOT / "src" / "kylin_gpu_control" / "kylin_gpu_control.py").read_text(encoding="utf-8")

        for expected in [
            "麒麟 GPU 兼容控制器",
            "GLX 状态",
            "桌面优化",
            "屏幕刷新率",
            "已安装应用",
            "Zink 白名单",
            "通过 Zink 启动",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        for legacy in ["GLX Status", "Run glxinfo -B", "Remove Selected", "Launch via Zink"]:
            with self.subTest(legacy=legacy):
                self.assertNotIn(legacy, text)

    def test_repository_declares_gpl_license(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("GNU GENERAL PUBLIC LICENSE", license_text)
        self.assertIn("Version 3", license_text)
        self.assertIn("GPL-3.0-or-later", readme)

    def test_readme_lists_refresh_rate_dependency(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("| 依赖 | Python 3、PyQt5、mesa-utils、policykit、kscreen-doctor |", readme)

    def test_release_packaging_script_includes_gui_controller_assets(self):
        text = (ROOT / "scripts" / "package-release.sh").read_text(encoding="utf-8")

        for expected in [
            "LICENSE",
            "README.md",
            "install-gpu-control.sh",
            "src/kylin_gpu_control",
            "packaging",
            "kylin-gpu-control",
            "kylin-gpu-control-$VERSION.tar.gz",
            "COPYFILE_DISABLE",
            "--no-xattrs",
            "__pycache__",
            "*.pyc",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
