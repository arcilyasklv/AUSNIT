# ui/main.py
import os
import sys
import json
import psutil
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image

from ui.utils import resource_path, load_json, check_winget_installed
from backend.install import install_programs
from backend.drivers import install_drivers
from backend.osbuilder import build_usb
from backend.preload import get_cache_path

# --- КОНСТАНТЫ ---
APP_FONT = "Quartell VF"
PALETTE = {"dark": "#2b2b2b", "light": "#e9e7e2"}
ACCENTS = {"zelen": "#2e7d32", "malina": "#d81b60", "slivov": "#6a4c93", "biruza": "#00897b", "ambar": "#ffb300"}
MONITOR_COLORS = {
    "normal": ("#000000", "#FFFFFF"),
    "warning": ("#E65100", "#FFAB40"),
    "critical": ("#B71C1C", "#FF5252")
}

# --- КЛАСС ДЛЯ УПРАВЛЕНИЯ ЛОКАЛИЗАЦИЕЙ ---
class LocalizationManager:
    def __init__(self, lang="ru"):
        self.locales = load_json("data/locales.json")
        self.lang = lang

    def set_language(self, lang):
        if lang in self.locales:
            self.lang = lang

    def get(self, key):
        return self.locales.get(self.lang, {}).get(key, key)


class InstallationTab(ctk.CTkFrame):
    def __init__(self, master, data, install_function, cache, loc: LocalizationManager):
        super().__init__(master, fg_color="transparent")
        self.data = data; self.install_function = install_function; self.cache = cache; self.loc = loc
        self.installed_set = set(map(str.lower, cache.get("installed", {}).get("installed_list_raw", [])))
        self.selected_items = []; self.install_thread = None; self.cancel_event = threading.Event()
        self.category_labels = []; self.check_widgets = []; self.widget_map = {}
        self.accent_buttons = []; self.tooltip_window = None
        self._create_widgets()
        self._populate_list()
        self.update_texts()

    def _log(self, message_key, *args):
        message = self.loc.get(message_key).format(*args)
        self.log_box.configure(state="normal"); self.log_box.insert("end", message + "\n"); self.log_box.see("end"); self.log_box.configure(state="disabled")

    def _create_widgets(self):
        top_frame = ctk.CTkFrame(self); top_frame.pack(side="top", fill="both", expand=True, padx=6, pady=(8, 4))
        left_panel = ctk.CTkFrame(top_frame, fg_color="transparent"); left_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right_frame = ctk.CTkFrame(top_frame, width=280); right_frame.pack(side="left", fill="y"); right_frame.pack_propagate(False)
        selection_frame = ctk.CTkFrame(left_panel); selection_frame.pack(fill="x", pady=(0, 5))
        self.select_all_btn = ctk.CTkButton(selection_frame, command=self._select_all, font=(APP_FONT, 12)); self.select_all_btn.pack(side="left", expand=True, padx=4, pady=4)
        self.deselect_all_btn = ctk.CTkButton(selection_frame, command=self._deselect_all, font=(APP_FONT, 12)); self.deselect_all_btn.pack(side="left", expand=True, padx=4, pady=4)
        self.accent_buttons.extend([self.select_all_btn, self.deselect_all_btn])
        self.container_frame = ctk.CTkFrame(left_panel); self.container_frame.pack(fill="both", expand=True)
        self.specs_label = ctk.CTkLabel(right_frame, font=(APP_FONT, 15, "bold")); self.specs_label.pack(anchor="w", pady=(6, 4), padx=8)
        self.specs_box = ctk.CTkTextbox(right_frame, state="disabled", font=(APP_FONT, 12)); self.specs_box.pack(padx=8, pady=(0, 8), fill="both", expand=True); self._fill_specs()
        self.progress_bar = ctk.CTkProgressBar(self); self.progress_bar.pack(fill="x", padx=8, pady=(6, 4)); self.progress_bar.set(0)
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent"); buttons_frame.pack(fill="x", padx=8, pady=(0, 2))
        self.install_btn = ctk.CTkButton(buttons_frame, command=self._start_installation, state="disabled", font=(APP_FONT, 12)); self.install_btn.pack(side="left", padx=4, pady=2)
        self.cancel_btn = ctk.CTkButton(buttons_frame, command=self._cancel_installation, state="disabled", font=(APP_FONT, 12)); self.cancel_btn.pack(side="left", padx=4, pady=2)
        self.accent_buttons.extend([self.install_btn, self.cancel_btn])
        self.log_box = ctk.CTkTextbox(self, state="disabled", height=80, font=(APP_FONT, 12)); self.log_box.pack(padx=8, pady=(4, 8), fill="x")

    def update_texts(self):
        self.select_all_btn.configure(text=self.loc.get("select_all"))
        self.deselect_all_btn.configure(text=self.loc.get("deselect_all"))
        self.specs_label.configure(text=self.loc.get("pc_specs"))
        self.install_btn.configure(text=self.loc.get("install_button"))
        self.cancel_btn.configure(text=self.loc.get("cancel_button"))

    def _fill_specs(self):
        specs = self.cache.get("specs", {}); lines = [f"OS:  {specs.get('os','-')}", f"CPU: {specs.get('cpu','-')}", f"RAM: {specs.get('ram_total_gb','-')} GB", *[f"Disk {d.get('device','?')} — {d.get('total_gb','?')} GB" for d in specs.get("disks", [])], "Baseboard:", (specs.get('baseboard_raw','') or '-').strip(), "GPU:", (specs.get('gpu_raw','') or '-').strip()]
        self.specs_box.configure(state="normal"); self.specs_box.delete("1.0", "end"); self.specs_box.insert("end", "\n".join(lines)); self.specs_box.configure(state="disabled")

    def _populate_list(self):
        for i in range(2): self.container_frame.grid_rowconfigure(i, weight=1)
        for i in range(3): self.container_frame.grid_columnconfigure(i, weight=1)
        category_items = list(self.data.items())
        for i, (category, items) in enumerate(category_items):
            row, col = i // 3, i % 3
            cat_frame = ctk.CTkFrame(self.container_frame, fg_color="transparent"); cat_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            header_btn = ctk.CTkButton(cat_frame, text=category, font=(APP_FONT, 15, "bold"), state="disabled", text_color_disabled=("white", "white")); header_btn.pack(fill="x")
            self.category_labels.append(header_btn)
            scroll_frame = ctk.CTkScrollableFrame(cat_frame, fg_color="transparent"); scroll_frame.pack(fill="both", expand=True)
            for name, item_id in items.items():
                var = ctk.IntVar(); chk = ctk.CTkCheckBox(scroll_frame, text=name, variable=var, command=lambda i=item_id, v=var: self._toggle_item(i, v), font=(APP_FONT, 12))
                self.check_widgets.append(chk); self.widget_map[item_id] = chk
                if name.lower() in self.installed_set: self._apply_installed_style(chk)
                chk.pack(anchor="w", padx=10, pady=2)

    def _apply_installed_style(self, checkbox_widget):
        strikethrough_font = ctk.CTkFont(family=APP_FONT, size=12, overstrike=True); checkbox_widget.configure(state="disabled", font=strikethrough_font)
        checkbox_widget.bind("<Enter>", self._show_tooltip); checkbox_widget.bind("<Leave>", self._hide_tooltip)
    def _show_tooltip(self, event):
        if self.tooltip_window: self.tooltip_window.destroy()
        self.tooltip_window = ctk.CTkToplevel(self); self.tooltip_window.overrideredirect(True)
        x, y = self.winfo_pointerx() + 15, self.winfo_pointery() + 10; self.tooltip_window.geometry(f"+{x}+{y}")
        label = ctk.CTkLabel(self.tooltip_window, text=self.loc.get("tooltip_installed"), font=(APP_FONT, 10), fg_color="#333333", corner_radius=5, padx=5, pady=2); label.pack()
    def _hide_tooltip(self, event):
        if self.tooltip_window: self.tooltip_window.destroy(); self.tooltip_window = None
    def _update_install_button_state(self): self.install_btn.configure(state="normal" if self.selected_items else "disabled")
    def _toggle_item(self, item_id, var):
        if var.get() == 1 and item_id not in self.selected_items: self.selected_items.append(item_id)
        elif var.get() == 0 and item_id in self.selected_items: self.selected_items.remove(item_id)
        self._update_install_button_state()
    def _select_all(self):
        self.selected_items.clear()
        for item_id, chk in self.widget_map.items():
            if chk.cget("state") == "normal": chk.select(); self.selected_items.append(item_id)
        self._update_install_button_state()
    def _deselect_all(self):
        for chk in self.check_widgets: chk.deselect()
        self.selected_items.clear(); self._update_install_button_state()
    def _start_installation(self):
        if not self.selected_items or (self.install_thread and self.install_thread.is_alive()): return
        self.cancel_event.clear(); self.install_btn.configure(state="disabled"); self.cancel_btn.configure(state="normal")
        ids_to_install = list(self.selected_items); self.install_thread = threading.Thread(target=self._installation_worker, args=(ids_to_install,), daemon=True); self.install_thread.start()
    def _cancel_installation(self): self.cancel_event.set(); self.cancel_btn.configure(state="disabled")
    def _installation_worker(self, item_ids):
        total = len(item_ids); self._log("log_start"); self.progress_bar.set(0)
        for i, item_id in enumerate(item_ids, 1):
            if self.cancel_event.is_set(): self._log("log_cancelled"); break
            result = self.install_function([item_id]); success = result.get(item_id, False)
            self.log_box.configure(state="normal"); self.log_box.insert("end", ("✅ " if success else "❌ ") + item_id + "\n"); self.log_box.see("end"); self.log_box.configure(state="disabled")
            if success:
                widget = self.widget_map.get(item_id)
                if widget: self._apply_installed_style(widget); self.installed_set.add(widget.cget("text").lower())
            self.progress_bar.set(i / total); self.master.master.update_idletasks()
        else: self._log("log_done")
        self.selected_items.clear(); self.cancel_btn.configure(state="disabled"); self.install_btn.configure(state="disabled")

