import configparser
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from io import StringIO
from pathlib import Path


KWIN_CONFIG = Path.home() / ".config/ukui-kwinrc"
KWIN_DEST = "org.ukui.KWin"

RUNTIME_EFFECTS = (
    "magnifier",
    "zoom",
    "colorfilter",
    "touchclick",
    "touchmotionstreak",
    "kwin4_effect_eyeonscreen",
    "desktopgrid",
    "slide",
    "slidingpopups",
    "kwin4_effect_modalshake",
    "kwin4_effect_squashtablet",
    "kwin4_effect_fadedropdownmenu",
    "kwin4_effect_fadecascadingmenu",
    "kwin4_effect_squash",
    "kwin4_effect_frozenapp",
    "ubr",
    "stickyborder",
    "UKUI-KWin-Windows-View",
    "watermark",
    "kwin4_effect_scaletooltip",
    "kwin4_effect_dialogparent",
    "kwin4_effect_scaledesktop",
    "kwin4_effect_fadingpopups",
    "kwin4_effect_login",
    "kwin4_effect_sessionquit",
    "kwin4_effect_logout",
    "screenshot",
    "colorpicker",
    "screencopy",
    "kwin4_effect_scale",
)

PLUGIN_KEYS_TO_DISABLE = (
    "blurEnabled",
    "colorfilterEnabled",
    "colorpickerEnabled",
    "desktopchangeosdEnabled",
    "desktopgridEnabled",
    "flipswitchEnabled",
    "highlightwindowEnabled",
    "kwin4_effect_dialogparentEnabled",
    "kwin4_effect_eyeonscreenEnabled",
    "kwin4_effect_fadeEnabled",
    "kwin4_effect_fadecascadingmenuEnabled",
    "kwin4_effect_fadedropdownmenuEnabled",
    "kwin4_effect_fadingpopupsEnabled",
    "kwin4_effect_frozenappEnabled",
    "kwin4_effect_loginEnabled",
    "kwin4_effect_logoutEnabled",
    "kwin4_effect_maximizeEnabled",
    "kwin4_effect_modalshakeEnabled",
    "kwin4_effect_morphingpopupsEnabled",
    "kwin4_effect_scaleEnabled",
    "kwin4_effect_scaledesktopEnabled",
    "kwin4_effect_scaletooltipEnabled",
    "kwin4_effect_sessionquitEnabled",
    "kwin4_effect_squashEnabled",
    "kwin4_effect_squashtabletEnabled",
    "kwin4_effect_translucencyEnabled",
    "kwin4_effect_windowapertureEnabled",
    "magnifierEnabled",
    "presentwindowsEnabled",
    "screencopyEnabled",
    "screenshotEnabled",
    "shakecursorEnabled",
    "slideEnabled",
    "slidingpopupsEnabled",
    "startupfeedbackEnabled",
    "touchclickEnabled",
    "touchmotionstreakEnabled",
    "watermarkEnabled",
    "zoomEnabled",
)


@dataclass(frozen=True)
class KWinConfigSummary:
    animation_speed: str
    gl_smooth_scale: str
    mode: str
    disabled_managed_plugins: int
    managed_plugins: int


@dataclass(frozen=True)
class DisplayMode:
    id: str
    name: str
    width: int
    height: int
    refresh_rate: int


@dataclass(frozen=True)
class DisplayOutput:
    id: int
    name: str
    enabled: bool
    primary: bool
    current_mode_id: str
    modes: tuple

    @property
    def current_mode(self):
        for mode in self.modes:
            if mode.id == self.current_mode_id:
                return mode
        return None

    def same_resolution_modes(self):
        current = self.current_mode
        if current is None:
            return ()
        return tuple(
            mode
            for mode in self.modes
            if mode.width == current.width and mode.height == current.height
        )

    def find_refresh_mode(self, refresh_rate):
        target = int(refresh_rate)
        for mode in self.same_resolution_modes():
            if int(round(mode.refresh_rate)) == target:
                return mode
        return None


def parse_active_effects(dbus_output):
    return re.findall(r'string "([^"]+)"', dbus_output or "")


def parse_compositing_properties(dbus_output):
    properties = {}
    current_key = None
    for line in (dbus_output or "").splitlines():
        key_match = re.search(r'string "([^"]+)"', line)
        if key_match and "variant" not in line:
            current_key = key_match.group(1)
            continue
        if current_key is None or "variant" not in line:
            continue
        if "boolean true" in line:
            properties[current_key] = True
        elif "boolean false" in line:
            properties[current_key] = False
        else:
            value_match = re.search(r'string "([^"]*)"', line)
            if value_match:
                properties[current_key] = value_match.group(1)
        current_key = None
    return properties


