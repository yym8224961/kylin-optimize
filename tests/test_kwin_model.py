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


if __name__ == "__main__":
    unittest.main()
