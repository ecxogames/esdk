class Archivo:
    def __init__(self, nombre, contenido):
        self.nombre = nombre
        self.contenido = contenido

    # Create a method to save the content to a file and another method to load the content from a file
    def guardar(self):
        with open(self.nombre, 'w') as archivo:
            archivo.write(self.contenido)

    # Create a method to load the content from a file
    def cargar(self):
        with open(self.nombre, 'r') as archivo:
            self.contenido = archivo.read()