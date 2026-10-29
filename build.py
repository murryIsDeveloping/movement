"""Build the packaged app for the current OS. Output lands in dist/.

  python build.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    for d in ("build", "dist"):
        shutil.rmtree(ROOT / d, ignore_errors=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "movement.spec"], cwd=ROOT, check=True)
    if sys.platform == "darwin":
        app = ROOT / "dist" / "Movement.app"
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], check=True)
        print(f"Built {app}")
    else:
        print(f"Built {ROOT / 'dist' / 'Movement' / 'Movement.exe'}")


if __name__ == "__main__":
    main()
