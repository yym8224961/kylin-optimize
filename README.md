# kylin-optimize

面向银河麒麟桌面操作系统 V10 SP1 / UKUI 的桌面与 GPU 兼容优化工具集。

这个项目目前包含两部分：

- **麒麟 GPU 兼容控制器**：中文 PyQt5 图形界面，用于管理指定 GLX/OpenGL 应用的 Mesa Zink 硬件加速白名单。
- **KWin 桌面流畅优化**：精简 UKUI/KWin 合成器特效，降低高分辨率桌面的动画和缩放开销。

项目目标是解决华为擎云 L420x-A121、麒麟 V10 SP1、Kirin 9000C / Maleoon 910 这类 ARM64 机器上的两个实际问题：桌面特效过重导致卡顿，以及部分 GLX 应用没有走到 Maleoon GPU 硬件路径。

## 功能

### 麒麟 GPU 兼容控制器

- 中文 GUI，安装后可从开始菜单搜索 **麒麟 GPU 兼容控制器** 启动。
- 读取系统 `.desktop` 启动器，按应用名称搜索并自动提取真实可执行命令。
- 管理 `/etc/drirc` 中的 Zink 白名单，只让指定 GLX 应用走 Zink。
- 通过 `/usr/local/bin/kylin-zink-run` 按需启动应用。
- 显示 `glxinfo -B`、OpenGL renderer、KWin 合成器、活跃特效和当前显示模式。
- 内置“桌面流畅优化”按钮，复用本仓库的 KWin 优化策略。

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
| 面板 | 2880x1920，当前系统常见配置为 60Hz |
| 依赖 | Python 3、PyQt5、mesa-utils、policykit |

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
Display mode: 2880x1920_60000
```

## 项目结构

```text
kylin-optimize/
├── README.md
├── KWIN-OPTIMIZE-GUIDE.md
├── install-gpu-control.sh
├── kwin-optimize.sh
├── kwin-optimize.desktop
├── ukui-kwinrc-optimized
├── packaging/
│   ├── kylin-gpu-control
│   ├── kylin-gpu-control.desktop
│   ├── kylin-gpu-control.svg
│   └── org.kylin.gpu-control.policy
├── src/kylin_gpu_control/
│   ├── app_catalog.py
│   ├── drirc_model.py
│   ├── kwin_model.py
│   ├── kylin_gpu_control.py
│   └── kylin_gpu_control_apply.py
└── tests/
    ├── test_app_catalog.py
    ├── test_apply_helper.py
    ├── test_drirc_model.py
    ├── test_kwin_model.py
    └── test_packaging_assets.py
```

## 开发与测试

```bash
python3 -m unittest \
  tests.test_app_catalog \
  tests.test_apply_helper \
  tests.test_drirc_model \
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

GitHub Releases 会提供 `kylin-gpu-control-<version>.tar.gz`。下载后：

```bash
tar -xf kylin-gpu-control-<version>.tar.gz
cd kylin-gpu-control-<version>
sudo ./install-gpu-control.sh
```

## 许可证

本仓库当前未声明开源许可证。复用、分发或二次打包前请先补充 LICENSE。
