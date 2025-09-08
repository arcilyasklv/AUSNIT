# backend/preload.py
import threading, time, psutil, platform, subprocess, json, os, tempfile, sys
from datetime import datetime

RESULT = {}
DONE = threading.Event()

# --- Вспомогательные функции для загрузки данных ---
def _resource_path(rel_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, rel_path)

def _load_json(rel_path):
    path = _resource_path(rel_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _safe(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, timeout=25, encoding='utf-8', errors='ignore')
    except Exception as e:
        print(f"Ошибка при выполнении команды '{cmd}': {e}")
        return ""

def collect_specs():
    specs = {}
    specs["timestamp"] = datetime.now().isoformat(timespec="seconds")
    specs["os"] = platform.platform()
    cpu_name = platform.processor() or _safe("wmic cpu get Name /value").strip()
    if "Name=" in cpu_name:
        cpu_name = cpu_name.split("=",1)[-1].strip()
    specs["cpu"] = cpu_name or "Unknown CPU"
    vm = psutil.virtual_memory()
    specs["ram_total_gb"] = round(vm.total / (1024**3), 2)
    specs["disks"] = []
    for p in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(p.mountpoint)
            specs["disks"].append({"device": p.device, "mount": p.mountpoint, "total_gb": round(u.total / (1024**3), 2), "used_gb": round(u.used / (1024**3), 2)})
        except Exception: pass
    base = _safe("wmic baseboard get Product,Manufacturer,Version,SerialNumber /format:list")
    specs["baseboard_raw"] = base.strip()
    gpu = _safe("wmic path win32_VideoController get name /value")
    specs["gpu_raw"] = gpu.strip()
    return specs

def scan_installed_programs():
    programs_data = _load_json("data/programs.json")
    drivers_data = _load_json("data/drivers.json")
    
    known_ids = {}
    for category in programs_data.values():
        for name, pid in category.items():
            known_ids[pid.lower()] = name
    for category in drivers_data.values():
        for name, did in category.items():
            known_ids[did.lower()] = name
            
    out = _safe("winget list")
    installed_names = set()
    
    for line in out.splitlines():
        line_lower = line.lower()
        for pid, name in known_ids.items():
            if pid in line_lower:
                installed_names.add(name.lower())
                break

    return {"installed_list_raw": sorted(list(installed_names))}

def run_all(target_cache_path=None):
    global RESULT
    try:
        RESULT["specs"] = collect_specs()
        RESULT["installed"] = scan_installed_programs()
        if target_cache_path:
            with open(target_cache_path, "w", encoding="utf-8") as f:
                json.dump(RESULT, f, ensure_ascii=False, indent=2)
    finally:
        DONE.set()

def start_preload(target_cache_path=None):
    t = threading.Thread(target=run_all, args=(target_cache_path,), daemon=True)
    t.start()
    return t

def get_cache_path():
    return os.path.join(tempfile.gettempdir(), "ausnit_boot_cache.json")