# kylin-optimize

面向银河麒麟桌面操作系统 V10 SP1 / UKUI 的桌面与 GPU 兼容优化工具集。

这个项目目前包含两部分：

- **麒麟 GPU 兼容控制器**：中文 PyQt5 图形界面，用于管理指定 GLX/OpenGL 应用的 Mesa Zink 硬件加速白名单。
- **KWin 桌面流畅优化**：精简 UKUI/KWin 合成器特效，降低高分辨率桌面的动画和缩放开销。

项目目标是解决华为擎云 L420x-A121、麒麟 V10 SP1、Kirin 9000C / Maleoon 910 这类 ARM64 机器上的两个实际问题：桌面特效过重导致卡顿，以及部分 GLX 应用没有走到 Maleoon GPU 硬件路径。

本项目采用 **GPL-3.0-or-later** 许可证，详见 [LICENSE](LICENSE)。

## 功能

### 麒麟 GPU 兼容控制器

- 中文 GUI，安装后可从开始菜单搜索 **麒麟 GPU 兼容控制器** 启动。
- 读取系统 `.desktop` 启动器，按应用名称搜索并自动提取真实可执行命令。
- 管理 `/etc/drirc` 中的 Zink 白名单，只让指定 GLX 应用走 Zink。
- 通过 `/usr/local/bin/kylin-zink-run` 按需启动应用。
- 显示 `glxinfo -B`、OpenGL renderer、KWin 合成器、活跃特效和当前显示模式。
- 内置“桌面流畅优化”按钮，复用本仓库的 KWin 优化策略。
- 内置“屏幕刷新率”控制，可在支持的同分辨率模式间切换 60Hz / 120Hz。
- 内置“CPU 性能”控制，默认前台加速会把通过 GUI 启动的应用绑定到 Kirin 9000C 的中核+大核（CPU 4-11）。
- 内置“麒麟 AI 精简”控制，可禁用 Kylin AI 文档问答、Milvus Lite、Triton 和 AI Runtime 的当前会话/自启，且不卸载软件包、不删除模型和用户数据。

### KWin 桌面优化

- 禁用 blur、slide、zoom、fade、scale 等非必要 KWin 特效。
- 保留 UKUI/KWin 的 GLES 合成器硬件加速。
- 设置 `AnimationSpeed=5`，缩短动画完成时间。
- 设置 `glSmoothScale=0`，降低窗口缩放采样开销。
- 提供 `kwin-optimize.sh` 和 `kwin-optimize.desktop`，支持运行时优化和登录自启。

## 安全边界

本项目只做用户态兼容和桌面配置优化。

不会做这些事情：

- 不更新 BIOS / 固件。
- 不修改 `/boot`。
- 不替换系统全局 `libGL`、`libEGL`、`libGLX`。
- 不改系统动态链接器全局配置。
- 不把所有应用强制切到 Zink。
- 不把普通桌面应用默认切到实时调度。

GPU 控制器采用白名单方式：只有写入 `/etc/drirc` 的应用才会使用 Zink 路径。

## 适用环境

| 项目 | 说明 |
| --- | --- |
| 操作系统 | 银河麒麟桌面操作系统 V10 SP1 |
| 桌面环境 | UKUI / ukui-kwin_wayland |
| 架构 | ARM64 / aarch64 |
| 已验证硬件 | Huawei QingYun L420x-A121 |
| CPU | Kirin 9000C 系列 |
| GPU | Maleoon 910 |
| 面板 | 2880x1920，已验证 60Hz / 120Hz |
| 依赖 | Python 3、PyQt5、mesa-utils、policykit、kscreen-doctor |

理论上也可用于其他 Kylin V10 SP1 + UKUI + ARM64 机器，但需要自行验证 GPU 驱动和 Vulkan ICD 路径。

## 安装 GUI 控制器

```bash
git clone https://github.com/yym8224961/kylin-optimize.git
cd kylin-optimize
sudo ./install-gpu-control.sh
```

安装内容：

- `/usr/local/lib/kylin-gpu-control/`
- `/usr/local/bin/kylin-gpu-control`
- `/usr/local/bin/kylin-zink-run`
- `/usr/share/applications/kylin-gpu-control.desktop`
- `/usr/share/icons/hicolor/scalable/apps/kylin-gpu-control.svg`
- `/usr/share/polkit-1/actions/org.kylin.gpu-control.policy`

安装后从开始菜单启动 **麒麟 GPU 兼容控制器**。

## 使用 GPU 控制器

1. 打开 **麒麟 GPU 兼容控制器**。
2. 在“已安装应用”里搜索应用，例如 `glmark2`、`Chromium`、`FreeCAD`。
3. 选中应用后点击“添加选中应用到白名单”。
4. 点击“通过 Zink 启动选中应用”。
5. 在“GLX 状态”区域确认 renderer。

如果机器的面板支持 120Hz，可以在“屏幕刷新率”区域点击“切换到 120Hz”。该操作会先通过 `kscreen-doctor` 做运行时切换，再把 `~/.config/ukui-kwinrc` 中对应输出的 `Mode=` 持久化为 120Hz，并自动生成 `.bak.*` 备份。需要回退时点击“切换回 60Hz”。

“CPU 性能”区域默认勾选“默认前台加速”。开启后，通过 GUI 的“通过 Zink 启动”按钮启动的应用会使用 `taskset -c 4-11`，优先使用 Kirin 9000C 的中核和大核。这个模式不使用实时调度；`SCHED_FIFO` / `SCHED_RR` 这类实时策略可能让 KWin、输入、音频等桌面关键线程抢不到 CPU，不适合作为默认桌面优化。

