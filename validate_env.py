"""
Script de validación rápida del pipeline.
Verifica que todas las dependencias estén instaladas y que el entorno esté configurado.
"""

import sys
import os
import subprocess

def check_module(module_name, import_name=None):
    """Verifica si un módulo está instalado."""
    if import_name is None:
        import_name = module_name
    
    try:
        __import__(import_name)
        print(f"✓ {module_name}")
        return True
    except ImportError:
        print(f"✗ {module_name} (no instalado)")
        return False

def check_file(file_path):
    """Verifica si un archivo existe."""
    if os.path.exists(file_path):
        print(f"✓ {file_path}")
        return True
    else:
        print(f"✗ {file_path} (no encontrado)")
        return False

def main():
    print("\n" + "="*80)
    print("  VALIDACIÓN DEL ENTORNO - Reconstrucción 3D")
    print("="*80 + "\n")
    
    # 1. Verificar dependencias
    print("[1] Verificando librerías requeridas...")
    deps_ok = True
    
    required = [
        ('numpy', 'numpy'),
        ('OpenCV', 'cv2'),
        ('matplotlib', 'matplotlib'),
    ]
    
    for name, import_name in required:
        if not check_module(name, import_name):
            deps_ok = False
    
    optional = [
        ('ultralytics (YOLO)', 'ultralytics'),
    ]
    
    #print("\nOpcionales:")
    #for name, import_name in optional:
    #    check_module(name, import_name)
    
    # 2. Verificar archivos principales
    print(f"\n[2] Verificando archivos principales...")
    files_ok = True
    
    required_files = [
        'reconstruction_3d_main.py',
        'config_reconstruction.py',
        'run_examples.py',
        'requirements.txt',
        'README.md',
    ]
    
    for f in required_files:
        if not check_file(f):
            files_ok = False
    
    # 3. Verificar directorios
    print(f"\n[3] Verificando directorios...")
    dirs_needed = ['images', 'datasets', 'evidencias']
    
    for d in dirs_needed:
        if os.path.exists(d):
            print(f"✓ {d}/ (existe)")
        else:
            print(f"ℹ {d}/ (será creado automáticamente)")
    
    # 4. Probar import del script principal
    print(f"\n[4] Verificando importación del script principal...")
    try:
        # No importar, solo verificar que el archivo es válido Python
        with open('reconstruction_3d_main.py', 'r', encoding='utf-8') as f:
            compile(f.read(), 'reconstruction_3d_main.py', 'exec')
        print(f"✓ reconstruction_3d_main.py (sintaxis válida)")
        code_ok = True
    except SyntaxError as e:
        print(f"✗ reconstruction_3d_main.py (error de sintaxis: {e})")
        code_ok = False
    except Exception as e:
        print(f"✗ reconstruction_3d_main.py (error al leer: {e})")
        code_ok = False
    
    # 5. Resumen
    print(f"\n" + "="*80)
    if deps_ok and files_ok and code_ok:
        print("  ✓ VALIDACIÓN EXITOSA")
        print("="*80)
        print(f"\nPuedes ejecutar:")
        print(f"  python reconstruction_3d_main.py images/")
        print(f"  python run_examples.py")
        return 0
    else:
        print("  ✗ VALIDACIÓN CON PROBLEMAS")
        print("="*80)
        print(f"\nAcciones recomendadas:")
        if not deps_ok:
            print(f"  1. Instalar dependencias: pip install -r requirements.txt")
        if not files_ok:
            print(f"  2. Verificar que los archivos .py estén en el directorio actual")
        if not code_ok:
            print(f"  3. Revisar sintaxis de reconstruction_3d_main.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
