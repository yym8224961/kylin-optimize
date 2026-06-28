import unittest

from src.kylin_gpu_control import perf_model


class PerformanceModelTests(unittest.TestCase):
    def test_build_launch_command_uses_medium_and_big_cores_by_default(self):
        command = perf_model.build_launch_command(["/usr/local/bin/kylin-zink-run", "freecad"])

        self.assertEqual(command, ["taskset", "-c", "4-11", "/usr/local/bin/kylin-zink-run", "freecad"])

    def test_build_launch_command_can_target_big_cores_for_single_threaded_apps(self):
        command = perf_model.build_launch_command(["wps"], mode="big")

        self.assertEqual(command, ["taskset", "-c", "10-11", "wps"])

    def test_build_launch_command_rejects_realtime_as_default_user_mode(self):
        with self.assertRaisesRegex(ValueError, "实时调度"):
            perf_model.build_launch_command(["wps"], mode="realtime")

    def test_resolve_launch_command_falls_back_when_taskset_is_missing(self):
        command, accelerated = perf_model.resolve_launch_command(["wps"], mode="balanced", taskset_path=None)

        self.assertEqual(command, ["wps"])
        self.assertFalse(accelerated)

    def test_resolve_launch_command_reports_acceleration_when_taskset_exists(self):
        command, accelerated = perf_model.resolve_launch_command(["wps"], mode="balanced", taskset_path="/usr/bin/taskset")

        self.assertEqual(command, ["taskset", "-c", "4-11", "wps"])
        self.assertTrue(accelerated)

    def test_background_noise_patterns_cover_ai_kmre_and_vendor_apps(self):
        patterns = " ".join(perf_model.BACKGROUND_NOISE_PATTERNS)

        for expected in [
            "kylin-ai-runtime",
            "tritonserver",
            "milvus",
            "kylin-kmre",
            "com.huawei.pcmanager",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, patterns)

    def test_status_text_summarizes_kirin_9000c_core_layout(self):
        text = perf_model.cpu_layout_text()

        self.assertIn("小核 0-3", text)
        self.assertIn("中核 4-9", text)
        self.assertIn("大核 10-11", text)


if __name__ == "__main__":
    unittest.main()
