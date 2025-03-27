import sys
import firebase_admin
from firebase_admin import credentials, firestore
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLabel, QMessageBox, QComboBox,
                             QHBoxLayout, QPushButton)
from PyQt5.QtCore import Qt

class FirestoreUserApp(QWidget):
    def __init__(self):
        super().__init__()
        self.collections = {
            "usuarios": ["ID", "Nombre", "Edad", "Peso", "Altura", "Dias de entrenamiento por semana", "Nivel de Experiencia", "Objetivo Fitness"],
            "eventos": ["ID", "Nombre", "Fecha", "Ubicación", "Descripción"],
            "reservas": ["ID", "Usuario", "Evento", "Fecha", "Estado"]
            # Add more collections as needed
        }

        self.current_collection = "usuarios"
        self.initUI()
        self.initFirebase()
        self.load_data()

    def initUI(self):
        # Set up the main window
        self.setWindowTitle('GymRace Admin Panel')
        self.setGeometry(100, 100, 1000, 700)

        # Create main layout
        layout = QVBoxLayout()

        # Title label
        title_label = QLabel('Panel de Administración GymRace')
        title_label.setStyleSheet('font-size: 20px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(title_label)

        # Collection selection controls
        collection_layout = QHBoxLayout()
        
        # Collection label
        collection_label = QLabel('Seleccionar colección:')
        collection_layout.addWidget(collection_label)
        
        # Collection dropdown
        self.collection_dropdown = QComboBox()
        for collection in self.collections.keys():
            self.collection_dropdown.addItem(collection.capitalize())
        self.collection_dropdown.currentTextChanged.connect(self.change_collection)
        collection_layout.addWidget(self.collection_dropdown)
        
        # Refresh button
        refresh_button = QPushButton('Actualizar')
        refresh_button.clicked.connect(self.load_data)
        collection_layout.addWidget(refresh_button)
        
        collection_layout.addStretch()
        layout.addLayout(collection_layout)

        # Create table for data
        self.data_table = QTableWidget()
        self.setup_table_headers()
        self.data_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.data_table)

        self.setLayout(layout)

    def setup_table_headers(self):
        headers = self.collections.get(self.current_collection, [])
        self.data_table.setColumnCount(len(headers))
        self.data_table.setHorizontalHeaderLabels(headers)

    def initFirebase(self):
        # Initialize Firebase Admin SDK
        try:
            # Initialize the app only if it hasn't been initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate('gymrace-cd864-firebase-adminsdk-fbsvc-33462da279.json')
                firebase_admin.initialize_app(cred)
            
            # Get Firestore client
            self.db = firestore.client()
        except Exception as e:
            QMessageBox.critical(self, 'Error de Firebase', 
                                 f'No se pudo inicializar Firebase: {str(e)}')

    def change_collection(self, collection_name):
        self.current_collection = collection_name.lower()
        self.setup_table_headers()
        self.load_data()

    def load_data(self):
        try:
            # Clear existing rows
            self.data_table.setRowCount(0)

            # Fetch data from current Firestore collection
            collection_ref = self.db.collection(self.current_collection)
            documents = collection_ref.stream()

            # Populate table
            for index, doc in enumerate(documents):
                doc_data = doc.to_dict()
                
                # Expand table rows
                self.data_table.insertRow(index)
                
                # Add document details to table
                # self.data_table.setItem(index, 0, QTableWidgetItem(str(doc.id)))
                
                # Handle different collection types
                if self.current_collection == "usuarios":
                    self.data_table.setItem(index, 0, QTableWidgetItem(str(doc.id)))
                    self.data_table.setItem(index, 1, QTableWidgetItem(doc_data.get('nombre', 'N/A')))
                    self.data_table.setItem(index, 2, QTableWidgetItem(doc_data.get('edad', 'N/A')))
                    self.data_table.setItem(index, 3, QTableWidgetItem(doc_data.get('peso', 'N/A')))
                    self.data_table.setItem(index, 4, QTableWidgetItem(str(doc_data.get('altura', 'N/A'))))
                    self.data_table.setItem(index, 5, QTableWidgetItem(str(doc_data.get('diasEntrenamientoPorSemana', 'N/A'))))
                    self.data_table.setItem(index, 6, QTableWidgetItem(str(doc_data.get('nivelExperiencia', 'N/A'))))
                    self.data_table.setItem(index, 7, QTableWidgetItem(str(doc_data.get('objetivoFitness', 'N/A'))))
                elif self.current_collection == "eventos":
                    self.data_table.setItem(index, 1, QTableWidgetItem(doc_data.get('nombre', 'N/A')))
                    self.data_table.setItem(index, 2, QTableWidgetItem(str(doc_data.get('fecha', 'N/A'))))
                    self.data_table.setItem(index, 3, QTableWidgetItem(doc_data.get('ubicacion', 'N/A')))
                    self.data_table.setItem(index, 4, QTableWidgetItem(doc_data.get('descripcion', 'N/A')))
                elif self.current_collection == "reservas":
                    self.data_table.setItem(index, 1, QTableWidgetItem(doc_data.get('usuario', 'N/A')))
                    self.data_table.setItem(index, 2, QTableWidgetItem(doc_data.get('evento', 'N/A')))
                    self.data_table.setItem(index, 3, QTableWidgetItem(str(doc_data.get('fecha', 'N/A'))))
                    self.data_table.setItem(index, 4, QTableWidgetItem(doc_data.get('estado', 'N/A')))
                # Add more collection handling as needed

            # Resize columns to content
            self.data_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, 'Error de Carga', 
                                 f'No se pudieron cargar los datos: {str(e)}')

def main():
    app = QApplication(sys.argv)
    user_app = FirestoreUserApp()
    user_app.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()