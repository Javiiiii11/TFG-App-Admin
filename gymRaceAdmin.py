import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
import firebase_admin
from firebase_admin import credentials, firestore
import threading
import time
import csv
import json
import sqlite3
import os

class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("")
        self.geometry("400x300")
        self.overrideredirect(True)
        self.resizable(False, False)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 300) // 2
        self.geometry(f'+{x}+{y}')
        self.configure(bg='white')
        try:
            logo_img = Image.open("img/gymrace.png")
            logo_img = logo_img.resize((200, 200), Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            logo_label = tk.Label(self, image=self.logo_photo, bg='white')
            logo_label.pack(expand=True)
            self.loading_label = tk.Label(self, text="Cargando...", font=("Helvetica", 14), bg='white', fg='#2c3e50')
            self.loading_label.pack(pady=10)
            self.progress = ttk.Progressbar(self, orient="horizontal", length=300, mode='indeterminate')
            self.progress.pack(pady=10)
            self.progress.start()
        except Exception as e:
            print(f"Error cargando logo de splash: {e}")


class FirestoreAdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.splash = SplashScreen(self)
        # Variables que se usan en varias partes de la aplicación
        self.collections = {
            "usuarios": ["ID", "Nombre", "Edad", "Peso", "Altura", "Días entrenamiento", "Nivel de Experiencia", "Objetivo Fitness"],
            "rutinas": ["ID", "Nombre", "Usuario", "Descripción", "Dificultad", "Ejercicios", "Fecha de Creación"],
            "dietas": ["ID", "Nombre", "Descripción", "Alimentos Permitidos", "Alimentos Prohibidos", "Calorias", "Comidas"]
        }
        self.field_mappings = {
            "usuarios": {
                "Nombre": "nombre",
                "Edad": "edad",
                "Peso": "peso",
                "Altura": "altura",
                "Días entrenamiento": "diasEntrenamientoPorSemana",
                "Nivel de Experiencia": "nivelExperiencia",
                "Objetivo Fitness": "objetivoFitness"
            },
            "rutinas": {
                "Nombre": "nombre",
                "Usuario": "usuarioId",
                "Descripción": "descripcion",
                "Dificultad": "dificultad",
                "Ejercicios": "ejercicios",
                "Fecha de Creación": "fechaCreacion"
            },
            "dietas": {
                "Nombre": "nombre",
                "Descripción": "descripcion",
                "Alimentos Permitidos": "alimentosPermitidos",
                "Alimentos Prohibidos": "alimentosProhibidos",
                "Calorias": "calorias",
                "Comidas": "comidas"
            }
        }
        self.current_collection = "usuarios"
        self.current_data = []
        self.active_bg = "#3498db"   # Botón activo
        self.inactive_bg = "#34495e" # Botón inactivo
        # threading.Thread(target=self.init_app, daemon=True).start()
        # Iniciar el proceso de carga en un hilo
        threading.Thread(target=self.init_app, daemon=True).start()
        
        # Iniciar la función cargando_datos_prints en otro hilo
        threading.Thread(target=cargando_datos_prints, daemon=True).start()

    def init_app(self):
        time.sleep(5)
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate('credencialesFireBase/firebase-credentials.json')
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
        except Exception as e:
            messagebox.showerror("Error de Firebase", f"No se pudo inicializar Firebase: {e}")
            self.splash.destroy()
            return
        self.load_user_names()
        self.after(0, self.setup_main_window)

    def setup_main_window(self):
        self.splash.destroy()
        self.title("GymRace Admin Panel")
        self.geometry("1200x700")
        self.minsize(1000, 650)
        self.state('zoomed')
        try:
            self.iconbitmap('icono/gymrace.ico')
        except Exception as e:
            print(f"Error cargando icono: {e}")
        # Configuración de la grilla principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.configure(bg="#ecf0f1")
        self.create_widgets()
        self.load_data()

    def load_user_names(self):
        try:
            self.user_id_to_name = {}
            users_ref = self.db.collection("usuarios")
            users = users_ref.stream()
            for user in users:
                user_data = user.to_dict()
                user_id = user.id
                user_name = user_data.get("nombre", "Usuario sin nombre")
                self.user_id_to_name[user_id] = user_name
            # print(f"Caché de nombres de usuarios cargada: {len(self.user_id_to_name)} usuarios")
        except Exception as e:
            print(f"Error cargando nombres de usuarios: {e}")

    def create_widgets(self):
        # === HEADER ===
        header_frame = tk.Frame(self, bg="#2c3e50", height=80)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        try:
            logo_img = Image.open("img/gymrace.png")
            logo_img = logo_img.resize((60, 60), Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            logo_label = tk.Label(header_frame, image=self.logo_photo, bg="#2c3e50")
            logo_label.grid(row=0, column=0, padx=20, pady=10)
        except Exception as e:
            print(f"Error cargando logo: {e}")
        title_label = tk.Label(header_frame, text="Panel de Administración GymRace", 
                               font=("Helvetica", 20, "bold"), fg="white", bg="#2c3e50")
        title_label.grid(row=0, column=1, sticky="w", padx=10)
        
        # === STATUS BAR ===
        self.status_var = tk.StringVar(value="Listo")
        status_bar = tk.Label(self, textvariable=self.status_var, font=("Helvetica", 10),
                              bg="#ecf0f1", relief=tk.SUNKEN, anchor=tk.W, padx=10)
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        
        # === MENÚ LATERAL ===
        sidebar_frame = tk.Frame(self, bg="#34495e", width=250)
        sidebar_frame.grid(row=1, column=0, sticky="nsew")
        sidebar_frame.grid_propagate(False)
        collections_label = tk.Label(sidebar_frame, text="COLECCIONES", font=("Helvetica", 13, "bold"),
                                     fg="white", bg="#34495e", pady=10)
        collections_label.pack(fill=tk.X, padx=15, pady=(20, 10))
        collections_frame = tk.Frame(sidebar_frame, bg="#34495e")
        collections_frame.pack(fill=tk.X, padx=5)
        self.menu_buttons = {}
        for collection_id, display_name in [("usuarios", "👤 Usuarios"),
                                              ("rutinas", "💪 Rutinas"),
                                              ("dietas", "🍎 Dietas")]:
            btn = tk.Button(collections_frame, text=display_name,
                            bg=self.active_bg if collection_id == self.current_collection else self.inactive_bg,
                            fg="white", font=("Helvetica", 12), bd=0, padx=15, pady=8,
                            anchor="w", width=25, highlightthickness=0,
                            command=lambda col=collection_id: self.switch_collection(col))
            btn.pack(fill=tk.X, pady=2)
            self.menu_buttons[collection_id] = btn
        tk.Frame(sidebar_frame, height=2, bg="#2c3e50").pack(fill=tk.X, padx=15, pady=15)
        # Sección de búsqueda
        search_label = tk.Label(sidebar_frame, text="BUSCAR", font=("Helvetica", 13, "bold"),
                                fg="white", bg="#34495e")
        search_label.pack(fill=tk.X, padx=15, pady=(15, 10))
        search_frame = tk.Frame(sidebar_frame, bg="#34495e", padx=15, pady=5)
        search_frame.pack(fill=tk.X)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=("Helvetica", 12))
        search_entry.pack(fill=tk.X, pady=5)
        # search_entry.bind("<Return>", lambda e: self.filter_data()) # Filtrar al presionar Enter
        search_entry.bind("<KeyRelease>", lambda e: self.filter_data()) # Filtrar al escribir
        search_btn = tk.Button(search_frame, text="🔍 Buscar", font=("Helvetica", 12),
                               bg="#3498db", fg="white", command=self.filter_data)
        search_btn.pack(fill=tk.X, pady=5)
        # advanced_filter_btn = tk.Button(search_frame, text="📊 Filtros Avanzados", font=("Helvetica", 12),
        #                                 bg="#3498db", fg="white", command=self.show_advanced_filter)
        # advanced_filter_btn.pack(fill=tk.X, pady=5)
        # Operaciones (actualizar y exportar)
        operations_label = tk.Label(sidebar_frame, text="OPERACIONES", font=("Helvetica", 13, "bold"),
                                    fg="white", bg="#34495e")
        operations_label.pack(fill=tk.X, padx=15, pady=(50, 10))
        operations_frame = tk.Frame(sidebar_frame, bg="#34495e", padx=15)
        operations_frame.pack(fill=tk.X)
        refresh_btn = tk.Button(operations_frame, text="🔄 Actualizar Datos", font=("Helvetica", 12),
                                bg="#3498db", fg="white", command=self.load_data)
        refresh_btn.pack(fill=tk.X, pady=5)
        export_btn = tk.Button(operations_frame, text="📥 Exportar Datos", font=("Helvetica", 12),
                               bg="#3498db", fg="white", command=self.show_export_options)
        export_btn.pack(fill=tk.X, pady=5)
        
        # === TABLA DE DATOS ===
        table_frame = tk.Frame(self, bd=0)
        table_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        style = ttk.Style()
        style.configure("Treeview", background="#ffffff", foreground="#333333", rowheight=25,
                        fieldbackground="#ffffff", borderwidth=0)
        style.map('Treeview', background=[('selected', '#3498db')])
        style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'),
                        background="#ecf0f1", foreground="#2c3e50")
        tree_container = tk.Frame(table_frame, bd=1, relief=tk.SOLID, bg="#ecf0f1")
        tree_container.pack(fill=tk.BOTH, expand=True)
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(tree_container, columns=self.collections[self.current_collection],
                                 show="headings", style="Treeview")
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        self.setup_table_headers()
        self.setup_context_menu()

    def setup_table_headers(self):
        headers = self.collections[self.current_collection]
        self.tree["columns"] = headers
        base_column_widths = {
            "ID": 210, "Nombre": 150, "Descripción": 400, "Edad": 70,
            "Peso": 70, "Altura": 70, "Días entrenamiento": 150,
            "Nivel de Experiencia": 180, "Objetivo Fitness": 150,
            "Alimentos Permitidos": 400, "Alimentos Prohibidos": 400,
            "Calorias": 100, "Comidas": 270, "Usuario": 150, "Dificultad": 120,
            "Ejercicios": 300, "Fecha de Creación": 150
        }
        numeric_columns = ["Edad", "Peso", "Altura", "Días entrenamiento", "Calorias"]
        # Inicializamos el diccionario para la dirección de ordenación
        self.sort_orders = {}
        for header in headers:
            self.sort_orders[header] = True  # True = ascendente, False = descendente
            width = base_column_widths.get(header, 150)
            anchor = tk.E if header in numeric_columns else tk.W
            self.tree.heading(header, text=header, anchor=tk.CENTER,
                              command=lambda c=header: self.sort_tree(c))
            self.tree.column(header, width=width, anchor=anchor, minwidth=50, stretch=False)
        # Inicialmente, ningún encabezado muestra flecha
        self.sorted_column = None
        self.sorted_direction = None

    def sort_tree(self, col):
        headers = self.collections[self.current_collection]
        col_index = headers.index(col)
        # Obtenemos el orden actual para la columna (True = ascendente)
        current_order = self.sort_orders[col]
        try:
            # Intentamos ordenar numéricamente
            self.current_data.sort(
                key=lambda row: float(row[col_index]) if row[col_index] != 'N/A' else float('inf'),
                reverse=not current_order
            )
        except ValueError:
            # Si no es numérico, se ordena como cadenas
            self.current_data.sort(
                key=lambda row: row[col_index],
                reverse=not current_order
            )
        # Guardamos la columna ordenada y la dirección usada
        self.sorted_column = col
        self.sorted_direction = "asc" if current_order else "desc"
        # Alternamos el orden para el siguiente clic
        self.sort_orders[col] = not current_order
        self.populate_tree()
        self.update_headers()
        self.status_var.set(f"Ordenado por {col} ({self.sorted_direction})")

    def update_headers(self):
        headers = self.collections[self.current_collection]
        for header in headers:
            arrow = ""
            if self.sorted_column == header:
                arrow = " ↑" if self.sorted_direction == "asc" else " ↓"
            new_text = header + arrow
            # Actualizamos el encabezado con la flecha correspondiente
            self.tree.heading(header, text=new_text,
                              command=lambda c=header: self.sort_tree(c))
            
    def load_data(self):
        try:
            # Vaciar la tabla
            for row in self.tree.get_children():
                self.tree.delete(row)
            field_mapping = self.field_mappings.get(self.current_collection, {})
            collection_ref = self.db.collection(self.current_collection)
            docs = collection_ref.stream()
            self.all_data = []
            for doc in docs:
                data = doc.to_dict()
                row = [str(doc.id)]
                for header in self.collections[self.current_collection][1:]:
                    firestore_field = field_mapping.get(header, header.lower())
                    if self.current_collection == "rutinas" and header == "Usuario":
                        user_id = data.get("usuarioId", "")
                        user_name = self.user_id_to_name.get(user_id, "N/A")
                        row.append(user_name)
                    else:
                        val = data.get(firestore_field, 'N/A')
                        row.append(str(val))
                self.all_data.append(row)
            # Inicialmente se muestran todos los datos
            self.current_data = self.all_data.copy()
            self.populate_tree()
            self.status_var.set(f"Mostrando {len(self.current_data)} registros")
            print(f"Cargados {len(self.current_data)} datos")
        except Exception as e:
            messagebox.showerror("Error de Carga", f"No se pudieron cargar los datos: {e}")

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for row_data in self.current_data:
            self.tree.insert("", tk.END, values=row_data)

    def filter_data(self):
        search_term = self.search_var.get().strip().lower()
        if not search_term:
            self.current_data = self.all_data.copy()
        else:
            self.current_data = [
                row for row in self.all_data
                if any(search_term in str(cell).lower() for cell in row)
            ]
        self.populate_tree()
        self.status_var.set(f"Mostrando {len(self.current_data)} registros (filtrados)")

    def switch_collection(self, collection_id):
        if collection_id == self.current_collection:
            return
        self.current_collection = collection_id
        # Actualizar los botones del menú
        for col_id, btn in self.menu_buttons.items():
            btn.config(bg=self.active_bg if col_id == collection_id else self.inactive_bg)
        if collection_id == "rutinas":
            self.load_user_names()
        self.setup_table_headers()
        self.load_data()
        self.status_var.set(f"Colección cambiada a: {collection_id.capitalize()}")

    def show_export_options(self):
        if not self.current_data:
            messagebox.showinfo("Exportar", "No hay datos para exportar")
            return
        
        # Crear ventana de opciones de exportación
        export_window = tk.Toplevel(self)
        export_window.title("Opciones de Exportación")
        export_window.geometry("400x300")
        export_window.resizable(False, False)
        export_window.transient(self)
        export_window.grab_set()
        
        # Centrar la ventana
        export_window.update_idletasks()
        width = export_window.winfo_width()
        height = export_window.winfo_height()
        x = (export_window.winfo_screenwidth() // 2) - (width // 2)
        y = (export_window.winfo_screenheight() // 2) - (height // 2)
        export_window.geometry(f'+{x}+{y}')
        
        # Contenido de la ventana
        main_frame = tk.Frame(export_window, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title_label = tk.Label(main_frame, text="Seleccione formato de exportación", 
                              font=("Helvetica", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Opciones de formato
        formats_frame = tk.Frame(main_frame)
        formats_frame.pack(fill=tk.BOTH, expand=True)
        
        # Variable para el formato seleccionado
        self.export_format = tk.StringVar(value="csv")
        
        # Estilos de botones
        button_style = {"font": ("Helvetica", 12), "width": 30, "height": 2, 
                        "cursor": "hand2", "bd": 1, "relief": tk.RAISED}
        
        # Botones de formato
        csv_btn = tk.Radiobutton(formats_frame, text="CSV (Excel, LibreOffice Calc)", 
                                variable=self.export_format, value="csv", 
                                font=("Helvetica", 12), anchor="w", padx=10)
        csv_btn.pack(fill=tk.X, pady=5)
        
        json_btn = tk.Radiobutton(formats_frame, text="JSON (JavaScript, API)", 
                                 variable=self.export_format, value="json", 
                                 font=("Helvetica", 12), anchor="w", padx=10)
        json_btn.pack(fill=tk.X, pady=5)
        
        txt_btn = tk.Radiobutton(formats_frame, text="TXT (Texto plano)", 
                                variable=self.export_format, value="txt", 
                                font=("Helvetica", 12), anchor="w", padx=10)
        txt_btn.pack(fill=tk.X, pady=5)
        
        db_btn = tk.Radiobutton(formats_frame, text="BD SQLite (Base de datos)", 
                               variable=self.export_format, value="db", 
                               font=("Helvetica", 12), anchor="w", padx=10)
        db_btn.pack(fill=tk.X, pady=5)
        
        # Botones de acción
        buttons_frame = tk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(20, 0))
        
        export_btn = tk.Button(buttons_frame, text="Exportar", 
                              command=lambda: self.export_data(export_window),
                              bg="#3498db", fg="white", font=("Helvetica", 12))
        export_btn.pack(side=tk.RIGHT, padx=5)
        
        cancel_btn = tk.Button(buttons_frame, text="Cancelar", 
                              command=export_window.destroy,
                              bg="#95a5a6", fg="white", font=("Helvetica", 12))
        cancel_btn.pack(side=tk.RIGHT, padx=5)

    def export_data(self, export_window=None):
        if not self.current_data:
            messagebox.showinfo("Exportar", "No hay datos para exportar")
            return
        
        if export_window:
            format_selected = self.export_format.get()
            export_window.destroy()
        else:
            format_selected = "csv"  # Valor por defecto si se llama directamente
        
        # Definir extensiones y tipos de archivo según el formato
        formats = {
            "csv": (".csv", "CSV Files"),
            "json": (".json", "JSON Files"),
            "txt": (".txt", "Text Files"),
            "db": (".db", "SQLite Database")
        }
        
        ext, file_type = formats.get(format_selected, (".csv", "CSV Files"))
        
        # Diálogo para seleccionar dónde guardar
        filename = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(file_type, f"*{ext}"), ("All Files", "*.*")],
            title=f"Exportar datos como {format_selected.upper()}"
        )
        
        if not filename:
            return
            
        try:
            headers = self.collections[self.current_collection]
            
            # Exportar según el formato seleccionado
            if format_selected == "csv":
                self.export_as_csv(filename, headers)
            elif format_selected == "json":
                self.export_as_json(filename, headers)
            elif format_selected == "txt":
                self.export_as_txt(filename, headers)
            elif format_selected == "db":
                self.export_as_sqlite(filename, headers)
            
            messagebox.showinfo("Exportar", f"Datos exportados exitosamente a {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar datos: {e}")
    
    def export_as_csv(self, filename, headers):
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            for row in self.current_data:
                writer.writerow(row)
    
    def export_as_json(self, filename, headers):
        json_data = []
        for row in self.current_data:
            item = {}
            for i, header in enumerate(headers):
                item[header] = row[i]
            json_data.append(item)
            
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, ensure_ascii=False, indent=2)
    
    def export_as_txt(self, filename, headers):
        with open(filename, 'w', encoding='utf-8') as txtfile:
            # Encabezado
            header_line = "\t".join(headers)
            txtfile.write(f"{header_line}\n")
            txtfile.write("-" * len(header_line) + "\n")
            
            # Datos
            for row in self.current_data:
                row_text = "\t".join(str(cell) for cell in row)
                txtfile.write(f"{row_text}\n")
    
    def export_as_sqlite(self, filename, headers):
        # Eliminar el archivo si ya existe
        if os.path.exists(filename):
            os.remove(filename)
            
        # Crear conexión a la base de datos
        conn = sqlite3.connect(filename)
        cursor = conn.cursor()
        
        # Crear tabla
        table_name = self.current_collection
        fields = ", ".join([f'"{header}" TEXT' for header in headers])
        cursor.execute(f'CREATE TABLE "{table_name}" ({fields})')
        
        # Insertar datos
        placeholders = ", ".join(["?" for _ in headers])
        for row in self.current_data:
            cursor.execute(f'INSERT INTO "{table_name}" VALUES ({placeholders})', row)
        
        # Guardar cambios y cerrar
        conn.commit()
        conn.close()

    def setup_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Ver detalles", command=self.view_details)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def view_details(self):
        selected = self.tree.selection()
        if not selected:
            return
        item_values = self.tree.item(selected[0], 'values')
        if not item_values:
            return
        details_window = tk.Toplevel(self)
        details_window.title(f"Detalles - {self.current_collection.capitalize()}")
        details_window.geometry("600x400")
        details_window.minsize(500, 300)
        details_window.grab_set()
        details_frame = tk.Frame(details_window, padx=20, pady=20)
        details_frame.pack(fill=tk.BOTH, expand=True)
        header_label = tk.Label(details_frame, text=f"Detalles de {self.current_collection.capitalize()}",
                                 font=("Helvetica", 16, "bold"))
        header_label.pack(pady=(0, 20))
        canvas = tk.Canvas(details_frame)
        scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        headers = self.collections[self.current_collection]
        for i, (header, value) in enumerate(zip(headers, item_values)):
            field_frame = tk.Frame(scrollable_frame)
            field_frame.pack(fill=tk.X, pady=5)
            label = tk.Label(field_frame, text=f"{header}:", font=("Helvetica", 11, "bold"),
                             width=15, anchor="w")
            label.pack(side=tk.LEFT, padx=(0, 10))
            value_text = tk.Text(field_frame, height=2 if len(str(value)) > 50 else 1,
                                 wrap=tk.WORD, font=("Helvetica", 11))
            value_text.insert(tk.END, value)
            value_text.config(state=tk.DISABLED)
            value_text.pack(side=tk.LEFT, fill=tk.X, expand=True)


def cargando_datos_prints():
    # Simulación de carga de muchos datos con muchos prints
    for i in range(1, 10001):
        print(f"Cargando datos {i}/{10000}")

if __name__ == "__main__":
    app = FirestoreAdminApp()
    app.mainloop()