def optimize_kwinrc_text(text):
    parser = _read_config(text)
    _ensure_section(parser, "Compositing")
    parser["Compositing"]["Enabled"] = "true"
    parser["Compositing"]["OpenGLIsUnsafe"] = "false"
    parser["Compositing"]["HiddenPreviews"] = "2"
    parser["Compositing"]["AnimationSpeed"] = "5"
    parser["Compositing"]["glSmoothScale"] = "0"

    _ensure_section(parser, "Plugins")
    for key in PLUGIN_KEYS_TO_DISABLE:
        parser["Plugins"][key] = "false"
    if "contrastEnabled" in parser["Plugins"]:
        parser["Plugins"]["contrastEnabled"] = "true"
    return _write_config(parser)


def summarize_kwinrc(text):
    parser = _read_config(text)
    compositing = parser["Compositing"] if parser.has_section("Compositing") else {}
    plugins = parser["Plugins"] if parser.has_section("Plugins") else {}
    mode = _find_first_option(parser, "Mode")
    disabled = sum(1 for key in PLUGIN_KEYS_TO_DISABLE if plugins.get(key, "").lower() == "false")
    return KWinConfigSummary(
        animation_speed=compositing.get("AnimationSpeed", ""),
        gl_smooth_scale=compositing.get("glSmoothScale", ""),
        mode=mode,
        disabled_managed_plugins=disabled,
        managed_plugins=len(PLUGIN_KEYS_TO_DISABLE),
    )


def parse_kscreen_json(text):
    payload = json.loads(text or "{}")
    displays = []
    for output in payload.get("outputs", []):
        modes = []
        for raw_mode in output.get("modes", []):
            size = raw_mode.get("size", {})
            modes.append(
                DisplayMode(
                    id=str(raw_mode.get("id", "")),
                    name=raw_mode.get("name", ""),
                    width=int(size.get("width", 0)),
                    height=int(size.get("height", 0)),
                    refresh_rate=int(round(float(raw_mode.get("refreshRate", 0)))),
                )
            )
        displays.append(
            DisplayOutput(
                id=int(output.get("id", 0)),
                name=output.get("name") or output.get("metadata", {}).get("name", ""),
                enabled=bool(output.get("enabled")),
                primary=bool(output.get("primary")),
                current_mode_id=str(output.get("currentModeId", "")),
                modes=tuple(modes),
            )
        )
    return displays


def kscreen_mode_command(display, mode):
    return ["kscreen-doctor", f"output.{display.name}.mode.{mode.id}"]


def current_displays():
    result = subprocess.run(
        ["kscreen-doctor", "-j"],
        env=_session_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=8,
        check=True,
    )
    return parse_kscreen_json(result.stdout)


def primary_display(displays=None):
    displays = tuple(displays if displays is not None else current_displays())
    for display in displays:
        if display.enabled and display.primary:
            return display
    for display in displays:
        if display.enabled:
            return display
    return None


def set_kwinrc_refresh_rate_text(text, output_name, refresh_rate):
    parser = _read_config(text)
    for section in parser.sections():
        if parser.get(section, "Name", fallback="") != output_name:
            continue
        mode = parser.get(section, "Mode", fallback="")
        updated_mode = _mode_with_refresh(mode, refresh_rate)
        if updated_mode:
            parser[section]["Mode"] = updated_mode
    return _write_config(parser)


