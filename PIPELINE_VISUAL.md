# Pipeline de Reconstrucción 3D - Diagrama Visual

## Flujo General

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ENTRADA: CARPETA DE IMÁGENES                        │
│                    (Secuencia de fotos de 360° de un objeto)               │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PASO 1: CARGA Y PREPARACIÓN                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Cargar imágenes en orden (001.jpg, 002.jpg, ...)                         │
│ • Convertir a escala de grises                                              │
│ • Obtener matriz de calibración K (matriz intrínseca)                      │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PASO 2: SELECCIÓN DINÁMICA DE PARES ⭐ KEY                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ Para cada imagen "ancla":                                                    │
│   ┌─ Busca siguiente imagen con ángulo de rotación > 12°                   │
│   ├─ Evita procesar pares muy similares (bajo cambio)                      │
│   ├─ Garantiza triangulación estable                                        │
│   └─ Mejora robustez de reconstrucción                                      │
│                                                                              │
│ VENTAJA: No procesa TODOS los pares consecutivos                           │
│          → Reduce ruido, mejora calidad                                    │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PASO 3: DETECCIÓN SIFT (Imagen 1 e Imagen 2)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Imagen 1              SIFT              Keypoints 1                       │
│  ┌──────────┐    ───────────────>    ┌──────────────┐                     │
│  │          │                        │ • 150 puntos │                     │
│  │  (objeto)│    Detecta             │ • Invariante │                     │
│  │          │    características     │   escala     │                     │
│  └──────────┘    + descriptores      │ • Rotación   │                     │
│                                       └──────────────┘                     │
│                                                                              │
│  Imagen 2              SIFT              Keypoints 2                       │
│  ┌──────────┐    ───────────────>    ┌──────────────┐                     │
│  │          │                        │ • 145 puntos │                     │
│  │  (objeto)│    Detecta             │ • Invariante │                     │
│  │          │    características     │   escala     │                     │
│  └──────────┘    + descriptores      │ • Rotación   │                     │
│                                       └──────────────┘                     │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PASO 4: MATCHING (Encontrar correspondencias)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Descriptores 1        BFMatcher         Matches (candidatos)              │
│  ┌──────────┐    ───────────────>    ┌──────────────┐                     │
│  │ 150 desc │                        │ • 120 match  │                     │
│  │          │    Compara cada        │   candidatos │                     │
│  │          │    descriptor con      │ • Distancia: │                     │
│  └──────────┘    todos los demás     │   similitud  │                     │
│                  (fuerza bruta)       └──────────────┘                     │
│  Descriptores 2                                                             │
│  ┌──────────┐                                                               │
│  │ 145 desc │                                                               │
│  │          │                                                               │
│  │          │                                                               │
│  └──────────┘                                                               │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PASO 5: FILTRO DE LOWE (Ratio Test)                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ Para cada match:                                                            │
│   Distancia al mejor   :  d1                                                │
│   Distancia al 2º best :  d2                                                │
│                                                                              │
│   SI  d1 < 0.70 * d2   ENTONCES match es BUENO ✓                          │
│   SI  d1 ≥ 0.70 * d2   ENTONCES match es RECHAZADO ✗                      │
│                                                                              │
│ Resultado: 120 → 85 matches buenos (filtrados)                             │
│                                                                              │
│ VENTAJA: Solo mantiene correspondencias de ALTA CONFIANZA                   │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PASO 6: EXTRACCIÓN DE PUNTOS 2D                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ De los 85 matches buenos, extraer coordenadas (x, y):                      │
│                                                                              │
│  Imagen 1                    Imagen 2                                       │
│  ┌─────────┐                 ┌─────────┐                                   │
│  │ (100,50)│─────────────────│(105,52) │  Match 1                         │
│  │ (200,75)│─────────────────│(210,78) │  Match 2                         │
│  │  ...    │─────────────────│  ...    │  ...                             │
│  │         │ 85 correspondencias                                            │
│  └─────────┘                 └─────────┘                                   │
│                                                                              │
│ Resultado:                                                                   │
│   pts1 = [(x1,y1), (x2,y2), ...]  # 85 puntos en imagen 1                │
│   pts2 = [(x1,y1), (x2,y2), ...]  # 85 puntos en imagen 2                │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PASO 7: ESTIMACIÓN DE POSE (RANSAC) ⭐ CRÍTICO                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ INPUT:  85 puntos en imagen 1 (pts1)                                       │
│         85 puntos en imagen 2 (pts2)                                       │
│         Matriz K (calibración cámara)                                       │
│                                                                              │
│         ┌─────────────────────────────────────────────────────────┐        │
│         │ cv2.findEssentialMat(pts1, pts2, K, method=RANSAC)    │        │
│         │                                                          │        │
│         │ • Itera múltiples veces                                 │        │
│         │ • Prueba subsets aleatorios                             │        │
│         │ • Calcula matriz esencial E                             │        │
│         │ • Genera máscara de inliers/outliers                    │        │
│         │ • Mantiene la mejor E (máximo consenso)                │        │
│         └─────────────────────────────────────────────────────────┘        │
│                                                                              │
│ OUTPUT: E (matriz esencial) + máscara de 85 puntos                         │
│                                                                              │
│         ┌─────────────────────────────────────────────────────────┐        │
│         │ cv2.recoverPose(E, pts1, pts2, K)                      │        │
│         │                                                          │        │
│         │ Descompone E en:                                         │        │
│         │   R = matriz de rotación 3x3                            │        │
│         │   t = vector de traslación 3x1                          │        │
│         │                                                          │        │
│         │ CALCULA ÁNGULO DE ROTACIÓN:                             │        │
│         │   θ = arccos((trace(R) - 1) / 2)                        │        │
│         │   SI θ < 12°  → RECHAZAR par                            │        │
│         │   SI θ ≥ 12°  → ACEPTAR par ✓                           │        │
│         └─────────────────────────────────────────────────────────┘        │
│                                                                              │
│ RESULTADO: R (rotación), t (traslación), máscara (inliers)                 │
│                                                                              │
│ VENTAJA: RANSAC elimina outliers automáticamente                            │
│          Ángulo mínimo garantiza triangulación estable                      │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               ↓
                    ┌─ ¿Ángulo válido? ─┐
                    │    (> 12°)        │
                    │                    │
              NO    ↓                     ↓ SÍ
            ┌─────────────┐      ┌────────────────────┐
            │ CONTINUAR   │      │ Pasar a triangular │
            │ (buscar     │      │                    │
            │  siguiente) │      └────────────────────┘
            └─────────────┘              ↓
                 ↑        ┌──────────────────────────────────────────────────┐
                 │        │ PASO 8: TRIANGULACIÓN (Generar nube 3D)         │
                 │        ├──────────────────────────────────────────────────┤
                 │        │                                                  │
                 │        │ INPUT:  Puntos 2D en imagen 1 (inliers)        │
                 │        │         Puntos 2D en imagen 2 (inliers)        │
                 │        │         R, t (pose relativa)                    │
                 │        │         K (calibración)                         │
                 │        │                                                  │
                 │        │ CONSTRUIR MATRICES DE PROYECCIÓN:               │
                 │        │   P1 = K @ [I | 0]       (cámara 1 en origen)  │
                 │        │   P2 = K @ [R | t]       (cámara 2 transformada)│
                 │        │                                                  │
                 │        │ TRIANGULAR:                                      │
                 │        │   pts_4d = triangulatePoints(P1, P2, pts1, pts2)│
                 │        │   pts_3d = pts_4d[:3] / pts_4d[3]  (normalizar)│
                 │        │                                                  │
                 │        │ OUTPUT: Nube 3D local (N puntos x 3 coords)    │
                 │        └──────────────────────────────────────────────────┘
                 │                         ↓
                 │        ┌──────────────────────────────────────────────────┐
                 │        │ PASO 9: TRANSFORMAR AL SISTEMA GLOBAL            │
                 │        ├──────────────────────────────────────────────────┤
                 │        │                                                  │
                 │        │ INPUT:  Nube 3D local (pts_3d)                  │
                 │        │         Pose acumulada global (R_acc, t_acc)   │
                 │        │                                                  │
                 │        │ TRANSFORMACIÓN:                                  │
                 │        │   pts_3d_global = R_acc @ pts_3d + t_acc       │
                 │        │                                                  │
                 │        │ ACTUALIZAR POSE ACUMULADA:                      │
                 │        │   t_acc = t_acc + R_acc @ t                    │
                 │        │   R_acc = R_acc @ R                            │
                 │        │                                                  │
                 │        │ ESTO ES CLAVE: Integra la nube en un sistema   │
                 │        │ de coordenadas global consistente               │
                 │        └──────────────────────────────────────────────────┘
                 │                         ↓
                 │        ┌──────────────────────────────────────────────────┐
                 │        │ PASO 10: ACUMULAR EN NUBE GLOBAL                 │
                 │        ├──────────────────────────────────────────────────┤
                 │        │                                                  │
                 │        │ all_points.append(pts_3d_global)                │
                 │        │                                                  │
                 │        │ Después de procesar todos los pares:             │
                 │        │   cloud_final = np.hstack(all_points)           │
                 │        │                                                  │
                 │        │ Resultado: NUBE 3D COMPLETA (miles de puntos)   │
                 │        └──────────────────────────────────────────────────┘
                 │                         ↓
                 │        ┌──────────────────────────────────────────────────┐
                 │        │ PASO 11: FILTRADO DE OUTLIERS                    │
                 │        ├──────────────────────────────────────────────────┤
                 │        │                                                  │
                 │        │ Elimina puntos:                                  │
                 │        │   • |X| > width * 2.0      (muy lejano lateral) │
                 │        │   • |Y| > height * 2.0     (muy alto)           │
                 │        │   • Z ≤ 0                  (atrás cámara)       │
                 │        │   • Z > width * 5.0        (muy lejano)         │
                 │        │                                                  │
                 │        │ Ejemplo: 5000 → 3500 puntos (30% eliminado)    │
                 │        └──────────────────────────────────────────────────┘
                 │                         ↓
                 │        ┌──────────────────────────────────────────────────┐
                 │        │ PASO 12: VISUALIZACIÓN Y GUARDADO                │
                 │        ├──────────────────────────────────────────────────┤
                 │        │                                                  │
                 │        │ • Crear figura 3D (matplotlib)                   │
                 │        │ • Scatter plot: (X, Z, -Y)                       │
                 │        │ • Colorear por Z (profundidad)                   │
                 │        │ • Colormap: viridis                              │
                 │        │ • Guardar PNG (300 DPI)                          │
                 │        │                                                  │
                 │        │ SALIDA: evidencias/<carpeta>/                    │
                 │        │         reconstruccion_3d_completa.png          │
                 │        └──────────────────────────────────────────────────┘
                 │                         ↓
                 │        ┌──────────────────────────────────────────────────┐
                 │        │ PASO 13: SELECCIONAR SIGUIENTE ANCLA              │
                 │        ├──────────────────────────────────────────────────┤
                 │        │                                                  │
                 │        │ idx_ancla = idx_candidata                       │
                 │        │ (La candidata ahora es la nueva ancla)           │
                 │        │ Repetir desde PASO 2                             │
                 │        └──────────────────────────────────────────────────┘
                 │                         ↓
                 └──────────────────────────┘
                          
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ SALIDA FINAL                                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ evidencias/<nombre_carpeta>/                                               │
│ ├─ reconstruccion_3d_completa.png    ← NUBE 3D FINAL (tu objetivo)        │
│ ├─ match_001_to_002.jpg              ← Matches visualizados               │
│ ├─ match_002_to_004.jpg              ← ...                                │
│ └─ ...                                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Parámetros Clave y su Impacto

