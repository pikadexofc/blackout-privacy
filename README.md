# Blackout Privacy 🛡️

A zero-dependency, ultra-lightweight Windows desktop privacy app for screen sharing on **Google Meet, Zoom, Microsoft Teams, Discord, WebRTC**, and any screen recording/capture tool.

---

## 💡 What it Does

When you are screen sharing and need to quickly do something private (check passwords, open private tabs, view confidential documents):

1. **Click the Single Button** (or press `Ctrl + Alt + B`).
2. **Your screen immediately turns solid black to viewers / screen sharing platforms.**
3. **Your monitor stays completely visible, interactive, and transparent to you.** You can click, type, and do your work without anyone on the call seeing anything!
4. **Click the button again** (or press `Ctrl + Alt + B`) to instantly bring your screen share back to life!

---

## ⚡ How It Works (Technical Architecture)

Unlike software that pauses screen sharing (which alerts everyone or freezes the last frame), **Blackout Privacy** uses the native Windows Desktop Window Manager (DWM) display affinity subsystem:

1. **Virtual Screen Coverage:** Automatically maps and spans all connected monitors (`SM_XVIRTUALSCREEN`, `SM_YVIRTUALSCREEN`, `SM_CXVIRTUALSCREEN`, `SM_CYVIRTUALSCREEN`).
2. **Layered Click-Through:** Creates a top-level window with `WS_EX_LAYERED`, `WS_EX_TRANSPARENT`, and `WS_EX_TOPMOST`.
3. **Alpha Invisibility:** Sets window alpha to 1/255 (invisible to human eye locally, click and key events pass straight through).
4. **Display Affinity (`WDA_MONITOR = 0x1`):** Instructs the Windows DWM engine that this window must only render on a physical display. When any capture pipeline (Desktop Duplication, WebRTC, BitBlt, Windows Graphics Capture) asks for a frame, Windows replaces the entire region with **solid opaque black (`0x000000`)**.

---

## 🚀 Quick Start

### Prerequisites
- Windows 10 (Version 2004 / Build 19041 or newer) or Windows 11.
- Python 3.8+ (Zero external pip packages needed! Uses built-in `ctypes` and `tkinter`).

### Running the App
Double-click `run.bat` or run:
```bash
python app.py
```

### Hotkey
- `Ctrl + Alt + B`: Instantly toggle screen blackout on or off from any active window or game.

---

## 💬 Integrated GitHub Feedback
The app features a built-in feedback button. Users can submit ideas, bug reports, and suggestions directly into this repository's GitHub Issues via the GitHub CLI (`gh`) or directly via their browser.

---

## 🧪 Automated Testing
Run the included verification suite:
```bash
python test_blackout.py
```
This test objectively verifies:
- Multi-monitor virtual desktop metric resolution.
- Window handle allocation and display affinity enforcement.
- Real-time BitBlt capture inspection ensuring pixels read pure black `0x0`.
- Deactivation and memory cleanup.

---

## 📜 License
MIT License.
