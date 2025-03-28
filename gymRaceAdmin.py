import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import firebase_admin
from firebase_admin import credentials, firestore

class FirestoreAdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GymRace Admin Panel")
        self.geometry("1200x700")  # Tamaño inicial
        self.minsize(1000, 600)    # Tamaño mínimo para evitar desbordamientos
        self.state('zoomed')       # Maximizando la ventana
        self.iconbitmap('icono/gymrace.ico')
        
        # User cache for faster lookup
        self.user_id_to_name = {}  # Dictionary to cache user IDs and names
        
        # Collections dictionary with display headers
        self.collections = {
            "usuarios": [
                "ID", 
                "Nombre", 
                "Edad", 
                "Peso", 
                "Altura", 
                "Días entrenamiento", 
                "Nivel de Experiencia", 
                "Objetivo Fitness"
            ],
            "rutinas": [
                "ID", 
                "Nombre", 
                "Usuario",  # <-- NUEVO: Agregamos la columna "Usuario"
                "Descripción",
                "Dificultad",
                "Ejercicios",
                "Fecha de Creación"  # <-- NUEVO: Agregamos la columna "Fecha de Creación"
            ],
            "dietas": [
                "ID",
                "Nombre",
                "Descripción",
                "Alimentos Permitidos",
                "Alimentos Prohibidos",
                "Calorias",
                "Comidas"
            ]
        }
        self.current_collection = "usuarios"
        
        # Field mappings for each collection type
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
                "Usuario": "usuarioId",  # <-- NUEVO: Mapeamos "Usuario" a "usuarioID"
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
        
        # Variables para ordenación
        self.current_data = []
        self.sort_column = None
        self.sort_reverse = False
        
        self.init_firebase()
        self.create_widgets()
        self.load_user_names()  # Load user cache initially
        self.load_data()

    def init_firebase(self):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate('credencialesFireBase/firebase-credentials.json')
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
        except Exception as e:
            messagebox.showerror("Error de Firebase", f"No se pudo inicializar Firebase: {e}")

    def load_user_names(self):
        """Carga todos los nombres de usuarios para referenciarlos por ID."""
        try:
            self.user_id_to_name = {}  # Limpiar caché existente
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
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(1, weight=1)
        
        # === HEADER ===
        header_frame = tk.Frame(self, bg="#2c3e50", height=80)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        try:
            logo_img = Image.open("img/gymrace.png")
            try:
                logo_img = logo_img.resize((60, 60), Image.Resampling.LANCZOS)
            except AttributeError:
                try:
                    logo_img = logo_img.resize((60, 60), Image.LANCZOS)
                except AttributeError:
                    logo_img = logo_img.resize((60, 60), Image.BICUBIC)
                    
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            tk.Label(header_frame, image=self.logo_photo, bg="#2c3e50").grid(row=0, column=0, padx=20, pady=10)
        except Exception as e:
            print(f"Error cargando logo: {e}")
        
        tk.Label(
            header_frame, 
            text="Panel de Administración GymRace", 
            font=("Helvetica", 20, "bold"), 
            fg="white", 
            bg="#2c3e50"
        ).grid(row=0, column=1, sticky="w", padx=10)
        
        # === MENÚ LATERAL ===
        sidebar_frame = tk.Frame(self, bg="#34495e", width=250)
        sidebar_frame.grid(row=1, column=0, sticky="ns")
        sidebar_frame.grid_propagate(False)
        
        tk.Label(
            sidebar_frame, 
            text="Colecciones", 
            font=("Helvetica", 14, "bold"), 
            fg="white", 
            bg="#34495e"
        ).pack(pady=10)
        
        # Collection dropdown with display names
        self.collection_var = tk.StringVar(value="Usuarios")
        self.collection_dropdown = ttk.Combobox(
            sidebar_frame, 
            textvariable=self.collection_var, 
            state="readonly",
            values=["Usuarios", "Rutinas", "Dietas"],
            font=("Helvetica", 12)
        )
        self.collection_dropdown.pack(padx=10, pady=5, fill="x")
        self.collection_dropdown.bind("<<ComboboxSelected>>", self.on_collection_change)
        
        tk.Button(
            sidebar_frame, 
            text="Actualizar", 
            font=("Helvetica", 12), 
            command=self.load_data
        ).pack(padx=10, pady=10, fill="x")
        
        tk.Label(sidebar_frame, text="Buscar:", font=("Helvetica", 12), fg="white", bg="#34495e").pack(pady=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(sidebar_frame, textvariable=self.search_var, font=("Helvetica", 12))
        search_entry.pack(padx=10, pady=5, fill="x")
        tk.Button(
            sidebar_frame, 
            text="Buscar", 
            font=("Helvetica", 12), 
            command=self.filter_data
        ).pack(padx=10, pady=5, fill="x")
        
        # === TABLA DE DATOS ===
        table_frame = tk.Frame(self, bd=2, relief=tk.RIDGE)
        table_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Create the Treeview
        style = ttk.Style()
        style.configure("Treeview", stretchheadings=False, stretchcolumns=False)
        self.tree = ttk.Treeview(table_frame, columns=self.collections[self.current_collection], show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure the Treeview to use both scrollbars
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.setup_table_headers()

    def setup_table_headers(self):
        headers = self.collections[self.current_collection]
        self.tree["columns"] = headers
        
        # Define base column widths for all collections
        base_column_widths = {
            "ID": 210,
            "Nombre": 120,
            "Descripción": 550,
            "Edad": 70,
            "Peso": 70,
            "Altura": 70,
            "Días entrenamiento": 130,
            "Nivel de Experiencia": 180,
            "Objetivo Fitness": 200,
            "Estado": 80,
            "Alimentos Permitidos": 400,
            "Alimentos Prohibidos": 400,
            "Calorias": 100,
            "Comidas": 270,
            "Usuario": 150  # <-- Para la nueva columna "Usuario"
        }
        
        # Collection-specific overrides
        collection_overrides = {
            "dietas": {
                # Podrías añadir overrides específicos si deseas
                "Nombre": 200
            },
            "rutinas": {
                # Podrías añadir overrides específicos si deseas
                "Nombre": 200,
                "Dificultad": 100,
                "Ejercicios": 900,
                "Fecha de Creacion": 150,

            },
            "usuarios": {
                # Podrías añadir overrides específicos si deseas
            }
        }
        
        # Collection-specific text alignment settings
        collection_anchors = {
            "dietas": tk.W,
            "rutinas": tk.W,
            "usuarios": tk.W
        }
        
        current_overrides = collection_overrides.get(self.current_collection, {})
        anchor = collection_anchors.get(self.current_collection, tk.CENTER)
        
        total_width = 0
        
        for header in headers:
            width = current_overrides.get(header, base_column_widths.get(header, 150))
            total_width += width
            
            self.tree.heading(header, text=header, command=lambda col=header: self.sort_treeview(col))
            self.tree.column(header, width=width, anchor=anchor, minwidth=50, stretch=False)
        
        # Ajuste opcional si el total de columnas es menor que el espacio disponible
        table_frame_width = self.winfo_width() - 300  # Aproximación
        if total_width < table_frame_width:
            for important_col in ["Descripción", "Objetivo Fitness", "Nombre"]:
                if important_col in headers:
                    self.tree.column(
                        important_col, 
                        width=base_column_widths.get(important_col, 150) + (table_frame_width - total_width)
                    )
                    break

    def sort_treeview(self, column):
        """Ordena la tabla cuando se hace clic en una columna."""
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
            if idx in [2, 3, 4]:  # Ejemplo: columnas que sean numéricas (ajustar según tus necesidades)
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
        
        # Si cambiamos a rutinas, aseguramos que los nombres de usuarios estén cargados
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
                
                # Recorremos las columnas definidas en self.collections, 
                # excepto la primera (ID) que ya añadimos.
                for header in self.collections[self.current_collection][1:]:
                    firestore_field = field_mapping.get(header, header.lower())

                    if self.current_collection == "rutinas" and header == "Usuario":
                        # Usar el caché de nombres en lugar de consultar Firestore
                        user_id = data.get("usuarioId", "")
                        user_name = self.user_id_to_name.get(user_id, "N/A")
                        row.append(user_name)
                    else:
                        row.append(str(data.get(firestore_field, 'N/A')))


                self.current_data.append(row)
            
            # Insertar en el Treeview
            for row_data in self.current_data:
                self.tree.insert("", tk.END, values=row_data)
            
            # Reset de sort
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
                        
                        # Usar el caché de nombres en lugar de consultar Firestore
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

if __name__ == '__main__':
    app = FirestoreAdminApp()
    app.mainloop()
    firebase_admin.delete_app(firebase_admin.get_app())
    print("Conexión a Firebase cerrada.")