### 1. ANGULO_MINIMO (grados)

```
Función: Valida que la rotación sea suficiente
Valores recomendados:

 5° │ ████████████████ Muy permisivo → RUIDO ALTO
 8° │ ██████████ Permisivo → Ruido moderado
12° │ ██████ Recomendado (balance óptimo)  ⭐
15° │ ███ Estricto → Menos pares procesados
20° │ █ Muy estricto → Muy poco ruido, pero pocas nubes

Impacto:
 ↑ ANGULO → Menos pares, nube más limpia, menos puntos
 ↓ ANGULO → Más pares, nube más ruidosa, más puntos
```

### 2. LOWE_RATIO (0.0 - 1.0)

```
Función: Filtra matches de mala calidad
Valores recomendados:

0.60 │ █████ Muy estricto → 30-40% matches rechazados
0.70 │ ██████████ Recomendado (estándar en literatura)  ⭐
0.75 │ ███████████ Menos estricto → Más matches
0.80 │ ████████████ Muy permisivo → Riesgo outliers

Impacto:
 ↑ RATIO → Menos matches pero de mejor calidad
 ↓ RATIO → Más matches pero menos confiables
```

### 3. FILTER_Z_SCALE (relativo a width)

```
Función: Limita profundidad (Z) para eliminar outliers
Valores recomendados:

3.0 │ ██ Muy restrictivo → Muchos puntos eliminados
5.0 │ █████ Recomendado (balance)  ⭐
7.0 │ ███████ Menos restrictivo
10.0│ ██████████ Muy permisivo

Impacto:
 ↑ SCALE → Acepta puntos más lejanos
 ↓ SCALE → Solo acepta puntos cercanos
```

