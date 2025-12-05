import cv2
import numpy as np
import matplotlib.pyplot as plt

### Reconstrucción 3D (Nube de puntos) entre dos imágenes usando SIFT y triangulación

# La idea central será aplicar nuevamente SIFT y matching, pero esta vez lo que haremos será triangular esos puntos 
# para obtener sus coordenadas 3D relativas y visualizar la nube como un scatter plot 3D

# Cargar las fotos originales
print("Cargando imágenes para reconstrucción 3D...")
img1 = cv2.imread('Img_prueba/Llama/minus_15.jpeg')  # Izquierda
img2 = cv2.imread('Img_prueba/Llama/front.jpeg')     # Centro

# Redimensionar para que tenga el mismo analisis que en apply_sift_images.py
scale_percent = 100
w = int(img1.shape[1] * scale_percent / 100)
h = int(img1.shape[0] * scale_percent / 100)
img1 = cv2.resize(img1, (w, h))
img2 = cv2.resize(img2, (w, h))

# Calculo de SIFT
sift = cv2.SIFT_create()
kp1, des1 = sift.detectAndCompute(cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY), None)
kp2, des2 = sift.detectAndCompute(cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY), None)

# Hallando matches
bf = cv2.BFMatcher()
matches = bf.knnMatch(des1, des2, k=2)

# Filtro y extracción de coordenadas (x,y)
pts1 = []
pts2 = []
for m, n in matches:
    if m.distance < 0.70 * n.distance: 
        pts1.append(kp1[m.queryIdx].pt)
        pts2.append(kp2[m.trainIdx].pt)

pts1 = np.float32(pts1)
pts2 = np.float32(pts2)

## Aplicación de la triangulación para obtener coordenadas 3D
# Estimación simple de focal length (Ancho de la imagen)
focal_length = w  
center = (w/2, h/2)
K = np.array([[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]])

# Calcular Matriz Esencial y Pose
E, _ = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
_, R, t, _ = cv2.recoverPose(E, pts1, pts2, K)

# Matrices de Proyección
P1 = K @ np.hstack((np.eye(3), np.zeros((3, 1))))
P2 = K @ np.hstack((R, t))

# Triangular
points_4d = cv2.triangulatePoints(P1, P2, pts1.T, pts2.T)
points_3d = points_4d[:3] / points_4d[3]

# Visualización de la nube de puntos 3D en las coordenadas relativas
print("Generando ventana 3D")
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Ejes
Xs = points_3d[0]
Ys = points_3d[1]
Zs = points_3d[2]

# Filtro de limpieza visual (para quitar puntos infinitos)
mask = (abs(Xs) < w) & (abs(Ys) < h) & (Zs > 0) & (Zs < w*2)

ax.scatter(Xs[mask], Zs[mask], -Ys[mask], c='b', marker='.', s=2)
ax.set_xlabel('X')
ax.set_ylabel('Profundidad Z')
ax.set_zlabel('Altura Y')
ax.set_title('Nube de Puntos Generada (Objetivo Específico 3)')

plt.show()