#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    from . import drirc_model
except ImportError:
    import drirc_model


DEFAULT_DRIRC = Path("/etc/drirc")


def apply_change(action, executable, drirc_path=DEFAULT_DRIRC):
    path = Path(drirc_path)
    executable = drirc_model.validate_executable(executable)
    current = path.read_text(encoding="utf-8") if path.exists() else ""

    if action == "add":
        updated = drirc_model.ensure_zink_apps(current, [executable])
    elif action == "remove":
        updated = drirc_model.remove_zink_app(current, executable)
    else:
        raise ValueError(f"Unsupported action: {action}")

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(path.name + ".bak." + datetime.now().strftime("%Y%m%d%H%M%S%f"))
        shutil.copy2(path, backup)

    tmp_path = path.with_name(path.name + ".tmp." + str(os.getpid()))
    tmp_path.write_text(updated, encoding="utf-8")
    os.chmod(tmp_path, 0o644)
    os.replace(tmp_path, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Apply Kylin GPU drirc whitelist changes.")
    parser.add_argument("action", choices=["add", "remove"])
    parser.add_argument("executable")
    parser.add_argument("--drirc", default=str(DEFAULT_DRIRC))
    args = parser.parse_args(argv)

    try:
        apply_change(args.action, args.executable, Path(args.drirc))
    except Exception as exc:
        print(f"Failed to update drirc: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
