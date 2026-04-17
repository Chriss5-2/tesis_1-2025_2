"""
Reconstrucción 3D robusta a partir de secuencias de imágenes usando SIFT y triangulación.

Pipeline completo:
1. SIFT: Detección de características
2. Matching: Correspondencia entre pares
3. Pose Estimation: Cálculo de rotación y traslación
4. Triangulación: Generación de nube 3D
5. Acumulación: Integración en sistema de coordenadas global
6. Visualización: Renderizado y guardado de resultados

Dataset: EPFL GIMS08 (Multi-View Car Dataset)
Entrada: Carpeta con imágenes numeradas (e.g., 001.jpg, 002.jpg, ...)
Salida: Nube 3D visualizada en evidencias/<carpeta>/

Uso:
    python reconstruction_3d_main.py <input_path>
    
Ejemplo:
    python reconstruction_3d_main.py datasets/epfl_gims08/epfl-gims08/tripod-seq
    python reconstruction_3d_main.py images
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os
import sys
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReconstruccionSIFT3D:
    """Clase para realizar reconstrucción 3D mediante SIFT y triangulación."""
    
    def __init__(self, lowe_ratio=0.70):
        """
        Inicializa el reconstructor 3D.
        
        Args:
            lowe_ratio (float): Ratio para filtro de Lowe (0.75 recomendado)
        """
        self.lowe_ratio = lowe_ratio
        self.sift = cv2.SIFT_create()
    
    @staticmethod
    def calcular_angulo_rotacion(R):
        """
        Calcula el ángulo de rotación en grados a partir de una matriz de rotación.
        
        Args:
            R (np.ndarray): Matriz de rotación 3x3
            
        Returns:
            float: Ángulo en grados
        """
        tr = np.trace(R)
        # Evitar errores de precisión numérica
        val = (tr - 1) / 2
        val = np.clip(val, -1.0, 1.0)
        return np.degrees(np.arccos(val))
    
    def detectar_y_matchear(self, img1_gray, img2_gray):
        """
        Detecta características SIFT y encuentra correspondencias entre dos imágenes.
        
        Args:
            img1_gray (np.ndarray): Primera imagen en escala de grises
            img2_gray (np.ndarray): Segunda imagen en escala de grises
            
        Returns:
            tuple: (kp1, kp2, good_matches, pts1, pts2) o None si hay error
        """
        # Detectar características SIFT
        kp1, des1 = self.sift.detectAndCompute(img1_gray, None)
        kp2, des2 = self.sift.detectAndCompute(img2_gray, None)
        
        if des1 is None or des2 is None or len(kp1) < 5 or len(kp2) < 5:
            logger.warning("Insuficientes características detectadas")
            return None
        
        # Matching con BFMatcher
        bf = cv2.BFMatcher()
        matches = bf.knnMatch(des1, des2, k=2)
        
        if not matches:
            logger.warning("No se encontraron matches")
            return None
        
        # Aplicar filtro de Lowe
        good_matches = []
        pts1, pts2 = [], []
        
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < self.lowe_ratio * n.distance:
                    good_matches.append(m)
                    pts1.append(kp1[m.queryIdx].pt)
                    pts2.append(kp2[m.trainIdx].pt)
        
        if len(pts1) < 8:
            logger.warning(f"Muy pocos matches válidos: {len(pts1)}")
            return None
        
        pts1 = np.float32(pts1)
        pts2 = np.float32(pts2)
        
        return kp1, kp2, good_matches, pts1, pts2
    
    def estimar_pose_y_triangular(self, pts1, pts2, K):
        """
        Estima la pose relativa y triangula puntos 3D.
        
        Args:
            pts1 (np.ndarray): Puntos en primera imagen
            pts2 (np.ndarray): Puntos en segunda imagen
            K (np.ndarray): Matriz de calibración de cámara
            
        Returns:
            tuple: (pts_3d, R, t, mask) o None si hay error
        """
        try:
            # Calcular matriz esencial
            E, mask = cv2.findEssentialMat(
                pts1, pts2, K, 
                method=cv2.RANSAC, 
                prob=0.999, 
                threshold=1.0
            )
            
            if E is None:
                logger.warning("No se pudo calcular matriz esencial")
                return None
            
            # Recuperar pose (R, t)
            _, R, t, mask = cv2.recoverPose(E, pts1, pts2, K)
            
            # Filtrar inliers según RANSAC
            pts1_in = pts1[mask.ravel() == 255]
            pts2_in = pts2[mask.ravel() == 255]
            
            if len(pts1_in) < 4:
                logger.warning("Muy pocos inliers después de RANSAC")
                return None
            
            # Matrices de proyección
            P1 = K @ np.hstack((np.eye(3), np.zeros((3, 1))))
            P2 = K @ np.hstack((R, t))
            
            # Triangulación
            pts_4d = cv2.triangulatePoints(P1, P2, pts1_in.T, pts2_in.T)
            pts_3d = pts_4d[:3] / pts_4d[3]
            
            return pts_3d, R, t, mask
        
        except Exception as e:
            logger.error(f"Error en estimación de pose: {e}")
            return None
    
    def procesar_carpeta(self, folder_path, folder_name, K):
        """
        Procesa una carpeta de imágenes secuenciales para obtener reconstrucción 3D.
        
        Args:
            folder_path (str): Ruta a la carpeta
            folder_name (str): Nombre de la carpeta
            K (np.ndarray): Matriz de calibración
            
        Returns:
            np.ndarray: Nube de puntos 3D (3 x N)
        """
        # Cargar archivos de imagen
        image_files = sorted([
            f for f in os.listdir(folder_path) 
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])
        
        if len(image_files) < 2:
            logger.error(f"Carpeta {folder_name} contiene < 2 imágenes")
            return None
        
        logger.info(f"Procesando {folder_name}: {len(image_files)} imágenes")
        
        # Inicialización
        all_points = []
        R_acc = np.eye(3)  # Rotación acumulada
        t_acc = np.zeros((3, 1))  # Traslación acumulada
        matches_guardados = 0
        
        # Crear carpeta de salida
        output_dir = os.path.join('evidencias', folder_name)
        os.makedirs(output_dir, exist_ok=True)
        
        # Procesar todos los pares consecutivos para usar toda la secuencia.
        for idx_ancla in range(len(image_files) - 1):
            idx_cand = idx_ancla + 1

            img_ancla_path = os.path.join(folder_path, image_files[idx_ancla])
            img_cand_path = os.path.join(folder_path, image_files[idx_cand])

            img_ancla_color = cv2.imread(img_ancla_path)
            img_cand_color = cv2.imread(img_cand_path)

            if img_ancla_color is None or img_cand_color is None:
                logger.warning(
                    f"No se pudieron leer imágenes del par: "
                    f"{image_files[idx_ancla]} -> {image_files[idx_cand]}"
                )
                continue

            img_ancla_gray = cv2.cvtColor(img_ancla_color, cv2.COLOR_BGR2GRAY)
            img_cand_gray = cv2.cvtColor(img_cand_color, cv2.COLOR_BGR2GRAY)

            # Detectar y matchear
            resultado_match = self.detectar_y_matchear(img_ancla_gray, img_cand_gray)
            if resultado_match is None:
                continue

            kp1, kp2, matches, pts1, pts2 = resultado_match

            # Estimar pose y triangular
            resultado_pose = self.estimar_pose_y_triangular(pts1, pts2, K)
            if resultado_pose is None:
                continue

            pts_3d, R, t, mask = resultado_pose
            angulo = self.calcular_angulo_rotacion(R)

            logger.info(
                f"[MATCH] {image_files[idx_ancla]} → "
                f"{image_files[idx_cand]} | Ángulo: {angulo:.2f}° | "
                f"Puntos: {pts_3d.shape[1]} | Matches: {len(matches)}"
            )

            # Transformar puntos al sistema global
            points_global = R_acc @ pts_3d + t_acc
            all_points.append(points_global)

            # Actualizar pose acumulada
            t_acc = t_acc + R_acc @ t
            R_acc = R_acc @ R

            # Guardar visualización de matches
            img_matches = cv2.drawMatches(
                img_ancla_color, kp1,
                img_cand_color, kp2,
                matches, None,
                matchesMask=mask.ravel().tolist(),
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
            )

            match_filename = os.path.join(
                output_dir,
                f"match_{image_files[idx_ancla][:-4]}_"
                f"to_{image_files[idx_cand][:-4]}.jpg"
            )
            cv2.imwrite(match_filename, img_matches)
            matches_guardados += 1
        
        logger.info(f"Completado: {len(all_points)} pares procesados, "
                   f"{matches_guardados} matches guardados")
        
        if not all_points:
            logger.error("No se generaron puntos 3D")
            return None
        
        # Consolidar nube
        cloud_final = np.hstack(all_points)
        return cloud_final
    
    @staticmethod
    def filtrar_y_visualizar(cloud, folder_name, img_width, img_height, aplicar_filtro_outliers=False):
        """
        Filtra outliers y visualiza la nube 3D.
        
        Args:
            cloud (np.ndarray): Nube 3D (3 x N)
            folder_name (str): Nombre de carpeta
            img_width (int): Ancho de imagen
            img_height (int): Alto de imagen
            aplicar_filtro_outliers (bool): Si True aplica filtro de outliers,
                si False muestra todos los puntos.
        """
        Xs, Ys, Zs = cloud[0], cloud[1], cloud[2]

        if aplicar_filtro_outliers:
            # Filtro de outliers basado en escala de imagen
            mask = (
                (np.abs(Xs) < img_width * 2) &
                (np.abs(Ys) < img_height * 2) &
                (Zs > 0) &
                (Zs < img_width * 5)
            )
            logger.info(f"Puntos antes de filtro: {cloud.shape[1]}")
            logger.info(f"Puntos después de filtro: {np.sum(mask)}")
        else:
            # Usar todos los puntos sin recorte.
            mask = np.ones_like(Zs, dtype=bool)
            logger.info(f"Puntos totales (sin filtro de outliers): {cloud.shape[1]}")
        
        # Crear figura 3D
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Scatter plot con colormapping por profundidad
        scatter = ax.scatter(
            Xs[mask], Zs[mask], -Ys[mask],
            c=Zs[mask], cmap='viridis',
            marker='.', s=2, alpha=0.6
        )
        
        ax.set_xlabel('X (Lateral)', fontsize=10)
        ax.set_ylabel('Z (Profundidad)', fontsize=10)
        ax.set_zlabel('Y (Altura)', fontsize=10)
        ax.set_title(f'Reconstrucción 3D: {folder_name}', fontsize=12, fontweight='bold')
        
        plt.colorbar(scatter, ax=ax, label='Profundidad Z')
        
        # Guardar
        output_dir = os.path.join('evidencias', folder_name)
        output_file = os.path.join(output_dir, 'reconstruccion_3d_completa.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Visualización guardada: {output_file}")
        
        # Mostrar
        plt.show()
        plt.close()


def obtener_matriz_calibracion(img_width, img_height):
    """
    Obtiene matriz de calibración intrínseca simplificada.
    
    Args:
        img_width (int): Ancho de imagen
        img_height (int): Alto de imagen
        
    Returns:
        np.ndarray: Matriz K (3x3)
    """
    focal_length = img_width  # Aproximación: focal_length ≈ width
    cx, cy = img_width / 2, img_height / 2
    K = np.array([
        [focal_length, 0, cx],
        [0, focal_length, cy],
        [0, 0, 1]
    ])
    return K


def main():
    """Función principal del pipeline."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nEjemplo de uso:")
        print("  python reconstruction_3d_main.py images/")
        print("  python reconstruction_3d_main.py datasets/epfl_gims08/epfl-gims08/tripod-seq")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    if not os.path.exists(input_path):
        logger.error(f"La ruta no existe: {input_path}")
        sys.exit(1)
    
    # Crear directorio de evidencias
    os.makedirs('evidencias', exist_ok=True)
    
    # Inicializar reconstructor
    reconstructor = ReconstruccionSIFT3D(lowe_ratio=0.70)
    
    logger.info(f"Iniciando reconstrucción 3D desde: {input_path}")
    logger.info(f"Parámetros: lowe_ratio={reconstructor.lowe_ratio}")
    
    # Procesar cada carpeta
    folders_procesadas = 0
    
    for folder_name in sorted(os.listdir(input_path)):
        folder_path = os.path.join(input_path, folder_name)
        
        if not os.path.isdir(folder_path):
            continue
        
        logger.info(f"\n{'='*70}")
        logger.info(f"PROCESANDO CARPETA: {folder_name}")
        logger.info(f"{'='*70}")
        
        try:
            # Cargar primera imagen para obtener dimensiones
            image_files = [
                f for f in os.listdir(folder_path)
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))
            ]
            
            if not image_files:
                logger.warning(f"No hay imágenes en {folder_name}")
                continue
            
            img_test = cv2.imread(os.path.join(folder_path, image_files[0]))
            img_height, img_width = img_test.shape[:2]
            
            # Obtener matriz de calibración
            K = obtener_matriz_calibracion(img_width, img_height)
            
            # Procesar carpeta
            cloud = reconstructor.procesar_carpeta(folder_path, folder_name, K)
            
            if cloud is not None:
                # Visualizar y guardar
                reconstructor.filtrar_y_visualizar(
                    cloud,
                    folder_name,
                    img_width,
                    img_height,
                    aplicar_filtro_outliers=False
                )
                folders_procesadas += 1
            else:
                logger.warning(f"No se generó nube 3D para {folder_name}")
        
        except Exception as e:
            logger.error(f"Error procesando {folder_name}: {e}")
            continue
    
    logger.info(f"\n{'='*70}")
    logger.info(f"PROCESO COMPLETADO")
    logger.info(f"Carpetas procesadas exitosamente: {folders_procesadas}")
    logger.info(f"{'='*70}")


if __name__ == "__main__":
    main()