class USBBuilderTab(ctk.CTkFrame):
    def __init__(self, master, loc: LocalizationManager):
        super().__init__(master, fg_color="transparent")
        self.loc = loc; self.iso_path = None; self.accent_buttons = []; self.build_thread = None
        self._create_widgets(); self.update_drive_list(); self.update_texts()

    def _log(self, message_key, *args):
        message = self.loc.get(message_key).format(*args)
        self.log_box.configure(state="normal"); self.log_box.insert("end", message + "\n"); self.log_box.see("end"); self.log_box.configure(state="disabled")

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)
        self.device_label = ctk.CTkLabel(self, font=(APP_FONT, 12)); self.device_label.grid(row=0, column=0, sticky="w", padx=20, pady=(10, 0))
        self.drive_combo = ctk.CTkComboBox(self, font=(APP_FONT, 12)); self.drive_combo.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.choose_iso_btn = ctk.CTkButton(self, command=self._choose_iso, width=120, font=(APP_FONT, 12)); self.choose_iso_btn.grid(row=2, column=1, sticky="e", padx=20, pady=(10, 0))
        self.iso_path_label = ctk.CTkLabel(self, font=(APP_FONT, 12), fg_color=("gray80", "gray20"), corner_radius=5); self.iso_path_label.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 0))
        options_frame = ctk.CTkFrame(self); options_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=10); options_frame.grid_columnconfigure(0, weight=1)
        self.partition_label = ctk.CTkLabel(options_frame, font=(APP_FONT, 12)); self.partition_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.partition_combo = ctk.CTkComboBox(options_frame, values=["GPT", "MBR"], font=(APP_FONT, 12)); self.partition_combo.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10)); self.partition_combo.set("GPT")
        self.target_system_header_label = ctk.CTkLabel(options_frame, font=(APP_FONT, 12)); self.target_system_header_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.target_system_label = ctk.CTkLabel(options_frame, text="UEFI (non CSM)", font=(APP_FONT, 12), fg_color=("gray80", "gray20"), corner_radius=5); self.target_system_label.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        bottom_controls_frame = ctk.CTkFrame(self, fg_color="transparent"); bottom_controls_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=10); bottom_controls_frame.grid_columnconfigure(0, weight=1)
        self.fs_label = ctk.CTkLabel(bottom_controls_frame, font=(APP_FONT, 12)); self.fs_label.grid(row=0, column=0, sticky="w")
        self.fs_combo = ctk.CTkComboBox(bottom_controls_frame, values=["NTFS", "FAT32"], font=(APP_FONT, 12)); self.fs_combo.grid(row=1, column=0, sticky="ew", pady=(0, 10)); self.fs_combo.set("NTFS")
        self.build_button = ctk.CTkButton(bottom_controls_frame, command=self._start_build, font=(APP_FONT, 14, "bold"), height=40); self.build_button.grid(row=0, rowspan=2, column=1, padx=(20, 0))
        self.log_box = ctk.CTkTextbox(self, state="disabled", font=(APP_FONT, 12)); self.log_box.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=20, pady=(0, 10))
        self.accent_buttons.extend([self.choose_iso_btn, self.build_button, self.drive_combo, self.partition_combo, self.fs_combo])

    def update_texts(self):
        self.device_label.configure(text=self.loc.get("usb_device"))
        self.choose_iso_btn.configure(text=self.loc.get("usb_choose_iso"))
        self.iso_path_label.configure(text=self.loc.get("usb_iso_not_selected"))
        self.partition_label.configure(text=self.loc.get("usb_partition_scheme"))
        self.target_system_header_label.configure(text=self.loc.get("usb_target_system"))
        self.fs_label.configure(text=self.loc.get("usb_file_system"))
        self.build_button.configure(text=self.loc.get("usb_start_button"))
        self.update_drive_list()

    def update_drive_list(self):
        try: drives = [f"{p.device} ({psutil.disk_usage(p.mountpoint).total / (1024**3):.1f} GB)" for p in psutil.disk_partitions() if 'removable' in p.opts]
        except: drives = []
        if drives: self.drive_combo.configure(values=drives); self.drive_combo.set(drives[0])
        else: self.drive_combo.configure(values=[self.loc.get("usb_device_not_found")]); self.drive_combo.set(self.loc.get("usb_device_not_found"))
    
    def _choose_iso(self):
        path = filedialog.askopenfilename(title=self.loc.get("usb_choose_iso"), filetypes=[("ISO", "*.iso")])
        if path: self.iso_path = path; self.iso_path_label.configure(text=os.path.basename(path)); self._log("usb_log_iso_selected", os.path.basename(path))
        else: self.iso_path = None; self.iso_path_label.configure(text=self.loc.get("usb_iso_not_selected"))
    
    def _start_build(self):
        if not self.iso_path: self._log("usb_error_no_iso"); return
        if self.loc.get("usb_device_not_found") in self.drive_combo.get(): self._log("usb_error_no_drive"); return
        if self.build_thread and self.build_thread.is_alive(): return
        params = {"iso": self.iso_path, "drive": self.drive_combo.get().split(" ")[0], "partition_scheme": self.partition_combo.get(), "file_system": self.fs_combo.get()}
        self.build_thread = threading.Thread(target=self._build_worker, args=(params,), daemon=True); self.build_thread.start()

    def _build_worker(self, params):
        self.build_button.configure(state="disabled"); self._log("usb_log_start")
        self._log("usb_log_build_params"); self.log_box.configure(state="normal"); self.log_box.insert("end", str(params) + "\n"); self.log_box.configure(state="disabled")
        success = build_usb(params)
        if success: self._log("usb_log_success"); self._log("log_done")
        else: self._log("usb_log_error")
        self.build_button.configure(state="normal")

