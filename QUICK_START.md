# 🚀 Guía de Inicio Rápido - Reconstrucción 3D

## 1. Validar el Entorno (2 min)

```bash
python validate_env.py
```

Debe mostrar ✓ en todas las dependencias.

---

## 2. Ejecutar con Ejemplos Interactivos (Recomendado)

```bash
python run_examples.py
```

Sigue el menú para elegir qué procesar.

---

## 3. O Ejecutar Directamente

### Testing Rápido (1 secuencia)
```bash
python reconstruction_3d_main.py images/tripod_seq_01
```
**Tiempo**: ~2-5 min | **Salida**: `evidencias/tripod_seq_01/`

### Procesar Todo
```bash
python reconstruction_3d_main.py images/
```
**Tiempo**: ~30-60 min | **Salida**: `evidencias/`

### Dataset EPFL Completo
```bash
python reconstruction_3d_main.py datasets/epfl_gims08/epfl-gims08/tripod-seq
```

---

## 4. Resultados

Busca en `evidencias/<nombre_carpeta>/`:
- `reconstruccion_3d_completa.png` ← **Tu nube 3D**
- `match_*.jpg` → Matches SIFT entre pares válidos

---

## 5. Ajustar Parámetros

Edita `config_reconstruction.py`:

```python
ANGULO_MINIMO = 12.0   # ↑ aumentar si nube muy ruidosa
LOWE_RATIO = 0.70      # ↓ disminuir para más matches
FILTER_Z_SCALE = 5.0   # ↓ disminuir para menos outliers
```

Luego ejecuta de nuevo.

---

## 6. Troubleshooting

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| Nube muy ruidosa | Aumenta `ANGULO_MINIMO` a 15-18° |
| Muy pocos puntos | Disminuye `LOWE_RATIO` a 0.65 |
| Proceso lento | Aumenta `ANGULO_MINIMO` |

---

## 7. Documentación Completa

- **README.md**: Descripción detallada del pipeline
- **AVANCE_TESIS.md**: Estado del proyecto y evolución
- **config_reconstruction.py**: Todos los parámetros explicados

---

## Ejemplo Completo (Paso a Paso)

```bash
# 1. Activar ambiente virtual (si lo tienes)
source venv/Scripts/activate  # Linux/Mac
# o
.\venv\Scripts\Activate.ps1   # Windows PowerShell

# 2. Validar
python validate_env.py

# 3. Testing rápido
python reconstruction_3d_main.py images/tripod_seq_01

# 4. Revisar resultado
# → Abre evidencias/tripod_seq_01/reconstruccion_3d_completa.png

# 5. Si se ve bien, procesar todo
python reconstruction_3d_main.py images/

# 6. Esperar y revisar resultados en evidencias/
```

---

**¿Listo?** Comienza con:
```bash
python validate_env.py && python run_examples.py
```
