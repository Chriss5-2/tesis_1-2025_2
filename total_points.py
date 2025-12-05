import cv2
import numpy as np
import matplotlib.pyplot as plt

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


def read_and_display_3d_reconstruction(folder_name):
    # Cargar las 3 imágenes
    img_left = cv2.imread('Img_prueba/' + folder_name + '/minus_15.jpeg', cv2.IMREAD_GRAYSCALE)
    img_center = cv2.imread('Img_prueba/' + folder_name + '/front.jpeg', cv2.IMREAD_GRAYSCALE)
    img_right = cv2.imread('Img_prueba/' + folder_name + '/plus_15.jpeg', cv2.IMREAD_GRAYSCALE)

    if img_left is None or img_center is None or img_right is None:
        print("Error: Faltan imágenes.")
        exit()

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
    print("Procesando centro e izquierda ====")
    # Usamos el centro como ancla
    cloud_left = obtener_nube_puntos(img_center, img_left, K, 'b')

    print("Procesando centro y derecha ====")
    # Usamos el centro como ancla
    cloud_right = obtener_nube_puntos(img_center, img_right, K, 'r')

    # Generando la visualización 3D fusionando ambas nubes
    print("Generando visualización 3D")
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Función para limpiar y plotear puntos
    def plot_cloud(cloud, color, label):
        if cloud is None: return
        Xs = cloud[0]
        Ys = cloud[1]
        Zs = cloud[2]
        
        # Quitamos los puntos muy lejanos o erróneos para que la visualización sea mejor
        mask = (abs(Xs) < w) & (abs(Ys) < h) & (Zs > 0) & (Zs < w*2)
        
        ax.scatter(Xs[mask], Zs[mask], -Ys[mask], c=color, marker='.', s=2, label=label, alpha=0.6)

    # Graficamos ambas nubes en el MISMO espacio
    plot_cloud(cloud_left, 'blue', 'Datos Vista Izquierda')
    plot_cloud(cloud_right, 'red', 'Datos Vista Derecha')

    ax.set_xlabel('X')
    ax.set_ylabel('Profundidad Z')
    ax.set_zlabel('Altura Y')
    ax.set_title('Reconstrucción 3D Fusionada (3 Vistas) - ' + folder_name)
    ax.legend()

    # Guardando la reconstrucción 3D como imagen en movimiento
    filename = 'visualizacion/' + folder_name + '/reconstruccion_3D_fusionada.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print("Imagen de reconstrucción 3D guardada como: " + filename)
    plt.show()

def main():
    ## Cargado de imágenes
    print("Cargando imágenes")
    Img_pruebas=["C_America", "Kirby", "Llama"]
    print("Seleccionando carpeta de imágenes: C_America")
    print("Generando reconstrucción 3D para la carpeta: C_America")
    read_and_display_3d_reconstruction("C_America")
    print("Seleccionando carpeta de imágenes: Kirby")
    print("Generando reconstrucción 3D para la carpeta: Kirby")
    read_and_display_3d_reconstruction("Kirby")
    print("Seleccionando carpeta de imágenes: Llama")
    print("Generando reconstrucción 3D para la carpeta: Llama")
    read_and_display_3d_reconstruction("Llama")

if __name__ == "__main__":
    main()