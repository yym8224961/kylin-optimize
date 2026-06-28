import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

try:
    from . import drirc_model
except ImportError:
    import drirc_model


FIELD_CODE_RE = re.compile(r"%[fFuUdDnNickvm]")
LOCALE_KEYS = ("zh_CN", "zh", "zh_Hans")


@dataclass(frozen=True)
class DesktopApp:
    name: str
    executable: str
    desktop_file: Path
    comment: str = ""
    icon: str = ""


def desktop_application_dirs():
    directories = []
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        directories.append(Path(data_home) / "applications")
    else:
        directories.append(Path.home() / ".local/share/applications")

    data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
    for value in data_dirs.split(":"):
        if value:
            directories.append(Path(value) / "applications")
    return directories


def load_desktop_apps(directories=None):
    apps = []
    seen = set()
    for directory in directories or desktop_application_dirs():
        path = Path(directory)
        if not path.exists():
            continue
        for desktop_file in sorted(path.rglob("*.desktop")):
            try:
                app = parse_desktop_entry(desktop_file.read_text(encoding="utf-8"), desktop_file)
            except UnicodeDecodeError:
                app = parse_desktop_entry(desktop_file.read_text(errors="ignore"), desktop_file)
            except OSError:
                continue
            if app is None or app.executable in seen:
                continue
            seen.add(app.executable)
            apps.append(app)
    return sorted(apps, key=lambda app: (app.name.casefold(), app.executable.casefold()))


def parse_desktop_entry(text, desktop_file):
    values = _parse_desktop_values(text)
    if values.get("Type") != "Application":
        return None
    if _truthy(values.get("Hidden")) or _truthy(values.get("NoDisplay")):
        return None

    executable = extract_executable(values.get("Exec", ""))
    if not executable:
        return None
    try:
        executable = drirc_model.validate_executable(executable)
    except ValueError:
        return None

    name = _localized_value(values, "Name") or executable
    comment = _localized_value(values, "Comment") or ""
    icon = values.get("Icon", "")
    return DesktopApp(name=name, executable=executable, desktop_file=Path(desktop_file), comment=comment, icon=icon)


def extract_executable(exec_line):
    try:
        tokens = shlex.split(exec_line or "")
    except ValueError:
        return ""
    tokens = [_strip_field_codes(token) for token in tokens]
    tokens = [token for token in tokens if token]
    if not tokens:
        return ""

    command = _command_after_env(tokens)
    return Path(command).name if command else ""


def _parse_desktop_values(text):
    values = {}
    section = None
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section != "Desktop Entry" or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _localized_value(values, key):
    for locale in LOCALE_KEYS:
        value = values.get(f"{key}[{locale}]")
        if value:
            return value
    return values.get(key, "")


def _truthy(value):
    return (value or "").strip().lower() == "true"


def _strip_field_codes(token):
    placeholder = "\0"
    token = token.replace("%%", placeholder)
    token = FIELD_CODE_RE.sub("", token)
    return token.replace(placeholder, "%").strip()


def _command_after_env(tokens):
    command = tokens[0]
    if Path(command).name != "env":
        return command

    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            index += 1
            break
        if token in ("-i", "-0"):
            index += 1
            continue
        if token == "-u":
            index += 2
            continue
        if token.startswith("-u") and len(token) > 2:
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        if _looks_like_env_assignment(token):
            index += 1
            continue
        break
    return tokens[index] if index < len(tokens) else ""


def _looks_like_env_assignment(token):
    if "=" not in token or token.startswith("="):
        return False
    name = token.split("=", 1)[0]
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name))
