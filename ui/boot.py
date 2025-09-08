# ui/boot.py
import sys
import os
import traceback
from datetime import datetime
import customtkinter as ctk
import time

# Этот блок должен быть первым
if getattr(sys, 'frozen', False):
    project_root = sys._MEIPASS
    log_dir = os.path.dirname(sys.executable)
else:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    log_dir = project_root
if project_root not in sys.path:
    sys.path.insert(0, project_root)

log_file_path = os.path.join(log_dir, "error_log.txt")

try:
    from backend.preload import start_preload, get_cache_path
    from ui.splash import SplashScreen
    from ui.main import App
    from ui.utils import resource_path

    # --- НОВАЯ, НАДЁЖНАЯ ЛОГИКА ЗАПУСКА ---

    # 1. Запускаем фоновую загрузку данных
    cache_path = get_cache_path()
    preload_thread = start_preload(target_cache_path=cache_path)

    # 2. Создаем временный рут для заставки, чтобы избежать окна "tk"
    splash_root = ctk.CTk()
    splash_root.withdraw() # Держим его невидимым

    # 3. Загружаем кастомный шрифт до создания основного окна
    ctk.FontManager.load_font(resource_path("assets/Quartell VF.ttf"))

    # 4. Создаем и показываем окно заставки
    splash = SplashScreen(splash_root)
    splash_start_time = time.time()
    min_splash_duration = 4.0

    # 5. Главный цикл для заставки, ждем завершения фоновой задачи
    while preload_thread.is_alive() or (time.time() - splash_start_time) < min_splash_duration:
        splash_root.update()
        time.sleep(0.01)
    
    # 6. Закрываем заставку и её временный рут
    splash.stop()
    splash_root.destroy()

    # 7. Теперь создаем и запускаем основное приложение
    app = App()
    app.mainloop()
    
except Exception as e:
    # --- Блок перехвата любой ошибки ---
    error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_message = f"--- ОШИБКА ---\nВремя: {error_time}\n"
    error_message += f"Тип ошибки: {type(e).__name__}\nСообщение: {e}\n\n"
    error_message += "--- TRACEBACK ---\n"
    error_message += traceback.format_exc()
    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write(error_message)