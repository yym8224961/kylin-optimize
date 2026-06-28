#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from . import app_catalog
    from . import drirc_model
    from . import kwin_model
except ImportError:
    import app_catalog
    import drirc_model
    import kwin_model


LOCAL_DRIRC = Path("/etc/drirc")
VENDOR_DRIRC = Path("/usr/share/drirc.d/01-hisi.conf")
HELPER = Path(__file__).with_name("kylin_gpu_control_apply.py")
ZINK_RUN = Path("/usr/local/bin/kylin-zink-run")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_entries = []
        self.setWindowTitle("麒麟 GPU 兼容控制器")
        self.setWindowIcon(QIcon.fromTheme("kylin-gpu-control"))
        self.resize(940, 860)
        self._build_ui()
        self.refresh_app_catalog()
        self.refresh_all()

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)

        status_box = QGroupBox("GLX 状态")
        status_layout = QVBoxLayout(status_box)
        self.status_output = QTextEdit()
        self.status_output.setReadOnly(True)
        self.status_output.setLineWrapMode(QTextEdit.NoWrap)
        status_layout.addWidget(self.status_output)

        status_buttons = QHBoxLayout()
        self.refresh_button = QPushButton("刷新")
        self.probe_button = QPushButton("检测 glxinfo -B")
        status_buttons.addWidget(self.refresh_button)
        status_buttons.addWidget(self.probe_button)
        status_buttons.addStretch(1)
        status_layout.addLayout(status_buttons)

        desktop_box = QGroupBox("桌面优化（KWin）")
        desktop_layout = QVBoxLayout(desktop_box)
        self.desktop_output = QTextEdit()
        self.desktop_output.setReadOnly(True)
        self.desktop_output.setMaximumHeight(150)
        desktop_layout.addWidget(self.desktop_output)

        desktop_buttons = QHBoxLayout()
        self.desktop_refresh_button = QPushButton("刷新桌面状态")
        self.desktop_apply_button = QPushButton("应用桌面流畅优化")
        self.desktop_reconfigure_button = QPushButton("重载 KWin")
        desktop_buttons.addWidget(self.desktop_refresh_button)
        desktop_buttons.addWidget(self.desktop_apply_button)
        desktop_buttons.addWidget(self.desktop_reconfigure_button)
        desktop_buttons.addStretch(1)
        desktop_layout.addLayout(desktop_buttons)

        refresh_box = QGroupBox("屏幕刷新率")
        refresh_layout = QVBoxLayout(refresh_box)
        self.refresh_rate_label = QLabel("")
        self.refresh_rate_label.setWordWrap(True)
        refresh_layout.addWidget(self.refresh_rate_label)

        refresh_buttons = QHBoxLayout()
        self.refresh_rate_refresh_button = QPushButton("刷新刷新率状态")
        self.refresh_rate_120_button = QPushButton("切换到 120Hz")
        self.refresh_rate_60_button = QPushButton("切换回 60Hz")
        refresh_buttons.addWidget(self.refresh_rate_refresh_button)
        refresh_buttons.addWidget(self.refresh_rate_120_button)
        refresh_buttons.addWidget(self.refresh_rate_60_button)
        refresh_buttons.addStretch(1)
        refresh_layout.addLayout(refresh_buttons)

        app_box = QGroupBox("已安装应用")
        app_layout = QGridLayout(app_box)
        app_layout.addWidget(QLabel("搜索："), 0, 0)
        self.app_search = QLineEdit()
        self.app_search.setPlaceholderText("输入应用名称、命令或说明")
        app_layout.addWidget(self.app_search, 0, 1, 1, 3)

        self.app_list = QListWidget()
        self.app_list.setAlternatingRowColors(True)
        app_layout.addWidget(self.app_list, 1, 0, 1, 4)

        self.app_detail_label = QLabel("从列表中选择应用，会自动填入对应的程序命令。")
        self.app_detail_label.setWordWrap(True)
        app_layout.addWidget(self.app_detail_label, 2, 0, 1, 4)

        self.reload_apps_button = QPushButton("刷新应用列表")
        self.use_app_button = QPushButton("使用选中应用")
        self.add_app_button = QPushButton("添加选中应用到白名单")
        self.launch_app_button = QPushButton("通过 Zink 启动选中应用")
        app_layout.addWidget(self.reload_apps_button, 3, 0)
        app_layout.addWidget(self.use_app_button, 3, 1)
        app_layout.addWidget(self.add_app_button, 3, 2)
        app_layout.addWidget(self.launch_app_button, 3, 3)

        whitelist_box = QGroupBox("Zink 白名单（/etc/drirc）")
        whitelist_layout = QGridLayout(whitelist_box)
        self.whitelist = QListWidget()
        whitelist_layout.addWidget(self.whitelist, 0, 0, 1, 4)

        whitelist_layout.addWidget(QLabel("程序命令："), 1, 0)
        self.executable_input = QLineEdit()
        self.executable_input.setPlaceholderText("例如：freecad")
        whitelist_layout.addWidget(self.executable_input, 1, 1)

        self.browse_button = QPushButton("浏览")
        self.add_button = QPushButton("添加")
        self.remove_button = QPushButton("移除选中项")
        self.launch_button = QPushButton("通过 Zink 启动")
        whitelist_layout.addWidget(self.browse_button, 1, 2)
        whitelist_layout.addWidget(self.add_button, 1, 3)
        whitelist_layout.addWidget(self.remove_button, 2, 1)
        whitelist_layout.addWidget(self.launch_button, 2, 2, 1, 2)

        self.vendor_label = QLabel("")
        self.vendor_label.setWordWrap(True)
        whitelist_layout.addWidget(self.vendor_label, 3, 0, 1, 4)

        layout.addWidget(status_box, 2)
        layout.addWidget(desktop_box, 1)
        layout.addWidget(refresh_box, 1)
        layout.addWidget(app_box, 3)
        layout.addWidget(whitelist_box, 1)
        self.setCentralWidget(root)

        self.refresh_button.clicked.connect(self.refresh_all)
        self.probe_button.clicked.connect(self.run_glx_probe)
        self.desktop_refresh_button.clicked.connect(self.refresh_desktop_status)
        self.desktop_apply_button.clicked.connect(self.apply_desktop_optimization)
        self.desktop_reconfigure_button.clicked.connect(self.reconfigure_kwin)
        self.refresh_rate_refresh_button.clicked.connect(self.refresh_screen_status)
        self.refresh_rate_120_button.clicked.connect(lambda: self.set_screen_refresh_rate(120))
        self.refresh_rate_60_button.clicked.connect(lambda: self.set_screen_refresh_rate(60))
        self.reload_apps_button.clicked.connect(self.refresh_app_catalog)
        self.use_app_button.clicked.connect(self.use_selected_app)
        self.add_app_button.clicked.connect(self.add_selected_app)
        self.launch_app_button.clicked.connect(self.launch_selected_app)
        self.app_search.textChanged.connect(self.filter_app_list)
        self.app_list.currentItemChanged.connect(self.update_selected_app)
        self.app_list.itemDoubleClicked.connect(lambda _item: self.use_selected_app())
        self.browse_button.clicked.connect(self.browse_executable)
        self.add_button.clicked.connect(self.add_executable)
        self.remove_button.clicked.connect(self.remove_selected)
        self.launch_button.clicked.connect(self.launch_selected)
        self.whitelist.currentTextChanged.connect(self.executable_input.setText)

    def refresh_all(self):
        self.refresh_whitelist()
        self.refresh_vendor_label()
        self.refresh_desktop_status()
        self.refresh_screen_status()
        self.run_glx_probe()

    def refresh_app_catalog(self):
        self.app_entries = app_catalog.load_desktop_apps()
        self.filter_app_list()

    def refresh_whitelist(self):
        self.whitelist.clear()
        apps = drirc_model.parse_zink_apps(_read_text(LOCAL_DRIRC))
        for app in apps:
            self.whitelist.addItem(app)

    def refresh_vendor_label(self):
        vendor_apps = drirc_model.parse_zink_apps(_read_text(VENDOR_DRIRC))
        if vendor_apps:
            self.vendor_label.setText("厂商默认白名单（/usr/share/drirc.d/01-hisi.conf）：" + ", ".join(vendor_apps))
        else:
            self.vendor_label.setText("未发现厂商默认 Zink 白名单。")

    def filter_app_list(self):
        query = self.app_search.text().strip().casefold() if hasattr(self, "app_search") else ""
        self.app_list.clear()
        for app in self.app_entries:
            haystack = " ".join([app.name, app.executable, app.comment, str(app.desktop_file)]).casefold()
            if query and query not in haystack:
                continue
            item = QListWidgetItem(f"{app.name}\n命令：{app.executable}")
            if app.icon:
                item.setIcon(QIcon.fromTheme(app.icon))
            item.setData(Qt.UserRole, app)
            item.setToolTip(f"{app.name}\n命令：{app.executable}\n启动器：{app.desktop_file}")
            self.app_list.addItem(item)
        if self.app_list.count() == 0:
            self.app_detail_label.setText("没有找到匹配的应用。")
        else:
            self.app_list.setCurrentRow(0)

    def update_selected_app(self):
        app = self._current_catalog_app()
        if app is None:
            self.app_detail_label.setText("从列表中选择应用，会自动填入对应的程序命令。")
            return
        self.executable_input.setText(app.executable)
        detail = f"已选择：{app.name}（命令：{app.executable}）"
        if app.comment:
            detail += f"\n说明：{app.comment}"
        detail += f"\n启动器：{app.desktop_file}"
        self.app_detail_label.setText(detail)

    def use_selected_app(self):
        app = self._current_catalog_app()
        if app is None:
            QMessageBox.information(self, "未选择应用", "请先在已安装应用列表中选择一个应用。")
            return False
        self.executable_input.setText(app.executable)
        return True

    def add_selected_app(self):
        if self.use_selected_app():
            self.add_executable()

    def launch_selected_app(self):
        if self.use_selected_app():
            self.launch_selected()

    def refresh_desktop_status(self):
        self.desktop_output.setPlainText(kwin_model.desktop_status_text())

    def apply_desktop_optimization(self):
        try:
            backup = kwin_model.optimize_kwinrc_file()
            kwin_model.reconfigure_kwin()
            kwin_model.apply_runtime_optimization()
        except Exception as exc:
            QMessageBox.critical(self, "桌面优化失败", str(exc))
            return
        message = "已应用桌面流畅优化。"
        if backup:
            message += f"\n已备份原配置：{backup}"
        QMessageBox.information(self, "桌面优化", message)
        self.refresh_desktop_status()

    def reconfigure_kwin(self):
        try:
            kwin_model.reconfigure_kwin()
        except Exception as exc:
            QMessageBox.critical(self, "KWin 重载失败", str(exc))
            return
        self.refresh_desktop_status()

    def refresh_screen_status(self):
        self.refresh_rate_label.setText(kwin_model.refresh_status_text())

    def set_screen_refresh_rate(self, refresh_rate):
        try:
            backup = kwin_model.set_display_refresh_rate(refresh_rate)
        except Exception as exc:
            QMessageBox.critical(self, "刷新率切换失败", str(exc))
            return
        message = f"已切换到 {refresh_rate}Hz。"
        if backup:
            message += f"\n已备份原配置：{backup}"
        QMessageBox.information(self, "屏幕刷新率", message)
        self.refresh_screen_status()
        self.refresh_desktop_status()

    def run_glx_probe(self):
        env = os.environ.copy()
        env.setdefault("DISPLAY", ":0")
        env.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")
        result = subprocess.run(
            ["glxinfo", "-B"],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=12,
            check=False,
        )
        self.status_output.setPlainText(result.stdout.strip())

    def browse_executable(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择可执行程序", "/usr/bin")
        if path:
            self.executable_input.setText(Path(path).name)

    def add_executable(self):
        executable = self._validated_input()
        if not executable:
            return
        if self._apply_change("add", executable):
            self.refresh_all()

    def remove_selected(self):
        item = self.whitelist.currentItem()
        if item is None:
            QMessageBox.information(self, "未选择条目", "请先选择一个白名单条目。")
            return
        executable = item.text()
        if self._apply_change("remove", executable):
            self.refresh_all()

    def launch_selected(self):
        executable = self._validated_input()
        if not executable:
            return
        if not ZINK_RUN.exists():
            QMessageBox.critical(self, "缺少启动器", f"未找到 {ZINK_RUN}。")
            return
        env = os.environ.copy()
        env.setdefault("DISPLAY", ":0")
        env.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")
        try:
            subprocess.Popen([str(ZINK_RUN), executable], env=env)
        except Exception as exc:
            QMessageBox.critical(self, "启动失败", str(exc))

    def _validated_input(self):
        value = self.executable_input.text()
        try:
            return drirc_model.validate_executable(value)
        except ValueError:
            QMessageBox.warning(
                self,
                "无效的程序命令",
                "请输入程序命令名，只能包含字母、数字、点、下划线、加号或短横线。",
            )
            return None

    def _apply_change(self, action, executable):
        command = ["pkexec", str(HELPER), action, executable]
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "授权请求已取消。").strip()
            QMessageBox.critical(self, "更新失败", message)
            return False
        return True

    def _current_catalog_app(self):
        item = self.app_list.currentItem()
        return item.data(Qt.UserRole) if item is not None else None


def _read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--check"]:
        print("kylin-gpu-control import check ok")
        return 0
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
