"""
Configuración de parámetros para la reconstrucción 3D.
Modifica estos valores según tus necesidades sin editar reconstruction_3d_main.py
"""

# ============================================================================
# PARÁMETROS DE ALGORITMO
# ============================================================================

# Ángulo mínimo de rotación requerido entre dos imágenes (en grados)
# - Valores bajos (5-8°): Más pares procesados, pero más ruidoso
# - Valores altos (15-20°): Menos pares, pero más robusto
# - Recomendado: 12° (balance)
ANGULO_MINIMO = 5.0

# Ratio de Lowe para filtrado de matches
# - 0.70: Más estricto, menos matches pero de mejor calidad
# - 0.75: Estándar
# - 0.80: Más permisivo
LOWE_RATIO = 0.70

# Umbral de RANSAC para matriz esencial (en píxeles)
# - Valores bajos (0.5): Más estricto
# - Valores altos (2.0): Más permisivo
RANSAC_THRESHOLD = 1.0

# Probabilidad para RANSAC
# - 0.999: Muy conservador (por defecto, recomendado)
# - 0.95: Menos conservador
RANSAC_PROB = 0.999

# ============================================================================
# FILTROS DE OUTLIERS (en escala relativa a tamaño de imagen)
# ============================================================================

# Límites de coordenada X (lateral)
# Puntos fuera de esto se descartan: |X| < width * FILTER_X_SCALE
FILTER_X_SCALE = 2.0

# Límites de coordenada Y (altura)
# Puntos fuera de esto se descartan: |Y| < height * FILTER_Y_SCALE
FILTER_Y_SCALE = 2.0

# Límites de coordenada Z (profundidad)
# Puntos fuera de esto se descartan: 0 < Z < width * FILTER_Z_SCALE
FILTER_Z_SCALE = 5.0

# ============================================================================
# PARÁMETROS DE VISUALIZACIÓN
# ============================================================================

# Tamaño de figura 3D (ancho, alto) en pulgadas
FIG_SIZE = (14, 10)

# DPI para guardar imagen
DPI = 300

# Transparencia de puntos (0-1)
ALPHA = 0.6

# Tamaño de marcadores en scatter plot
MARKER_SIZE = 2

# Colormap para visualización
# Opciones: 'viridis', 'plasma', 'inferno', 'magma', 'hot', 'cool'
COLORMAP = 'viridis'

# ============================================================================
# LOGGING Y VERBOSIDAD
# ============================================================================

# Nivel de logging
# DEBUG: Máximo detalle
# INFO: Información normal
# WARNING: Solo advertencias y errores
LOG_LEVEL = 'INFO'

# Mostrar estadísticas detalladas
VERBOSE = True

# ============================================================================
# RUTAS POR DEFECTO
# ============================================================================

# Directorio de salida para evidencias
OUTPUT_DIR = 'evidencias'

# Directorio de entrada por defecto (si no se especifica en línea de comandos)
DEFAULT_INPUT_DIR = 'images'

# ============================================================================
# PROCESAMIENTO
# ============================================================================

# Crear directorio de salida automáticamente si no existe
CREATE_OUTPUT_DIR = True

# Máximo número de carpetas a procesar (0 = sin límite)
MAX_FOLDERS = 0

# Máximo de imágenes por carpeta (0 = sin límite)
MAX_IMAGES_PER_FOLDER = 0
