# ui/utils.py
import sys
import os
import json
import subprocess

CREATE_NO_WINDOW = 0x08000000

def resource_path(relative_path):
    """
    Получает абсолютный путь к ресурсу.
    Работает как для запуска из скрипта, так и для собранного .exe файла.
    """
    try:
        # PyInstaller создает временную папку и сохраняет путь в sys._MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Если запускается не .exe, то получаем путь к корню проекта (на уровень выше папки ui)
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    return os.path.join(base_path, relative_path)

def load_json(rel_path):
    """ Безопасно загружает JSON файл, используя правильный путь. """
    path = resource_path(rel_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка загрузки файла {path}: {e}")
        return {}

def check_winget_installed():
    """
    Проверяет, доступна ли команда winget в системе.
    Возвращает True, если доступна, иначе False.
    """
    try:
        subprocess.run(
            ["winget", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
            check=True
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False