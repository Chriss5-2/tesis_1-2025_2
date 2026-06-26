# Fundamentos Matemáticos de la Reconstrucción 3D Monocular

Este documento detalla las fórmulas matemáticas y procedimientos de álgebra lineal implementados subyacentemente en el script `reconstruction_3d_general.py`. Estos fundamentos son la base de la fotogrametría clásica y la estructura a partir del movimiento (Structure from Motion - SfM).

## 1. Extracción y Emparejamiento de Características (SIFT)

El script comienza detectando puntos clave usando el algoritmo SIFT. Para decidir si un punto en la imagen 1 corresponde a un punto en la imagen 2, se compara la distancia euclidiana entre sus descriptores $x$ e $y$ (vectores de 128 dimensiones):

\[ d(x, y) = \sqrt{\sum_{i=1}^{128} (x_i - y_i)^2} \]

Para filtrar falsos positivos, se aplica el **Criterio de Lowe (Ratio Test)**, el cual exige que la distancia a la mejor coincidencia ($d_1$) sea significativamente menor que la distancia a la segunda mejor coincidencia ($d_2$):

\[ \frac{d_1}{d_2} < 0.70 \]

## 2. Geometría Epipolar y la Matriz Esencial ($E$)

La relación geométrica entre dos cámaras que observan la misma escena en el espacio tridimensional está encapsulada en la **Matriz Esencial ($E$)**. Si tenemos un punto 3D $X$ proyectado en las coordenadas normalizadas de la primera cámara como $x_1$ y en la segunda como $x_2$, se debe cumplir la **restricción epipolar**:

\[ x_2^T E x_1 = 0 \]

El algoritmo utiliza RANSAC junto con el algoritmo de los 5 puntos de Nistér para encontrar la matriz $E$ que satisfaga esta ecuación para el mayor número de inliers.

## 3. Diagonalización y Descomposición de Valores Singulares (SVD)

Este es el núcleo matemático que permite extraer la posición y rotación de la cámara. La "diagonalización" de matrices rectangulares o no simétricas como $E$ se realiza a través de la **Descomposición de Valores Singulares (Singular Value Decomposition - SVD)**. 

Cualquier matriz $E \in \mathbb{R}^{3 \times 3}$ se puede factorizar como:

\[ E = U \Sigma V^T \]

Donde:
*   $U$ y $V$ son matrices ortogonales de $3 \times 3$ (representan rotaciones).
*   $\Sigma$ es una matriz diagonal que contiene los valores singulares.

Por las propiedades intrínsecas de la matriz esencial, sus valores singulares deben ser obligatoriamente de la forma $(\sigma, \sigma, 0)$. Internamente, OpenCV obliga esta propiedad "limpiando" la matriz obtenida en el paso anterior y recalculándola como:

\[ E' = U \text{diag}(1, 1, 0) V^T \]

### 3.1 Recuperación de la Pose ($R, t$)
Una vez diagonalizada y factorizada la matriz $E = U \Sigma V^T$, se puede extraer la matriz de Rotación ($R$) y el vector de Traslación ($t$). Se define una matriz fija $W$ que representa una rotación de $\pm 90^\circ$ alrededor del eje Z:

\[ W = \begin{pmatrix} 0 & -1 & 0 \\ 1 & 0 & 0 \\ 0 & 0 & 1 \end{pmatrix} \]

Las posibles soluciones matemáticas para la rotación son:
\[ R = U W V^T \quad \text{o} \quad R = U W^T V^T \]

Y el vector de traslación se extrae directamente de la última columna de la matriz ortogonal $U$:
\[ t = \pm U_3 \]

La función `cv2.recoverPose` evalúa las 4 posibles combinaciones (2 rotaciones $\times$ 2 traslaciones) y escoge la única solución válida en la que los puntos 3D triangulados caen **delante** de ambas cámaras (profundidad $Z > 0$).

## 4. Triangulación de Puntos (Transformación Lineal Directa - DLT)

Una vez que se tienen las matrices de proyección de ambas cámaras:
*   Cámara 1 (en el origen): $P_1 = K [I_{3 \times 3} \mid 0_{3 \times 1}]$
*   Cámara 2: $P_2 = K [R \mid t]$

Buscamos encontrar las coordenadas del punto 3D $X = (X, Y, Z, 1)^T$ a partir de sus proyecciones 2D en cada imagen $x_1$ y $x_2$. 

Matemáticamente, la proyección de un punto 3D en la imagen se define como:
\[ s_i x_i = P_i X \]

Para eliminar el factor de escala $s_i$, se utiliza el producto cruz, asumiendo que el rayo proyectado y el punto 3D deben ser colineales (su producto cruz es cero):
\[ x_i \times (P_i X) = 0 \]

Desarrollando esta ecuación para ambas cámaras simultáneamente, se formula un sistema homogéneo de ecuaciones lineales de la forma:
\[ A X = 0 \]

Para resolver este sistema y encontrar el punto óptimo minimizando el error, nuevamente se utiliza el concepto de diagonalización/SVD. Se calcula la SVD de la matriz $A = U_A \Sigma_A V_A^T$. El punto tridimensional óptimo $X$ (en coordenadas homogéneas) corresponde a la última columna de la matriz ortogonal $V_A$ (el vector propio asociado al menor valor singular de $A$).

## 5. Transformación Global de Coordenadas

El pipeline del script acumula las transformaciones de cada par de fotos local para formar una nube de puntos global. Matemáticamente, las transformaciones afines se combinan y se encadenan mediante multiplicaciones matriciales.

Para el par de imágenes en el instante $i+1$, la rotación y traslación global acumulada se calcula iterativamente:
\[ R_{global}^{(i+1)} = R_{global}^{(i)} R_{local}^{(i+1)} \]
\[ t_{global}^{(i+1)} = t_{global}^{(i)} + R_{global}^{(i)} t_{local}^{(i+1)} \]

Finalmente, un punto local 3D ($P_{local}$) calculado en la iteración actual se transforma al sistema de coordenadas global inicial usando:
\[ P_{global} = R_{global} P_{local} + t_{global} \]
