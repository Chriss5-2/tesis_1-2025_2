# Actualización: Solución al error de triangulación en `reconstruction_3d_general.py`

Se ha corregido un error crítico que causaba que el script fallara con una excepción de OpenCV al procesar pares de imágenes donde no se encontraban suficientes coincidencias válidas (inliers).

## Problema Identificado

Durante el emparejamiento de características entre dos imágenes contiguas:
1. Si no hay suficientes correspondencias geométricas consistentes, `cv2.findEssentialMat` puede retornar `None` para la matriz esencial.
2. Si se calcula la matriz esencial pero `cv2.recoverPose` no encuentra puntos que estén en frente de ambas cámaras (inliers), la máscara (`mask`) devuelta no contendrá ningún elemento válido (ningún valor igual a `255`).
3. Esto resultaba en que los arreglos `pts1_in` y `pts2_in` quedaran vacíos (tamaño `(0, 2)`).
4. Al llamar a `cv2.triangulatePoints(..., pts1_in.T, pts2_in.T)`, se le pasaban matrices vacías de forma `(2, 0)`.
5. OpenCV rechaza matrices con 0 columnas para triangulación y lanza la siguiente excepción:
   ```
   cv2.error: OpenCV(4.13.0) D:\a\opencv-python\opencv-python\opencv\modules\calib3d\src\triangulate.cpp:64: error: (-210:Unsupported format or combination of formats) Input parameters must be matrices in function 'icvTriangulatePoints'
   ```

## Modificaciones Realizadas

Se editó la función `obtener_datos_3d` en [reconstruction_3d_general.py](file:///C:/Tesis/tesis_1-2025_2/reconstruction_3d_general.py):

* **Validación de la matriz esencial (`E`):**
  Se verifica que `E` no sea `None` y que su forma sea `(3, 3)`. De lo contrario, se aborta el procesamiento de ese par retornando `None, None, None`.
  ```python
  if E is None or E.shape != (3, 3):
      return None, None, None
  ```

* **Validación de inliers en la máscara (`mask`):**
  Se verifica que `mask` no sea `None` y que contenga al menos un inlier válido (valor `255`). De lo contrario, se retorna `None, None, None`.
  ```python
  if mask is None or np.sum(mask == 255) == 0:
      return None, None, None
  ```

Con estas validaciones, cuando una pareja de imágenes no tiene correspondencias 3D válidas, el pipeline la ignora de manera segura y prosigue con la siguiente pareja, evitando la caída del script.

---

## Análisis de Problemas Actuales en el Script

Aunque `reconstruction_3d_general.py` logra una reconstrucción básica, presenta varias limitaciones inherentes a su enfoque secuencial monocular clásico:

1. **Acumulación de Error (Drift):** El script calcula la trayectoria de la cámara sumando transformaciones secuenciales de forma ciega (`R_acc = R_acc @ R` y `t_acc = t_acc + R_acc @ t`). Sin herramientas de ajuste global como *Bundle Adjustment* o detección de cierres de bucle (*Loop Closure*), los pequeños errores se acumulan rápidamente, causando que la nube de puntos se deforme severamente en trayectos largos.
2. **Ambigüedad de Escala:** Al depender de una sola cámara para estimar la traslación desde la matriz esencial, el vector `t` siempre tiene magnitud 1 (escala normalizada). El script asume que la distancia física entre cada par de fotos es exactamente igual. Si la cámara se movió con velocidad variable, las proporciones de los objetos en la nube de puntos se distorsionarán y perderán cohesión.
3. **Fragilidad Secuencial Estricta:** Solo empareja la imagen actual con la inmediatamente siguiente. Si un solo par falla (por movimiento brusco o falta de texturas), el seguimiento se rompe totalmente desde ese punto hacia adelante. No aprovecha la redundancia de comparar la imagen con fotos anteriores o posteriores (ej. $i$ con $i+2$).
4. **Filtro de Outliers Básico:** El filtrado de puntos anómalos es muy básico (cortes rígidos de límites geométricos en el espacio basado en el ancho/alto de la imagen), manteniendo puntos ruidosos generados por falsos positivos del descriptor SIFT.

## Object Detection (YOLO)

**¿Es una buena idea implementarlo?**
Sí, es una **excelente idea**. La integración de un detector de objetos de IA como YOLO moderniza enormemente los enfoques de fotogrametría clásica, aportando robustez y dándole "contexto semántico" a los puntos.

**¿Cómo podemos aplicarlo al pipeline actual?**

Existen tres formas principales de aprovechar YOLO en este script:

1. **Eliminación de Objetos Dinámicos (Masking out):** 
   * **El problema:** SIFT detecta puntos en objetos que se mueven (autos, personas, animales). Al triangularlos asumiendo que están quietos, arruinan el cálculo de la cámara y generan ruido.
   * **La solución:** Pasar la imagen por YOLO, identificar las *bounding boxes* de objetos que pueden moverse, crear una máscara negra sobre ellos y proporcionársela a SIFT (`sift.detectAndCompute(img, mask)`). De esta forma, SIFT ignorará a las personas/vehículos y solo tomará como referencia edificios o terreno (el fondo estático), haciendo que la estimación de la matriz `E` sea mucho más estable.
2. **Reconstrucción Enfocada (Object-Centric):**
   * **El problema:** Si solo te interesa reconstruir una estatua, SIFT reconstruirá también árboles, calles y edificios lejanos.
   * **La solución:** Detectar el objeto de interés con YOLO e invertir la máscara (cubrir todo de negro *excepto* la bounding box del objeto). Así te asegurarás de que tu nube de puntos final solo pertenezca a la figura deseada.
3. **Generación de Nubes de Puntos Semánticas:**
   * En lugar de una nube de puntos genérica, cada punto 3D puede heredar la etiqueta de clasificación de YOLO a partir del píxel de donde fue extraído. Podrías visualizar el resultado asignando diferentes colores en matplotlib a los puntos que corresponden a "vegetación" frente a los que son "edificios" o "vehículos".

---

## Integración del Script `reconstruction_3d_yolo.py`

Siguiendo el principio de **Eliminación de Objetos Dinámicos**, se ha creado el nuevo script [reconstruction_3d_yolo.py](file:///C:/Tesis/tesis_1-2025_2/reconstruction_3d_yolo.py).

### Funcionamiento de la Integración

1. **Inicialización de YOLO:** El script carga el modelo local `yolov8n.pt` importando la librería `ultralytics`.
2. **Generación de Máscaras:** Por cada imagen analizada, se ejecuta la función `obtener_mascara_estatica`. Esta función evalúa los objetos detectados e ignora las clases dinámicas más comunes en COCO (personas, bicicletas, autos, motos, buses, camiones, y animales). 
   Las áreas correspondientes a las *bounding boxes* dinámicas se pintan de negro (`0`) en una máscara, forzando a que SIFT únicamente extraiga características del fondo estático.
3. **Guardado de Verificación Visual (`YOLO-Img`):** Para comprobar el correcto funcionamiento de las detecciones de la IA, cada máscara aplicada se guarda en la nueva carpeta `YOLO-Img`. Las imágenes guardadas conservan el mismo nombre de la imagen original y resaltan los objetos dinámicos omitidos (con su clase y un rectángulo rojo) oscureciéndolos para facilitar la revisión visual.
4. **Triangulación Estática:** SIFT se alimenta de estas máscaras (`sift.detectAndCompute(img, mask)`) en la etapa de emparejamiento, lo que reduce el ruido de la reconstrucción y hace mucho más consistente el cálculo de rotación (`R`) y traslación (`t`).
