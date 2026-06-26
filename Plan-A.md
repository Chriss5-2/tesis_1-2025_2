# Plan A: Eliminación de Objetos Dinámicos (Masking Out)

## ¿En qué consistía?
El Plan A se centraba en utilizar la red neuronal YOLO para **detectar y ocultar (enmascarar de negro)** objetos que comúnmente son dinámicos o que introducen ruido en una reconstrucción 3D clásica. La idea teórica era que al eliminar elementos como personas, autos, bicicletas o animales, el algoritmo SIFT (y posteriormente el cálculo de la Matriz Esencial) se enfocaría exclusivamente en el entorno estático (calles, edificios, pisos).

## Implementación Inicial
Se modificó el script para crear `reconstruction_3d_yolo.py`, el cual:
1. Cargaba una imagen y ejecutaba inferencia con `yolov8n.pt`.
2. Identificaba *bounding boxes* de una lista predefinida de clases dinámicas (ej. `car` = 2, `person` = 0).
3. Pintaba un rectángulo negro sobre dichas detecciones en una máscara de imagen, dejando el resto de la imagen en blanco.
4. Alimentaba a `sift.detectAndCompute` con dicha máscara, prohibiéndole buscar características en las zonas negras.

## Errores Hallados y Resultados Visuales
Al ejecutar el código sobre el set de datos `tripod_seq_01`, la nube de puntos resultante no tenía forma y presentaba una extrema escasez de puntos (entre 9 a 20 puntos consistentes por par de imágenes).

Al revisar las imágenes de verificación visual generadas en la carpeta `YOLO-Img`, se detectó la causa exacta:
- El set de datos no era una captura general de un escenario, sino una captura **centrada en un vehículo** sobre una plataforma.
- Como el vehículo (`car`) estaba configurado como un "objeto a eliminar", YOLO colocó una máscara negra gigante cubriendo casi el 80% de la imagen (justo donde estaba la información importante).
- SIFT solo tenía permitido buscar puntos en el 20% restante, compuesto por paredes lisas del fondo y el reflejo del piso, zonas que inherentemente carecen de la textura necesaria para extraer descriptores consistentes.

## ¿Por qué aplicar el Plan B?
El Plan A funciona excepcionalmente bien para fotogrametría urbana (por ejemplo, escanear una fachada de un edificio mientras pasan autos por enfrente). Sin embargo, cuando el **sujeto a reconstruir es precisamente uno de los objetos que YOLO considera dinámicos**, el Plan A fracasa por definición.

Dado que en este dataset el objetivo de la reconstrucción es un auto, debemos invertir por completo la lógica. Necesitamos pasar a un modelo de **Reconstrucción Enfocada (Object-Centric)** o Plan B, en el cual YOLO no elimine al auto, sino que elimine todo el ruido del fondo (personas lejanas, reflejos, paredes) y obligue al sistema 3D a enfocarse estrictamente en la carrocería del vehículo.
