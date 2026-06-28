import os
import unittest

from src.kylin_gpu_control import kwin_model


ACTIVE_EFFECTS_DBUS = """
method return time=1 sender=:1.6 -> destination=:1.660 serial=1 reply_serial=2
   variant       array [
         string "stickyborder"
         string "ubr"
         string "contrast"
      ]
"""


COMPOSITING_DBUS = """
method return time=1 sender=:1.6 -> destination=:1.661 serial=1 reply_serial=2
   array [
      dict entry(
         string "active"
         variant             boolean true
      )
      dict entry(
         string "compositingType"
         variant             string "gles"
      )
      dict entry(
         string "openGLIsBroken"
         variant             boolean false
      )
   ]
"""


KWINRC = """
[Compositing]
AnimationSpeed=2
Enabled=true
glSmoothScale=2

[DrmOutputs]
Mode=2880x1920_60000
Name=DP-1

[Plugins]
blurEnabled=true
contrastEnabled=true
slideEnabled=true
"""


KSCREEN_JSON = """
{
    "outputs": [
        {
            "currentModeId": "0",
            "enabled": true,
            "id": 1,
            "modes": [
                {
                    "id": "0",
                    "name": "2880x1920@60",
                    "refreshRate": 60,
                    "size": {"height": 1920, "width": 2880}
                },
                {
                    "id": "1",
                    "name": "2880x1920@120",
                    "refreshRate": 120,
                    "size": {"height": 1920, "width": 2880}
                }
            ],
            "name": "DP-1",
            "primary": true,
            "size": {"height": 1920, "width": 2880}
        }
    ]
}
"""


class KWinModelTests(unittest.TestCase):
    def test_parse_active_effects_from_dbus_output(self):
        self.assertEqual(
            kwin_model.parse_active_effects(ACTIVE_EFFECTS_DBUS),
            ["stickyborder", "ubr", "contrast"],
        )

    def test_parse_compositing_properties_from_dbus_output(self):
        self.assertEqual(
            kwin_model.parse_compositing_properties(COMPOSITING_DBUS),
            {
                "active": True,
                "compositingType": "gles",
                "openGLIsBroken": False,
            },
        )

    def test_optimize_kwinrc_preserves_current_mode_and_disables_effects(self):
        updated = kwin_model.optimize_kwinrc_text(KWINRC)

        self.assertIn("AnimationSpeed=5", updated)
        self.assertIn("glSmoothScale=0", updated)
        self.assertIn("Mode=2880x1920_60000", updated)
        self.assertIn("blurEnabled=false", updated)
        self.assertIn("slideEnabled=false", updated)
        self.assertIn("contrastEnabled=true", updated)
        self.assertNotIn("Mode=2880x1920_120000", updated)

    def test_summarize_kwinrc_reports_refresh_mode_and_optimization_values(self):
        summary = kwin_model.summarize_kwinrc(kwin_model.optimize_kwinrc_text(KWINRC))

        self.assertEqual(summary.mode, "2880x1920_60000")
        self.assertEqual(summary.animation_speed, "5")
        self.assertEqual(summary.gl_smooth_scale, "0")
        self.assertGreaterEqual(summary.disabled_managed_plugins, 2)

    def test_parse_kscreen_json_reports_current_and_supported_refresh_rates(self):
        displays = kwin_model.parse_kscreen_json(KSCREEN_JSON)

        self.assertEqual(len(displays), 1)
        self.assertEqual(displays[0].name, "DP-1")
        self.assertEqual(displays[0].current_mode.name, "2880x1920@60")
        self.assertEqual([mode.refresh_rate for mode in displays[0].same_resolution_modes()], [60, 120])

    def test_find_refresh_mode_returns_mode_for_same_resolution(self):
        display = kwin_model.parse_kscreen_json(KSCREEN_JSON)[0]

        mode = display.find_refresh_mode(120)

        self.assertEqual(mode.id, "1")
        self.assertEqual(mode.name, "2880x1920@120")

    def test_kscreen_mode_command_targets_output_and_mode_id(self):
        display = kwin_model.parse_kscreen_json(KSCREEN_JSON)[0]
        mode = display.find_refresh_mode(120)

        self.assertEqual(
            kwin_model.kscreen_mode_command(display, mode),
            ["kscreen-doctor", "output.DP-1.mode.1"],
        )

    def test_set_kwinrc_refresh_rate_updates_all_drm_output_modes(self):
        text = """
[DrmOutputs]
Mode=2880x1920_60000
Name=DP-1

[DrmOutputs][abc][abc]
Mode=2880x1920_60000
Name=DP-1
"""

        updated = kwin_model.set_kwinrc_refresh_rate_text(text, "DP-1", 120)

        self.assertIn("Mode=2880x1920_120000", updated)
        self.assertNotIn("Mode=2880x1920_60000", updated)

    def test_session_env_removes_offscreen_qt_backend_for_kscreen_tools(self):
        old_value = os.environ.get("QT_QPA_PLATFORM")
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        try:
            env = kwin_model._session_env()
        finally:
            if old_value is None:
                os.environ.pop("QT_QPA_PLATFORM", None)
            else:
                os.environ["QT_QPA_PLATFORM"] = old_value

        self.assertNotIn("QT_QPA_PLATFORM", env)


if __name__ == "__main__":
    unittest.main()
