import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
from ultralytics import YOLO

# Clases Objetivo en COCO (ej. 2 para 'car') - Plan B: Object-Centric
TARGET_CLASSES = {2}

def obtener_mascara_estatica(img_color, model, save_path):
    """
    Ejecuta YOLO para detectar objetos objetivo y retorna una máscara enfocada.
    Guarda una imagen de verificación visual.
    """
    # 1. Ejecutar inferencia
    results = model(img_color, verbose=False)
    
    # 2. Crear máscara inicial completamente negra (0) - Solo el objeto será blanco
    h, w = img_color.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    
    # Imagen de visualización (copia)
    vis_img = img_color.copy()

    # 3. Procesar detecciones
    if len(results) > 0:
        boxes = results[0].boxes
        for box in boxes:
            cls_id = int(box.cls[0].item())
            if cls_id in TARGET_CLASSES:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                # Pintar de blanco (255) el área del objeto objetivo en la máscara
                mask[y1:y2, x1:x2] = 255
                
                # Dibujar rectángulo verde en la imagen de visualización
                cv2.rectangle(vis_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(vis_img, f"Target {cls_id}", (x1, y1-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # 4. Oscurecer el área enmascarada (el fondo) para la visualización
    vis_img[mask == 0] = (vis_img[mask == 0] * 0.3).astype(np.uint8)

    # 5. Asegurar que el directorio exista y guardar la imagen
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    cv2.imwrite(save_path, vis_img)

    return mask



def procesar_carpeta(folder_path, folder_name, yolo_model):
    # Cargar imágenes de la subcarpeta
    image_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    if len(image_files) < 2:
        return

    # Parámetros de cámara simplificados
    test_img = cv2.imread(os.path.join(folder_path, image_files[0]))
    h, w = test_img.shape[:2]
    focal_length = w
    cx, cy = w / 2, h / 2
    K = np.array([[focal_length, 0, cx], [0, focal_length, cy], [0, 0, 1]])

    # Inicialización de la nube global
    all_points = []
    
    # Pose acumulada
    R_acc = np.eye(3)
    t_acc = np.zeros((3, 1))

    print(f"--- Procesando {folder_name}: {len(image_files)} imágenes ---")

    # Carpeta base para guardar las imágenes de YOLO
    yolo_output_dir = os.path.join('YOLO-Img', folder_name)

    # Buscar archivo Ground-Truth bbox.txt
    seq_num = ''.join(filter(str.isdigit, folder_name))
    bbox_filename = f'bbox_{seq_num}.txt' if seq_num else 'bbox.txt'
    bbox_file_path = None
    
    if os.path.exists(os.path.join(folder_path, bbox_filename)):
        bbox_file_path = os.path.join(folder_path, bbox_filename)
    else:
        for root, dirs, files in os.walk('datasets'):
            if bbox_filename in files:
                bbox_file_path = os.path.join(root, bbox_filename)
                break

    bbox_lines = []
    if bbox_file_path:
        print(f"  > Archivo Ground-Truth bbox detectado: {bbox_file_path}")
        with open(bbox_file_path, 'r') as f:
            bbox_lines = [line.strip().split() for line in f.readlines() if line.strip()]
            
    if len(bbox_lines) == len(image_files):
        print("  > Usando bbox_20.txt para enmascarado perfecto en lugar de YOLO...")
    else:
        print("  > Detectando objetos objetivo con YOLO...")
        bbox_lines = []

    masks = []
    gray_images = []
    for idx, img_file in enumerate(image_files):
        img_path = os.path.join(folder_path, img_file)
        img_color = cv2.imread(img_path)
        gray_images.append(cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY))
        
        save_path = os.path.join(yolo_output_dir, img_file)
        
        if bbox_lines:
            # Formato EPFL (x, y, w, h)
            b_vals = [float(v) for v in bbox_lines[idx]]
            x1, y1 = int(b_vals[0]), int(b_vals[1])
            x2, y2 = int(x1 + b_vals[2]), int(y1 + b_vals[3])
            
            h_img, w_img = img_color.shape[:2]
            mask = np.zeros((h_img, w_img), dtype=np.uint8)
            mask[y1:y2, x1:x2] = 255
            
            vis_img = img_color.copy()
            cv2.rectangle(vis_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(vis_img, "GT BBox", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            vis_img[mask == 0] = (vis_img[mask == 0] * 0.3).astype(np.uint8)
            
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            cv2.imwrite(save_path, vis_img)
        else:
            mask = obtener_mascara_estatica(img_color, yolo_model, save_path)
            
        masks.append(mask)

    print("  > Iniciando triangulación secuencial con PnP...")
    
    sift = cv2.SIFT_create()
    bf = cv2.BFMatcher()
    
    print("  > Extrayendo descriptores SIFT...")
    keypoints = []
    descriptors = []
    for i in range(len(image_files)):
        kp, des = sift.detectAndCompute(gray_images[i], masks[i])
        keypoints.append(kp)
        descriptors.append(des)

    all_points_global = []
    P_mats = {}
    P_mats[0] = K @ np.hstack((np.eye(3), np.zeros((3, 1))))
    
    # Diccionario de tracking: keypoint_index_en_img_anterior -> 3D_point_global
    track_3d = {}

    for i in range(1, len(image_files)):
        kp1, des1 = keypoints[i-1], descriptors[i-1]
        kp2, des2 = keypoints[i], descriptors[i]
        
        if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
            print(f"  > Par {i-1}-{i} ignorado (faltan keypoints).")
            track_3d = {}
            continue
            
        matches = bf.knnMatch(des1, des2, k=2)
        good = []
        for m_n in matches:
            if len(m_n) == 2:
                m, n = m_n
                if m.distance < 0.70 * n.distance:
                    good.append(m)
                    
        if len(good) < 10:
            print(f"  > Par {i-1}-{i} ignorado (faltan matches).")
            track_3d = {}
            continue

        pts1 = np.float32([kp1[m.queryIdx].pt for m in good])
        pts2 = np.float32([kp2[m.trainIdx].pt for m in good])
        
        if i == 1 or len(track_3d) < 10:
            print(f"  > Intentando inicializar/recuperar en par {i-1}-{i} con {len(pts1)} matches...")
            # Inicialización con Matriz Esencial
            E, mask_E = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
            if E is None or E.shape != (3, 3):
                print(f"  > Fallo en EssentialMat en par {i-1}-{i}. E es None o shape incorrecto.")
                track_3d = {}
                continue
                
            _, R_rel, t_rel, mask_E = cv2.recoverPose(E, pts1, pts2, K)
            
            if mask_E is None:
                print(f"  > recoverPose devolvió mask_E None.")
                track_3d = {}
                continue
            
            inliers_count = np.sum(mask_E == 255)
            print(f"  > recoverPose inliers: {inliers_count} de {len(mask_E)}")
            if inliers_count == 0:
                print(f"  > recoverPose falló: 0 inliers.")
                track_3d = {}
                continue
                
            if i == 1:
                P_mats[i] = K @ np.hstack((R_rel, t_rel))
            else:
                # Si se perdió el rastro, reiniciamos el sistema de coordenadas local
                P_mats[i-1] = K @ np.hstack((np.eye(3), np.zeros((3, 1))))
                P_mats[i] = K @ np.hstack((R_rel, t_rel))
                
            inliers_idx = np.where(mask_E.ravel() == 255)[0]
            pts1_in = pts1[inliers_idx]
            pts2_in = pts2[inliers_idx]
            
            pts_4d = cv2.triangulatePoints(P_mats[i-1], P_mats[i], pts1_in.T, pts2_in.T)
            pts_3d = (pts_4d[:3] / pts_4d[3]).T
            
            all_points_global.append(pts_3d)
            print(f"  > Inicialización (Par {i-1}-{i}) completada. Puntos: {len(pts_3d)}")
            
            track_3d = {}
            for idx_in_inlier, orig_idx in enumerate(inliers_idx):
                m = good[orig_idx]
                track_3d[m.trainIdx] = pts_3d[idx_in_inlier]
                
        else:
            # PnP para propagar la escala y la pose global
            obj_pts = []
            img_pts = []
            train_idx_list = []
            
            for m in good:
                if m.queryIdx in track_3d:
                    obj_pts.append(track_3d[m.queryIdx])
                    img_pts.append(kp2[m.trainIdx].pt)
                    train_idx_list.append(m.trainIdx)
                    
            if len(obj_pts) < 10:
                print(f"  > PnP falló en {i-1}-{i}: pocos puntos 3D-2D ({len(obj_pts)}).")
                track_3d = {}
                continue
                
            obj_pts = np.float32(obj_pts)
            img_pts = np.float32(img_pts)
            
            success, rvec, tvec, inliers = cv2.solvePnPRansac(obj_pts, img_pts, K, None, flags=cv2.SOLVEPNP_ITERATIVE)
            
            if not success or inliers is None or len(inliers) < 5:
                print(f"  > PnP falló RANSAC en {i-1}-{i}.")
                track_3d = {}
                continue
                
            R_global, _ = cv2.Rodrigues(rvec)
            P_mats[i] = K @ np.hstack((R_global, tvec))
            
            # Actualizar tracker con inliers de PnP
            new_track_3d = {}
            for inl in inliers:
                idx = inl[0]
                new_track_3d[train_idx_list[idx]] = obj_pts[idx]
                
            # Triangular nuevos puntos usando la nueva pose para densificar
            E, mask_E = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
            if E is not None:
                inliers_E_idx = np.where(mask_E.ravel() == 255)[0]
                pts1_in = pts1[inliers_E_idx]
                pts2_in = pts2[inliers_E_idx]
                
                if len(pts1_in) > 0:
                    pts_4d = cv2.triangulatePoints(P_mats[i-1], P_mats[i], pts1_in.T, pts2_in.T)
                    pts_3d = (pts_4d[:3] / pts_4d[3]).T
                    
                    added = 0
                    for idx_in_inlier, orig_idx in enumerate(inliers_E_idx):
                        m = good[orig_idx]
                        if m.trainIdx not in new_track_3d:
                            new_track_3d[m.trainIdx] = pts_3d[idx_in_inlier]
                            added += 1
                    
                    all_points_global.append(pts_3d)
                    print(f"  > Par {i-1}-{i} procesado (PnP). Puntos añadidos: {added}")
            
            track_3d = new_track_3d

    if not all_points_global:
        print("No se pudieron generar puntos globales.")
        return

    cloud_final = np.vstack(all_points_global).T
    visualizar_y_guardar(cloud_final, folder_name, w, h)

def visualizar_y_guardar(cloud, folder_name, w, h):
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')

    Xs, Ys, Zs = cloud[0], cloud[1], cloud[2]

    # Filtro de Outliers (Estadístico simple para mitigar visualmente el Scale Drift)
    z_median = np.median(Zs)
    z_std = np.std(Zs)
    # Mantener puntos que no se disparen hacia el infinito en Z ni estén fuera de vista en XY
    mask = (np.abs(Xs) < w * 2) & (np.abs(Ys) < h * 2) & (Zs > 0) & (Zs < z_median + 2 * z_std)
    
    ax.scatter(Xs[mask], Zs[mask], -Ys[mask], c=Zs[mask], cmap='viridis', marker='.', s=2, alpha=0.8)

    ax.set_title(f"Reconstrucción 3D Completa: {folder_name} (Filtered & GT BBox)")
    ax.set_xlabel('X')
    ax.set_ylabel('Profundidad (Z)')
    ax.set_zlabel('Altura (Y)')

    output_dir = os.path.join('evidencias', folder_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    plt.savefig(os.path.join(output_dir, 'nube_3d_yolo_completa.png'), dpi=300)
    print(f"Resultado guardado en evidencias/{folder_name}/nube_3d_yolo_completa.png")
    
    # Vista interactiva 3D con Matplotlib
    #plt.show() 

def main():
    if len(sys.argv) != 2:
        print("Uso: python reconstruction_3d_yolo.py <input_path_carpetas>")
        sys.exit(1)

    input_path = sys.argv[1]

    if not os.path.exists('evidencias'):
        os.makedirs('evidencias')
        
    print("Cargando modelo YOLO (yolov8n.pt)...")
    model = YOLO("yolov8n.pt")

    for folder_name in os.listdir(input_path):
        folder_path = os.path.join(input_path, folder_name)
        if os.path.isdir(folder_path):
            procesar_carpeta(folder_path, folder_name, model)

if __name__ == "__main__":
    main()
