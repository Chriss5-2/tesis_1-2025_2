# Plan B: Reconstrucción Enfocada (Object-Centric YOLO Masking)

## ¿De qué trata el Plan B?
A diferencia del Plan A, que asume que el objeto principal es el fondo (y elimina cosas móviles), el **Plan B** asume que el objetivo central de la fotogrametría es **escanear un objeto individual**. 

En este paradigma, se utiliza la detección de objetos de IA no para limpiar ruido, sino para **aislar semánticamente al sujeto de interés**. Todo lo que no pertenezca a la *bounding box* del objeto deseado se considera ruido y se enmascara.

## Mecanismo de Acción
1. **Definición de Clase Objetivo:** Se configura YOLO con una o varias `TARGET_CLASSES`. En el caso del dataset `tripod_seq_01`, nuestra clase objetivo principal es `car` (ID 2 en COCO).
2. **Inversión de la Máscara:** 
   - A diferencia de antes, la máscara fotográfica se inicializa completamente **negra (valor 0)**.
   - Cuando YOLO detecta el vehículo, dibuja su *bounding box* de color **blanco (valor 255)** en la máscara.
3. **Extracción de Puntos Enfocada:**
   - SIFT recibe la imagen junto con esta máscara invertida.
   - Por lo tanto, SIFT tiene prohibido extraer puntos clave (*keypoints*) de las paredes, de las personas en el fondo o de los reflejos en el suelo de la sala de exhibición. 
   - Todos los cientos de puntos extraídos provendrán estricta y únicamente de la chapa y bordes del vehículo.

## Beneficios Esperados
* **Reducción de Tiempo de Procesamiento:** Al ignorar el 80% del fondo de la imagen, `BFMatcher` y SIFT procesan muchos menos descriptores irrelevantes, acelerando el algoritmo.

---

## 2. El Problema de la Ambigüedad de Escala (Scale Drift)
A pesar de que el Plan B aisla correctamente el objeto logrando decenas o cientos de puntos (*inliers*), en secuencias largas (ej. 75 imágenes) la nube de puntos puede terminar viéndose "estirada" o como un tubo en lugar de un objeto 3D reconocible. 

Esto se debe a dos factores matemáticos en la **Fotogrametría Secuencial Monocular** (una sola cámara):
1. **Ambigüedad de Escala:** Al extraer el movimiento de la cámara entre dos fotos usando la Matriz Esencial, es matemáticamente imposible determinar la escala real del movimiento. El sistema siempre asume que la cámara se movió **exactamente 1 unidad de distancia**. Si en la vida real la cámara aceleró, frenó, o giró sin trasladarse mucho, asumir saltos constantes de "1" estira y deforma la geometría acumulada.
2. **Deriva (Drift):** Al ir sumando las posiciones secuencialmente (Foto 1 + Foto 2 + Foto 3...), cualquier milímetro de error en la rotación de la cámara se va acumulando, causando que la trayectoria se "doble" incorrectamente.

## 3. Uso de Archivos Complementarios del Dataset
Al explorar datasets científicos (como el EPFL GIMS08), es común encontrar archivos de texto adicionales que son extremadamente valiosos:

### Archivos `bbox.txt` (Ej: `bbox_20.txt`)
Contienen las **Cajas Delimitadoras (Bounding Boxes)** exactas del objeto principal para cada fotograma (normalmente en formato `xmin ymin xmax ymax`). 
* **Importancia:** Son creadas por los autores del dataset (Ground-Truth). A diferencia de YOLO, que puede "parpadear" o cambiar de tamaño de forma inestable entre un cuadro y otro, el `bbox.txt` es perfectamente consistente.
* **Integración:** El script ha sido modificado para buscar archivos `bbox*.txt` en la carpeta de las imágenes. Si lo encuentra, ignora a YOLO y dibuja la máscara directamente usando estas coordenadas precisas, estabilizando enormemente la extracción de puntos y reduciendo el salto de cámara.

### Archivos `times.txt` (Ej: `times_20.txt` y `times.txt`)
Contienen las marcas de tiempo exactas en las que se tomó cada fotografía (año, mes, día, hora, minuto, segundo, e incluso milisegundo).
* **Importancia:** Permiten estimar la **velocidad** real de la cámara. Si la cámara grababa a 30 FPS, el tiempo ayuda a sincronizar algoritmos de video. En modelos más avanzados (Visual Odometry), el tiempo entre fotos ayuda a corregir la Ambigüedad de Escala mencionada arriba (sabiendo que si pasó menos tiempo, la cámara se movió menos de "1 unidad").

## 4. Consideraciones para Crear tu Propio Dataset
Si en el futuro deseas recolectar tu propio dataset para tu tesis, ten en cuenta lo siguiente:
1. **Captura Constante:** Intenta moverte a una velocidad y distancia constante alrededor del objeto. Evita aceleraciones bruscas, ya que la matemática de la Matriz Esencial asume traslaciones unitarias.
2. **Registra los Bounding Boxes:** Si usas videos propios, puedes procesarlos primero con un algoritmo de Tracking robusto (ej. SORT o DeepSORT acoplado con YOLO) y exportar tus propios archivos `bbox.txt`. Esto evitará que la máscara fotogramétrica "salte" frame a frame.
3. **Calibración Precisa:** Los datasets profesionales traen la Matriz K perfecta. Para fotos propias, asegúrate de calibrar tu cámara (con un tablero de ajedrez) para evitar distorsión de lente (efecto barril), lo cual arruina las proyecciones 3D rectas.
