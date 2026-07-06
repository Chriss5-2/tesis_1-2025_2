import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

# Triangulación y reconstrucción 3D usando SIFT entre tres imágenes
# Este script será la extensión de medium_points.py ya que ahora uniremos las nubes de puntos entre las tres vistas para 
# tener una reconstrucción 3D más completa de la escena

# Triangulación por par de imágenes
def obtener_nube_puntos(img_origen, img_destino, K, color_code):
    """
    Calcula puntos 3D de 'img_destino' relativos a 'img_origen'.
    img_origen será considerada la cámara en (0,0,0).
    """
    # Creación de SIFT
    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(img_origen, None)
    kp2, des2 = sift.detectAndCompute(img_destino, None)

    # Hallando matches
    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    pts1 = []
    pts2 = []
    for m, n in matches:
        if m.distance < 0.70 * n.distance:
            pts1.append(kp1[m.queryIdx].pt)
            pts2.append(kp2[m.trainIdx].pt)

    pts1 = np.float32(pts1)
    pts2 = np.float32(pts2)
    
    if len(pts1) < 5:
        return None # No hay suficientes puntos

    # Calculando matriz esencial para obtener R y t
    E, mask = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
    
    # Calculo de R y t para que la cámara destino se posicione correctamente
    _, R, t, mask = cv2.recoverPose(E, pts1, pts2, K)

    # Generando las matrices de proyección
    # Cámara 1 (Origen) está fija en el centro
    P1 = K @ np.hstack((np.eye(3), np.zeros((3, 1))))
    # Cámara 2 (Destino) se mueve según R y t calculado
    P2 = K @ np.hstack((R, t))

    # 6. Triangular
    points_4d = cv2.triangulatePoints(P1, P2, pts1.T, pts2.T)
    points_3d = points_4d[:3] / points_4d[3]
    
    return points_3d


def read_and_display_3d_reconstruction(img_left, img_center, img_right, label):
    """
    Calcula y retorna las nubes de puntos 3D a partir de tres imágenes.
    """
    if img_left is None or img_center is None or img_right is None:
        print(f"Error: Faltan imágenes para {label}")
        return None, None

    # Redimensionado igual que en medium_points.py
    scale = 100 
    h, w = int(img_center.shape[0] * scale / 100), int(img_center.shape[1] * scale / 100)
    img_left = cv2.resize(img_left, (w, h))
    img_center = cv2.resize(img_center, (w, h))
    img_right = cv2.resize(img_right, (w, h))

    # Generando matríz intrínseca K para las cámaras
    focal_length = w  # Se usa el ancho de la imagen como focal length
    cx, cy = w/2, h/2
    K = np.array([[focal_length, 0, cx], [0, focal_length, cy], [0, 0, 1]])

    # En ambos casos, nuestro punto de referencia será la cámara central
    print(f"Procesando grupo: {label}")
    # Usamos el centro como ancla
    cloud_left = obtener_nube_puntos(img_center, img_left, K, 'b')
    cloud_right = obtener_nube_puntos(img_center, img_right, K, 'r')

    return cloud_left, cloud_right

def main():
    ## Cargado de imágenes de la secuencia
    print("Cargando imágenes de tripod_seq_20/")
    
    if not os.path.exists('tripod_seq_20'):
        print("Error: La carpeta 'tripod_seq_20' no existe.")
        return
    
    # Obtener todos los archivos .jpg de la carpeta
    files = sorted([f for f in os.listdir('tripod_seq_20') if f.lower().endswith('.jpg')])
    
    if len(files) == 0:
        print("Error: No hay archivos .jpg en tripod_seq_20/")
        return
    
    print(f"Se encontraron {len(files)} imágenes")
    
    # Crear carpeta de salida
    output_dir = os.path.join('visualizacion', 'tripod_seq_20')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Acumular todas las nubes de puntos
    all_clouds_left = []
    all_clouds_right = []
    
    # Obtener primera imagen para escala
    first_img = cv2.imread(os.path.join('tripod_seq_20', files[1]), cv2.IMREAD_GRAYSCALE)
    scale = 100
    h, w = int(first_img.shape[0] * scale / 100), int(first_img.shape[1] * scale / 100)
    
    # Procesar cada grupo de 3 imágenes consecutivas (left, center, right)
    for i in range(0, len(files) - 2, 3):
        img_left_path = os.path.join('tripod_seq_20', files[i])
        img_center_path = os.path.join('tripod_seq_20', files[i + 1])
        img_right_path = os.path.join('tripod_seq_20', files[i + 2])
        
        img_left = cv2.imread(img_left_path, cv2.IMREAD_GRAYSCALE)
        img_center = cv2.imread(img_center_path, cv2.IMREAD_GRAYSCALE)
        img_right = cv2.imread(img_right_path, cv2.IMREAD_GRAYSCALE)
        
        label = f"{files[i][:-4]}_{files[i+1][:-4]}_{files[i+2][:-4]}"
        print(f"Procesando grupo: {label}")
        
        cloud_left, cloud_right = read_and_display_3d_reconstruction(img_left, img_center, img_right, label)
        
        if cloud_left is not None:
            all_clouds_left.append(cloud_left)
        if cloud_right is not None:
            all_clouds_right.append(cloud_right)
    
    # Generar visualización unida de todas las nubes
    print("\nGenerando visualización 3D combinada de toda la secuencia...")
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Función para plotear puntos
    def plot_cloud(cloud, color, alpha=0.3):
        if cloud is None: return
        Xs = cloud[0]
        Ys = cloud[1]
        Zs = cloud[2]
        
        # Quitamos los puntos muy lejanos o erróneos
        mask = (abs(Xs) < w) & (abs(Ys) < h) & (Zs > 0) & (Zs < w*2)
        
        ax.scatter(Xs[mask], Zs[mask], -Ys[mask], c=color, marker='.', s=1, alpha=alpha)
    
    # Plotear todas las nubes izquierdas y derechas
    for cloud in all_clouds_left:
        plot_cloud(cloud, 'blue', alpha=0.2)
    
    for cloud in all_clouds_right:
        plot_cloud(cloud, 'red', alpha=0.2)
    
    ax.set_xlabel('X')
    ax.set_ylabel('Profundidad Z')
    ax.set_zlabel('Altura Y')
    ax.set_title('Reconstrucción 3D Fusionada - Toda la Secuencia tripod_seq_20')
    
    # Guardar imagen
    filename = os.path.join(output_dir, 'reconstruccion_3D_completa.png')
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Imagen de reconstrucción 3D combinada guardada como: {filename}")
    plt.show()

if __name__ == "__main__":
    main()