“后台降噪”会尝试对 Kylin AI、KMRE、华为电脑管家、更新与搜索等当前用户后台进程降低 CPU/IO 优先级。失败项会被忽略，不会终止进程。

“麒麟 AI 精简”会停止并禁用当前用户的 Kylin AI 文档问答服务、文档服务、Milvus Lite，并通过 `~/.config/autostart/` 覆盖 Triton Server 与 Kylin AI Runtime 自启。若用户已有同名 autostart 自定义文件，工具会先保留备份，恢复时还原原文件。该操作不卸载软件包，不删除 `/usr/share/kylin-ai` 模型，也不删除 `~/.local/share/milvus-lite` 数据；点击“恢复 Kylin AI”可恢复用户服务和登录自启。当前 UKUI 会话可能会复活已经注册的 Kylin AI Runtime，重新登录后精简状态会完全生效。

期望看到类似输出：

```text
Device: zink (Maleoon 910)
Accelerated: yes
OpenGL renderer string: zink (Maleoon 910)
```

手动测试可以使用：

```bash
sudo apt install mesa-utils glmark2
glxinfo -B
/usr/local/bin/kylin-zink-run glmark2
```

## 使用 KWin 桌面优化

GUI 中点击“应用桌面流畅优化”即可写入 KWin 配置并运行时卸载非必要特效。

也可以继续使用原始脚本：

```bash
bash ./kwin-optimize.sh
```

如果希望登录后自动执行：

```bash
mkdir -p ~/.config/autostart
cp ./kwin-optimize.desktop ~/.config/autostart/
```

详细说明见 [KWIN-OPTIMIZE-GUIDE.md](KWIN-OPTIMIZE-GUIDE.md)。

## 验证

检查 GLX/OpenGL：

```bash
glxinfo -B
```

检查 KWin 合成器：

```bash
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
dbus-send --session --dest=org.ukui.KWin --print-reply \
  /Compositor org.freedesktop.DBus.Properties.GetAll \
  string:org.ukui.kwin.Compositing
```

检查活跃特效：

```bash
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
dbus-send --session --dest=org.ukui.KWin --print-reply \
  /Effects org.freedesktop.DBus.Properties.Get \
  string:org.ukui.kwin.Effects string:activeEffects
```

已验证的一组状态：

```text
GL_RENDERER: zink (Maleoon 910)
KWin compositingType: gles
KWin openGLIsBroken: false
Display mode: 2880x1920_120000
```

## 项目结构

```text
kylin-optimize/
├── README.md
├── LICENSE
├── KWIN-OPTIMIZE-GUIDE.md
├── install-gpu-control.sh
├── scripts/
│   └── package-release.sh
├── kwin-optimize.sh
├── kwin-optimize.desktop
├── ukui-kwinrc-optimized
├── packaging/
│   ├── kylin-gpu-control
│   ├── kylin-gpu-control.desktop
│   ├── kylin-gpu-control.svg
│   ├── kylin-zink-run
│   └── org.kylin.gpu-control.policy
├── src/kylin_gpu_control/
│   ├── ai_model.py
│   ├── app_catalog.py
│   ├── drirc_model.py
│   ├── kwin_model.py
│   ├── kylin_gpu_control.py
│   ├── kylin_gpu_control_apply.py
│   └── perf_model.py
└── tests/
    ├── test_ai_model.py
    ├── test_app_catalog.py
    ├── test_apply_helper.py
    ├── test_drirc_model.py
    ├── test_perf_model.py
    ├── test_kwin_model.py
    └── test_packaging_assets.py
```

## 开发与测试

```bash
python3 -m unittest \
  tests.test_ai_model \
  tests.test_app_catalog \
  tests.test_apply_helper \
  tests.test_drirc_model \
  tests.test_perf_model \
  tests.test_kwin_model \
  tests.test_packaging_assets

python3 -m py_compile src/kylin_gpu_control/*.py
```

## 恢复与卸载

移除 GUI 控制器：

```bash
sudo rm -rf /usr/local/lib/kylin-gpu-control
sudo rm -f /usr/local/bin/kylin-gpu-control
sudo rm -f /usr/local/bin/kylin-zink-run
sudo rm -f /usr/share/applications/kylin-gpu-control.desktop
sudo rm -f /usr/share/icons/hicolor/scalable/apps/kylin-gpu-control.svg
sudo rm -f /usr/share/polkit-1/actions/org.kylin.gpu-control.policy
```

恢复 KWin 默认配置：

```bash
rm -f ~/.config/autostart/kwin-optimize.desktop
```

如果曾经覆盖过 `~/.config/ukui-kwinrc`，请从 `.bak.*` 备份恢复，或删除该文件后重新登录让系统生成默认配置。

恢复 Zink 白名单：

```bash
sudoedit /etc/drirc
```

删除不需要的 `<application ...>` 条目即可。GUI 的“移除选中项”按钮也可以处理白名单删除。

## Release

GitHub Releases 会提供 `kylin-gpu-control-<version>.tar.gz`，包内包含 GUI 控制器、安装脚本、README 和 `LICENSE`。发布包由仓库内脚本生成：

```bash
./scripts/package-release.sh v0.2.0
```

下载后：

```bash
tar -xf kylin-gpu-control-<version>.tar.gz
cd kylin-gpu-control-<version>
sudo ./install-gpu-control.sh
```

## 许可证

本项目采用 [GNU General Public License v3.0 or later](LICENSE)，SPDX 标识为 `GPL-3.0-or-later`。

由于图形界面使用 PyQt5，选择 GPL 系列许可证可以保持依赖许可证边界清晰。复用、分发或二次打包时请同时保留 `LICENSE` 文件和相应源码。
