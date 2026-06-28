# kylin-optimize

麒麟 Kylin V10 SP1 (UKUI) 桌面性能优化工具集

[![Platform](https://img.shields.io/badge/platform-Kylin%20V10%20SP1-blue)](http://www.kylinos.cn/)
[![Arch](https://img.shields.io/badge/arch-ARM64%20(aarch64)-green)]()

---

## 📖 目录

- [背景](#-背景)
- [优化内容](#-优化内容)
- [文件说明](#-文件说明)
- [快速开始](#-快速开始)
- [效果对比](#-效果对比)
- [适用环境](#-适用环境)
- [原理](#-原理)
- [FAQ](#-faq)
- [参考](#-参考)

---

## 🎯 背景

在高分辨率（2880×1920）ARM64 平台上，银河麒麟 V10 SP1 的 UKUI 桌面环境默认开启大量窗口动画特效，导致：

- 🐌 窗口最小化/恢复有明显拖影
- 🐌 启动器（开始菜单）打开/关闭掉帧
- 🐌 右键菜单弹出有延迟
- 🐌 多窗口切换时 GPU 负载过高

本工具集通过**精简 KWin 特效**、**优化合成器参数**和**运行时脚本**三管齐下，显著提升桌面流畅度。

仓库现在还包含一个中文 GUI：**麒麟 GPU 兼容控制器**。它用于管理指定 GLX/OpenGL 应用的 Mesa Zink 白名单，并把 KWin 桌面优化状态整合到同一个窗口里。

---

## ⚡ 优化内容

### 配置文件（`ukui-kwinrc`）

| 参数 | 默认值 | 优化值 | 说明 |
|------|--------|--------|------|
| `AnimationSpeed` | 2 | **5** | 动画播放速度，越大越快 |
| `glSmoothScale` | 2（双线性） | **0**（最近邻） | 窗口缩放算法，0 最快 |
| `Enabled` | — | **true** | 启用合成器硬件加速 |

禁用 **28 个** 非必要 KWin 特效插件，仅保留：

| 保留特效 | 原因 |
|----------|------|
| `contrast` | 对比度调节，用于无障碍/夜间模式 |

### 运行时脚本（`kwin-optimize.sh`）

通过 dbus 接口在运行时卸载已加载的特效插件，无需重启桌面：

```bash
bash ~/桌面/kwin-optimize.sh
```

### 自启配置（`kwin-optimize.desktop`）

登录后自动执行优化脚本，确保每次启动都生效。

### 麒麟 GPU 兼容控制器

- 读取系统 `.desktop` 启动器，支持按中文应用名搜索并自动提取实际命令
- 管理 `/etc/drirc` 中的 Zink 白名单，避免全局替换 OpenGL/GLX 系统库
- 通过 `/usr/local/bin/kylin-zink-run` 按需启动应用
- 显示 `glxinfo -B`、KWin 合成器、活跃特效、当前显示模式等状态
- 提供“桌面流畅优化”按钮，复用本仓库的 KWin 优化策略，但不会强行切换 120Hz

---

## 📁 文件说明

```
kylin-optimize/
├── README.md                     ← 本文件
├── KWIN-OPTIMIZE-GUIDE.md        ← 详细优化指南（八章）
├── install-gpu-control.sh         ← 安装 GUI 控制器
├── ukui-kwinrc-optimized         ← 优化后的 KWin 配置文件（参考）
├── kwin-optimize.sh              ← 运行时特效卸载脚本
├── kwin-optimize.desktop         ← autostart 桌面入口
├── src/kylin_gpu_control/        ← GUI 控制器源码
├── packaging/                    ← desktop、polkit、图标、启动器
├── tests/                        ← 单元测试
└── .gitignore
```

| 文件 | 类型 | 作用 |
|------|------|------|
| `KWIN-OPTIMIZE-GUIDE.md` | 文档 | 完整的操作指南，含原理、步骤、验证、FAQ |
| `ukui-kwinrc-optimized` | 配置参考 | 可直接替换 `~/.config/ukui-kwinrc` |
| `kwin-optimize.sh` | 脚本 | 运行时通过 dbus 卸载特效 |
| `kwin-optimize.desktop` | 自启 | 复制到 `~/.config/autostart/` 实现开机自启 |
| `install-gpu-control.sh` | 安装脚本 | 安装中文 GUI、polkit helper、desktop 入口和图标 |
| `src/kylin_gpu_control/` | Python 源码 | GLX/Zink 白名单、应用目录、KWin 状态与 GUI |

---

## 🚀 快速开始

### 方法一：一键部署（推荐）

```bash
# 1. 克隆仓库
cd ~/桌面
git clone https://github.com/yym8224961/kylin-optimize.git

# 2. 替换 KWin 配置（需要先解决 /home 只读问题）
unshare -m bash -c '
mount -o remount,rw /home
cp ~/桌面/kylin-optimize/ukui-kwinrc-optimized ~/.config/ukui-kwinrc
chown kylin:kylin ~/.config/ukui-kwinrc
'

# 3. 安装 autostart
mkdir -p ~/.config/autostart
cp ~/桌面/kylin-optimize/kwin-optimize.desktop ~/.config/autostart/

# 4. 通知 KWin 重载
DBUS="unix:path=/run/user/1000/bus"
sudo -u kylin DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="$DBUS" \
  dbus-send --session --dest=org.ukui.KWin --print-reply \
  /KWin org.ukui.KWin.reconfigure

# 5. 运行优化脚本
sudo -u kylin DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="$DBUS" \
  bash ~/桌面/kylin-optimize/kwin-optimize.sh
```

### 方法二：手动操作

参考 [`KWIN-OPTIMIZE-GUIDE.md`](KWIN-OPTIMIZE-GUIDE.md) 第四章的详细步骤。

### 方法三：安装中文 GUI 控制器

```bash
sudo ./install-gpu-control.sh
```

安装后从开始菜单搜索 **麒麟 GPU 兼容控制器**。推荐测试顺序：

```bash
sudo apt install glmark2 mesa-utils
```

在 GUI 中搜索 `glmark2`，加入 Zink 白名单后通过 Zink 启动。状态栏中应看到：

```text
OpenGL renderer string: zink (Maleoon 910)
Accelerated: yes
```

---

## 📊 效果对比

| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| 窗口最小化/恢复 | 拖影明显 | ✅ 顺滑 |
| 启动器弹出 | 掉帧 | ✅ 流畅 |
| 右键菜单 | 动画延迟 | ✅ 即时 |
| 窗口缩放 | 双线性插值(GPU) | ✅ 最近邻(零开销) |
| 活跃特效数 | 28+ 个 | ✅ 1 个 |
| 动画完成时间 | 默认速度 | ✅ 2.5× 加速 |

---

## 💻 适用环境

| 项目 | 要求 |
|------|------|
| **操作系统** | 银河麒麟桌面操作系统 V10 SP1 |
| **桌面环境** | UKUI (Wayland + ukui-kwin_wayland) |
| **架构** | ARM64 (aarch64) |
| **GPU** | Maleoon 910 / Mali 系列 |
| **CPU** | Kirin 9000C 系列 |
| **分辨率** | 2880×1920 @ 60Hz（也适用其他分辨率） |
| **权限** | root（需修改 ~/.config/ 下的只读配置） |

> 理论上兼容所有 Kylin V10 SP1 + UKUI 桌面，不限于特定硬件型号。

---

## 🔧 原理

### KWin 合成器架构

```
┌─────────────────────────────────┐
│         KWin (Wayland)          │
│  ┌───────────────────────────┐  │
│  │     Compositing (gles)    │  │  ← GPU 合成管线
│  │  ┌─────┐ ┌─────┐ ┌─────┐ │  │
│  │  │Blur │ │Slide│ │Zoom │ │  │  ← 特效插件（每个都占 GPU）
│  │  └─────┘ └─────┘ └─────┘ │  │
│  │  ┌─────┐ ┌─────┐  ...    │  │
│  │  │Fade │ │Scale│         │  │
│  │  └─────┘ └─────┘         │  │
│  └───────────────────────────┘  │
│              ↕ dbus              │
│     kwin-optimize.sh (运行时)    │
└─────────────────────────────────┘
```

### 优化策略

1. **配置文件层**：`ukui-kwinrc` 中 `[Plugins]` 段设为 `false`，KWin 启动时不加载
2. **运行时层**：已加载的旧特效通过 `dbus-send unloadEffect` 卸载
3. **渲染层**：`glSmoothScale=0` 关闭双线性插值，缩放时直接用最近邻采样
4. **感知层**：`AnimationSpeed=5` 让动画更快完成，体感更流畅

---

## ❓ FAQ

<details>
<summary><b>为什么 /home 是只读的？</b></summary>

麒麟系统出于安全考虑将 `/home` 挂载为 `ro,nosuid,nodev`。可通过 `unshare -m` 创建新 mount namespace 后 `mount -o remount,rw /home` 临时突破。

```bash
unshare -m bash -c 'mount -o remount,rw /home; <你的操作>'
```
</details>

<details>
<summary><b>重启后优化会失效吗？</b></summary>

不会。配置写在 `~/.config/ukui-kwinrc` 中，KWin 每次启动都会读取。`kwin-optimize.desktop` 放入 `~/.config/autostart/` 后，登录时自动运行优化脚本。
</details>

<details>
<summary><b>如何恢复默认？</b></summary>

```bash
# 删除自定义配置，重新登录即可恢复默认
rm ~/.config/ukui-kwinrc
rm ~/.config/autostart/kwin-optimize.desktop
```
</details>

<details>
<summary><b>如何验证是否生效？</b></summary>

```bash
# 检查合成器状态
dbus-send --session --dest=org.ukui.KWin --print-reply \
  /Compositor org.freedesktop.DBus.Properties.GetAll \
  string:"org.ukui.kwin.Compositing"

# 检查活跃特效（应该只有 contrast）
dbus-send --session --dest=org.ukui.KWin --print-reply \
  /Effects org.freedesktop.DBus.Properties.Get \
  string:"org.ukui.kwin.Effects" string:"activeEffects"
```
</details>

<details>
<summary><b>能否用在其他 Linux 发行版上？</b></summary>

KWin 是 KDE 的窗口管理器。如果你用的是 KDE Plasma，配置文件路径和方法类似，但 dbus 接口名可能不同（`org.kde.KWin` 而非 `org.ukui.KWin`），需自行调整。
</details>

---

## 📚 参考

- [KWin 配置项文档](https://userbase.kde.org/KWin_Rules)
- [UKUI 桌面环境](https://www.ukui.org/)
- [银河麒麟操作系统](http://www.kylinos.cn/)

---

<p align="center">
  <sub>Made for Kirin 9000C · Maleoon 910 · Kylin V10 SP1</sub>
</p>
