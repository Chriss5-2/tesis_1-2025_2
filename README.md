# Tesis II: Reconstrucción 3D a partir de Secuencias de Imágenes (360°) con SIFT

Reconstrucción tridimensional de objetos usando el algoritmo SIFT, triangulación y acumulación de poses en un sistema de coordenadas global. 

**Dataset**: [EPFL GIMS08 - Multi-View Car Dataset](https://www.epfl.ch/labs/cvlab/data/data-pose-index-php/)

---

## 🚀 Inicio Rápido

### Opción 1: Script Principal (Recomendado)

```bash
# Procesar todas las secuencias de imágenes
python reconstruction_3d_main.py images/

# O procesar el dataset EPFL
python reconstruction_3d_main.py datasets/epfl_gims08/epfl-gims08/tripod-seq

# O procesar una secuencia individual
python reconstruction_3d_main.py images/tripod_seq_01
```

**Salida**: 
- `evidencias/<carpeta>/reconstruccion_3d_completa.png` - Nube 3D visualizada
- `evidencias/<carpeta>/match_*.jpg` - Matches SIFT entre pares válidos

### Opción 2: Con Ejemplos Interactivos

```bash
python run_examples.py
```

Menú interactivo para elegir qué procesar.

---

## 📋 Pipeline Completo

```
Input (Imágenes secuenciales)
    ↓
[1] SIFT Detection & Matching
    ↓
[2] Pose Estimation (R, t)
    ↓
[3] Triangulation (Puntos 3D)
    ↓
[4] Global Accumulation (Sistema de coordenadas global)
    ↓
[5] Outlier Filtering
    ↓
Output (Nube 3D visualizada + Evidencias)
```

---

## 📁 Scripts Disponibles

### 🎯 `reconstruction_3d_main.py` (PRINCIPAL)
**Script definitivo que abarrea todo el pipeline.**

- ✓ Detección SIFT de características
- ✓ Matching con filtro de Lowe (ratio test)
- ✓ Estimación de pose (matriz esencial + RANSAC)
- ✓ Triangulación de puntos 3D
- ✓ Validación de ángulo de rotación mínimo
- ✓ Acumulación correcta en sistema global
- ✓ Filtrado de outliers
- ✓ Visualización 3D y guardado

**Uso**:
```bash
python reconstruction_3d_main.py <input_path>
```

**Parámetros ajustables** (ver `config_reconstruction.py`):
- `ANGULO_MINIMO`: 12.0° (ángulo de rotación requerido)
- `LOWE_RATIO`: 0.70 (ratio para matching)
- `FILTER_*_SCALE`: Umbrales de outliers

---

### 🔧 Scripts Utilitarios

#### `data_filtrer.py`
Organiza imágenes del dataset EPFL en carpetas por secuencia.

```bash
python data_filtrer.py <input_folder> <output_folder> jpg
```

Ejemplo:
```bash
python data_filtrer.py raw_epfl_images/ images tripod
```

---

#### `apply_sift_images.py`
Visualiza matches SIFT entre pares de imágenes.

```bash
python apply_sift_images.py <input_path> <output_path>
```

---

#### `run_examples.py`
Script interactivo con ejemplos de uso.

```bash
python run_examples.py
```

---

## ⚙️ Configuración

Edita `config_reconstruction.py` para ajustar parámetros:

```python
# Ángulo mínimo entre imágenes
ANGULO_MINIMO = 12.0  # grados

# Ratio de Lowe para matching
LOWE_RATIO = 0.70

# Filtros de outliers
FILTER_X_SCALE = 2.0
FILTER_Y_SCALE = 2.0
FILTER_Z_SCALE = 5.0

# Visualización
FIG_SIZE = (14, 10)
DPI = 300
COLORMAP = 'viridis'
```

---

## 📊 Resultados

Los resultados se guardan en `evidencias/`:

```
evidencias/
├── tripod_seq_01/
│   ├── reconstruccion_3d_completa.png    ← Nube 3D final
│   ├── match_001_to_002.jpg
│   ├── match_002_to_004.jpg
│   └── ...
├── tripod_seq_02/
│   ├── reconstruccion_3d_completa.png
│   └── ...
└── ...
```

---

## 🔍 Algoritmo Detallado

### 1. SIFT (Scale-Invariant Feature Transform)
- Detecta puntos de interés invariantes a escala y rotación
- Genera descriptores para cada punto

### 2. Matching
- Brute Force Matcher (BFMatcher)
- Filtro Lowe's ratio test: `distancia(mejor) < 0.70 * distancia(segundo_mejor)`

### 3. Pose Estimation
- Calcula matriz esencial con RANSAC
- Recupera rotación (R) y traslación (t)
- Solo mantiene inliers según máscara RANSAC

### 4. Triangulación
- Genera coordenadas 3D a partir de puntos 2D en dos vistas
- Matriz de proyección P1 = K @ [I | 0] (cámara 1)
- Matriz de proyección P2 = K @ [R | t] (cámara 2)

### 5. Acumulación Global
```python
# Transformar puntos al sistema global
points_global = R_acc @ pts_3d + t_acc

# Actualizar pose acumulada
t_acc = t_acc + R_acc @ t
R_acc = R_acc @ R
```

### 6. Validación de Ángulo
- Evita procesar pares muy similares (bajo cambio de perspectiva)
- Ángulo mínimo recomendado: 12°
- Fórmula: `θ = arccos((trace(R) - 1) / 2)`

---

## ✅ Requisitos

```
numpy
opencv-python
opencv-contrib-python
matplotlib
ultralytics  # (opcional, para YOLO)
```

Instala con:
```bash
pip install -r requirements.txt
```

---

## 📈 Evolución del Proyecto

| Fase | Alcance | Estado |
|------|---------|--------|
| **Tesis I** | 3 fotos, concepto | ✓ Completado |
| **Tesis II** | Dataset EPFL, generalización | ✓ En desarrollo |
| **Pipeline** | SIFT → Pose → 3D → Global | ✓ Implementado |
| **Validación** | Ángulo mínimo, filtros | ✓ Implementado |
| **Testing** | Múltiples secuencias | ⏳ En progreso |

---

## 🐛 Solución de Problemas

### Problema: Nube 3D muy ruidosa
**Solución**: Aumenta `ANGULO_MINIMO` en config (ej: 15-18°)

### Problema: Muy pocos puntos 3D
**Solución**: Disminuye `LOWE_RATIO` (ej: 0.65-0.70)

### Problema: Proceso muy lento
**Solución**: 
- Reduce resolución de imágenes
- Aumenta `ANGULO_MINIMO` para procesar menos pares

### Problema: Outliers masivos
**Solución**: Ajusta `FILTER_*_SCALE` en config

---

## 📝 Notas

- Matriz de calibración K calculada como: `focal_length = width`
- Sistema de coordenadas: X (lateral), Y (altura), Z (profundidad)
- Visualización: scatter plot coloreado por profundidad

---

## 📚 Referencias

- SIFT: [Lowe, D. G. (2004). Distinctive Image Features from Scale-Invariant Keypoints](https://www.cs.ubc.ca/~lowe/papers/ijcv04.pdf)
- Epipolar Geometry: [Hartley & Zisserman - Multiple View Geometry](https://www.robots.ox.ac.uk/~vgg/book/)
- EPFL Dataset: [Multi-View Car Dataset](https://www.epfl.ch/labs/cvlab/data/data-pose-index-php/)

