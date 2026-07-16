# AirControl

A **vibe-coded** hand gesture control agent for Windows.
Wave your hand in front of the camera to move the mouse, click, scroll, and trigger custom macros.

## Features

| Gesture | Action |
|---------|--------|
| :point_up: Index finger up | Move cursor |
| :pinched_fingers: Thumb + index pinch | Left click |
| :vulcan_salute: Index + middle up, ring down | Scroll |
| :o: Air draw a circle | Win+Shift+S (snipping tool) |
| :raised_hand: Three fingers open :arrow_right: draw :arrow_right: release | Record and save custom gesture |

- :eyes: **Face orientation early exit** : look away or leave, CPU drops to ~0%, zero false touch
- :chart_with_upwards_trend: **DTW gesture recognition** : dynamic time warping matches trajectory shapes, no cold-start
- :dart: **Comfort zone calibration** : hand only needs to move in a small area, interpolated to full screen
- :sparkles: **Real-time Siri-style glow shell** : fullscreen transparent overlay with cyberpunk gradient animation and state-aware capsule
- :desktop: **System tray persistence** : close button hides to tray, agent stays running
- :floppy_disk: **JSON config persistence** : slider adjustments survive restart

## Quick Start

`ash
pip install -r requirements.txt
python -m src.main
`

### Controls
- **Ctrl+C** in terminal to quit
- Dashboard shows on launch with master toggle, theme selector, gesture matrix
- Close dashboard :arrow_right: hides to system tray (double-click tray icon to restore)

## Build Standalone EXE

`ash
pip install pyinstaller
python build_app.py
# Find AirControl.exe in dist/
`

## Project Structure

`
src/
    config.py            # Central threshold management + JSON persistence
    main.py              # Engine: poison pill thread lifecycle
    vision/
        pipeline.py      # FaceMesh early exit + MediaPipe hands + DTW
        dtw_recognizer.py # Pure numpy DTW matcher
    control/
        os_mapper.py     # Adaptive smoother + click lock + comfort zone mapping
    ui/
        siri_window.py   # Fullscreen transparent glow overlay + GlowCapsule (glassmorphism + gradient border)
        main_dashboard.py # 800x550 control center
        settings_window.py # Quick-access floating panel
`

## Tech Stack

opencv-python :arrow_right: mediapipe :arrow_right: pynput :arrow_right: PyQt5 :arrow_right: 
umpy

---
*Built with vibe coding, ChatGPT-powered iteration, and a webcam.*
