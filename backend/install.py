# backend/install.py
import subprocess
from typing import List, Dict

CREATE_NO_WINDOW = 0x08000000  # не показывать чёрное окно

def _run(cmd: list[str]) -> bool:
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=CREATE_NO_WINDOW,
            shell=False
        )
        return p.returncode == 0
    except Exception:
        return False

def install_programs(ids: List[str]) -> Dict[str, bool]:
    results: Dict[str, bool] = {}
    for pkg in ids:
        cmd = [
            "winget", "install", "-e",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--id", pkg
        ]
        results[pkg] = _run(cmd)
    return results
