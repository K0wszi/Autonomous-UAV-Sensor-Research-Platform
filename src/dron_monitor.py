import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import serial
import serial.tools.list_ports
import threading
import datetime
import csv
import os
import time
import platform
import subprocess
import glob
import winsound
from collections import deque 

# Matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation

# --- KONFIGURACJA ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

COLORS = {
    "bg": "#141416",
    "panel": "#23262f",
    "accent_blue": "#3772ff",     
    "accent_purple": "#9757d7",
    "accent_green": "#45b26b",    
    "accent_red": "#ef466f",      
    "accent_orange": "#ffbc99",   
    "text_main": "#fcfcfd",
    "text_dim": "#777e90",
    "plot_bg": "#1e1e24",        
    "grid_color": "#353945"
}

# --- HISTORIA: 5 POMIARÓW ---
HISTORY_SIZE = 5 

class CircularProgress(tk.Canvas):
    def __init__(self, parent, width=140, height=140, color=COLORS["accent_blue"], max_val=800):
        super().__init__(parent, width=width, height=height, bg=COLORS["panel"], bd=0, highlightthickness=0)
        self.max_val = max_val
        self.stroke_width = 12
        self.radius = (min(width, height) / 2) - 15
        self.center_x = width / 2
        self.center_y = height / 2
        self.color = color
        
        self.create_arc(self.center_x - self.radius, self.center_y - self.radius,
                        self.center_x + self.radius, self.center_y + self.radius,
                        start=135, extent=-270, style="arc", width=self.stroke_width, outline="#353945")
        
        self.progress_arc = self.create_arc(self.center_x - self.radius, self.center_y - self.radius,
                                            self.center_x + self.radius, self.center_y + self.radius,
                                            start=135, extent=0, style="arc", width=self.stroke_width, outline=self.color)
        
        self.text_id = self.create_text(self.center_x, self.center_y, text="0", fill="white", font=("Roboto Medium", 22))
        self.create_text(self.center_x, self.center_y + 20, text="mm", fill="#777e90", font=("Roboto", 10))

    def set_value(self, value):
        if value < 0: value = 0
        if value > self.max_val: value = self.max_val
        percentage = value / self.max_val
        extent = -270 * percentage
        self.itemconfig(self.progress_arc, extent=extent)
        self.itemconfig(self.text_id, text=f"{int(value)}")

class DashboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Drone Sense // Advanced Lab v5.2")
        self.geometry("1350x900")
        self.configure(fg_color=COLORS["bg"])
        
        self.ser = None
        self.is_running = False
        self.filename = "pomiary_lab_full.csv"
        self.last_hit_time = 0
        self.merged_view = False 

        # --- BUFORY DANYCH ---
        self.plot_len = 100
        self.y_ultra = deque([0]*self.plot_len, maxlen=self.plot_len)
        self.y_sharp = deque([0]*self.plot_len, maxlen=self.plot_len)
        self.y_laser = deque([0]*self.plot_len, maxlen=self.plot_len)
        
        # Bufor historii do CSV
        self.history_buffer = deque(maxlen=HISTORY_SIZE)

        self.init_csv()
        self.setup_ui()
        self.scan_ports()

        self.ani = animation.FuncAnimation(self.fig, self.animate_plot, interval=100, blit=False)

    def init_csv(self):
        # Sprawdź czy plik istnieje I czy nie jest pusty
        file_exists = os.path.exists(self.filename)
        file_is_empty = False
        if file_exists:
            if os.path.getsize(self.filename) == 0:
                file_is_empty = True
        
        # Jeśli nie istnieje LUB jest pusty -> Utwórz nagłówki
        if not file_exists or file_is_empty:
            try:
                with open(self.filename, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, delimiter=';')
                    # TWORZENIE NAGŁÓWKÓW
                    writer.writerow(["Data", "Godzina", "Material", "Event_Type", "Offset_ID", "Limit[mm]", "Ultra[mm]", "Sharp[mm]", "Laser[mm]", "Trigger"])
            except Exception as e:
                print(f"Błąd tworzenia pliku: {e}")

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === SIDEBAR ===
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color=COLORS["panel"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="DRONE SENSE", font=("Roboto", 20, "bold")).grid(row=0, column=0, padx=20, pady=(30, 10), sticky="w")
        
        # Connect
        self.combo_ports = ctk.CTkComboBox(self.sidebar, values=[], state="readonly")
        self.combo_ports.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.btn_connect = ctk.CTkButton(self.sidebar, text="POŁĄCZ", fg_color=COLORS["accent_blue"], command=self.toggle_connection)
        self.btn_connect.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        # Materiał
        ctk.CTkLabel(self.sidebar, text="MATERIAŁ:", font=("Roboto", 10, "bold"), text_color=COLORS["text_dim"]).grid(row=4, column=0, padx=20, pady=(20, 5), sticky="w")
        self.entry_mat = ctk.CTkEntry(self.sidebar, placeholder_text="np. Szkło")
        self.entry_mat.insert(0, "Testowy")
        self.entry_mat.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

        # Slider
        ctk.CTkLabel(self.sidebar, text="PRÓG DETEKCJI:", font=("Roboto", 10, "bold"), text_color=COLORS["text_dim"]).grid(row=6, column=0, padx=20, pady=(20, 5), sticky="w")
        self.lbl_thresh = ctk.CTkLabel(self.sidebar, text="12 cm", font=("Roboto", 12, "bold"), text_color="white")
        self.lbl_thresh.grid(row=7, column=0, padx=20, pady=0, sticky="w")
        self.slider = ctk.CTkSlider(self.sidebar, from_=5, to=50, number_of_steps=45, command=self.on_slider_change)
        self.slider.set(12)
        self.slider.grid(row=8, column=0, padx=20, pady=10, sticky="ew")

        # Plot Toggle
        self.btn_plot_mode = ctk.CTkButton(self.sidebar, text="🔀 WSPÓLNY WYKRES", fg_color=COLORS["panel"], border_width=1, border_color="#555", command=self.toggle_plot_mode)
        self.btn_plot_mode.grid(row=9, column=0, padx=20, pady=30, sticky="ew")

        # Files
        ctk.CTkLabel(self.sidebar, text="BAZA DANYCH (CSV)", font=("Roboto", 10, "bold"), text_color=COLORS["text_dim"]).grid(row=10, column=0, padx=20, pady=(10,5), sticky="w")
        self.history_list = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent", height=200)
        self.history_list.grid(row=11, column=0, padx=10, pady=5, sticky="nsew")
        self.refresh_file_list()

        # === MAIN ===
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Status
        self.top_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.top_frame.pack(fill="x", pady=(0, 20))
        self.lbl_status = ctk.CTkLabel(self.top_frame, text="ROZŁĄCZONY", font=("Roboto", 24, "bold"), text_color=COLORS["text_dim"])
        self.lbl_status.pack(side="left")
        self.lbl_countdown = ctk.CTkLabel(self.top_frame, text="", font=("Roboto Mono", 24, "bold"), text_color=COLORS["accent_orange"])
        self.lbl_countdown.pack(side="right", padx=20)

        # Gauges
        self.gauges_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.gauges_frame.pack(fill="x", pady=10)
        self.gauges_frame.grid_columnconfigure((0,1,2), weight=1)
        self.gauge_u = self.create_gauge_card(self.gauges_frame, 0, "Ultra", COLORS["accent_orange"])
        self.gauge_s = self.create_gauge_card(self.gauges_frame, 1, "Sharp", COLORS["accent_red"])
        self.gauge_l = self.create_gauge_card(self.gauges_frame, 2, "Laser", COLORS["accent_blue"])

        # Plots
        self.plot_frame = ctk.CTkFrame(self.main_area, fg_color=COLORS["panel"], corner_radius=10)
        self.plot_frame.pack(fill="both", expand=True, pady=20)
        
        self.fig = Figure(figsize=(8, 4), dpi=100, facecolor=COLORS["panel"])
        self.ax1 = self.fig.add_subplot(311)
        self.ax2 = self.fig.add_subplot(312, sharex=self.ax1)
        self.ax3 = self.fig.add_subplot(313, sharex=self.ax1)
        self.style_plots()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def create_gauge_card(self, parent, col, title, color):
        card = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=15)
        card.grid(row=0, column=col, padx=10, sticky="ew")
        ctk.CTkFrame(card, height=4, fg_color=color).pack(fill="x", padx=30, pady=(0,10))
        ctk.CTkLabel(card, text=title, font=("Roboto", 14, "bold")).pack()
        g = CircularProgress(card, color=color)
        g.pack(pady=15)
        return g

    def style_plots(self):
        for ax in [self.ax1, self.ax2, self.ax3]:
            ax.set_facecolor(COLORS["plot_bg"])
            ax.tick_params(colors=COLORS["text_dim"], labelsize=8)
            ax.spines['bottom'].set_color(COLORS["grid_color"])
            ax.spines['top'].set_color(COLORS["grid_color"])
            ax.spines['left'].set_color(COLORS["grid_color"])
            ax.spines['right'].set_color(COLORS["grid_color"])
            ax.grid(True, color=COLORS["grid_color"], linestyle='--', alpha=0.5)

        self.line_u, = self.ax1.plot([], [], color=COLORS["accent_orange"], lw=2)
        self.line_s, = self.ax2.plot([], [], color=COLORS["accent_red"], lw=2)
        self.line_l, = self.ax3.plot([], [], color=COLORS["accent_blue"], lw=2)
        
        self.ax1.set_ylim(0, 800)
        self.ax2.set_ylim(0, 800)
        self.ax3.set_ylim(0, 800)
        self.ax1.set_xticklabels([])
        self.ax2.set_xticklabels([])

    def toggle_plot_mode(self):
        self.merged_view = not self.merged_view
        self.fig.clf()
        if self.merged_view:
            self.btn_plot_mode.configure(text="🔀 ROZDZIEL WYKRESY", fg_color=COLORS["accent_blue"])
            self.ax_merged = self.fig.add_subplot(111)
            self.ax_merged.set_facecolor(COLORS["plot_bg"])
            self.ax_merged.tick_params(colors=COLORS["text_dim"])
            self.ax_merged.grid(True, color=COLORS["grid_color"], alpha=0.5)
            self.ax_merged.set_ylim(0, 800)
            self.line_u, = self.ax_merged.plot([], [], color=COLORS["accent_orange"], lw=2, label="Ultra")
            self.line_s, = self.ax_merged.plot([], [], color=COLORS["accent_red"], lw=2, label="Sharp")
            self.line_l, = self.ax_merged.plot([], [], color=COLORS["accent_blue"], lw=2, label="Laser")
            self.ax_merged.legend(loc="upper right", facecolor=COLORS["panel"], labelcolor="white")
        else:
            self.btn_plot_mode.configure(text="🔀 WSPÓLNY WYKRES", fg_color=COLORS["panel"])
            self.ax1 = self.fig.add_subplot(311)
            self.ax2 = self.fig.add_subplot(312, sharex=self.ax1)
            self.ax3 = self.fig.add_subplot(313, sharex=self.ax1)
            self.style_plots()
        self.canvas.draw()

    def animate_plot(self, i):
        if not self.is_running: return
        x_vals = list(range(len(self.y_ultra)))
        if self.merged_view:
            self.line_u.set_data(x_vals, self.y_ultra)
            self.line_s.set_data(x_vals, self.y_sharp)
            self.line_l.set_data(x_vals, self.y_laser)
            self.ax_merged.set_xlim(0, self.plot_len)
        else:
            self.line_u.set_data(x_vals, self.y_ultra)
            self.line_s.set_data(x_vals, self.y_sharp)
            self.line_l.set_data(x_vals, self.y_laser)
            self.ax1.set_xlim(0, self.plot_len)
            self.ax2.set_xlim(0, self.plot_len)
            self.ax3.set_xlim(0, self.plot_len)

    def refresh_file_list(self):
        for w in self.history_list.winfo_children(): w.destroy()
        files = glob.glob("*.csv")
        files.sort(key=os.path.getmtime, reverse=True)
        for f in files:
            ctk.CTkButton(self.history_list, text=f, fg_color="transparent", border_width=1, 
                          border_color="#444", text_color="white", anchor="w",
                          command=lambda x=f: self.open_file(x)).pack(fill="x", pady=2)

    def open_file(self, filename):
        try: os.startfile(filename)
        except: pass

    def on_slider_change(self, val):
        cm = int(val)
        self.lbl_thresh.configure(text=f"{cm} cm")
        if self.ser and self.ser.is_open:
            try: self.ser.write(f"T{cm*10}\n".encode())
            except: pass

    def scan_ports(self):
        ports = serial.tools.list_ports.comports()
        self.combo_ports.configure(values=[p.device for p in ports])
        if ports: self.combo_ports.set(ports[0].device)

    def toggle_connection(self):
        if not self.is_running:
            try:
                port = self.combo_ports.get()
                self.ser = serial.Serial(port, 115200, timeout=1)
                self.is_running = True
                self.btn_connect.configure(text="ROZŁĄCZ", fg_color=COLORS["accent_red"])
                threading.Thread(target=self.read_serial, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Błąd", str(e))
        else:
            self.is_running = False
            if self.ser: self.ser.close()
            self.btn_connect.configure(text="POŁĄCZ", fg_color=COLORS["accent_blue"])
            self.lbl_status.configure(text="ROZŁĄCZONY", text_color=COLORS["text_dim"])

    def read_serial(self):
        while self.is_running and self.ser.is_open:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("D;"):
                    parts = line.split(";")
                    if len(parts) >= 7:
                         self.after(0, self.update_data, 
                                    float(parts[1]), float(parts[2]), int(parts[3]), 
                                    int(parts[4]), int(parts[5]), int(parts[6]))
            except: pass

    def update_data(self, u, s, l, status_id, trigger_id, current_thresh):
        self.gauge_u.set_value(u)
        self.gauge_s.set_value(s)
        self.gauge_l.set_value(l)
        
        self.y_ultra.append(u)
        self.y_sharp.append(s)
        self.y_laser.append(l)

        now_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.history_buffer.append( (now_str, int(u), int(s), int(l)) )

        t_name = "---"
        if trigger_id == 1: t_name = "SHARP"
        elif trigger_id == 2: t_name = "LASER"
        elif trigger_id == 3: t_name = "OBA"

        if status_id == 0:
            self.lbl_status.configure(text="MONITOROWANIE", text_color=COLORS["accent_green"])
            self.lbl_countdown.configure(text="")
            
        elif status_id == 1: 
            if time.time() - self.last_hit_time > 2.0:
                self.last_hit_time = time.time()
                self.lbl_status.configure(text=f"WYKRYCIE: {t_name}", text_color=COLORS["accent_red"])
                self.save_sequence(u, s, l, t_name, current_thresh)
                self.play_sound("error")

        elif status_id == 2:
            self.lbl_status.configure(text="PAUZA SYSTEMU", text_color=COLORS["accent_orange"])
            elapsed = time.time() - self.last_hit_time
            remaining = 10.0 - elapsed
            if remaining < 0: remaining = 0
            self.lbl_countdown.configure(text=f"{remaining:.1f} s")

        elif status_id == 3:
            self.lbl_status.configure(text="GOTOWY (>30cm)", text_color=COLORS["accent_blue"])
            self.lbl_countdown.configure(text="")

    def play_sound(self, type):
        if platform.system() == "Windows":
            if type == "error": winsound.MessageBeep(winsound.MB_ICONHAND)

    def save_sequence(self, hit_u, hit_s, hit_l, trigger_src, threshold):
        d_str = datetime.datetime.now().strftime("%Y-%m-%d")
        material = self.entry_mat.get()
        
        try:
            with open(self.filename, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                
                # Zapisz 5 ostatnich (PRE-HIT)
                offset = -len(self.history_buffer)
                for entry in self.history_buffer:
                    writer.writerow([d_str, entry[0], material, "PRE-HIT", offset, threshold, entry[1], entry[2], entry[3], "---"])
                    offset += 1

                # Zapisz Snapshot
                t_now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                writer.writerow([d_str, t_now, material, "SNAPSHOT", 0, threshold, int(hit_u), int(hit_s), int(hit_l), trigger_src])
                
                # Dodaj pusty wiersz dla czytelności
                writer.writerow([]) 
            
            self.refresh_file_list()
            print(f"Zapisano sekwencję")
            
        except Exception as e:
            print(f"Błąd zapisu: {e}")

if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()