---

## Matrices Importantes

### Matriz de Calibración K (3x3)

```
K = | f  0  cx |
    | 0  f  cy |
    | 0  0   1 |

Donde:
  f  = focal length (aproximadamente igual a width)
  cx = center X (width / 2)
  cy = center Y (height / 2)

Usualmente:
  K = | 640  0  320 |   (para imagen 640x480)
      |  0 640  240 |
      |  0   0    1 |
```

### Matriz Esencial E (3x3)

```
Relaciona dos vistas de la misma escena:
  [p']T @ E @ p = 0  (epipolar constraint)

Donde:
  p  = punto en imagen 1
  p' = punto correspondiente en imagen 2

Se descompone en:
  E = [t]× @ R

  t = vector de traslación (3x1)
  R = matriz de rotación (3x3)
  [t]× = matriz antisimétrica de t
```

### Matrices de Proyección

```
P1 = K @ [I | 0]    # Cámara 1: Origen
     ↓
     Proyecta puntos 3D en imagen 1

P2 = K @ [R | t]    # Cámara 2: Transformada por R, t
     ↓
     Proyecta puntos 3D en imagen 2

Triangulación invierte este proceso:
  Dado (p1, p2), encontrar (X, Y, Z)
```

---

## Coordenadas y Orientación

```
Sistema de Coordenadas 3D:
        ↑ Y (altura)
        │
        └────→ X (lateral)
       /
      Z (profundidad - hacia adelante)

Cámara 1:  En el origen (0, 0, 0)
Cámara 2:  Transformada por R y t

Objeto:    Frente a la cámara (Z > 0)
```

