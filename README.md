# AirControl ???

A **vibe-coded** hand gesture control agent for Windows.  
Wave your hand in front of the camera to move the mouse, click, scroll, and trigger custom macros ? like a real-life Minority Report interface.

## Features

| Gesture | Action |
|---------|--------|
| ?? Index finger up | Move cursor |
| ?? Thumb + index pinch | Left click |
| ?? Index + middle up, ring down | Scroll |
| ?? Air draw a circle | Win+Shift+S (snipping tool) |
| ?? Three fingers open ? draw ? release | Record & save custom gesture |

-  **Face orientation early exit** ? look away or leave, CPU drops to ~0%, zero false touch
-  **DTW gesture recognition** ? dynamic time warping matches trajectory shapes, no cold-start
-  **Comfort zone calibration** ? hand only needs to move in a small area, interpolated to full screen
-  **Real-time Siri-style glow shell** ? fullscreen transparent overlay with cyberpunk gradient animation
-  **System tray persistence** ? close button hides to tray, agent stays running
-  **JSON config persistence** ? slider adjustments survive restart

## Quick Start

```bash
pip install -r requirements.txt
python -m src.main
```

### Controls
- **Ctrl+C** in terminal to quit
- Dashboard shows on launch with master toggle, theme selector, gesture matrix
- Close dashboard ? hides to system tray (double-click tray icon to restore)

## Build Standalone EXE

```bash
pip install pyinstaller
python build_app.py
# Find AirControl.exe in dist/
```

## Project Structure

```
src/
??? config.py            # Central threshold management + JSON persistence
??? main.py              # Engine: poison pill thread lifecycle
??? vision/
?   ??? pipeline.py      # FaceMesh early exit + MediaPipe hands + DTW
?   ??? dtw_recognizer.py # Pure numpy DTW matcher
??? control/
?   ??? os_mapper.py     # Adaptive smoother + click lock + comfort zone mapping
??? ui/
    ??? siri_window.py   # Fullscreen transparent glow overlay
    ??? main_dashboard.py # 800x550 control center
    ??? settings_window.py # Quick-access floating panel
```

## Tech Stack

`opencv-python` ? `mediapipe` ? `pynput` ? `PyQt5` ? `numpy`

---
*Built with vibe coding, ChatGPT-powered iteration, and a webcam.*