def set_kwinrc_refresh_rate_file(output_name, refresh_rate, path=KWIN_CONFIG):
    path = Path(path)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    updated = set_kwinrc_refresh_rate_text(current, output_name, refresh_rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if path.exists():
        backup = path.with_name(path.name + ".bak." + time.strftime("%Y%m%d%H%M%S"))
        shutil.copy2(path, backup)
    path.write_text(updated, encoding="utf-8")
    return backup


def set_display_refresh_rate(refresh_rate, path=KWIN_CONFIG):
    display = primary_display()
    if display is None:
        raise RuntimeError("未找到已启用的显示器。")
    mode = display.find_refresh_mode(refresh_rate)
    if mode is None:
        raise RuntimeError(f"{display.name} 当前分辨率不支持 {refresh_rate}Hz。")
    subprocess.run(
        kscreen_mode_command(display, mode),
        env=_session_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=12,
        check=True,
    )
    backup = set_kwinrc_refresh_rate_file(display.name, refresh_rate, path)
    reconfigure_kwin()
    return backup


def refresh_status_text():
    try:
        display = primary_display()
    except Exception as exc:
        return f"刷新率状态读取失败：{exc}"
    if display is None:
        return "未找到已启用的显示器。"

    current = display.current_mode
    if current is None:
        return f"{display.name}：当前模式未知。"
    rates = ", ".join(f"{mode.refresh_rate}Hz" for mode in display.same_resolution_modes())
    return f"{display.name}：当前 {current.name}，同分辨率可选：{rates or '未知'}"


def optimize_kwinrc_file(path=KWIN_CONFIG):
    path = Path(path)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    updated = optimize_kwinrc_text(current)
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if path.exists():
        backup = path.with_name(path.name + ".bak." + time.strftime("%Y%m%d%H%M%S"))
        shutil.copy2(path, backup)
    path.write_text(updated, encoding="utf-8")
    return backup


def active_effects():
    result = _dbus_send(
        "/Effects",
        "org.freedesktop.DBus.Properties.Get",
        "string:org.ukui.kwin.Effects",
        "string:activeEffects",
    )
    return parse_active_effects(result.stdout)


def compositing_properties():
    result = _dbus_send(
        "/Compositor",
        "org.freedesktop.DBus.Properties.GetAll",
        "string:org.ukui.kwin.Compositing",
    )
    return parse_compositing_properties(result.stdout)


def reconfigure_kwin():
    return _dbus_send("/KWin", "org.ukui.KWin.reconfigure")


def apply_runtime_optimization():
    outputs = []
    for effect in RUNTIME_EFFECTS:
        result = _dbus_send(
            "/Effects",
            "org.ukui.kwin.Effects.unloadEffect",
            f"string:{effect}",
            check=False,
        )
        if result.stdout.strip() or result.stderr.strip():
            outputs.append((result.stdout + result.stderr).strip())
    _dbus_send("/Compositor", "org.ukui.kwin.Compositing.suspend", check=False)
    time.sleep(0.5)
    _dbus_send("/Compositor", "org.ukui.kwin.Compositing.resume", check=False)
    return "\n".join(output for output in outputs if output)


def desktop_status_text(path=KWIN_CONFIG):
    lines = []
    try:
        props = compositing_properties()
        lines.append(f"合成器：{'启用' if props.get('active') else '未启用'}")
        lines.append(f"合成类型：{props.get('compositingType', '未知')}")
        lines.append(f"OpenGL 异常：{'是' if props.get('openGLIsBroken') else '否'}")
    except Exception as exc:
        lines.append(f"合成器状态读取失败：{exc}")

    try:
        effects = active_effects()
        lines.append("活跃特效：" + (", ".join(effects) if effects else "无"))
    except Exception as exc:
        lines.append(f"活跃特效读取失败：{exc}")

    try:
        text = Path(path).read_text(encoding="utf-8")
        summary = summarize_kwinrc(text)
        lines.append(f"当前模式：{summary.mode or '未知'}")
        lines.append(f"动画速度：{summary.animation_speed or '未知'}")
        lines.append(f"缩放算法 glSmoothScale：{summary.gl_smooth_scale or '未知'}")
        lines.append(f"已禁用管理特效：{summary.disabled_managed_plugins}/{summary.managed_plugins}")
    except Exception as exc:
        lines.append(f"KWin 配置读取失败：{exc}")
    return "\n".join(lines)


def _mode_with_refresh(mode, refresh_rate):
    match = re.fullmatch(r"(\d+x\d+)_\d+", mode or "")
    if not match:
        return ""
    return f"{match.group(1)}_{int(refresh_rate) * 1000}"


def _read_config(text):
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    parser.read_string(text or "")
    return parser


def _write_config(parser):
    output = StringIO()
    parser.write(output, space_around_delimiters=False)
    return output.getvalue()


def _ensure_section(parser, section):
    if not parser.has_section(section):
        parser.add_section(section)


def _find_first_option(parser, option):
    for section in parser.sections():
        if parser.has_option(section, option):
            return parser.get(section, option)
    return ""


def _dbus_send(*args, check=True):
    command = ["dbus-send", "--session", f"--dest={KWIN_DEST}", "--print-reply", *args]
    return subprocess.run(
        command,
        env=_session_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=8,
        check=check,
    )


def _session_env():
    env = os.environ.copy()
    uid = os.getuid()
    if env.get("QT_QPA_PLATFORM") == "offscreen":
        env.pop("QT_QPA_PLATFORM", None)
    env.setdefault("DISPLAY", ":0")
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{uid}")
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{uid}/bus")
    return env
