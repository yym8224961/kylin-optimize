import re
import xml.etree.ElementTree as ET
from xml.dom import minidom


EXECUTABLE_RE = re.compile(r"^[A-Za-z0-9._+-]+$")


def validate_executable(value):
    executable = (value or "").strip()
    if not EXECUTABLE_RE.fullmatch(executable):
        raise ValueError(
            "Executable must be a command name using only letters, numbers, '.', '_', '+', or '-'."
        )
    return executable


def parse_zink_apps(xml_text):
    root = _parse_root(xml_text)
    apps = []
    seen = set()
    for app in root.findall(".//application"):
        executable = app.get("executable")
        if not executable:
            continue
        for option in app.findall("option"):
            if option.get("name") == "dri_driver" and option.get("value") == "zink":
                if executable not in seen:
                    seen.add(executable)
                    apps.append(executable)
                break
    return apps


def ensure_zink_apps(xml_text, executables):
    root = _parse_root(xml_text)
    device = _first_device(root)
    existing = _apps_by_executable(device)

    for raw in executables:
        executable = validate_executable(raw)
        app = existing.get(executable)
        if app is None:
            app = ET.SubElement(device, "application", {"name": executable, "executable": executable})
            existing[executable] = app
        _set_zink_option(app)

    return _to_xml(root)


def remove_zink_app(xml_text, executable):
    executable = validate_executable(executable)
    root = _parse_root(xml_text)

    for device in root.findall("device"):
        for app in list(device.findall("application")):
            if app.get("executable") != executable:
                continue
            for option in list(app.findall("option")):
                if option.get("name") == "dri_driver" and option.get("value") == "zink":
                    app.remove(option)
            if len(list(app)) == 0:
                device.remove(app)

    return _to_xml(root)


def _parse_root(xml_text):
    text = (xml_text or "").strip()
    if not text:
        root = ET.Element("driconf")
        ET.SubElement(root, "device")
        return root
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        root = ET.Element("driconf")
        ET.SubElement(root, "device")
        return root
    if root.tag != "driconf":
        new_root = ET.Element("driconf")
        new_root.append(root)
        root = new_root
    if root.find("device") is None:
        ET.SubElement(root, "device")
    return root


def _first_device(root):
    device = root.find("device")
    if device is None:
        device = ET.SubElement(root, "device")
    return device


def _apps_by_executable(device):
    apps = {}
    for app in device.findall("application"):
        executable = app.get("executable")
        if executable and executable not in apps:
            apps[executable] = app
    return apps


def _set_zink_option(app):
    for option in app.findall("option"):
        if option.get("name") == "dri_driver":
            option.set("value", "zink")
            return
    ET.SubElement(app, "option", {"name": "dri_driver", "value": "zink"})


def _to_xml(root):
    raw = ET.tostring(root, encoding="unicode")
    parsed = minidom.parseString(raw)
    body = parsed.documentElement.toprettyxml(indent="  ")
    lines = [line for line in body.splitlines() if line.strip()]
    return '<?xml version="1.0" standalone="yes"?>\n' + "\n".join(lines) + "\n"
