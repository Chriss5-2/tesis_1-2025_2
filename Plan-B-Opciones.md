# Soluciones al Problema de Escala (Scale Drift)

## Diagnóstico
Cuando se usa el enfoque más básico de Fotogrametría Secuencial (iterar usando `findEssentialMat` y `recoverPose`), el algoritmo calcula la posición de la cámara imagen por imagen. 
El gran defecto matemático de `recoverPose` es que **no conoce la escala del universo**. Siempre normaliza la distancia de movimiento de la cámara a un valor exacto de `1.0`. Si la cámara en la vida real se movió un poco o si rotó sobre un trípode (donde la traslación es casi 0), forzar la traslación a `1.0` estira y deforma la nube de puntos hasta convertirla en una curva o un tubo irreconocible.

## Opción 1: Propagación de Escala con PnP (Elegida)
En lugar de "olvidar" el modelo 3D en cada foto nueva, esta técnica mantiene viva una nube de puntos global en memoria.
- **Mecanismo:** La primera pareja de fotos (0 y 1) se usa para iniciar el modelo 3D. Para la foto 2, en lugar de calcular la Matriz Esencial ciega, buscamos qué puntos de la foto 2 ya existen en nuestro modelo 3D. Luego usamos el algoritmo **Perspective-n-Point (PnP)** para resolver la posición de la cámara usando esos puntos 3D.
- **Por qué sí:** Bloquea la escala. Al basar la posición de la cámara en puntos 3D preexistentes, el algoritmo se ve obligado a respetar el tamaño real y evita que el objeto se estire a lo largo de las 75 imágenes. Es ideal para scripts hechos en Python/OpenCV desde cero.
- **Por qué no:** Requiere programar lógica compleja de "seguimiento" (*tracking*) para saber qué descriptor 2D corresponde a qué punto 3D iteración tras iteración.

## Opción 2: Bundle Adjustment (Ajuste Global)
Es un modelo matemático de optimización. Primero se recolectan todos los puntos 3D defectuosos y las poses de las 75 fotos, y luego un optimizador matemático no lineal (`scipy.optimize.least_squares`) los mueve todos simultáneamente hasta que el error de reproyección sea el mínimo posible.
- **Por qué sí:** Es el estándar de oro (Gold Standard) de la fotogrametría profesional. Corrige hasta el más mínimo defecto de deriva y ruido.
- **Por qué no:** Programarlo desde cero en Python implica matemáticas muy complejas (matrices Jacobianas, funciones de error) y computacionalmente es tan costoso que puede colgar la computadora si no se programa con optimizaciones dispersas (*sparse matrices*).

## Opción 3: Multi-View Stereo (Reconstrucción Densa) y Librerías Externas
Utilizar el motor básico de `SIFT` nos limita a ver esquinas y bordes (nubes dispersas). Para tener un modelo que parezca sólido como en un videojuego, se debe hacer reconstrucción densa.
- **Por qué sí:** El modelo se ve espectacular.
- **Por qué no:** Hacerlo en OpenCV puro es casi imposible o resulta obsoleto. Lo correcto en la industria para esto es abandonar el script manual y alimentar las imágenes a una suite profesional como **COLMAP** o utilizar **Open3D**. Dado que el enfoque de la tesis parece ser implementar el algoritmo paso a paso, esto mataría el propósito educativo/investigativo.
