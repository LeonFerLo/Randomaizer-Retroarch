import os
import random
import subprocess
import time
import psutil
import tkinter as tk
from tkinter import font, ttk
from pathlib import Path
from threading import Thread
import screeninfo

# CONFIGURACIÓN
RETROARCH_PATH = "C:\\RetroArch-Win64\\retroarch.exe"
CORES_DIR = "C:\\RetroArch-Win64\\cores\\"
ROM_DIR = "roms"
SAVE_DIR = "saves"
INTERVALO_MINUTOS = 1
ESPERA_GUARDADO = 3

# Mapeo de cores
CORE_MAP = {
    '.nes': 'nestopia_libretro.dll',
    '.sfc': 'snes9x_libretro.dll',
    '.smc': 'snes9x_libretro.dll',
    '.gba': 'mgba_libretro.dll',
    '.gb': 'gambatte_libretro.dll',
    '.gbc': 'gambatte_libretro.dll',
    '.n64': 'mupen64plus_next_libretro.dll',
    '.z64': 'mupen64plus_next_libretro.dll',
}

# Variables globales
ultima_rom = None
en_ejecucion = False
pausado = False
proceso_retroarch = None
modo_oscuro = False
fuentes_disponibles = []
ultima_tecla_presionada = ''
tiempo_ultima_tecla = 0
siempre_visible = False
monitor_actual = 0
controles_visibles = True

class RetroArchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RetroArch Automático")
        self.root.geometry("400x150")
        self.root.resizable(False, False)
        
        # Obtener información de monitores
        try:
            self.monitores = screeninfo.get_monitors()
            if not self.monitores:
                self.monitores = [screeninfo.Monitor(x=0, y=0, width=800, height=600, name="Default")]
        except:
            self.monitores = [screeninfo.Monitor(x=0, y=0, width=800, height=600, name="Default")]
        
        # Configurar colores iniciales
        self.bg_color = "white"
        self.fg_color = "black"
        self.root.configure(bg=self.bg_color)
        
        # Obtener todas las fuentes del sistema
        self.obtener_fuentes_sistema()
        
        # Frame principal
        self.main_frame = tk.Frame(root, bg=self.bg_color, highlightthickness=0)
        self.main_frame.pack(expand=True, fill=tk.BOTH)
        
        # Botón de fijar ventana (siempre visible, esquina superior izquierda)
        self.btn_fijar = tk.Button(
            self.main_frame,
            text="O",
            font=('Arial', 10),
            command=self.toggle_siempre_visible,
            relief="flat",
            bg=self.bg_color,
            fg=self.fg_color,
            bd=0,
            highlightthickness=0
        )
        self.btn_fijar.place(relx=0, rely=0, anchor='nw', x=5, y=5)
        
        # Contador
        self.contador = tk.StringVar()
        self.contador.set("00:00")
        self.lbl_contador = tk.Label(
            self.main_frame, 
            textvariable=self.contador, 
            font=('Arial', 36),
            anchor='center',
            bg=self.bg_color,
            fg=self.fg_color,
            highlightthickness=0
        )
        self.lbl_contador.pack(expand=True, fill=tk.BOTH, pady=20)
        
        # Botón de alternar (esquina superior derecha)
        self.btn_alternar = tk.Button(
            self.main_frame,
            text="☰",
            font=('Arial', 12),
            command=self.toggle_controles,
            relief="flat",
            bg=self.bg_color,
            fg=self.fg_color,
            bd=0,
            highlightthickness=0
        )
        self.btn_alternar.place(relx=1.0, rely=0, anchor='ne', x=-5, y=5)
        
        # Frame de controles (inicialmente oculto)
        self.control_frame = tk.Frame(self.main_frame, bg=self.bg_color, highlightthickness=0)
        
        # Frame para botones principales
        self.frame_botones = tk.Frame(self.control_frame, bg=self.bg_color, highlightthickness=0)
        self.frame_botones.pack(fill=tk.X, pady=5)
        
        # Botones principales
        self.btn_iniciar = tk.Button(
            self.frame_botones, 
            text="Iniciar", 
            command=self.iniciar_reanudar,
            bg=self.bg_color,
            fg=self.fg_color,
            relief="solid",
            bd=1,
            highlightthickness=0
        )
        self.btn_iniciar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)  # <--- Añade esta línea

        self.btn_pausar = tk.Button(
            self.frame_botones, 
            text="Pausar", 
            command=self.pausar,
            state=tk.DISABLED,
            bg=self.bg_color,
            fg=self.fg_color,
            relief="solid",
            bd=1,
            highlightthickness=0
        )
        self.btn_pausar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)  # <--- Añade esta línea

        self.btn_detener = tk.Button(
            self.frame_botones, 
            text="Detener", 
            command=self.detener,
            state=tk.DISABLED,
            bg=self.bg_color,
            fg=self.fg_color,
            relief="solid",
            bd=1,
            highlightthickness=0
        )
        self.btn_detener.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)  # <--- Añade esta línea
        
        # Frame para botón de configuración
        self.frame_config = tk.Frame(self.control_frame, bg=self.bg_color, highlightthickness=0)
        self.frame_config.pack(fill=tk.X, pady=5)
        
        # Botón de configuración
        self.btn_config = tk.Button(
            self.frame_config,
            text="Configuración",
            command=self.mostrar_configuracion,
            bg=self.bg_color,
            fg=self.fg_color,
            relief="solid",
            bd=1,
            highlightthickness=0
        )
        self.btn_config.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        # Etiqueta de estado
        self.lbl_estado = tk.Label(
            self.control_frame, 
            text="Detenido", 
            font=('Arial', 8),
            bg=self.bg_color,
            fg="red",
            highlightthickness=0
        )
        self.lbl_estado.pack(pady=5)
        
        # Aplicar tema inicial
        self.aplicar_tema()
        
        # Configurar eventos para mover la ventana
        self.lbl_contador.bind("<ButtonPress-1>", self.start_move)
        self.lbl_contador.bind("<B1-Motion>", self.do_move)
        
        # Iniciar con la barra de título oculta
        self.root.overrideredirect(True)
        
        # Posicionar en la esquina superior derecha del monitor principal
        self.posicionar_en_esquina()
    
    def posicionar_en_esquina(self):
        monitor = self.monitores[monitor_actual]
        x = monitor.x + monitor.width - 400  # 400 = ancho ventana, 10 = margen
        y = monitor.y  # Margen superior
        self.root.geometry(f"+{x}+{y}")
    
    def toggle_siempre_visible(self):
        global siempre_visible
        siempre_visible = not siempre_visible
        self.root.attributes('-topmost', siempre_visible)
        self.btn_fijar.config(text="X" if siempre_visible else "O")
        self.puede_mover = not siempre_visible  # Deshabilita movimiento al fijar
        if siempre_visible:
            self.posicionar_en_esquina()  # Reposicionar cada vez que se fija
        self.root.update_idletasks()

    def mostrar_configuracion(self):
        # Crear ventana de configuración
        ventana_config = tk.Toplevel(self.root)
        ventana_config.title("Configuración")
        ventana_config.resizable(False, False)
        ventana_config.geometry("300x200")
        ventana_config.configure(bg=self.bg_color)
        
        # Centrar en la pantalla
        ventana_config.update_idletasks()
        ancho = ventana_config.winfo_width()
        alto = ventana_config.winfo_height()
        x = (ventana_config.winfo_screenwidth() // 2) - (ancho // 2)
        y = (ventana_config.winfo_screenheight() // 2) - (alto // 2)
        ventana_config.geometry(f'+{x}+{y}')
        
        # Configurar para que esté siempre encima
        ventana_config.attributes('-topmost', True)
        
        # Marco para monitores
        frame_monitores = tk.Frame(ventana_config, bg=self.bg_color)
        frame_monitores.pack(pady=10)
        
        lbl_monitor = tk.Label(
            frame_monitores,
            text="Seleccionar monitor:",
            bg=self.bg_color,
            fg=self.fg_color
        )
        lbl_monitor.pack(side=tk.LEFT, padx=5)
        
        # Combobox para selección de monitor
        self.monitor_var = tk.StringVar()
        nombres_monitores = [f"Monitor {i+1} ({m.width}x{m.height})" for i, m in enumerate(self.monitores)]
        self.cb_monitores = ttk.Combobox(
            frame_monitores,
            textvariable=self.monitor_var,
            values=nombres_monitores,
            state="readonly"
        )
        self.cb_monitores.current(monitor_actual)
        self.cb_monitores.pack(side=tk.LEFT, padx=5)
        
        # Botón para aplicar cambios
        btn_aplicar = tk.Button(
            ventana_config,
            text="Aplicar",
            command=self.aplicar_configuracion,
            bg=self.bg_color,
            fg=self.fg_color,
            relief="solid"
        )
        btn_aplicar.pack(pady=10)
        
        # Marco para otras configuraciones
        frame_fuentes = tk.Frame(ventana_config, bg=self.bg_color)
        frame_fuentes.pack(pady=10)
        
        btn_fuentes = tk.Button(
            frame_fuentes,
            text="Cambiar Fuente",
            command=self.mostrar_menu_fuentes,
            bg=self.bg_color,
            fg=self.fg_color,
            relief="solid"
        )
        btn_fuentes.pack(side=tk.LEFT, padx=5)
        
        btn_colores = tk.Button(
            frame_fuentes,
            text="Invertir Colores",
            command=self.invertir_colores,
            bg=self.bg_color,
            fg=self.fg_color,
            relief="solid"
        )
        btn_colores.pack(side=tk.LEFT, padx=5)
    
    def aplicar_configuracion(self):
        global monitor_actual
        monitor_actual = self.cb_monitores.current()
        self.posicionar_en_esquina()
        self.root.focus_set()
    
    def obtener_fuentes_sistema(self):
        global fuentes_disponibles
        fuentes_disponibles = sorted(list(set(font.families())))
        
    def mostrar_menu_fuentes(self):
        # Crear ventana emergente para el menú con scroll
        self.ventana_menu = tk.Toplevel(self.root)
        self.ventana_menu.overrideredirect(True)
        self.ventana_menu.geometry("400x500")
        self.ventana_menu.configure(bg=self.bg_color)
        
        # Posicionar cerca del botón de fuentes
        x = self.btn_config.winfo_rootx()
        y = self.btn_config.winfo_rooty() + self.btn_config.winfo_height()
        self.ventana_menu.geometry(f"+{x}+{y}")
        
        # Frame principal
        frame_principal = tk.Frame(self.ventana_menu, bg=self.bg_color)
        frame_principal.pack(fill=tk.BOTH, expand=True)
        
        # Canvas y scrollbar
        canvas = tk.Canvas(frame_principal, bg=self.bg_color, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame_principal, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.bg_color)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Configurar evento de rueda del mouse
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Agregar fuentes al frame desplazable
        for fuente in fuentes_disponibles:
            btn = tk.Button(
                scrollable_frame,
                text=fuente,
                command=lambda f=fuente: self.seleccionar_fuente(f),
                font=(fuente, 10),
                bg=self.bg_color,
                fg=self.fg_color,
                relief="flat",
                anchor="w",
                width=40
            )
            btn.pack(fill=tk.X, padx=5, pady=2)
        
        # Botón para cerrar
        btn_cerrar = tk.Button(
            scrollable_frame,
            text="Cerrar",
            command=self.ventana_menu.destroy,
            bg=self.bg_color,
            fg=self.fg_color,
            relief="solid"
        )
        btn_cerrar.pack(fill=tk.X, padx=5, pady=10)
        
        # Guardar referencia para eventos
        self.canvas_menu = canvas
        self.scrollable_frame_menu = scrollable_frame
        
        # Configurar evento para cerrar al hacer clic fuera
        self.ventana_menu.bind("<FocusOut>", lambda e: self.ventana_menu.destroy())
        
        # Configurar evento de teclado para búsqueda rápida
        self.ventana_menu.bind("<Key>", self.buscar_fuente_teclado)
        
    def seleccionar_fuente(self, fuente):
        self.cambiar_fuente(fuente)
        self.ventana_menu.destroy()
        
    def buscar_fuente_teclado(self, event):
        if not hasattr(self, 'ventana_menu') or not self.ventana_menu.winfo_exists():
            return
            
        global ultima_tecla_presionada, tiempo_ultima_tecla
        
        # Ignorar teclas especiales
        if len(event.char) == 0 or ord(event.char) < 32:
            return
            
        tecla_actual = event.char.lower()
        tiempo_actual = time.time()
        
        # Verificar si es la misma tecla en un tiempo corto (para búsqueda por múltiples letras)
        if tecla_actual == ultima_tecla_presionada and tiempo_actual - tiempo_ultima_tecla < 1.0:
            busqueda = ultima_tecla_presionada + tecla_actual
        else:
            busqueda = tecla_actual
            
        ultima_tecla_presionada = tecla_actual
        tiempo_ultima_tecla = tiempo_actual
        
        # Buscar la primera fuente que empiece con la cadena de búsqueda
        for i, fuente in enumerate(fuentes_disponibles):
            if fuente.lower().startswith(busqueda):
                # Calcular posición para scroll
                posicion = i * 30  # Aprox 30px por item
                self.canvas_menu.yview_moveto(posicion / len(fuentes_disponibles))
                break
                
    def cambiar_fuente(self, fuente):
        self.lbl_contador.config(font=(fuente, 36))
        
    def invertir_colores(self):
        global modo_oscuro
        modo_oscuro = not modo_oscuro
        self.aplicar_tema()
        
    def aplicar_tema(self):
        if modo_oscuro:
            self.bg_color = "black"
            self.fg_color = "white"
        else:
            self.bg_color = "white"
            self.fg_color = "black"
            
        # Aplicar colores a todos los widgets
        widgets = [
            self.root, self.main_frame, self.control_frame, 
            self.frame_botones, self.frame_config,
            self.lbl_contador, self.lbl_estado,
            self.btn_alternar, self.btn_iniciar, 
            self.btn_pausar, self.btn_detener,
            self.btn_config, self.btn_fijar
        ]
        
        for widget in widgets:
            try:
                widget.config(bg=self.bg_color, fg=self.fg_color)
            except:
                pass
            
        # Estado especial para el label de estado
        if en_ejecucion:
            color = "green" if not pausado else "orange"
            self.lbl_estado.config(fg=color)
        else:
            self.lbl_estado.config(fg="red")
    
    def toggle_controles(self):
        global controles_visibles, siempre_visible
        controles_visibles = not controles_visibles
        
        if controles_visibles:
            self.control_frame.pack(fill=tk.X, pady=5)
            self.root.geometry("400x250")
            self.btn_alternar.config(text="▼")
            self.root.overrideredirect(False)  # Mostrar barra de título
        else:
            self.control_frame.pack_forget()
            self.root.geometry("400x150")
            self.btn_alternar.config(text="☰")
            self.root.overrideredirect(True)  # Ocultar barra de título
        
        # Mantener el estado de siempre visible
        self.root.attributes('-topmost', siempre_visible)
    
    def start_move(self, event):
        if self.puede_mover:
            self._x = event.x
            self._y = event.y

    def do_move(self, event):
        if self.puede_mover:
            x = self.root.winfo_x() + event.x - self._x
            y = self.root.winfo_y() + event.y - self._y
            self.root.geometry(f'+{x}+{y}')
    
    def iniciar_reanudar(self):
        global en_ejecucion, pausado
        if not en_ejecucion:
            en_ejecucion = True
            pausado = False
            self.btn_iniciar.config(state=tk.DISABLED)
            self.btn_detener.config(state=tk.NORMAL)
            self.btn_pausar.config(state=tk.NORMAL)
            self.lbl_estado.config(text="En ejecución", fg="green")
            Thread(target=self.ejecutar_ciclo, daemon=True).start()
        else:
            pausado = False
            self.btn_iniciar.config(text="Reanudar", state=tk.DISABLED)
            self.btn_pausar.config(state=tk.NORMAL)
            self.lbl_estado.config(text="En ejecución", fg="green")
        self.aplicar_tema()
        
    def pausar(self):
        global pausado
        pausado = True
        self.btn_iniciar.config(text="Reanudar", state=tk.NORMAL)
        self.btn_pausar.config(state=tk.DISABLED)
        self.lbl_estado.config(text="Pausado", fg="orange")
        self.aplicar_tema()
        
    def detener(self):
        global en_ejecucion, pausado
        en_ejecucion = False
        pausado = False
        self.btn_iniciar.config(text="Iniciar", state=tk.NORMAL)
        self.btn_detener.config(state=tk.DISABLED)
        self.btn_pausar.config(state=tk.DISABLED)
        self.lbl_estado.config(text="Detenido", fg="red")
        self.contador.set("00:00")
        self.aplicar_tema()
        cerrar_retroarch()
        
    def actualizar_contador(self, segundos):
        mins, secs = divmod(segundos, 60)
        self.contador.set(f"{mins:02d}:{secs:02d}")
        self.root.update()
        
    def ejecutar_ciclo(self):
        global ultima_rom, proceso_retroarch
        
        while en_ejecucion:
            if pausado:
                time.sleep(1)
                continue
                
            rom = get_random_rom()
            if not rom:
                self.contador.set("No hay ROMs")
                break
                
            # Ejecutar RetroArch
            core_path = os.path.join(CORES_DIR, CORE_MAP.get(
                os.path.splitext(rom)[1].lower(), 
                'mgba_libretro.dll'
            ))
            rom_path = os.path.join(ROM_DIR, rom)
            save_path = os.path.join(SAVE_DIR, f"{os.path.splitext(rom)[0]}.state")
            
            comando = [
                RETROARCH_PATH,
                "-L", core_path,
                rom_path,
                "--savestate", save_path if os.path.exists(save_path) else ""
            ]
            
            proceso_retroarch = subprocess.Popen(comando)
            ultima_rom = rom
            
            # Contador regresivo
            for i in range(INTERVALO_MINUTOS * 60, 0, -1):
                if not en_ejecucion:
                    break
                if pausado:
                    self.actualizar_contador(i)
                    while pausado and en_ejecucion:
                        time.sleep(1)
                    continue
                self.actualizar_contador(i)
                time.sleep(1)
            
            cerrar_retroarch()
            if not en_ejecucion:
                break

def get_roms_list():
    return [f for f in os.listdir(ROM_DIR) if f.lower().endswith(tuple(CORE_MAP.keys()))]
def ajustar_fuente(self):
    # Aquí va el código para ajustar la fuente dinámicamente
    pass  # quita esto y pon tu lógica

def get_random_rom():
    global ultima_rom
    roms = get_roms_list()
    
    if not roms:
        return None
    
    if len(roms) == 1:
        return roms[0]
    
    disponibles = [r for r in roms if r != ultima_rom]
    return random.choice(disponibles) if disponibles else None

def cerrar_retroarch():
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == 'retroarch.exe':
                subprocess.run([
                    'powershell',
                    '$wshell = New-Object -ComObject wscript.shell;',
                    '$wshell.SendKeys("%{F4}")'
                ], timeout=3)
                time.sleep(ESPERA_GUARDADO)
                if psutil.pid_exists(proc.info['pid']):
                    proc.terminate()
                break
    except Exception as e:
        print(f"Error al cerrar RetroArch: {e}")
def __init__(self, root):
    self.root = root
    self.root.title("RetroArch Automático")
    self.root.geometry("400x150")
    self.root.geometry("400x250")
    self.btn_alternar.config(text="▼")
    self.root.resizable(False, False)
    self.control_frame = tk.Frame(self.main_frame, bg=self.bg_color, highlightthickness=0)
    self.control_frame.pack(fill=tk.X, pady=5)  # Mostrar desde el inicio
      # Actualizar variable global
    self.puede_mover = False  # o True, según tu lógica
    # Añadir esta línea para que se inicie fijada si lo deseas
    self.root.attributes('-topmost', True)  # Iniciar siempre visible

if __name__ == "__main__":
    Path(ROM_DIR).mkdir(exist_ok=True)
    Path(SAVE_DIR).mkdir(exist_ok=True)
    
    try:
        import psutil, screeninfo
    except ImportError:
        subprocess.run(["pip", "install", "psutil", "screeninfo"], check=True)
        import psutil, screeninfo
    
    root = tk.Tk()
    app = RetroArchGUI(root)
    root.mainloop()