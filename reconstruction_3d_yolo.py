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

def obtener_datos_3d(img1, img2, mask1, mask2, K):
    """Calcula la pose y triangula puntos entre dos imágenes usando máscaras."""
    sift = cv2.SIFT_create()
    
    # Extraer características SOLO en el área permitida (fondo estático)
    kp1, des1 = sift.detectAndCompute(img1, mask1)
    kp2, des2 = sift.detectAndCompute(img2, mask2)

    # Si no hay suficientes puntos, abortar
    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        return None, None, None

    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    pts1, pts2 = [], []
    for m_n in matches:
        if len(m_n) == 2:
            m, n = m_n
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

    print("  > Iniciando triangulación...")
    for i in range(len(image_files) - 1):
        img1 = gray_images[i]
        img2 = gray_images[i+1]
        mask1 = masks[i]
        mask2 = masks[i+1]

        points_3d, R, t = obtener_datos_3d(img1, img2, mask1, mask2, K)

        if points_3d is not None:
            # Transformar puntos locales al sistema global
            points_global = R_acc @ points_3d + t_acc
            all_points.append(points_global)

            # Actualizar la pose acumulada
            t_acc = t_acc + R_acc @ t
            R_acc = R_acc @ R
            print(f"  > Par {i}-{i+1} procesado. Puntos: {points_3d.shape[1]}")
        else:
            print(f"  > Par {i}-{i+1} ignorado (sin suficientes inliers estáticos).")

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
    plt.show() 

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
