import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
import firebase_admin
from firebase_admin import credentials, firestore
import threading
import time
import csv

class EnhancedFilterDialog(simpledialog.Dialog):
    def __init__(self, parent, title, collection, field_mappings):
        self.collection = collection
        self.field_mappings = field_mappings
        # No inicialices self.result aquí, se sobrescribirá por la clase base
        self._filter_result = {}  # Usa un nombre diferente para evitar conflictos
        super().__init__(parent, title)

    def body(self, master):
        # Crea dinámicamente los campos de filtro según la colección
        self.fields = {}
        row_count = 0

        # Invertir field_mappings para obtener nombres amigables
        reverse_mappings = {v: k for k, v in self.field_mappings.items()}

        filter_options = {
            "usuarios": [
                "edad", "peso", "altura", "diasEntrenamientoPorSemana", 
                "nivelExperiencia", "objetivoFitness"
            ],
            "rutinas": [
                "dificultad", "fechaCreacion", "usuarioId"
            ],
            "dietas": [
                "calorias", "comidas"
            ]
        }

        for field in filter_options.get(self.collection, []):
            friendly_name = reverse_mappings.get(field, field.capitalize())
            tk.Label(master, text=friendly_name).grid(row=row_count, column=0, sticky='w', padx=5, pady=2)

            if field in ["edad", "peso", "altura", "calorias", "diasEntrenamientoPorSemana"]:
                # Filtros numéricos (rango)
                min_var = tk.StringVar()
                max_var = tk.StringVar()
                tk.Label(master, text="Min:").grid(row=row_count, column=1, sticky='w', padx=2)
                min_entry = ttk.Entry(master, textvariable=min_var, width=10)
                min_entry.grid(row=row_count, column=2, padx=2)
                tk.Label(master, text="Max:").grid(row=row_count, column=3, sticky='w', padx=2)
                max_entry = ttk.Entry(master, textvariable=max_var, width=10)
                max_entry.grid(row=row_count, column=4, padx=2)
                self.fields[field] = {"min": min_var, "max": max_var, "type": "numeric"}

            elif field in ["dificultad", "nivelExperiencia", "objetivoFitness"]:
                # Filtros de opción (dropdown)
                options = ["Todos", "Bajo", "Medio", "Alto", "Principiante", "Intermedio", "Avanzado"]
                var = tk.StringVar(value="Todos")
                dropdown = ttk.Combobox(master, textvariable=var, values=options, state="readonly", width=15)
                dropdown.grid(row=row_count, column=1, columnspan=4, sticky='ew', padx=5)
                self.fields[field] = {"var": var, "type": "categorical"}

            elif field == "fechaCreacion":
                # Filtro de fecha (rango)
                start_var = tk.StringVar()
                end_var = tk.StringVar()
                tk.Label(master, text="Desde (YYYY-MM-DD):").grid(row=row_count, column=1, sticky='w', padx=2)
                start_entry = ttk.Entry(master, textvariable=start_var, width=15)
                start_entry.grid(row=row_count, column=2, padx=2)
                tk.Label(master, text="Hasta:").grid(row=row_count, column=3, sticky='w', padx=2)
                end_entry = ttk.Entry(master, textvariable=end_var, width=15)
                end_entry.grid(row=row_count, column=4, padx=2)
                self.fields[field] = {"start": start_var, "end": end_var, "type": "date"}

            row_count += 1

        return None  # Para que se mantenga el foco por defecto

    def apply(self):
        for field, config in self.fields.items():
            if config['type'] == 'numeric':
                try:
                    min_val = config['min'].get()
                    max_val = config['max'].get()
                    if min_val or max_val:
                        min_val = float(min_val) if min_val else float('-inf')
                        max_val = float(max_val) if max_val else float('inf')
                        self._filter_result[field] = {'min': min_val, 'max': max_val}
                except ValueError:
                    messagebox.showerror("Error", f"Valor inválido para {field}")
                    return
            elif config['type'] == 'categorical':
                value = config['var'].get()
                if value != "Todos":
                    self._filter_result[field] = value
            elif config['type'] == 'date':
                start_val = config['start'].get()
                end_val = config['end'].get()
                if start_val or end_val:
                    self._filter_result[field] = {'start': start_val, 'end': end_val}
        
        # Asignar los filtros recogidos a self.result al final
        self.result = self._filter_result if self._filter_result else {}


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
        threading.Thread(target=self.init_app, daemon=True).start()

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
        self.minsize(1000, 600)
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
            print(f"Caché de nombres de usuarios cargada: {len(self.user_id_to_name)} usuarios")
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
        search_entry.bind("<Return>", lambda e: self.filter_data())
        search_btn = tk.Button(search_frame, text="🔍 Buscar", font=("Helvetica", 12),
                               bg="#3498db", fg="white", command=self.filter_data)
        search_btn.pack(fill=tk.X, pady=5)
        advanced_filter_btn = tk.Button(search_frame, text="📊 Filtros Avanzados", font=("Helvetica", 12),
                                        bg="#3498db", fg="white", command=self.show_advanced_filter)
        advanced_filter_btn.pack(fill=tk.X, pady=5)
        # Operaciones (actualizar y exportar)
        operations_label = tk.Label(sidebar_frame, text="OPERACIONES", font=("Helvetica", 13, "bold"),
                                    fg="white", bg="#34495e")
        operations_label.pack(fill=tk.X, padx=15, pady=(20, 10))
        operations_frame = tk.Frame(sidebar_frame, bg="#34495e", padx=15)
        operations_frame.pack(fill=tk.X)
        refresh_btn = tk.Button(operations_frame, text="🔄 Actualizar Datos", font=("Helvetica", 12),
                                bg="#3498db", fg="white", command=self.load_data)
        refresh_btn.pack(fill=tk.X, pady=5)
        export_btn = tk.Button(operations_frame, text="📥 Exportar Datos", font=("Helvetica", 12),
                               bg="#3498db", fg="white", command=self.export_data)
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
            "Peso": 70, "Altura": 70, "Días entrenamiento": 130,
            "Nivel de Experiencia": 180, "Objetivo Fitness": 200,
            "Alimentos Permitidos": 400, "Alimentos Prohibidos": 400,
            "Calorias": 100, "Comidas": 270, "Usuario": 150, "Dificultad": 120,
            "Ejercicios": 300, "Fecha de Creación": 150
        }
        numeric_columns = ["Edad", "Peso", "Altura", "Días entrenamiento", "Calorias"]
        for header in headers:
            width = base_column_widths.get(header, 150)
            anchor = tk.E if header in numeric_columns else tk.W
            self.tree.heading(header, text=header, anchor=tk.CENTER)
            self.tree.column(header, width=width, anchor=anchor, minwidth=50, stretch=False)

    def load_data(self):
        try:
            # Vaciar la tabla
            for row in self.tree.get_children():
                self.tree.delete(row)
            field_mapping = self.field_mappings.get(self.current_collection, {})
            collection_ref = self.db.collection(self.current_collection)
            docs = collection_ref.stream()
            self.current_data = []
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
                self.current_data.append(row)
            self.populate_tree()
            self.status_var.set(f"Mostrando {len(self.current_data)} registros")
        except Exception as e:
            messagebox.showerror("Error de Carga", f"No se pudieron cargar los datos: {e}")

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for row_data in self.current_data:
            self.tree.insert("", tk.END, values=row_data)

    def filter_data(self):
        # En este ejemplo simplemente se recarga la data.
        # Aquí podrías implementar filtros basados en self.search_var.get()
        self.load_data()

    def show_advanced_filter(self):
        dialog = EnhancedFilterDialog(self, "Filtros Avanzados", self.current_collection,
                                    self.field_mappings[self.current_collection])
        # La propiedad result se establece correctamente después de OK
        if dialog.result:  # Esto ya no será None si el usuario hizo clic en OK
            # Aquí puedes aplicar los filtros a la consulta de Firestore
            messagebox.showinfo("Filtros", f"Filtros aplicados: {dialog.result}")

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

    def export_data(self):
        if not self.current_data:
            messagebox.showinfo("Exportar", "No hay datos para exportar")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Exportar datos"
        )
        if not filename:
            return
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(self.collections[self.current_collection])
                for row in self.current_data:
                    writer.writerow(row)
            messagebox.showinfo("Exportar", f"Datos exportados exitosamente a {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar datos: {e}")

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


if __name__ == "__main__":
    app = FirestoreAdminApp()
    app.mainloop()
