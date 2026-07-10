# build_app.py
import os
import sys
import subprocess
import site


def get_mediapipe_path():
    search_paths = list(site.getsitepackages())
    user_path = site.getusersitepackages()
    if user_path:
        search_paths.append(user_path)
    for sp in search_paths:
        mp_path = os.path.join(sp, "mediapipe")
        if os.path.exists(mp_path):
            return mp_path
    raise FileNotFoundError(
        "MediaPipe not found. Run: pip install mediapipe"
    )


def run_bundling():
    print("[Packager] AirControl 1.0 build starting...")

    try:
        mp_src_dir = get_mediapipe_path()
        print(f"[Packager] MediaPipe assets found: {mp_src_dir}")
    except Exception as e:
        print(f"[Error] {e}")
        return

    sep = ";" if sys.platform.startswith("win") else ":"
    mediapipe_add_data = f"{mp_src_dir}{sep}mediapipe"

    command = [
        "pyinstaller",
        "--clean",
        "--onefile",
        "--noconsole",
        f"--add-data={mediapipe_add_data}",
        "--name=AirControl",
        os.path.join("src", "main.py"),
    ]

    print(f"[Packager] Running: {' '.join(command)}")
    subprocess.run(command, check=True)
    print("\n[Packager] Success! Find the .exe in dist/ folder.")


if __name__ == "__main__":
    run_bundling()
