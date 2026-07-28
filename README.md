<div align="center">

# P3 Studio 🔊

**轻量级 WAV ↔ P3 音频转换 & 播放器 · 机甲风格桌面工具**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows&logoColor=white)]()
[![Opus](https://img.shields.io/badge/Codec-Opus-DA6B20?logo=opus)](https://opus-codec.org)

[✨ 功能特性](#-功能特性) • [📦 安装方法](#-安装方法) • [🎮 使用指南](#-使用指南) • [🛠️ 自行编译](#️-自行编译) • [🏗️ 项目架构](#️-项目架构) • [📁 目录结构](#-目录结构) • [🔧 常见问题](#-常见问题) • [📜 开源许可](#-开源许可)

</div>

---

## 📖 项目简介

**P3 Studio** 是一款桌面音频转换与播放工具，围绕 **P3 音频格式** 设计 —— 这是一种基于 Opus 编码的轻量化自定义音频格式，专为嵌入式 AI 语音助手（如 ESP32 开发板）优化。

该项目最初是 [zhicloud_esp32](https://github.com/adkjkjdsaghj/zhicloud_esp32) 板级项目的工具链组件，为 ESP32 AI 语音助手开发提供便捷的音频样本处理与播放功能。

> **为什么用 P3？** — `.p3` 格式将 Opus 编码的音频封装为 16 kHz 单声道，在文件大小和语音清晰度之间取得了完美平衡。非常适合存储空间和带宽有限的嵌入式系统。

---

## ✨ 功能特性

### 🔄 音频转换

| 方向 | 输入格式 | 输出格式 | 说明 |
|------|----------|----------|------|
| **WAV → P3** | `.wav` / `.flac` / `.ogg` | `.p3` | 自动重采样至 16 kHz 单声道，Opus 编码 |
| **P3 → WAV** | `.p3` | `.wav` | 解码回 16 kHz PCM WAV |
| **批量处理** | 多文件选择 | 逐文件输出 | 批量添加，依次转换 |

### 🎚️ 响度归一化

- 基于 **ITU-R BS.1770 标准** 的 LUFS 响度归一化（使用 `pyloudnorm`）
- 默认目标：**−16 LUFS**（嵌入式语音输出的最佳值）
- **TTS 音频建议关闭**此功能 —— 防止预先优化的语音样本出现削波
- 可在每次转换前自由开关

### ▶️ P3 播放功能

- 原生 P3 文件播放（基于 `sounddevice` + PortAudio）
- 播放 / 暂停 / 停止 控制
- **循环播放模式**，便于反复试听
- 播放列表管理 —— 添加 / 删除文件
- 单击选中，状态栏实时显示当前曲目和状态

### 🧪 内置自检功能

```bash
P3Studio.exe --selftest <输出目录>
```

无需打开 GUI，即可运行一遍完整的**编码→解码往返测试**，验证所有依赖（Opus DLL、PortAudio、Scipy、SoundFile）在打包环境中是否正常工作。结果写入 `selftest_result.txt`。

---

## 📦 安装方法

### 方式一：直接下载 EXE（Windows，推荐）

1. 从 [Releases 页面](https://github.com/adkjkjdsaghj/p3-studio/releases) 下载最新的 `P3Studio.exe`
2. 放在任意位置 —— **无需安装，双击即用**

> **系统要求**：Windows 10/11 64 位。无需安装 Python 或任何依赖库。

### 方式二：从源码运行（跨平台）

```bash
# 1. 克隆仓库
git clone https://github.com/adkjkjdsaghj/p3-studio.git
cd p3-studio

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python p3_studio.py
```

> **Linux / macOS 用户须知**：需要系统安装 `libopus`（或等效的 `opus.dll`）。默认情况下 `opuslib` 的 `find_library` 会自动查找。

---

## 🎮 使用指南

### 转换页面

1. 选择**转换模式**：`音频 → P3`（编码）或 `P3 → 音频`（解码）
2. **添加文件** —— 编码支持 `.wav` / `.flac` / `.ogg`；解码支持 `.p3`
3. 开关**响度归一化**并设置目标 LUFS 值
4. 选择**输出目录**（默认是 EXE 所在位置）
5. 点击 **开始转换** —— 进度实时显示在控制台风格的日志面板

### 播放页面

1. **添加文件** —— 将 `.p3` 文件载入播放列表
2. 从列表中选中一个曲目
3. 使用 **▶ 播放 / ⏸ 暂停 / ■ 停止** 控制播放
4. 勾选 **⬢ 循环播放** 可重复播放
5. 状态栏显示 `▶ 文件名` / `⏸ 播放已暂停` / `■ 播放已停止`

### 快捷键

| 按键 | 功能 |
|------|------|
| `Enter`（播放列表中） | 播放选中曲目 |
| `Delete`（播放列表中） | 移除选中曲目 |

---

## 🛠️ 自行编译

### 用 PyInstaller 打包为 EXE

```bash
# 安装依赖
pip install -r requirements.txt
pip install pyinstaller

# 打包
pyinstaller --noconfirm --onefile --windowed --name "P3Studio" \
  --add-binary "你的opus.dll路径;." \
  --add-binary "你的opus.dll路径;pyogg" \
  --collect-all sounddevice \
  --hidden-import pyloudnorm --hidden-import scipy --hidden-import scipy.signal \
  --hidden-import numpy --hidden-import soundfile --hidden-import opuslib \
  --hidden-import tkinter \
  p3_studio.py
```

**关于 Opus DLL**：编码/解码需要 `opus.dll`。在 Windows 上它随 `pyogg` 包自带，路径为 `.../site-packages/pyogg/opus.dll`。PyInstaller 的 `--add-binary` 会将其打入打包后的包根目录和 `pyogg/` 子目录，确保 `opuslib` 的 `ctypes.find_library('opus')` 能找到它。

**关于 PortAudio**：`--collect-all sounddevice` 会自动收集随包自带的 PortAudio 二进制文件（位于 `_sounddevice_data/portaudio-binaries/`）。

---

## 🏗️ 项目架构

```
┌─────────────────────────────────────────────────────┐
│                   P3Studio (Tkinter 界面)            │
│  ┌──────────────────┐  ┌─────────────────────────┐  │
│  │  转换标签页       │  │  播放标签页             │  │
│  │  ┌──────────────┐ │  │  ┌───────────────────┐ │  │
│  │  │ 模式选择     │ │  │  │ 播放列表          │ │  │
│  │  │ (单选按钮)   │ │  │  │ (列表框+滚动条)   │ │  │
│  │  ├──────────────┤ │  │  ├───────────────────┤ │  │
│  │  │ 文件选择     │ │  │  │ 控制按钮          │ │  │
│  │  ├──────────────┤ │  │  │ ▶ ⏸ ■ 循环     │ │  │
│  │  │ 响度设置     │ │  │  ├───────────────────┤ │  │
│  │  ├──────────────┤ │  │  │ 状态栏            │ │  │
│  │  │ 转换日志     │ │  │  └───────────────────┘ │  │
│  │  │ (终端风格)   │ │  │                         │  │
│  │  └──────────────┘ │  └─────────────────────────┘  │
│  └──────────────────┘                                │
└─────────────────────────────────────────────────────┘
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌──────────────────────┐
│ 转换流水线       │   │ 播放流水线           │
│ WAV → 重采样    │   │ P3 → Opus 解码      │
│ (scipy.signal)  │   │ → sounddevice       │
│ → Opus 编码     │   │ → PortAudio → 扬声器│
│ (opuslib)       │   └──────────────────────┘
│ → P3 文件       │
└─────────────────┘
```

### 核心依赖库

| 库 | 作用 |
|-----|------|
| **opuslib** | libopus 的 Python 绑定 —— 核心编解码 |
| **soundfile** | 读写 WAV、FLAC、OGG 音频文件 |
| **sounddevice** | 基于 PortAudio 的音频播放 |
| **scipy.signal** | `resample_poly` 高质量重采样至 16 kHz |
| **pyloudnorm** | ITU-R BS.1770 响度归一化 |
| **numpy** | 音频数据数组操作 |
| **PyInstaller** | 打包为独立 Windows EXE |

### 为什么不用 librosa？

原型阶段使用了 librosa 进行音频加载和重采样，但它会引入 **numba + llvmlite**，导致打包后的 EXE 体积膨胀到 150 MB 以上且启动缓慢。最终版本改用 `soundfile` + `scipy.signal.resample_poly`—— 在保持相同质量的前提下，EXE 仅 **58 MB**，冷启动飞快。

---

## 📁 目录结构

```
p3-studio/
├── p3_studio.py          # 主程序（Tkinter GUI + 核心逻辑）
├── requirements.txt      # Python 依赖列表
├── README.md             # 本文件
├── LICENSE               # MIT 开源许可
└── .gitignore            # Git 忽略规则
```

---

## 🔧 常见问题

### "opus.dll not found" 错误

EXE 已内置 `opus.dll`，但在以下情况可能出现此错误：

- **从源码运行**：安装 `pyogg` 或将 `opus.dll` 放到系统 PATH 目录中
- **从 EXE 运行**：使用 `--selftest` 验证打包环境；如果自检通过，问题出在其他地方

### 播放没有声音

- 检查系统音量设置和扬声器连接
- 状态栏应显示 `▶`；如果立刻显示 `■`，文件可能损坏
- 运行 `P3Studio.exe --selftest .` 验证播放链路

### 某些 WAV 文件转换失败

- 本工具只处理 PCM 编码的 WAV。压缩格式（如 WMA、MP3-in-WAV）不支持
- 可先用 FFmpeg 等工具转换为标准 PCM WAV
- 非标准采样率会自动重采样至 16 kHz

### EXE 体积较大

EXE 体积约 58 MB，包含：
- Python 运行时和标准库
- NumPy / SciPy 科学计算库
- Opus 编解码器 DLL（libopus）
- PortAudio 音频 I/O 库
- 所有 GUI 和支持代码

这是 PyInstaller 打包 Python 数值计算应用的正常大小。

---

## 🧪 快速自检

验证当前 P3Studio 是否正常工作：

```bash
# 在 P3Studio.exe 所在目录打开终端
P3Studio.exe --selftest .
```

成功结果示例：

```
=== P3Studio Self-Test ===
encode: OK
decode: OK
result: Pass (src=0.84s dst=0.90s delta=0.06s)
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！这是一个小型的专注工具，建议先开 [Issue](https://github.com/adkjkjdsaghj/p3-studio/issues) 讨论你的想法。

**待改进方向：**
- Linux / macOS 支持（需要原生 opus 库）
- MP3 输入支持（通过 FFmpeg 集成或 pydub）
- 拖拽添加文件
- 深色/浅色主题切换
- 音量滑块
- 转换文件列表 + 元数据显示

---

## 📜 开源许可

本项目基于 **MIT License** 开源。详见 [LICENSE](LICENSE) 文件。

---

<div align="center">
为嵌入式 AI 语音助手开发而打造 ❤️
</div>