class SettingsTab(ctk.CTkFrame):
    def __init__(self, master, app_instance, loc: LocalizationManager):
        super().__init__(master, fg_color="transparent")
        self.app = app_instance; self.loc = loc
        self._create_widgets(); self.update_texts()

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        about_frame = ctk.CTkFrame(self); about_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.about_header = ctk.CTkLabel(about_frame, font=(APP_FONT, 16, "bold")); self.about_header.pack(pady=(5,10), padx=10, anchor="w")
        self.about_text = ctk.CTkLabel(about_frame, justify="left", font=(APP_FONT, 12)); self.about_text.pack(pady=5, padx=10, anchor="w")
        ui_frame = ctk.CTkFrame(self); ui_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.ui_header = ctk.CTkLabel(ui_frame, font=(APP_FONT, 16, "bold")); self.ui_header.pack(pady=(5,10), padx=10, anchor="w")
        theme_accent_frame = ctk.CTkFrame(ui_frame, fg_color="transparent"); theme_accent_frame.pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(theme_accent_frame, text="", width=30, height=30, corner_radius=8, fg_color=PALETTE["light"], hover=False, command=lambda: ctk.set_appearance_mode("light")).pack(side="left", padx=(0,5))
        ctk.CTkButton(theme_accent_frame, text="", width=30, height=30, corner_radius=8, fg_color=PALETTE["dark"], hover=False, command=lambda: ctk.set_appearance_mode("dark")).pack(side="left", padx=5)
        for name, color in ACCENTS.items(): ctk.CTkButton(theme_accent_frame, text="", width=30, height=30, corner_radius=8, fg_color=color, hover=False, command=lambda n=name: self.app._apply_accent(n)).pack(side="left", padx=5)
        lang_frame = ctk.CTkFrame(self); lang_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.lang_header = ctk.CTkLabel(lang_frame, font=(APP_FONT, 16, "bold")); self.lang_header.pack(pady=(5,10), padx=10, anchor="w")
        self.lang_segmented_button = ctk.CTkSegmentedButton(lang_frame, values=["RU", "EN", "KZ"], font=(APP_FONT, 12), command=self.app.change_language)
        self.lang_segmented_button.pack(pady=5, padx=10, anchor="w")
        # --- ИСПРАВЛЕНИЕ 1: Устанавливаем кнопку на ТЕКУЩИЙ язык ---
        self.lang_segmented_button.set(self.loc.lang.upper())

    def update_texts(self):
        self.about_header.configure(text=self.loc.get("settings_about_header"))
        self.about_text.configure(text=self.loc.get("settings_about_text"))
        self.ui_header.configure(text=self.loc.get("settings_ui_header"))
        self.lang_header.configure(text=self.loc.get("settings_lang_header"))

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.loc = LocalizationManager()
        self.tab_keys = ["tab_apps", "tab_drivers", "tab_usb", "tab_settings"]
        self.overrideredirect(True); self.geometry("1280x860")
        self._offset_x = 0; self._offset_y = 0; self.current_accent = "zelen"; self.accent_widgets = []
        self._prev_net_io = psutil.net_io_counters()
        self.main_container = ctk.CTkFrame(self, corner_radius=15); self.main_container.pack(fill="both", expand=True, padx=5, pady=5)
        self._create_title_bar()
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent"); self.content_frame.pack(fill="both", expand=True)
        self._load_data()
        self._create_footer()
        self._create_tab_view() 
        
        ctk.set_appearance_mode("dark"); self.after(20, self._apply_accent, self.current_accent, True)
        self.after(100, self._check_dependencies); self.after(1000, self._update_monitor)

    def _create_title_bar(self):
        title_bar = ctk.CTkFrame(self.main_container, height=40, corner_radius=0); title_bar.pack(fill="x", side="top", padx=1, pady=1)
        self.title_label = ctk.CTkLabel(title_bar, font=(APP_FONT, 12, "bold")); self.title_label.pack(side="left", padx=10)
        close_button = ctk.CTkButton(title_bar, text="✕", width=30, height=20, command=self.destroy, fg_color="transparent", hover_color="#B71C1C"); close_button.pack(side="right", padx=5, pady=5)
        title_bar.bind("<ButtonPress-1>", self.start_move); self.title_label.bind("<ButtonPress-1>", self.start_move)
        title_bar.bind("<ButtonRelease-1>", self.stop_move); self.title_label.bind("<ButtonRelease-1>", self.stop_move)
        title_bar.bind("<B1-Motion>", self.do_move); self.title_label.bind("<B1-Motion>", self.do_move)

    def start_move(self, event): self._offset_x, self._offset_y = event.x, event.y
    def stop_move(self, event): self._offset_x, self._offset_y = 0, 0
    def do_move(self, event): self.geometry(f"+{self.winfo_pointerx() - self._offset_x}+{self.winfo_pointery() - self._offset_y}")

    def _load_data(self):
        try: self.cache = json.load(open(get_cache_path(), "r", encoding="utf-8"))
        except: self.cache = {}
        self.programs_data = load_json("data/programs.json"); self.drivers_data = load_json("data/drivers.json")

    def _create_tab_view(self):
        self.tabview = ctk.CTkTabview(self.content_frame, command=self._on_tab_change)
        self.tabview._segmented_button.configure(font=(APP_FONT, 13, "bold"))
        self.tabview.pack(fill="both", expand=True, padx=10, pady=0)
        
        tab_widgets = {}
        for key in self.tab_keys:
            tab_widgets[key] = self.tabview.add(self.loc.get(key))

        self.apps_frame = InstallationTab(tab_widgets["tab_apps"], self.programs_data, install_programs, self.cache, self.loc); self.apps_frame.pack(fill="both", expand=True)
        self.drivers_frame = InstallationTab(tab_widgets["tab_drivers"], self.drivers_data, install_drivers, self.cache, self.loc); self.drivers_frame.pack(fill="both", expand=True)
        self.usb_frame = USBBuilderTab(tab_widgets["tab_usb"], self.loc); self.usb_frame.pack(fill="both", expand=True)
        self.settings_frame = SettingsTab(tab_widgets["tab_settings"], self, self.loc); self.settings_frame.pack(fill="both", expand=True)
        
        self.collect_accent_widgets()
        self.title_label.configure(text=self.loc.get("app_title"))
    
    def _create_footer(self):
        self.footer = ctk.CTkFrame(self.main_container, height=40); self.footer.pack(side="bottom", fill="x", padx=5, pady=(0,5))
        right_mon = ctk.CTkFrame(self.footer, fg_color="transparent"); right_mon.pack(side="right", padx=10, pady=5)
        _, self.cpu_bar, self.cpu_lbl, self.cpu_header = self._create_monitor_bar(right_mon, "CPU"); self.cpu_lbl.master.pack(side="left")
        _, self.ram_bar, self.ram_lbl, self.ram_header = self._create_monitor_bar(right_mon, "RAM"); self.ram_lbl.master.pack(side="left")
        _, self.dsk_bar, self.dsk_lbl, self.dsk_header = self._create_monitor_bar(right_mon, "Disk"); self.dsk_lbl.master.pack(side="left")
        _, self.gpu_bar, self.gpu_lbl, self.gpu_header = self._create_monitor_bar(right_mon, "GPU"); self.gpu_lbl.master.pack(side="left")
        self.net_lbl = ctk.CTkLabel(right_mon, text="↓ 0.0 KB/s | ↑ 0.0 KB/s", font=(APP_FONT, 12, "bold")); self.net_lbl.pack(side="left", padx=10)

    def _create_monitor_bar(self, parent, text_key):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        label = ctk.CTkLabel(frame, text=text_key, font=(APP_FONT, 12, "bold"), width=35, anchor="w"); label.pack(side="left")
        progress_bar = ctk.CTkProgressBar(frame, width=80); progress_bar.pack(side="left", padx=4)
        value_label = ctk.CTkLabel(frame, text="0%", font=(APP_FONT, 12, "bold"), width=40, anchor="w"); value_label.pack(side="left", padx=(4, 10))
        return frame, progress_bar, value_label, label

    def collect_accent_widgets(self):
        if hasattr(self, 'tabview') and self.tabview.winfo_exists():
            self.accent_widgets = [self.apps_frame.progress_bar, self.drivers_frame.progress_bar, self.settings_frame.lang_segmented_button, self.cpu_bar, self.ram_bar, self.dsk_bar, self.gpu_bar, *self.apps_frame.accent_buttons, *self.drivers_frame.accent_buttons, *self.usb_frame.accent_buttons, *self.apps_frame.category_labels, *self.drivers_frame.category_labels]

    def _on_tab_change(self):
        current_tab_name = self.tabview.get()
        if current_tab_name == self.loc.get("tab_usb"):
             self.usb_frame.update_drive_list()

    def _apply_accent(self, name, initial=False):
        if not initial and self.current_accent == name: return
        self.current_accent = name; color = ACCENTS[name]
        if hasattr(self, 'tabview') and self.tabview.winfo_exists():
            self.tabview._segmented_button.configure(selected_color=color, selected_hover_color=color)
        for widget in self.accent_widgets:
            if widget.winfo_exists():
                try:
                    if isinstance(widget, ctk.CTkProgressBar): widget.configure(progress_color=color)
                    elif isinstance(widget, ctk.CTkButton): widget.configure(fg_color=color, hover_color=color)
                    elif isinstance(widget, ctk.CTkSegmentedButton): widget.configure(selected_color=color, selected_hover_color=color)
                    elif isinstance(widget, ctk.CTkComboBox): widget.configure(button_color=color, button_hover_color=color)
                except Exception: pass
    
    def change_language(self, lang_value):
        # --- ИСПРАВЛЕНИЕ 2: Прячем окно на время обновления ---
        self.withdraw()

        current_tab_name = self.tabview.get()
        current_lang_tab_names = [self.loc.get(key) for key in self.tab_keys]
        try:
            current_index = current_lang_tab_names.index(current_tab_name)
        except ValueError:
            current_index = 0

        self.loc.set_language(lang_value.lower())
        self.tabview.destroy()
        self._create_tab_view()
        self._apply_accent(self.current_accent, initial=True)
        
        new_tab_name = self.loc.get(self.tab_keys[current_index])
        self.tabview.set(new_tab_name)

        # Возвращаем окно после всех изменений
        self.deiconify()
        
    def _update_monitor(self):
        cpu_percent = psutil.cpu_percent(); ram_percent = psutil.virtual_memory().percent
        self.cpu_bar.set(cpu_percent / 100); self.cpu_lbl.configure(text=f"{cpu_percent:.0f}%")
        self.ram_bar.set(ram_percent / 100); self.ram_lbl.configure(text=f"{ram_percent:.0f}%")
        try: dsk_usage = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + os.sep).percent
        except: dsk_usage = 0
        self.dsk_bar.set(dsk_usage / 100); self.dsk_lbl.configure(text=f"{dsk_usage:.0f}%")
        self.gpu_bar.set(0); self.gpu_lbl.configure(text=f"N/A")
        now_net_io = psutil.net_io_counters()
        sent_speed = (now_net_io.bytes_sent - self._prev_net_io.bytes_sent) / 1024
        recv_speed = (now_net_io.bytes_recv - self._prev_net_io.bytes_recv) / 1024
        self._prev_net_io = now_net_io
        self.net_lbl.configure(text=f"↓ {recv_speed:.1f} KB/s | ↑ {sent_speed:.1f} KB/s")
        mode = ctk.get_appearance_mode().lower(); color_index = 0 if mode == "light" else 1
        def get_color(value):
            if value > 90: return MONITOR_COLORS["critical"][color_index]
            if value > 75: return MONITOR_COLORS["warning"][color_index]
            return MONITOR_COLORS["normal"][color_index]
        self.cpu_lbl.configure(text_color=get_color(cpu_percent)); self.ram_lbl.configure(text_color=get_color(ram_percent)); self.dsk_lbl.configure(text_color=get_color(dsk_usage))
        self.after(1000, self._update_monitor)

    def _check_dependencies(self):
        if not check_winget_installed():
            messagebox.showerror(self.loc.get("winget_error_title"), self.loc.get("winget_error_text"))
            try:
                app_tab_name = self.loc.get("tab_apps")
                self.tabview.delete(app_tab_name)
            except Exception: pass