---

## Flujo de Datos: Ejemplo Concreto

```
INPUT: 20 imágenes (001.jpg a 020.jpg)

Imagen 001 (ancla) vs Imagen 002: ángulo 3° ✗ SKIP
Imagen 001 (ancla) vs Imagen 003: ángulo 6° ✗ SKIP
Imagen 001 (ancla) vs Imagen 004: ángulo 12° ✓ PROCESAR
  → Genera 500 puntos 3D
  → Filtra → 400 puntos válidos
  → Añade a nube global

Imagen 004 (ancla) vs Imagen 005: ángulo 3° ✗ SKIP
Imagen 004 (ancla) vs Imagen 006: ángulo 6° ✗ SKIP
Imagen 004 (ancla) vs Imagen 007: ángulo 10° ✗ SKIP
Imagen 004 (ancla) vs Imagen 008: ángulo 14° ✓ PROCESAR
  → Genera 480 puntos 3D
  → Filtra → 380 puntos válidos
  → Añade a nube global

... (continúa así) ...

FINAL:
  Total pares procesados: ~6-8
  Total puntos en nube: ~3000-4000
  → PNG con toda la estructura 3D del objeto
```

---

## Razón de la Validación de Ángulo

```
SIN validación (anterior):

  Par 1→2 (ángulo 2°):  Genera puntos con error ~1000 unidades
  Par 2→3 (ángulo 2°):  Acumula error → ~2000 unidades
  Par 3→4 (ángulo 2°):  Acumula error → ~3000 unidades
  ...
  
  RESULTADO: Nube deformada, sin estructura clara ✗

CON validación de ángulo > 12°:

  Par 1→4 (ángulo 12°):  Genera puntos con error ~50 unidades
  Par 4→8 (ángulo 14°):  Error ~60 unidades (menor acumulación)
  Par 8→12 (ángulo 13°): Error ~55 unidades
  ...
  
  RESULTADO: Nube limpia, estructura clara, objeto reconocible ✓
```

Esto es la **diferencia crítica** entre tu anterior reconstrucción y esta nueva.
