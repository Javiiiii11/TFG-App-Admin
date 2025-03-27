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
        self.minsize(1000, 600)  # Tamaño mínimo para evitar desbordamientos
        # maximizando la ventana
        self.state('zoomed')
        self.iconbitmap('gymrace.ico')
        
        # Collections dictionary with display headers
        self.collections = {
            "usuarios": ["ID", "Nombre", "Edad", "Peso", "Altura", "Días entrenamiento", "Nivel de Experiencia", "Objetivo Fitness"],
            "rutinas": ["ID", "Nombre", "Fecha", "Ubicación", "Descripción"],
            "dietas": ["ID", "Usuario", "Evento", "Fecha", "Estado"]
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
                "Fecha": "fecha",
                "Ubicación": "ubicacion",
                "Descripción": "descripcion"
            },
            "dietas": {
                "Usuario": "usuario",
                "Evento": "evento",
                "Fecha": "fecha", 
                "Estado": "estado",
                "alimentosPermitidos": {
                "proteinasMagras": ["pollo", "pescado"],
                "vegetalesNoFeculentos": ["espinacas", "brócoli"],
                "frutasBajasEnAzucar": ["fresas", "moras"]
  }
            }
        }
        
        # Variables para ordenación
        self.current_data = []
        self.sort_column = None
        self.sort_reverse = False
        
        self.init_firebase()
        self.create_widgets()
        self.load_data()

    def init_firebase(self):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate('firebase-credentials.json')
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
        except Exception as e:
            messagebox.showerror("Error de Firebase", f"No se pudo inicializar Firebase: {e}")

    def create_widgets(self):
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(1, weight=1)
        
        # === HEADER ===
        header_frame = tk.Frame(self, bg="#2c3e50", height=80)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        try:
            logo_img = Image.open("gymrace.png")
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
        
        tk.Label(header_frame, text="Panel de Administración GymRace", font=("Helvetica", 20, "bold"), fg="white", bg="#2c3e50").grid(row=0, column=1, sticky="w", padx=10)
        
        # === MENÚ LATERAL ===
        sidebar_frame = tk.Frame(self, bg="#34495e", width=250)
        sidebar_frame.grid(row=1, column=0, sticky="ns")
        sidebar_frame.grid_propagate(False)
        
        tk.Label(sidebar_frame, text="Colecciones", font=("Helvetica", 14, "bold"), fg="white", bg="#34495e").pack(pady=10)
        
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
        
        tk.Button(sidebar_frame, text="Actualizar", font=("Helvetica", 12), command=self.load_data).pack(padx=10, pady=10, fill="x")
        
        tk.Label(sidebar_frame, text="Buscar:", font=("Helvetica", 12), fg="white", bg="#34495e").pack(pady=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(sidebar_frame, textvariable=self.search_var, font=("Helvetica", 12))
        search_entry.pack(padx=10, pady=5, fill="x")
        tk.Button(sidebar_frame, text="Buscar", font=("Helvetica", 12), command=self.filter_data).pack(padx=10, pady=5, fill="x")
        
        # === TABLA DE DATOS ===
        table_frame = tk.Frame(self, bd=2, relief=tk.RIDGE)
        table_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        self.tree = ttk.Treeview(table_frame, columns=self.collections[self.current_collection], show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.setup_table_headers()

    def setup_table_headers(self):
        headers = self.collections[self.current_collection]
        self.tree["columns"] = headers
        
        # Define column widths based on content type
        column_widths = {
            "ID": 200,
            "Nombre": 120,
            "Edad": 70,      # Smaller width for numeric data
            "Peso": 70,      # Smaller width for numeric data
            "Altura": 70,    # Smaller width for numeric data
            "Días entrenamiento": 130,
            "Nivel de Experiencia": 150,
            "Objetivo Fitness": 200,  # Wider for longer text
            "Fecha": 100,
            "Ubicación": 150,
            "Descripción": 250,  # Wider for longer text
            "Usuario": 150,
            "Evento": 160,
            "Estado": 80
        }
    
        for header in headers:
            # Get optimal width from the dictionary, or use 150 as default
            width = column_widths.get(header, 150)
            
            self.tree.heading(header, text=header, 
                            command=lambda col=header: self.sort_treeview(col))
            self.tree.column(header, width=width, anchor=tk.CENTER, minwidth=50)

    def sort_treeview(self, column):
        """Ordena la tabla cuando se hace clic en una columna"""
        if not self.current_data:
            return
            
        # Obtener el índice de la columna
        headers = self.collections[self.current_collection]
        col_idx = headers.index(column)
        
        # Invertir el orden si se hace clic en la misma columna
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_reverse = False
            self.sort_column = column
        
        # Función para convertir valores para una ordenación adecuada
        def convert_value(value, idx):
            # Si es un número, convertir para ordenación numérica
            if idx in [2, 3, 4]:  # Edad, Peso, Altura son típicamente numéricos
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return str(value).lower()
            return str(value).lower()
        
        # Ordenar los datos
        self.current_data.sort(
            key=lambda x: convert_value(x[col_idx], col_idx), 
            reverse=self.sort_reverse
        )
        
        # Limpiar y repoblar el árbol
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        for row_data in self.current_data:
            self.tree.insert("", tk.END, values=row_data)
        
        # Actualizar las cabeceras de columna con indicadores de dirección
        for header in headers:
            if header == column:
                direction = " ↓" if self.sort_reverse else " ↑" 
                self.tree.heading(header, text=f"{header}{direction}", 
                                 command=lambda col=header: self.sort_treeview(col))
            else:
                # Eliminar cualquier indicador previo
                self.tree.heading(header, text=header, 
                                 command=lambda col=header: self.sort_treeview(col))

    def on_collection_change(self, event):
        # Map display names to collection names
        collection_mapping = {
            "Usuarios": "usuarios",
            "Rutinas": "rutinas",
            "Dietas": "dietas"
        }
        display_name = self.collection_var.get()
        self.current_collection = collection_mapping.get(display_name, display_name.lower())
        self.setup_table_headers()
        self.load_data()
    
    def load_data(self):
        try:
            for row in self.tree.get_children():
                self.tree.delete(row)
            
            # Get the appropriate field mapping for the current collection
            field_mapping = self.field_mappings.get(self.current_collection, {})
            
            collection_ref = self.db.collection(self.current_collection)
            docs = collection_ref.stream()
            
            self.current_data = []  # Reset current data

            for doc in docs:
                data = doc.to_dict()
                row = [str(doc.id)]
                
                for header in self.collections[self.current_collection][1:]:
                    # Use mapping if available, otherwise use lowercase header
                    firestore_field = field_mapping.get(header, header.lower())
                    row.append(str(data.get(firestore_field, 'N/A')))

                self.current_data.append(row)
            
            # Insert data into Treeview
            for row_data in self.current_data:
                self.tree.insert("", tk.END, values=row_data)
            
            # Reset sort indicators
            self.sort_column = None
            self.sort_reverse = False
            for header in self.collections[self.current_collection]:
                self.tree.heading(header, text=header)
                
        except Exception as e:
            messagebox.showerror("Error de Carga", f"No se pudieron cargar los datos: {e}")
    
    def filter_data(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self.load_data()  # Volver a cargar todos los datos si el filtro está vacío
            return

        try:
            for row in self.tree.get_children():
                self.tree.delete(row)

            # Get the appropriate field mapping for the current collection
            field_mapping = self.field_mappings.get(self.current_collection, {})
            
            self.current_data = []  # Reiniciar los datos actuales con los filtrados
            collection_ref = self.db.collection(self.current_collection)
            docs = collection_ref.stream()
            
            for doc in docs:
                data = doc.to_dict()
                # Check if query matches any field value
                match_found = False
                for field_value in data.values():
                    if query in str(field_value).lower():
                        match_found = True
                        break
                
                if match_found:
                    row = [str(doc.id)]
                    for header in self.collections[self.current_collection][1:]:
                        # Use mapping if available, otherwise use lowercase header
                        firestore_field = field_mapping.get(header, header.lower())
                        row.append(str(data.get(firestore_field, 'N/A')))
                    
                    self.current_data.append(row)
            
            # Check if no results were found and show message
            if not self.current_data:
                messagebox.showinfo("Sin resultados", f"No se encontraron resultados para '{query}'")
            
            # Insertar los datos en el Treeview
            for row_data in self.current_data:
                self.tree.insert("", tk.END, values=row_data)

            # Resetear indicadores de ordenación
            self.sort_column = None
            self.sort_reverse = False
            for header in self.collections[self.current_collection]:
                self.tree.heading(header, text=header)

        except Exception as e:
            messagebox.showerror("Error de Filtro", f"No se pudo encontrar los datos: {e}")
            
if __name__ == '__main__':
    app = FirestoreAdminApp()
    app.mainloop()
