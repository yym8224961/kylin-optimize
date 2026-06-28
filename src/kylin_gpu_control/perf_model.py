import os
import shutil
import subprocess


CPU_MODES = {
    "balanced": "4-11",
    "big": "10-11",
    "all": "0-11",
}

BACKGROUND_NOISE_PATTERNS = (
    "kylin-ai-runtime",
    "kylin-ai-document",
    "tritonserver",
    "milvus",
    "kylin-kmre",
    "com.huawei.pcmanager",
    "kylin-background-upgrade",
    "kylin-software-center-plugin",
    "ukui-search",
)


def build_launch_command(command, mode="balanced"):
    if mode == "realtime":
        raise ValueError("实时调度不适合作为默认用户态加速模式。")
    cpus = CPU_MODES.get(mode)
    if cpus is None:
        raise ValueError(f"未知 CPU 加速模式：{mode}")
    return ["taskset", "-c", cpus, *list(command)]


def resolve_launch_command(command, mode="balanced", taskset_path="auto"):
    if taskset_path == "auto":
        taskset_path = shutil.which("taskset")
    if not taskset_path:
        return list(command), False
    built = build_launch_command(command, mode)
    built[0] = "taskset"
    return built, True


def cpu_layout_text():
    return "\n".join(
        [
            "CPU 拓扑：Kirin 9000C 三集群",
            "小核 0-3：后台与轻负载",
            "中核 4-9：多线程前台应用",
            "大核 10-11：单线程与交互关键任务",
            "默认前台加速：绑定中核+大核（4-11），不使用实时调度。",
        ]
    )


def launch(command, mode="balanced", env=None):
    resolved, _accelerated = resolve_launch_command(command, mode)
    return subprocess.Popen(resolved, env=env or os.environ.copy())


def lower_background_noise(patterns=BACKGROUND_NOISE_PATTERNS, nice=10):
    changed = []
    for pattern in patterns:
        for pid in _pgrep(pattern):
            _run_best_effort(["renice", "-n", str(nice), "-p", str(pid)])
            _run_best_effort(["ionice", "-c", "3", "-p", str(pid)])
            changed.append((pattern, pid))
    return changed


def background_status_text():
    lines = ["后台降噪目标："]
    lines.extend(f"- {pattern}" for pattern in BACKGROUND_NOISE_PATTERNS)
    return "\n".join(lines)


def _pgrep(pattern):
    result = subprocess.run(
        ["pgrep", "-u", str(os.getuid()), "-f", pattern],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode not in (0, 1):
        return []
    return [int(line) for line in result.stdout.splitlines() if line.strip().isdigit()]


def _run_best_effort(command):
    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
