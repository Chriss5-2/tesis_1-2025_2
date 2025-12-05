import cv2
import numpy as np
import matplotlib.pyplot as plt

# --- 1. CONFIGURACIÓN DE ARCHIVOS ---
# Usaremos el par "Izquierda" (minus_15) vs "Centro" (front)
def apply_sift_matching(img1_path, img2_path, output_name):
    print(f"Cargando {img1_path} y {img2_path}...")
    img1 = cv2.imread(img1_path) 
    img2 = cv2.imread(img2_path)

    if img1 is None or img2 is None:
        print("No se encuentran las fotos")
        exit()

    # --- 2. REDIMENSIONAR (Importante para visualización) ---
    # Tus fotos son grandes. Las bajamos de tamaño para que SIFT vuele y la gráfica se vea bien.
    scale_percent = 40 # Porcentaje del tamaño original
    width = int(img1.shape[1] * scale_percent / 100)
    height = int(img1.shape[0] * scale_percent / 100)
    dim = (width, height)

    img1 = cv2.resize(img1, dim, interpolation = cv2.INTER_AREA)
    img2 = cv2.resize(img2, dim, interpolation = cv2.INTER_AREA)

    # Convertir a escala de grises (SIFT trabaja en B/N)
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # --- 3. ALGORITMO SIFT ---
    print("Aplicando algoritmo SIFT para detectar características entre las imágenes "+img1_path+" y "+img2_path)
    sift = cv2.SIFT_create()

    kp1, des1 = sift.detectAndCompute(gray1, None)
    kp2, des2 = sift.detectAndCompute(gray2, None)

    print(f"   > Puntos en Foto Izq: {len(kp1)}")
    print(f"   > Puntos en Foto Centro: {len(kp2)}")

    # --- 4. MATCHING (Correspondencia) ---
    print("Buscando coincidencias entre las imágenes "+img1_path+" y "+img2_path)
    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    # --- 5. FILTRO DE LOWE (El filtro de calidad) ---
    good_matches = []
    for m, n in matches:
        # Si la distancia del mejor match es menor al 75% del segundo mejor...
        if m.distance < 0.75 * n.distance:
            good_matches.append([m])

    print(f"✅ Coincidencias validadas: {len(good_matches)}")

    # --- 6. DIBUJAR RESULTADOS ---
    # Dibujamos las uniones. Flags=2 dibuja solo los puntos que hicieron match
    img_matches = cv2.drawMatchesKnn(img1, kp1, img2, kp2, good_matches, None, flags=2)

    # Convertir de BGR a RGB para que Matplotlib muestre los colores reales
    img_matches = cv2.cvtColor(img_matches, cv2.COLOR_BGR2RGB)

    plt.figure(figsize=(16, 8))
    plt.imshow(img_matches)
    plt.title(f"CORRESPONDENCIA SIFT: {len(good_matches)} puntos anclados\n(Nótese la detección en superficie texturizada)", fontsize=14)
    plt.axis('off')
    plt.tight_layout()
    plt.show()

    # Guardar imagen para tu PPT
    # Poner en la carpeta evidencias
    cv2.imwrite('evidencias/' + output_name, cv2.cvtColor(img_matches, cv2.COLOR_RGB2BGR))
    print(f"💾 ¡Imagen guardada como '{output_name}'!")


def main():
    # Par 1: Izquierda (minus_15) y Centro (front)
    apply_sift_matching('minus_15.jpeg', 'front.jpeg', 'left_plus_front.png')

    # Par 2: Centro (front) y Derecha (plus_15)
    apply_sift_matching('front.jpeg', 'plus_15.jpeg', 'front_plus_right.png')

if __name__ == "__main__":
    main()