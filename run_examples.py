#!/usr/bin/env python
"""
Script de ejemplo para ejecutar la reconstrucción 3D con diferentes configuraciones.
Demuestra cómo usar reconstruction_3d_main.py con el dataset EPFL.
"""

import subprocess
import sys
import os

def run_reconstruction(input_path, description):
    """Ejecuta la reconstrucción 3D."""
    print(f"\n{'='*80}")
    print(f"  {description}")
    print(f"{'='*80}")
    print(f"Input: {input_path}\n")
    
    if not os.path.exists(input_path):
        print(f"❌ ERROR: La ruta no existe: {input_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, 'reconstruction_3d_main.py', input_path],
            check=True
        )
        print(f"\n✓ Completado exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error durante ejecución: {e}")
        return False


def main():
    print("\n" + "="*80)
    print("  RECONSTRUCCIÓN 3D - Ejemplos de Uso")
    print("="*80)
    
    # Opción 1: Dataset EPFL (dataset completo)
    print("\n[1] Procesar dataset EPFL completo (todas las secuencias)")
    print("    - Entrada: datasets/epfl_gims08/epfl-gims08/tripod-seq/")
    print("    - Genera: evidencias/<secuencia>/reconstruccion_3d_completa.png")
    
    if input("\n¿Ejecutar? (s/n): ").lower() == 's':
        run_reconstruction(
            'datasets/epfl_gims08/epfl-gims08/tripod-seq',
            'Dataset EPFL - Reconstrucción completa de todas las secuencias'
        )
    
    # Opción 2: Imágenes organizadas
    print("\n[2] Procesar carpeta de imágenes organizadas")
    print("    - Entrada: images/")
    print("    - Genera: evidencias/<tripod_seq_XX>/reconstruccion_3d_completa.png")
    
    if input("\n¿Ejecutar? (s/n): ").lower() == 's':
        run_reconstruction(
            'images',
            'Imágenes organizadas por secuencia'
        )
    
    # Opción 3: Una sola secuencia (testing)
    print("\n[3] Procesar una única secuencia (testing rápido)")
    print("    - Entrada: images/tripod_seq_01/")
    print("    - Genera: evidencias/tripod_seq_01/reconstruccion_3d_completa.png")
    
    if input("\n¿Ejecutar? (s/n): ").lower() == 's':
        run_reconstruction(
            'images/tripod_seq_01',
            'Testing - Única secuencia (tripod_seq_01)'
        )
    
    print("\n" + "="*80)
    print("  Ejecución completada")
    print("="*80)
    print("\nPara más información, ejecuta:")
    print("  python reconstruction_3d_main.py --help")
    print("  python reconstruction_3d_main.py <tu_carpeta>/")
    

if __name__ == "__main__":
    main()
