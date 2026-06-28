import unittest

from src.kylin_gpu_control import drirc_model


SAMPLE = """<?xml version="1.0" standalone="yes"?>
<driconf>
  <device>
    <application name="glxinfo" executable="glxinfo">
      <option name="dri_driver" value="zink"/>
    </application>
    <application name="other" executable="otherapp">
      <option name="vblank_mode" value="0"/>
    </application>
  </device>
</driconf>
"""


class DrircModelTests(unittest.TestCase):
    def test_parse_zink_apps_returns_executables_with_zink_driver(self):
        self.assertEqual(drirc_model.parse_zink_apps(SAMPLE), ["glxinfo"])

    def test_ensure_zink_apps_adds_missing_entry_and_keeps_existing_options(self):
        updated = drirc_model.ensure_zink_apps(SAMPLE, ["glxdemo"])

        self.assertIn('executable="glxdemo"', updated)
        self.assertIn('name="dri_driver" value="zink"', updated)
        self.assertIn('executable="otherapp"', updated)
        self.assertIn('name="vblank_mode" value="0"', updated)
        self.assertEqual(drirc_model.parse_zink_apps(updated), ["glxinfo", "glxdemo"])

    def test_remove_zink_app_removes_only_zink_option(self):
        updated = drirc_model.remove_zink_app(SAMPLE, "glxinfo")

        self.assertNotIn('executable="glxinfo"', updated)
        self.assertIn('executable="otherapp"', updated)
        self.assertIn('name="vblank_mode" value="0"', updated)
        self.assertEqual(drirc_model.parse_zink_apps(updated), [])

    def test_validate_executable_rejects_shell_fragments_and_paths(self):
        for value in ["", "../glxinfo", "/usr/bin/glxinfo", "bad;rm", "bad app"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    drirc_model.validate_executable(value)

    def test_validate_executable_accepts_common_desktop_names(self):
        for value in ["glxinfo", "chromium-browser", "org.example.App", "app_1"]:
            with self.subTest(value=value):
                self.assertEqual(drirc_model.validate_executable(value), value)


if __name__ == "__main__":
    unittest.main()
