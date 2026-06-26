import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

def obtener_datos_3d(img1, img2, K, folder_name):
    """Calcula la pose y triangula puntos entre dos imágenes."""
    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(img1, None)
    kp2, des2 = sift.detectAndCompute(img2, None)

    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    


    pts1, pts2 = [], []
    for m, n in matches:
        if m.distance < 0.70 * n.distance:
            pts1.append(kp1[m.queryIdx].pt)
            pts2.append(kp2[m.trainIdx].pt)

    pts1 = np.float32(pts1)
    pts2 = np.float32(pts2)

    if len(pts1) < 10:
        return None, None, None

    # Matriz Esencial y recuperación de Pose
    E, mask = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
    if E is None or E.shape != (3, 3):
        return None, None, None

    _, R, t, mask = cv2.recoverPose(E, pts1, pts2, K)

    if mask is None or np.sum(mask == 255) == 0:
        return None, None, None

    # Solo puntos inliers según RANSAC
    pts1_in = pts1[mask.ravel() == 255]
    pts2_in = pts2[mask.ravel() == 255]

    # Triangulación local (Cámara 1 en el origen)
    P1 = K @ np.hstack((np.eye(3), np.zeros((3, 1))))
    P2 = K @ np.hstack((R, t))
    
    pts_4d = cv2.triangulatePoints(P1, P2, pts1_in.T, pts2_in.T)
    pts_3d = pts_4d[:3] / pts_4d[3]

    return pts_3d, R, t

def procesar_carpeta(folder_path, folder_name):
    # Cargar imágenes de la subcarpeta
    image_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    if len(image_files) < 2:
        return

    # Parámetros de cámara simplificados (puedes ajustarlos)
    test_img = cv2.imread(os.path.join(folder_path, image_files[0]))
    h, w = test_img.shape[:2]
    focal_length = w
    cx, cy = w / 2, h / 2
    K = np.array([[focal_length, 0, cx], [0, focal_length, cy], [0, 0, 1]])

    # Inicialización de la nube global
    all_points = []
    
    # Pose acumulada (Empezamos en el origen)
    R_acc = np.eye(3)
    t_acc = np.zeros((3, 1))

    print(f"--- Procesando {folder_name}: {len(image_files)} imágenes ---")

    for i in range(len(image_files) - 1):
        img1 = cv2.imread(os.path.join(folder_path, image_files[i]), cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(os.path.join(folder_path, image_files[i+1]), cv2.IMREAD_GRAYSCALE)

        points_3d, R, t = obtener_datos_3d(img1, img2, K, folder_name)

        if points_3d is not None:
            # Transformar puntos locales al sistema de coordenadas global
            # P_global = R_acumulada * P_local + t_acumulada
            points_global = R_acc @ points_3d + t_acc
            all_points.append(points_global)

            # Actualizar la pose acumulada para la siguiente imagen
            t_acc = t_acc + R_acc @ t
            R_acc = R_acc @ R
            print(f"  > Par {i}-{i+1} procesado. Puntos: {points_3d.shape[1]}")

    if not all_points:
        print("No se pudieron generar puntos.")
        return

    # Consolidar todos los puntos
    cloud_final = np.hstack(all_points)
    visualizar_y_guardar(cloud_final, folder_name, w, h)

def visualizar_y_guardar(cloud, folder_name, w, h):
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')

    Xs, Ys, Zs = cloud[0], cloud[1], cloud[2]

    # Filtro de Outliers (quitar puntos que se disparan al infinito)
    mask = (np.abs(Xs) < w * 2) & (np.abs(Ys) < h * 2) & (Zs > 0) & (Zs < w * 5)
    
    ax.scatter(Xs[mask], Zs[mask], -Ys[mask], c=Zs[mask], cmap='viridis', marker='.', s=1, alpha=0.5)

    ax.set_title(f"Reconstrucción 3D Completa: {folder_name}")
    ax.set_xlabel('X')
    ax.set_ylabel('Profundidad (Z)')
    ax.set_zlabel('Altura (Y)')

    # Crear carpeta de salida si no existe
    output_dir = os.path.join('evidencias', folder_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    plt.savefig(os.path.join(output_dir, 'nube_3d_completa.png'), dpi=300)
    print(f"Resultado guardado en evidencias/{folder_name}/nube_3d_completa.png")
    plt.show()

def main():
    if len(sys.argv) != 2:
        print("Uso: python reconstruccion_3d_general.py <input_path_carpetas>")
        sys.exit(1)

    input_path = sys.argv[1]

    if not os.path.exists('evidencias'):
        os.makedirs('evidencias')

    for folder_name in os.listdir(input_path):
        folder_path = os.path.join(input_path, folder_name)
        if os.path.isdir(folder_path):
            procesar_carpeta(folder_path, folder_name)

if __name__ == "__main__":
    main()