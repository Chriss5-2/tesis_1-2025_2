import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
from ultralytics import YOLO

# 1. Cargamos el modelo YOLOv8
detector = YOLO('yolov8n.pt')

def obtener_mascara_carro(img_bgr):
    """Detecta el objeto y crea una máscara para que SIFT solo trabaje ahí."""
    results = detector(img_bgr, verbose=False)
    h, w = img_bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    for result in results:
        for box in result.boxes:
            if int(box.cls[0]) in [2, 5, 7]: # Carro, Bus, Camión
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
    
    if np.sum(mask) == 0: return np.ones((h, w), dtype=np.uint8) * 255
    return mask

def calcular_angulo_rotacion(R):
    tr = np.trace(R)
    val = max(-1.0, min(1.0, (tr - 1) / 2))
    return np.degrees(np.arccos(val))

def procesar_par_sift_pose(img1_color, img2_color, K):
    gray1 = cv2.cvtColor(img1_color, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2_color, cv2.COLOR_BGR2GRAY)

    mask1 = obtener_mascara_carro(img1_color)
    mask2 = obtener_mascara_carro(img2_color)

    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(gray1, mask1)
    kp2, des2 = sift.detectAndCompute(gray2, mask2)

    if des1 is None or des2 is None: return None

    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)
    pts1, pts2, good_matches = [], [], []

    for m, n in matches:
        if m.distance < 0.70 * n.distance:
            good_matches.append(m)
            pts1.append(kp1[m.queryIdx].pt)
            pts2.append(kp2[m.trainIdx].pt)

    if len(pts1) < 20: return None

    pts1, pts2 = np.float32(pts1), np.float32(pts2)
    E, mask = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
    
    if E is None or E.shape != (3, 3): return None

    _, R, t, mask_pose = cv2.recoverPose(E, pts1, pts2, K)
    mask_ravel = mask_pose.ravel()
    pts1_in, pts2_in = pts1[mask_ravel == 255], pts2[mask_ravel == 255]

    if len(pts1_in) < 10: return None

    P1 = K @ np.hstack((np.eye(3), np.zeros((3, 1))))
    P2 = K @ np.hstack((R, t))
    pts_4d = cv2.triangulatePoints(P1, P2, pts1_in.T, pts2_in.T)
    pts_3d = pts_4d[:3] / pts_4d[3]

    return pts_3d, R, t, (kp1, kp2, good_matches, mask_pose)

def procesar_carpeta(input_root, folder_name):
    folder_path = os.path.join(input_root, folder_name)
    image_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    num_images = len(image_files)
    
    if num_images < 2: return

    temp_img = cv2.imread(os.path.join(folder_path, image_files[0]))
    h, w = temp_img.shape[:2]
    K = np.array([[w, 0, w/2], [0, w, h/2], [0, 0, 1]])

    all_points, R_acc, t_acc = [], np.eye(3), np.zeros((3, 1))

    print(f"\n>>> Procesando Secuencial con IA: {folder_name}")

    # Iteramos por cada par incluyendo el cierre (N con 001)
    for i in range(num_images):
        idx_a = i
        idx_c = (i + 1) % num_images # Wrap-around: 112 -> 001
        
        img_a = cv2.imread(os.path.join(folder_path, image_files[idx_a]))
        img_c = cv2.imread(os.path.join(folder_path, image_files[idx_c]))
        
        res = procesar_par_sift_pose(img_a, img_c, K)
        
        if res is not None:
            pts_3d, R, t, extra = res
            angulo = calcular_angulo_rotacion(R)

            print(f"   [PAR] {image_files[idx_a]} -> {image_files[idx_c]} | Ang: {angulo:.2f}°")
            
            # Transformación al mundo global
            all_points.append(R_acc @ pts_3d + t_acc)
            
            # Actualizamos pose acumulada (solo si no es el último par para no "volar" la nube al cerrar el loop)
            if i < num_images - 1:
                t_acc = t_acc + R_acc @ t
                R_acc = R_acc @ R

            # Guardar evidencia visual
            kp1, kp2, matches, m_pose = extra
            img_m = cv2.drawMatches(img_a, kp1, img_c, kp2, matches, None, matchesMask=m_pose.ravel().tolist(), flags=2)
            out_dir = os.path.join('evidencias', folder_name)
            os.makedirs(out_dir, exist_ok=True)
            cv2.imwrite(os.path.join(out_dir, f"sec_match_{image_files[idx_a]}_{image_files[idx_c]}.jpg"), img_m)
        else:
            print(f"   [X] Falló par: {image_files[idx_a]} -> {image_files[idx_c]}")

    if all_points:
        visualizar_nube(np.hstack(all_points), folder_name, w, h)

def visualizar_nube(cloud, folder_name, w, h):
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    Xs, Ys, Zs = cloud[0], cloud[1], cloud[2]
    # Filtro visual para centrar el carro
    mask = (np.abs(Xs) < w) & (np.abs(Ys) < h) & (Zs > 0) & (Zs < w*3)
    ax.scatter(Xs[mask], Zs[mask], -Ys[mask], c=Zs[mask], cmap='viridis', s=1, alpha=0.5)
    ax.set_title(f"Reconstrucción Secuencial IA: {folder_name}")
    plt.show()

def main():
    if len(sys.argv) < 2: return print("Uso: python script.py <carpeta>")
    for sub in os.listdir(sys.argv[1]):
        if os.path.isdir(os.path.join(sys.argv[1], sub)):
            procesar_carpeta(sys.argv[1], sub)

if __name__ == "__main__":
    main()