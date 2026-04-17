import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

def procesar_par_y_guardar_evidencia(img1_path, img2_path, K, folder_name, output_name):
    """Detecta SIFT, guarda imagen de matches y retorna datos 3D."""
    # Leer imágenes
    img1 = cv2.imread(img1_path)
    img2 = cv2.imread(img2_path)
    
    if img1 is None or img2 is None:
        return None, None, None

    # Escala consistente (puedes ajustarla al 40% como en tu otro script)
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(gray1, None)
    kp2, des2 = sift.detectAndCompute(gray2, None)

    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    good_matches = []
    pts1, pts2 = [], []
    
    # Filtro de Lowe
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append([m])
            pts1.append(kp1[m.queryIdx].pt)
            pts2.append(kp2[m.trainIdx].pt)

    pts1 = np.float32(pts1)
    pts2 = np.float32(pts2)

    # --- PARTE 1: GUARDAR EVIDENCIA VISUAL ---
    # Dibujamos los matches como en apply_sift_images.py
    img_matches = cv2.drawMatchesKnn(img1, kp1, img2, kp2, good_matches, None, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    
    output_dir = os.path.join('evidencias', folder_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    cv2.imwrite(os.path.join(output_dir, output_name), img_matches)
    # -----------------------------------------

    if len(pts1) < 10:
        return None, None, None

    # --- PARTE 2: CÁLCULO 3D ---
    E, mask = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
    _, R, t, mask = cv2.recoverPose(E, pts1, pts2, K)

    # Triangulación local
    P1 = K @ np.hstack((np.eye(3), np.zeros((3, 1))))
    P2 = K @ np.hstack((R, t))
    pts_4d = cv2.triangulatePoints(P1, P2, pts1.T, pts2.T)
    pts_3d = pts_4d[:3] / pts_4d[3]

    return pts_3d, R, t

def procesar_carpeta(input_root, folder_name):
    folder_path = os.path.join(input_root, folder_name)
    image_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    
    if len(image_files) < 2:
        return

    # Parámetros de cámara (K)
    temp_img = cv2.imread(os.path.join(folder_path, image_files[0]))
    h, w = temp_img.shape[:2]
    K = np.array([[w, 0, w/2], [0, w, h/2], [0, 0, 1]])

    all_points = []
    R_acc = np.eye(3)
    t_acc = np.zeros((3, 1))

    print(f"\n>> Procesando carpeta: {folder_name}")

    for i in range(len(image_files) - 1):
        img1_path = os.path.join(folder_path, image_files[i])
        img2_path = os.path.join(folder_path, image_files[i+1])
        
        output_name = f"match_{image_files[i][:-4]}_to_{image_files[i+1][:-4]}.jpg"
        
        points_3d, R, t = procesar_par_y_guardar_evidencia(img1_path, img2_path, K, folder_name, output_name)

        if points_3d is not None:
            # Transformación al sistema global
            points_global = R_acc @ points_3d + t_acc
            all_points.append(points_global)

            # Actualizar pose acumulada
            t_acc = t_acc + R_acc @ t
            R_acc = R_acc @ R
            print(f"   [OK] Par {i+1}/{len(image_files)-1} guardado y triangulado.")
        else:
            print(f"   [!] Par {i+1} falló: No hay suficientes coincidencias.")

    if all_points:
        cloud_final = np.hstack(all_points)
        visualizar_nube(cloud_final, folder_name, w, h)

def visualizar_nube(cloud, folder_name, w, h):
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    Xs, Ys, Zs = cloud[0], cloud[1], cloud[2]
    # Filtro para que la gráfica no se vea mal por puntos ruidosos
    mask = (np.abs(Xs) < w) & (np.abs(Ys) < h) & (Zs > 0) & (Zs < w*3)
    
    ax.scatter(Xs[mask], Zs[mask], -Ys[mask], c=Zs[mask], cmap='jet', s=1)
    ax.set_title(f"Reconstrucción 3D: {folder_name}")
    
    plt.savefig(os.path.join('evidencias', folder_name, 'resultado_3d.png'))
    print(f"Finalizado: Reconstrucción guardada en evidencias/{folder_name}/resultado_3d.png")
    plt.show()

def main():
    if len(sys.argv) < 2:
        print("Uso: python reconstruccion_3d_con_evidencia.py <directorio_con_subcarpetas>")
        return

    input_path = sys.argv[1]
    for subfolder in os.listdir(input_path):
        if os.path.isdir(os.path.join(input_path, subfolder)):
            procesar_carpeta(input_path, subfolder)

if __name__ == "__main__":
    main()