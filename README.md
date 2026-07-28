<!-- markdownlint-disable MD033 MD041 -->

<div align="center">

# P3 Studio 🔊

**A lightweight WAV ↔ P3 audio converter & player with a Mecha-themed UI**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows&logoColor=white)]()
[![Opus](https://img.shields.io/badge/Codec-Opus-DA6B20?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2NCIgaGVpZ2h0PSI2NCIgdmlld0JveD0iMCAwIDY0IDY0Ij48cGF0aCBmaWxsPSIjZmZmIiBkPSJNMzIgNkMxNy42IDYgNiAxNy42IDYgMzJzMTEuNiAyNiAyNiAyNiAyNi0xMS42IDI2LTI2UzQ2LjQgNiAzMiA2em0wIDQ4Yy0xMi4xIDAtMjItOS45LTIyLTIyczkuOS0yMiAyMi0yMiAyMiA5LjkgMjIgMjItOS45IDIyLTIyIDIyeiIvPjwvc3ZnPg==)](https://opus-codec.org)

[✨ Features](#-features) • [📦 Installation](#-installation) • [🎮 Usage](#-usage) • [🛠️ Build from Source](#️-build-from-source) • [🏗️ Architecture](#️-architecture) • [📁 Project Structure](#-project-structure) • [🔧 Troubleshooting](#-troubleshooting) • [📜 License](#-license)

</div>

---

## 📖 Overview

P3 Studio is a desktop application for **audio format conversion** and **playback**, specifically designed around the **P3 audio format** — a custom Opus-based container format optimized for embedded AI voice assistant applications (e.g., ESP32-based voice assistants).

The project was originally developed as a toolchain component for the [zhicloud_esp32](https://github.com/adkjkjdsaghj/zhicloud_esp32) board-level project, providing a convenient way to prepare and play audio samples for ESP32 AI voice assistant development.

> **Why P3?** — The `.p3` format wraps Opus-encoded audio at 16 kHz mono, striking the perfect balance between file size and voice clarity. It's ideal for embedded systems where storage and bandwidth are limited, but voice intelligibility is critical.

---

## ✨ Features

### 🔄 Audio Conversion

| Direction | Input | Output | Notes |
|-----------|-------|--------|-------|
| **WAV → P3** | `.wav`, `.flac`, `.ogg` | `.p3` | Automatic resampling to 16 kHz mono, Opus encoding |
| **P3 → WAV** | `.p3` | `.wav` | Decode back to 16 kHz PCM WAV |
| **Batch processing** | Multiple files | Per-file output | Select multiple files; all converted sequentially |

### 🎚️ Loudness Normalization

- **ITU-R BS.1770 LUFS normalization** using `pyloudnorm`
- Default target: **−16 LUFS** (optimal for embedded voice output)
- **Disable for TTS audio** — prevents clipping on pre-optimized speech samples
- Toggle on/off per conversion session

### ▶️ P3 Playback

- Native P3 file playback via `sounddevice` + PortAudio
- Play / Pause / Stop controls
- **Loop mode** for repeated listening
- Playlist management — add / remove files
- Click to select; status bar shows current track and state

### 🎨 Mecha-themed UI

- **Clean white background** with cyan (`#00acc1`) accent color system
- Custom **diamond (◆)** radio indicators and **hex (⬢)** check indicators
- Cyan accent border lines on every panel
- `▶` prefix headers on all section frames (terminal-style)
- Console-like log output area with monospace font
- Professional Tkinter `clam` theme with refined hover/pressed states

### 🧪 Built-in Self-Test

```bash
P3Studio.exe --selftest <output_dir>
```

Runs a complete encode → decode round-trip on a synthetic audio signal **without a GUI**, validates that all dependencies (Opus DLL, PortAudio, Scipy, SoundFile) are functional in the frozen environment. Results written to `selftest_result.txt`.

---

## 📦 Installation

### Option 1: Pre-built EXE (Windows, recommended)

1. Download the latest `P3Studio.exe` from the [Releases](https://github.com/adkjkjdsaghj/p3-studio/releases) page
2. Place it anywhere — no installation required
3. Double-click to launch

> **System requirements**: Windows 10/11, 64-bit. No Python or libraries needed.

### Option 2: Run from Source (Cross-platform)

```bash
# 1. Clone
git clone https://github.com/adkjkjdsaghj/p3-studio.git
cd p3-studio

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python p3_studio.py
```

> **Note on Linux/macOS**: You'll need `libopus` (or `opus.dll` equivalent) installed on your system. The default `opuslib` `find_library` call should locate it automatically.

---

## 🎮 Usage

### Conversion Tab

1. Select **mode**: `音频 → P3` (encode) or `P3 → 音频` (decode)
2. **Add files** — supports `.wav`, `.flac`, `.ogg` for encoding; `.p3` for decoding
3. Toggle **loudness normalization** on/off and set target LUFS
4. Choose **output directory** (defaults to EXE location)
5. Click **开始转换** — progress logged in terminal-style output panel

### Player Tab

1. **Add files** — load `.p3` files into the playlist
2. Select a track from the list
3. Use **▶ 播放 / ⏸ 暂停 / ■ 停止** to control playback
4. Toggle **⬢ 循环播放** for repeat mode
5. Status bar shows `▶ filename` / `⏸ 播放已暂停` / `■ 播放已停止`

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` (on playlist) | Play selected track |
| `Delete` (on playlist) | Remove selected track |

---

## 🛠️ Build from Source

### Build the EXE with PyInstaller

```bash
# Ensure dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build
pyinstaller --noconfirm --onefile --windowed --name "P3Studio" \
  --add-binary "path/to/opus.dll;." \
  --add-binary "path/to/opus.dll;pyogg" \
  --collect-all sounddevice \
  --hidden-import pyloudnorm --hidden-import scipy --hidden-import scipy.signal \
  --hidden-import numpy --hidden-import soundfile --hidden-import opuslib \
  --hidden-import tkinter \
  p3_studio.py
```

**The Opus DLL**: `opus.dll` is required for encoding/decoding. On Windows it ships with the `pyogg` package at `.../site-packages/pyogg/opus.dll`. PyInstaller's `--add-binary` places it in the frozen package root and `pyogg/` subdirectory so that `opuslib`'s `ctypes.find_library('opus')` can locate it.

**PortAudio**: Handled automatically via `--collect-all sounddevice`, which includes the bundled PortAudio binary from `_sounddevice_data/portaudio-binaries/`.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   P3Studio (Tkinter)                │
│  ┌──────────────────┐  ┌─────────────────────────┐  │
│  │  Convert Tab      │  │  Player Tab             │  │
│  │  ┌──────────────┐ │  │  ┌───────────────────┐ │  │
│  │  │ Mode Select  │ │  │  │ Playlist          │ │  │
│  │  │ (Radiobutton)│ │  │  │ (Listbox + Scroll)│ │  │
│  │  ├──────────────┤ │  │  ├───────────────────┤ │  │
│  │  │ File Browser │ │  │  │ Controls          │ │  │
│  │  ├──────────────┤ │  │  │ ▶ ⏸ ■  Loop     │ │  │
│  │  │ Loudness     │ │  │  ├───────────────────┤ │  │
│  │  │ Normalization│ │  │  │ Status Bar        │ │  │
│  │  ├──────────────┤ │  │  └───────────────────┘ │  │
│  │  │ Log Output   │ │  └─────────────────────────┘  │
│  │  │ (Console)    │ │                               │
│  │  └──────────────┘ │                               │
│  └──────────────────┘                                │
└─────────────────────────────────────────────────────┘
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌──────────────────────┐
│ Convert Pipeline│   │ Playback Pipeline     │
│ WAV → Resample  │   │ P3 → Opus Decode     │
│ (scipy.signal)  │   │ → sounddevice        │
│ → Opus Encode   │   │ → PortAudio → Speaker│
│ (opuslib)       │   └──────────────────────┘
│ → P3 File       │
└─────────────────┘
```

### Key Libraries

| Library | Role |
|---------|------|
| **opuslib** | Python bindings for libopus — core encoding/decoding |
| **soundfile** | Read/write WAV, FLAC, OGG audio files |
| **sounddevice** | Playback via PortAudio (cross-platform audio I/O) |
| **scipy.signal** | `resample_poly` for high-quality audio resampling to 16 kHz |
| **pyloudnorm** | ITU-R BS.1770 loudness normalization |
| **numpy** | Audio data array manipulation |
| **PyInstaller** | Packaging into standalone Windows EXE |

### Why not librosa?

The prototyping phase used librosa for audio loading and resampling, but it pulls in **numba + llvmlite**, which balloons the frozen EXE to 150+ MB with slow startup. The final build uses `soundfile` + `scipy.signal.resample_poly` instead — achieving the same quality at **58 MB with fast cold-start**.

---

## 📁 Project Structure

```
p3-studio/
├── p3_studio.py          # Main application (Tkinter GUI + core logic)
├── requirements.txt      # Python dependencies
├── README.md             # This file
├── LICENSE               # MIT License
└── .gitignore            # Git ignore rules
```

---

## 🔧 Troubleshooting

### "opus.dll not found" error

The EXE includes `opus.dll`, but if you see this error in a custom environment:

- **Run from source**: Install `pyogg` or place `opus.dll` in a system PATH directory
- **Run from EXE**: Use `--selftest` to verify the frozen environment; if it passes, the issue is elsewhere

### No audio output (playback)

- Check your system sound settings and speaker connection
- The status bar should show `▶` when playing; if it immediately shows `■`, the file may be corrupted
- Run `P3Studio.exe --selftest .` to verify the playback chain

### Conversion fails on certain WAV files

- The tool expects PCM-encoded WAV. Compressed formats (e.g., WMA, MP3-in-WAV) are not supported
- Convert to standard PCM WAV first using a tool like FFmpeg
- Non-standard sample rates are automatically resampled to 16 kHz

### Large EXE size

The EXE (~58 MB) includes:
- Python runtime and standard library
- NumPy / SciPy numerical libraries
- Opus codec DLL (libopus)
- PortAudio audio I/O library
- All GUI and support code

This is normal for PyInstaller-packaged Python applications with scientific dependencies.

---

## 🧪 Self-Test (Quick Validation)

To verify your copy of P3Studio is working correctly:

```bash
# In the folder containing P3Studio.exe
P3Studio.exe --selftest .
```

This creates a `selftest_result.txt` file. A successful result looks like:

```
=== P3Studio Self-Test ===
encode: OK
decode: OK
result: Pass (src=0.84s dst=0.90s delta=0.06s)
```

---

## 🤝 Contributing

Contributions are welcome! This is a small focused tool, so please open an [issue](https://github.com/adkjkjdsaghj/p3-studio/issues) first to discuss your proposed changes.

**Ideas for improvement:**
- Linux/macOS support (requires native opus library)
- MP3 input support (via FFmpeg integration or pydub)
- Drag-and-drop file adding
- Dark/light theme toggle
- Volume slider
- Converted file list with metadata display

---

## 📜 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<div align="center">
Made with ❤️ for embedded AI voice assistant development
</div>
