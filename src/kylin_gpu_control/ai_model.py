import os
import signal
import shutil
import subprocess
import time
from pathlib import Path


USER_SERVICES = (
    "kylin-ai-document-qa-service.service",
    "kylin-ai-document-service.service",
    "milvus-lite.service",
)

AUTOSTART_DESKTOP_FILES = (
    "tritonserver.desktop",
    "kylin-ai-runtime.desktop",
)

AUTOSTART_PROCESS_PATTERNS = (
    "tritonserver",
    "kylin-ai-runtime",
)
AUTOSTART_PROCESS_NAMES = AUTOSTART_PROCESS_PATTERNS
AUTOSTART_OVERRIDE_MARKER = "X-KylinGpuControl-Managed=true"
AUTOSTART_BACKUP_SUFFIX = ".kylin-gpu-control.bak"
KYLIN_AI_TRITON_HINTS = (
    "/usr/share/kylin-ai",
    "/usr/share/kylin-ai-python-env",
    "--model-repository=/usr/share/kylin-ai/model-repository",
)


def user_service_command(action):
    if action not in ("mask", "unmask", "start"):
        raise ValueError(f"不支持的 Kylin AI 服务操作：{action}")
    command = ["systemctl", "--user", action]
    if action == "mask":
        command.append("--now")
    return [*command, *USER_SERVICES]


def restore_service_commands():
    return user_service_command("unmask"), user_service_command("start")


def session_env(uid=None):
    uid = os.getuid() if uid is None else uid
    env = os.environ.copy()
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{uid}")
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{uid}/bus")
    return env


def write_autostart_overrides(home=None):
    home = Path.home() if home is None else Path(home)
    autostart_dir = home / ".config" / "autostart"
    autostart_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name in AUTOSTART_DESKTOP_FILES:
        path = autostart_dir / name
        backup = _autostart_backup_path(path)
        if path.exists() and not _is_tool_owned_override(path) and not backup.exists():
            shutil.copy2(path, backup)
        display_name = "TritonServer" if name == "tritonserver.desktop" else "Kylin AI Runtime"
        path.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={display_name}\n"
            "Hidden=true\n"
            f"{AUTOSTART_OVERRIDE_MARKER}\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


def remove_autostart_overrides(home=None):
    home = Path.home() if home is None else Path(home)
    removed = []
    for name in AUTOSTART_DESKTOP_FILES:
        path = home / ".config" / "autostart" / name
        backup = _autostart_backup_path(path)
        if path.exists() and not _is_tool_owned_override(path):
            continue
        if backup.exists():
            backup.replace(path)
            removed.append(path)
        elif path.exists():
            path.unlink()
            removed.append(path)
    return removed


def disable_ai():
    write_autostart_overrides()
    service_result = subprocess.run(
        user_service_command("mask"),
        env=session_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    stop_autostart_processes()
    return service_result


def restore_ai():
    remove_autostart_overrides()
    unmask = subprocess.run(
        user_service_command("unmask"),
        env=session_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if unmask.returncode != 0:
        return unmask
    return subprocess.run(
        user_service_command("start"),
        env=session_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def status_text():
    lines = ["麒麟 AI 组件："]
    for service in USER_SERVICES:
        lines.append(f"{service}：{_systemctl_value('is-active', service)} / {_systemctl_value('is-enabled', service)}")
    for name in AUTOSTART_DESKTOP_FILES:
        override = Path.home() / ".config" / "autostart" / name
        lines.append(f"{name}：{'已禁用自启' if override.exists() else '跟随系统自启'}")
    return "\n".join(lines)


def stop_autostart_processes(attempts=3, delay=0.4):
    for index in range(attempts):
        for pid in _autostart_process_pids():
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except PermissionError:
                pass
        if index + 1 < attempts:
            time.sleep(delay)


def _autostart_process_pids(uid=None, proc_root=Path("/proc")):
    uid = os.getuid() if uid is None else uid
    pids = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == os.getpid():
            continue
        try:
            status = (entry / "status").read_text(encoding="utf-8", errors="ignore")
            if not _status_has_uid(status, uid):
                continue
            comm = (entry / "comm").read_text(encoding="utf-8", errors="ignore").strip()
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "ignore")
        except OSError:
            continue
        if _is_kylin_ai_autostart_process(comm, cmdline):
            pids.append(pid)
    return pids


def _status_has_uid(status, uid):
    for line in status.splitlines():
        if not line.startswith("Uid:"):
            continue
        fields = line.split()
        return len(fields) > 1 and fields[1] == str(uid)
    return False


def _cmdline_process_names(cmdline):
    parts = [Path(part).name for part in cmdline.split() if part]
    return parts


def _is_kylin_ai_autostart_process(comm, cmdline):
    names = [comm, *_cmdline_process_names(cmdline)]
    if "kylin-ai-runtime" in names:
        return True
    if "tritonserver" not in names:
        return False
    return any(hint in cmdline for hint in KYLIN_AI_TRITON_HINTS)


def _autostart_backup_path(path):
    return path.with_name(f"{path.name}{AUTOSTART_BACKUP_SUFFIX}")


def _is_tool_owned_override(path):
    try:
        return AUTOSTART_OVERRIDE_MARKER in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def _systemctl_value(action, service):
    result = subprocess.run(
        ["systemctl", "--user", action, service],
        env=session_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    value = (result.stdout or result.stderr).strip()
    return value or "未知"
