import sys
import os

# Ingresar parametros de ejecucion de tipo, python data_filtrer.py <folder_input_path> <folder_output_path> <kind_file>
input_path = sys.argv[1]
output_path = sys.argv[2]
kind_file = sys.argv[3]
#input_path = os.path.join(folder_input_path, kind_file)
#output_path = os.path.join(folder_output_path, kind_file)
if not os.path.exists(output_path):
    os.makedirs(output_path)

# Entrar a la carpeta input y filtrar solo los archivos .jpg
# Leer el archivo .jpg y guardarlo en la carpeta de salida dentro de la subcarpeta la cual se encuentra dentro de kind_file y tiene como nombre, los 11 primeros valores del nombre del .jpg
# Así guardamos los archivos en carpetas separadas pero si son el mismo tipo de archivo se guardan en la misma carpeta
# Ejemplo: si el archivo se llama tripod_seq_20_058.jpg se guarda en la carpeta tripod_seq_20, dentro de la carpeta input, si se llama tripod_seq_20_059.jpg tambien se guarda en la misma carpeta tripod_seq_20
# Pero si el archivo se llama tripod_seq_21_001.jpg se guarda en la carpeta tripod_seq_21, dentro de la carpeta input es decir en una carpeta diferente a tripod_seq_20
# Además, si el archivo se llama tripod_seq_20_058.jpg se guarda con el nombre, 58.jpg, si se llama tripod_seq_20_059.jpg se guarda como 59.jpg, es decir solo se guarda el número del final del nombre del archivo
for file_name in os.listdir(input_path):
    if file_name.endswith('.jpg'):
        subfolder_name = file_name[:13]  # Obtener los primeros 13 caracteres del nombre del archivo
        subfolder_path = os.path.join(output_path, subfolder_name)
        
        if not os.path.exists(subfolder_path):
            os.makedirs(subfolder_path)
        
        input_file_path = os.path.join(input_path, file_name)
        output_file_name = file_name[14:]  # Obtener el número final del nombre del archivo
        output_file_path = os.path.join(subfolder_path, output_file_name)
        
        with open(input_file_path, 'rb') as infile:
            data = infile.read()
        
        with open(output_file_path, 'wb') as outfile:
            outfile.write(data)

print("Filtrado y guardado completado.")