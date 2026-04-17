import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

def calcular_angulo_rotacion(R):
    """Calcula el ángulo de rotación en grados a partir de la matriz R."""
    tr = np.trace(R)
    # Evitar errores de precisión numérica fuera del rango [-1, 1]
    val = (tr - 1) / 2
    val = max(-1.0, min(1.0, val))
    return np.degrees(np.arccos(val))

def procesar_par_sift_pose(img1_gray, img2_gray, K):
    """Realiza SIFT, busca matches y calcula la pose relativa (R, t)."""
    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(img1_gray, None)
    kp2, des2 = sift.detectAndCompute(img2_gray, None)

    if des1 is None or des2 is None: return None

    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    good_matches = []
    pts1, pts2 = [], []
    for m, n in matches:
        if m.distance < 0.70 * n.distance:
            good_matches.append(m)
            pts1.append(kp1[m.queryIdx].pt)
            pts2.append(kp2[m.trainIdx].pt)

    if len(pts1) < 20: return None

    pts1 = np.float32(pts1)
    pts2 = np.float32(pts2)

    E, mask = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
    _, R, t, mask = cv2.recoverPose(E, pts1, pts2, K)

    # Filtrar solo puntos inliers para triangulación
    pts1_in = pts1[mask.ravel() == 255]
    pts2_in = pts2[mask.ravel() == 255]

    # Triangulación (Puntos resultantes están en el espacio de img1)
    P1 = K @ np.hstack((np.eye(3), np.zeros((3, 1))))
    P2 = K @ np.hstack((R, t))
    pts_4d = cv2.triangulatePoints(P1, P2, pts1_in.T, pts2_in.T)
    pts_3d = pts_4d[:3] / pts_4d[3]

    return pts_3d, R, t, (kp1, kp2, good_matches, mask)

def procesar_carpeta(input_root, folder_name, angulo_umbral=12.0):
    folder_path = os.path.join(input_root, folder_name)
    image_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    
    if len(image_files) < 2: return

    # Inicialización de cámara y nubes
    temp_img = cv2.imread(os.path.join(folder_path, image_files[0]))
    h, w = temp_img.shape[:2]
    K = np.array([[w, 0, w/2], [0, w, h/2], [0, 0, 1]])

    all_points = []
    R_acc = np.eye(3) # Rotación acumulada global
    t_acc = np.zeros((3, 1)) # Posición acumulada global
    
    idx_ancla = 0 # Empezamos con la primera imagen como ancla
    print(f"\n>>> Iniciando reconstrucción dinámica: {folder_name}")

    while idx_ancla < len(image_files) - 1:
        encontrado = False
        img_ancla_path = os.path.join(folder_path, image_files[idx_ancla])
        img_ancla_color = cv2.imread(img_ancla_path)
        img_ancla_gray = cv2.cvtColor(img_ancla_color, cv2.COLOR_BGR2GRAY)

        # Buscamos la siguiente imagen que cumpla el ángulo
        for idx_candidata in range(idx_ancla + 1, len(image_files)):
            img_cand_path = os.path.join(folder_path, image_files[idx_candidata])
            img_cand_color = cv2.imread(img_cand_path)
            img_cand_gray = cv2.cvtColor(img_cand_color, cv2.COLOR_BGR2GRAY)

            res = procesar_par_sift_pose(img_ancla_gray, img_cand_gray, K)
            
            if res is not None:
                pts_3d, R, t, extra = res
                angulo = calcular_angulo_rotacion(R)

                if angulo <= angulo_umbral:
                    print(f"   [MATCH] Ancla {image_files[idx_ancla]} -> {image_files[idx_candidata]} | Ángulo: {angulo:.2f}°")
                    
                    # Transformar puntos locales al sistema global
                    points_global = R_acc @ pts_3d + t_acc
                    all_points.append(points_global)

                    # Guardar evidencia visual
                    kp1, kp2, matches, mask = extra
                    img_matches = cv2.drawMatches(img_ancla_color, kp1, img_cand_color, kp2, matches, None, 
                                                 matchesMask=mask.ravel().tolist(), flags=2)
                    
                    out_dir = os.path.join('evidencias', folder_name)
                    if not os.path.exists(out_dir): os.makedirs(out_dir)
                    cv2.imwrite(os.path.join(out_dir, f"match_{image_files[idx_ancla]}_to_{image_files[idx_candidata]}.jpg"), img_matches)

                    # Actualizar ancla y pose acumulada
                    t_acc = t_acc + R_acc @ t
                    R_acc = R_acc @ R
                    idx_ancla = idx_candidata # La candidata ahora es la nueva ancla
                    encontrado = True
                    break # Salir del for para buscar desde la nueva ancla
                else:
                    # Opcional: imprimir qué imágenes se skipean
                    # print(f"      [SKIP] {image_files[idx_candidata]} (Angulo: {angulo:.2f}°)")
                    pass

        if not encontrado:
            print(f"   [FIN] No se encontraron más pares con ángulo >= {angulo_umbral}°")
            break

    if all_points:
        cloud_final = np.hstack(all_points)
        visualizar_nube(cloud_final, folder_name, w, h)

def visualizar_nube(cloud, folder_name, w, h):
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    Xs, Ys, Zs = cloud[0], cloud[1], cloud[2]
    
    # Filtro de visualización basado en escala de imagen
    mask = (np.abs(Xs) < w) & (np.abs(Ys) < h) & (Zs > 0) & (Zs < w*3)
    
    ax.scatter(Xs[mask], Zs[mask], -Ys[mask], c=Zs[mask], cmap='viridis', s=2, alpha=0.5)
    ax.set_title(f"Reconstrucción SfM Dinámica: {folder_name}")
    plt.savefig(os.path.join('evidencias', folder_name, 'resultado_3d_acumulado.png'))
    plt.show()

def main():
    if len(sys.argv) < 2:
        print("Uso: python reconstruccion_sfm_dinamica.py <directorio>")
        return
    
    input_path = sys.argv[1]
    for sub in os.listdir(input_path):
        if os.path.isdir(os.path.join(input_path, sub)):
            procesar_carpeta(input_path, sub)

if __name__ == "__main__":
    main()