#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
LIB_DIR=/usr/local/lib/kylin-gpu-control
BIN_DIR=/usr/local/bin
APP_DIR=/usr/share/applications
ICON_DIR=/usr/share/icons/hicolor/scalable/apps
POLKIT_DIR=/usr/share/polkit-1/actions

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root: sudo ./install-gpu-control.sh" >&2
    exit 1
fi

install -d -m 0755 "$LIB_DIR" "$BIN_DIR" "$APP_DIR" "$ICON_DIR" "$POLKIT_DIR"

install -m 0644 "$ROOT_DIR/src/kylin_gpu_control/ai_model.py" "$LIB_DIR/ai_model.py"
install -m 0644 "$ROOT_DIR/src/kylin_gpu_control/app_catalog.py" "$LIB_DIR/app_catalog.py"
install -m 0644 "$ROOT_DIR/src/kylin_gpu_control/drirc_model.py" "$LIB_DIR/drirc_model.py"
install -m 0644 "$ROOT_DIR/src/kylin_gpu_control/kwin_model.py" "$LIB_DIR/kwin_model.py"
install -m 0644 "$ROOT_DIR/src/kylin_gpu_control/perf_model.py" "$LIB_DIR/perf_model.py"
install -m 0755 "$ROOT_DIR/src/kylin_gpu_control/kylin_gpu_control.py" "$LIB_DIR/kylin_gpu_control.py"
install -m 0755 "$ROOT_DIR/src/kylin_gpu_control/kylin_gpu_control_apply.py" "$LIB_DIR/kylin_gpu_control_apply.py"

install -m 0755 "$ROOT_DIR/packaging/kylin-gpu-control" "$BIN_DIR/kylin-gpu-control"
install -m 0755 "$ROOT_DIR/packaging/kylin-zink-run" "$BIN_DIR/kylin-zink-run"
install -m 0644 "$ROOT_DIR/packaging/kylin-gpu-control.desktop" "$APP_DIR/kylin-gpu-control.desktop"
install -m 0644 "$ROOT_DIR/packaging/kylin-gpu-control.svg" "$ICON_DIR/kylin-gpu-control.svg"
install -m 0644 "$ROOT_DIR/packaging/org.kylin.gpu-control.policy" "$POLKIT_DIR/org.kylin.gpu-control.policy"

python3 -m py_compile "$LIB_DIR"/*.py

if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$APP_DIR/kylin-gpu-control.desktop"
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR"
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi

echo "Installed kylin-gpu-control."
