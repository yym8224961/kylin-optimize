import tempfile
import unittest
from pathlib import Path

from src.kylin_gpu_control import ai_model


class KylinAiModelTests(unittest.TestCase):
    def test_disable_command_masks_user_services_without_purging_packages(self):
        command = ai_model.user_service_command("mask")

        self.assertEqual(command[:4], ["systemctl", "--user", "mask", "--now"])
        self.assertIn("kylin-ai-document-qa-service.service", command)
        self.assertIn("kylin-ai-document-service.service", command)
        self.assertIn("milvus-lite.service", command)

    def test_restore_commands_unmask_then_start_user_services(self):
        unmask, start = ai_model.restore_service_commands()

        self.assertEqual(unmask[:3], ["systemctl", "--user", "unmask"])
        self.assertEqual(start[:3], ["systemctl", "--user", "start"])
        self.assertIn("milvus-lite.service", start)

    def test_autostart_overrides_disable_triton_and_runtime_for_current_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)

            written = ai_model.write_autostart_overrides(home)

            self.assertEqual(
                sorted(path.name for path in written),
                ["kylin-ai-runtime.desktop", "tritonserver.desktop"],
            )
            for path in written:
                self.assertIn("Hidden=true", path.read_text(encoding="utf-8"))

    def test_autostart_override_removal_restores_login_startup(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            ai_model.write_autostart_overrides(home)

            removed = ai_model.remove_autostart_overrides(home)

            self.assertEqual(len(removed), 2)
            self.assertFalse((home / ".config/autostart/tritonserver.desktop").exists())
            self.assertFalse((home / ".config/autostart/kylin-ai-runtime.desktop").exists())

    def test_autostart_override_restore_preserves_existing_user_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            autostart = home / ".config" / "autostart"
            autostart.mkdir(parents=True)
            user_file = autostart / "tritonserver.desktop"
            original = "[Desktop Entry]\nType=Application\nName=Custom Triton\nHidden=false\n"
            user_file.write_text(original, encoding="utf-8")

            ai_model.write_autostart_overrides(home)
            self.assertIn("Hidden=true", user_file.read_text(encoding="utf-8"))

            ai_model.remove_autostart_overrides(home)

            self.assertEqual(user_file.read_text(encoding="utf-8"), original)

    def test_autostart_override_removal_leaves_user_owned_file_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            autostart = home / ".config" / "autostart"
            autostart.mkdir(parents=True)
            user_file = autostart / "kylin-ai-runtime.desktop"
            original = "[Desktop Entry]\nType=Application\nName=User Runtime\nHidden=true\n"
            user_file.write_text(original, encoding="utf-8")

            removed = ai_model.remove_autostart_overrides(home)

            self.assertEqual(removed, [])
            self.assertEqual(user_file.read_text(encoding="utf-8"), original)

    def test_session_env_points_to_user_bus(self):
        env = ai_model.session_env(uid=1000)

        self.assertEqual(env["XDG_RUNTIME_DIR"], "/run/user/1000")
        self.assertEqual(env["DBUS_SESSION_BUS_ADDRESS"], "unix:path=/run/user/1000/bus")

    def test_runtime_process_patterns_match_exact_autostart_processes(self):
        patterns = ai_model.AUTOSTART_PROCESS_PATTERNS

        self.assertIn("kylin-ai-runtime", patterns)
        self.assertIn("tritonserver", patterns)

    def test_autostart_process_names_are_exact_process_targets(self):
        self.assertEqual(ai_model.AUTOSTART_PROCESS_NAMES, ("tritonserver", "kylin-ai-runtime"))

    def test_process_filter_matches_kylin_ai_triton_but_not_user_triton(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            self._write_proc_entry(
                proc,
                101,
                "tritonserver",
                ["/home/kylin/bin/tritonserver", "--model-repository=/home/kylin/models"],
            )
            self._write_proc_entry(
                proc,
                102,
                "bash",
                [
                    "/bin/bash",
                    "-c",
                    "source /usr/share/kylin-ai-python-env/python-env/bin/activate && "
                    "tritonserver --model-repository=/usr/share/kylin-ai/model-repository",
                ],
            )

            self.assertEqual(ai_model._autostart_process_pids(uid=1000, proc_root=proc), [102])

    def _write_proc_entry(self, proc, pid, comm, argv):
        entry = proc / str(pid)
        entry.mkdir()
        (entry / "status").write_text("Name:\ttest\nUid:\t1000\t1000\t1000\t1000\n", encoding="utf-8")
        (entry / "comm").write_text(f"{comm}\n", encoding="utf-8")
        (entry / "cmdline").write_bytes(b"\0".join(arg.encode("utf-8") for arg in argv) + b"\0")


if __name__ == "__main__":
    unittest.main()
