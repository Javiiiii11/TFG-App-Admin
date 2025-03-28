import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import firebase_admin
from firebase_admin import credentials, firestore
import threading
import time

class EnhancedFilterDialog(simpledialog.Dialog):
    def __init__(self, parent, title, collection, field_mappings):
        self.collection = collection
        self.field_mappings = field_mappings
        self.result = {}
        super().__init__(parent, title)

    def body(self, master):
        # Dynamically create filter fields based on collection
        self.fields = {}
        row_count = 0
        
        # Invert field mappings to get user-friendly names
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
                # Numeric range filters
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
                # Dropdown filters for categorical data
                options = ["Todos", "Bajo", "Medio", "Alto", "Principiante", "Intermedio", "Avanzado"]
                var = tk.StringVar(value="Todos")
                dropdown = ttk.Combobox(master, textvariable=var, values=options, state="readonly", width=15)
                dropdown.grid(row=row_count, column=1, columnspan=4, sticky='ew', padx=5)
                
                self.fields[field] = {"var": var, "type": "categorical"}
            
            elif field == "fechaCreacion":
                # Date range filter
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

        return None  # Override default focus

    def apply(self):
        for field, config in self.fields.items():
            if config['type'] == 'numeric':
                try:
                    min_val = config['min'].get()
                    max_val = config['max'].get()
                    
                    if min_val or max_val:
                        min_val = float(min_val) if min_val else float('-inf')
                        max_val = float(max_val) if max_val else float('inf')
                        self.result[field] = {'min': min_val, 'max': max_val}
                except ValueError:
                    messagebox.showerror("Error", f"Valor inválido para {field}")
                    return
            
            elif config['type'] == 'categorical':
                value = config['var'].get()
                if value != "Todos":
                    self.result[field] = value
            
            elif config['type'] == 'date':
                start_val = config['start'].get()
                end_val = config['end'].get()
                
                if start_val or end_val:
                    self.result[field] = {'start': start_val, 'end': end_val}

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
            
            self.loading_label = tk.Label(
                self, 
                text="Cargando...", 
                font=("Helvetica", 14), 
                bg='white',
                fg='#2c3e50'
            )
            self.loading_label.pack(pady=10)
            
            self.progress = ttk.Progressbar(
                self, 
                orient="horizontal", 
                length=300, 
                mode='indeterminate'
            )
            self.progress.pack(pady=10)
            self.progress.start()
            
        except Exception as e:
            print(f"Error cargando logo de splash: {e}")

class FirestoreAdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.splash = SplashScreen(self)
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
        self.iconbitmap('icono/gymrace.ico')
        
        self.user_id_to_name = {}
        
        self.collections = {
            "usuarios": [
                "ID", "Nombre", "Edad", "Peso", "Altura", 
                "Días entrenamiento", "Nivel de Experiencia", "Objetivo Fitness"
            ],
            "rutinas": [
                "ID", "Nombre", "Usuario", "Descripción", 
                "Dificultad", "Ejercicios", "Fecha de Creación"
            ],
            "dietas": [
                "ID", "Nombre", "Descripción", "Alimentos Permitidos", 
                "Alimentos Prohibidos", "Calorias", "Comidas"
            ]
        }
        self.current_collection = "usuarios"
        
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
                "Fecha de Creación": "fechaCreacion",
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
        
        self.current_data = []
        self.sort_column = None
        self.sort_reverse = False
        
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
        # Configure main grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
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
        
        title_label = tk.Label(
            header_frame, 
            text="Panel de Administración GymRace", 
            font=("Helvetica", 20, "bold"), 
            fg="white", 
            bg="#2c3e50"
        )
        title_label.grid(row=0, column=1, sticky="w", padx=10)
        
        # === MENÚ LATERAL ===
        sidebar_frame = tk.Frame(self, bg="#34495e", width=250)
        sidebar_frame.grid(row=1, column=0, sticky="nsew")
        sidebar_frame.grid_propagate(False)
        
        # Style configuration
        style = ttk.Style()
        style.configure('Custom.TButton', 
                        font=('Helvetica', 10), 
                        background='#3498db',  # Brighter blue
                        foreground='white')
        style.map('Custom.TButton', 
                  background=[('active', '#2980b9')],  # Darker blue on hover
                  foreground=[('active', 'white')])
        
        # Colecciones Label
        collections_label = tk.Label(
            sidebar_frame, 
            text="Colecciones", 
            font=("Helvetica", 14, "bold"), 
            fg="white", 
            bg="#34495e"
        )
        collections_label.grid(row=0, column=0, pady=10, sticky="w", padx=10)
        
        # Collection Dropdown
        self.collection_var = tk.StringVar(value="Usuarios")
        self.collection_dropdown = ttk.Combobox(
            sidebar_frame, 
            textvariable=self.collection_var, 
            state="readonly",
            values=["Usuarios", "Rutinas", "Dietas"],
            font=("Helvetica", 12)
        )
        self.collection_dropdown.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.collection_dropdown.bind("<<ComboboxSelected>>", self.on_collection_change)
        
        # Update Button
        update_btn = tk.Button(
            sidebar_frame, 
            text="Actualizar", 
            font=("Helvetica", 12), 
            bg="#3498db",  # Bright blue
            fg="white",
            command=self.load_data
        )
        update_btn.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        # Search Label
        search_label = tk.Label(
            sidebar_frame, 
            text="Buscar:", 
            font=("Helvetica", 12), 
            fg="white", 
            bg="#34495e"
        )
        search_label.grid(row=3, column=0, pady=5, sticky="w", padx=10)
        
        # Search Entry
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(
            sidebar_frame, 
            textvariable=self.search_var, 
            font=("Helvetica", 12)
        )
        search_entry.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        
        # # Search and Advanced Filter Buttons
        # search_btn = tk.Button(
        #     sidebar_frame, 
        #     text="🔍 Buscar", 
        #     font=("Helvetica", 12), 
        #     bg="#3498db",  # Bright blue
        #     fg="white",
        #     command=self.filter_data
        # )
        # search_btn.grid(row=5, column=0, padx=10, pady=5, sticky="ew")

        # advanced_filter_btn = tk.Button(
        #     sidebar_frame, 
        #     text="📊 Filtros Avanzados", 
        #     font=("Helvetica", 12), 
        #     bg="#3498db",  # Bright blue
        #     fg="white",
        #     command=self.show_advanced_filter
        # )
        # advanced_filter_btn.grid(row=6, column=0, padx=10, pady=5, sticky="ew")
        
        # === TABLA DE DATOS ===
        table_frame = tk.Frame(self, bd=2, relief=tk.RIDGE)
        table_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        style = ttk.Style()
        style.configure("Treeview", stretchheadings=False, stretchcolumns=False)
        self.tree = ttk.Treeview(table_frame, columns=self.collections[self.current_collection], show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.setup_table_headers()

    def setup_table_headers(self):
        headers = self.collections[self.current_collection]
        self.tree["columns"] = headers
        
        base_column_widths = {
            "ID": 210, "Nombre": 120, "Descripción": 550, "Edad": 70,
            "Peso": 70, "Altura": 70, "Días entrenamiento": 130,
            "Nivel de Experiencia": 180, "Objetivo Fitness": 200,
            "Estado": 80, "Alimentos Permitidos": 400,
            "Alimentos Prohibidos": 400, "Calorias": 100,
            "Comidas": 270, "Usuario": 150
        }
        
        collection_overrides = {
            "dietas": {}, "rutinas": {}, "usuarios": {}
        }
        
        collection_anchors = {
            "dietas": tk.W, "rutinas": tk.W, "usuarios": tk.W
        }
        
        current_overrides = collection_overrides.get(self.current_collection, {})
        anchor = collection_anchors.get(self.current_collection, tk.CENTER)
        
        total_width = 0
        
        for header in headers:
            width = current_overrides.get(header, base_column_widths.get(header, 150))
            total_width += width
            
            self.tree.heading(header, text=header, command=lambda col=header: self.sort_treeview(col))
            self.tree.column(header, width=width, anchor=anchor, minwidth=50, stretch=False)
        
        table_frame_width = self.winfo_width() - 300
        if total_width < table_frame_width:
            for important_col in ["Descripción", "Objetivo Fitness", "Nombre"]:
                if important_col in headers:
                    self.tree.column(
                        important_col, 
                        width=base_column_widths.get(important_col, 150) + (table_frame_width - total_width)
                    )
                    break

    def sort_treeview(self, column):
        if not self.current_data:
            return
            
        headers = self.collections[self.current_collection]
        col_idx = headers.index(column)
        
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_reverse = False
            self.sort_column = column
        
        def convert_value(value, idx):
            if idx in [2, 3, 4]:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return str(value).lower()
            return str(value).lower()
        
        self.current_data.sort(
            key=lambda x: convert_value(x[col_idx], col_idx), 
            reverse=self.sort_reverse
        )
        
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        for row_data in self.current_data:
            self.tree.insert("", tk.END, values=row_data)
        
        for header in headers:
            if header == column:
                direction = " ↓" if self.sort_reverse else " ↑"
                self.tree.heading(header, text=f"{header}{direction}", 
                                  command=lambda col=header: self.sort_treeview(col))
            else:
                self.tree.heading(header, text=header, 
                                  command=lambda col=header: self.sort_treeview(col))

    def on_collection_change(self, event):
        collection_mapping = {
            "Usuarios": "usuarios",
            "Rutinas": "rutinas",
            "Dietas": "dietas"
        }
        display_name = self.collection_var.get()
        self.current_collection = collection_mapping.get(display_name, display_name.lower())
        
        if self.current_collection == "rutinas":
            self.load_user_names()
            
        self.setup_table_headers()
        self.load_data()

    def load_data(self):
        try:
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
                        row.append(str(data.get(firestore_field, 'N/A')))

                self.current_data.append(row)
            
            for row_data in self.current_data:
                self.tree.insert("", tk.END, values=row_data)
            
            self.sort_column = None
            self.sort_reverse = False
            for header in self.collections[self.current_collection]:
                self.tree.heading(header, text=header)
                
        except Exception as e:
            messagebox.showerror("Error de Carga", f"No se pudieron cargar los datos: {e}")
    
    def filter_data(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self.load_data()
            return

        try:
            for row in self.tree.get_children():
                self.tree.delete(row)

            field_mapping = self.field_mappings.get(self.current_collection, {})
            self.current_data = []
            collection_ref = self.db.collection(self.current_collection)
            docs = collection_ref.stream()
            
            for doc in docs:
                data = doc.to_dict()
                match_found = False
                for field_value in data.values():
                    if query in str(field_value).lower():
                        match_found = True
                        break
                
                if match_found:
                    row = [str(doc.id)]
                    for header in self.collections[self.current_collection][1:]:
                        firestore_field = field_mapping.get(header, header.lower())
                        
                        if self.current_collection == "rutinas" and header == "Usuario":
                            user_id = data.get("usuarioId", "")
                            user_name = self.user_id_to_name.get(user_id, "N/A")
                            row.append(user_name)
                        else:
                            row.append(str(data.get(firestore_field, 'N/A')))

                    self.current_data.append(row)
            
            if not self.current_data:
                messagebox.showinfo("Sin resultados", f"No se encontraron resultados para '{query}'")
            
            for row_data in self.current_data:
                self.tree.insert("", tk.END, values=row_data)

            self.sort_column = None
            self.sort_reverse = False
            for header in self.collections[self.current_collection]:
                self.tree.heading(header, text=header)

        except Exception as e:
            messagebox.showerror("Error de Filtro", f"No se pudo encontrar los datos: {e}")

    def show_advanced_filter(self):
        """Show advanced filter dialog for the current collection"""
        filter_dialog = EnhancedFilterDialog(
            self, 
            "Filtros Avanzados", 
            self.current_collection, 
            self.field_mappings[self.current_collection]
        )
        
        if filter_dialog.result:
            self.apply_advanced_filter(filter_dialog.result)

    def apply_advanced_filter(self, filter_conditions):
        """Apply advanced filtering based on user-selected conditions"""
        try:
            for row in self.tree.get_children():
                self.tree.delete(row)

            collection_ref = self.db.collection(self.current_collection)
            docs = collection_ref.stream()
            
            self.current_data = []

            for doc in docs:
                data = doc.to_dict()
                match = True

                for field, condition in filter_conditions.items():
                    if isinstance(condition, dict):
                        if 'min' in condition and 'max' in condition:
                            # Numeric range filter
                            value = float(data.get(field, 0))
                            if not (condition['min'] <= value <= condition['max']):
                                match = False
                                break
                        elif 'start' in condition and 'end' in condition:
                            # Date range filter
                            value = data.get(field, '')
                            if condition['start'] and value < condition['start']:
                                match = False
                                break
                            if condition['end'] and value > condition['end']:
                                match = False
                                break
                    else:
                        # Categorical filter
                        if str(data.get(field, '')).lower() != condition.lower():
                            match = False
                            break

                if match:
                    row = [str(doc.id)]
                    for header in self.collections[self.current_collection][1:]:
                        firestore_field = self.field_mappings[self.current_collection].get(header, header.lower())
                        
                        if self.current_collection == "rutinas" and header == "Usuario":
                            user_id = data.get("usuarioId", "")
                            user_name = self.user_id_to_name.get(user_id, "N/A")
                            row.append(user_name)
                        else:
                            row.append(str(data.get(firestore_field, 'N/A')))

                    self.current_data.append(row)
            
            if not self.current_data:
                messagebox.showinfo("Sin resultados", "No se encontraron resultados con los filtros aplicados")
            
            for row_data in self.current_data:
                self.tree.insert("", tk.END, values=row_data)

            self.sort_column = None
            self.sort_reverse = False
            for header in self.collections[self.current_collection]:
                self.tree.heading(header, text=header)

        except Exception as e:
            messagebox.showerror("Error de Filtro", f"No se pudo aplicar los filtros: {e}")


if __name__ == '__main__':
    app = FirestoreAdminApp()
    app.mainloop()
    try:
        firebase_admin.delete_app(firebase_admin.get_app())
        print("Conexión a Firebase cerrada.")
    except Exception as e:
        print(f"Error cerrando Firebase: {e}")