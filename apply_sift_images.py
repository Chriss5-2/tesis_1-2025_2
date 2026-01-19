import cv2
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# Leyendo argumentos de entrada desde ejecución, ejemplo: python apply_sift_images.py <input_path> <output_path>
if len(sys.argv) != 3:
    print("Uso: python apply_sift_images.py <input_path> <output_path>")
    sys.exit(1)

input_path = sys.argv[1]
output_path = sys.argv[2]

# Preparado de archivos
# Se trabajará por pares de imágenes
def apply_sift_matching(img1_path, img2_path, output_name, folder_name):
    print(f"Cargando {img1_path} y {img2_path}...")
    img1 = cv2.imread(img1_path) 
    img2 = cv2.imread(img2_path)

    if img1 is None or img2 is None:
        print("No se encuentran las fotos")
        exit()

    # --- 2. REDIMENSIONAR (Importante para visualización) ---
    # Le bajamos el tamaño para que se pueda aplicar mejor SIFT y se vea bien en la representación
    # Lo recomensable es disminuir el tamaño pero esto en algunas imágenes genera una pérdida de detalles en caso de que la imagen 
    # original sea pequeña. Por ello en este caso se opta por no reducir el tamaño
    scale_percent = 40 # 100% del tamaño original
    width = int(img1.shape[1] * scale_percent / 100)
    height = int(img1.shape[0] * scale_percent / 100)
    dim = (width, height)

    img1 = cv2.resize(img1, dim, interpolation = cv2.INTER_AREA)
    img2 = cv2.resize(img2, dim, interpolation = cv2.INTER_AREA)

    # Convertir a escala de grises (SIFT trabaja en B/N)
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Aplicando SIFT
    print("Aplicando algoritmo SIFT para detectar características entre las imágenes "+img1_path+" y "+img2_path)
    sift = cv2.SIFT_create()

    kp1, des1 = sift.detectAndCompute(gray1, None)
    kp2, des2 = sift.detectAndCompute(gray2, None)

    print(f"   > Puntos en Foto Izq: {len(kp1)}")
    print(f"   > Puntos en Foto Centro: {len(kp2)}")

    # Busqueda de coincidencias entre las dos imágenes
    print("Buscando coincidencias entre las imágenes "+img1_path+" y "+img2_path)
    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    # Aplicando el filtro de Lowe para obtener solo los mejores matches
    good_matches = []
    for m, n in matches:
        # La condicional nos va a servir para filtrar los matches de acuerdo a su distancia la cuál será la medida de calidad
        if m.distance < 0.75 * n.distance:
            good_matches.append([m])

    print(f"Número de coincidencias validadas: {len(good_matches)}")

    # Dibujando los resultados de las coincidencias en una sola imagen
    img_matches = cv2.drawMatchesKnn(img1, kp1, img2, kp2, good_matches, None, flags=2)

    # Como anteriormente se hizo el tratado en escala de grises
    # Ahora convertimos de BGR a RGB para que Matplotlib muestre los colores reales como la imagen original
    cv2.imwrite(
        output_path + folder_name + '/' + output_name,
        cv2.cvtColor(img_matches, cv2.COLOR_BGR2RGB)
    )
    
    # Mostrando la imagen resultante con Matplotlib
    #plt.figure(figsize=(16, 8))
    #plt.imshow(img_matches)
    #plt.title(f"CORRESPONDENCIA SIFT: {len(good_matches)} puntos anclados\n(Nótese la detección en superficie texturizada)", fontsize=14)
    #plt.axis('off')
    #plt.tight_layout()
    #plt.show()
    #plt.close()
    # Agregado para liberar memoria

    # Guardando la imagen resultante en la carpeta evidencias
    cv2.imwrite('evidencias/' + folder_name + '/' + output_name, cv2.cvtColor(img_matches, cv2.COLOR_RGB2BGR))
    print(f"Imagen guardada como '{output_name}' en la carpeta evidencias/{folder_name}!")


def main():
    # Lectura de subcarpetas en el input_path
    # Ejemplo, la carpeta imagenes, contiene la subcarpetas tripod_seq_20, tripod_seq_21, etc.
    # Leer los archivos dentro de la carpeta tripod_seq_20, y como están nombrados desde 001.jpg hasta que acaben
    # Tomar en pares consecutivos las imagenes, es decir, 001.jpg con 002.jpg, luego 002.jpg con 003.jpg, suponiendo q la ultima imagen es 100.jpg, será hasta 100.jpg con 001.jpg
    # Y guardar en la carpeta de evidencias, dentro de una subcarpeta con el mismo nombre de la subcarpeta leída
    for folder_name in os.listdir(input_path):
        folder_path = os.path.join(input_path, folder_name)
        if os.path.isdir(folder_path):
            print(f"Procesando carpeta: {folder_name}")
            output_folder = os.path.join('evidencias', folder_name)
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            image_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.jpg')])
            num_images = len(image_files)

            for i in range(num_images):
                img1_name = image_files[i]
                img2_name = image_files[(i + 1) % num_images]  # Siguiente imagen, con wrap-around

                img1_path = os.path.join(folder_path, img1_name)
                img2_path = os.path.join(folder_path, img2_name)

                output_name = f"sift_{img1_name[:-4]}_{img2_name[:-4]}.jpg"
                apply_sift_matching(img1_path, img2_path, output_name, folder_name)
        
if __name__ == "__main__":
    main()