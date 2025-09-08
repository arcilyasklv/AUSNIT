# ui/splash.py
import customtkinter as ctk
from PIL import Image
from ui.utils import resource_path

class SplashScreen(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        
        TARGET_WIDTH = 720
        TARGET_HEIGHT = 480
        
        self.overrideredirect(True)
        
        # --- ИСПРАВЛЕННАЯ ЛОГИКА ПРОЗРАЧНОСТИ ---
        # Вместо "systemTransparent" используем обычный "black"
        # Этот цвет будет сделан полностью прозрачным.
        self.config(bg="black") 
        self.attributes("-transparentcolor", "black")
        self.lift()

        try:
            img_original = Image.open(resource_path("assets/intro.png"))
            img_resized = img_original.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
            splash_img = ctk.CTkImage(light_image=img_resized, dark_image=img_resized, size=(TARGET_WIDTH, TARGET_HEIGHT))
            
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = (screen_width - TARGET_WIDTH) // 2
            y = (screen_height - TARGET_HEIGHT) // 2
            self.geometry(f"{TARGET_WIDTH}x{TARGET_HEIGHT}+{x}+{y}")
            
            # Указываем, что у самого лейбла фон тоже черный
            label = ctk.CTkLabel(self, text="", image=splash_img, bg_color="black")
            label.pack()

        except Exception as e:
            print(f"ОШИБКА: Не удалось загрузить splash-изображение: {e}")
            self.geometry("400x200")

    def stop(self):
        self.destroy()