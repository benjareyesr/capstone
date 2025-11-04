"""
SCRIPT MAESTRO - EJECUTAR TODAS LAS PRUEBAS Y COMPARACIONES
Ejecuta el modelo de optimización, caso base FIFO y genera comparación
"""

import subprocess
import sys
import os
import time

print("="*80)
print("🚀 EJECUCIÓN COMPLETA: MODELO DE OPTIMIZACIÓN VS CASO BASE FIFO")
print("="*80)
print("\nEste script ejecutará:")
print("  1. Caso Base FIFO (simulación)")
print("  2. Modelo de Optimización (Gurobi)")
print("  3. Comparación de resultados")
print("\n" + "="*80)

# Verificar que Python tiene acceso a los módulos necesarios
print("\n🔍 Verificando dependencias...")

try:
    import pandas as pd
    print("   ✅ pandas instalado")
except ImportError:
    print("   ❌ pandas no encontrado")
    sys.exit(1)

try:
    import numpy as np
    print("   ✅ numpy instalado")
except ImportError:
    print("   ❌ numpy no encontrado")
    sys.exit(1)

try:
    import gurobipy
    print("   ✅ gurobipy instalado")
except ImportError:
    print("   ❌ gurobipy no encontrado - necesario para el modelo de optimización")
    respuesta = input("\n¿Deseas continuar solo con el caso base? (s/n): ")
    if respuesta.lower() != 's':
        sys.exit(1)

print("\n" + "="*80)

# Directorio de trabajo
directorio_base = '/Users/benjaminreyes/UC/capstone-3'

# -------------------------
# 1. EJECUTAR CASO BASE
# -------------------------

print("\n" + "="*80)
print("📍 PASO 1/3: EJECUTANDO CASO BASE FIFO")
print("="*80)

inicio_casobase = time.time()

try:
    resultado = subprocess.run(
        [sys.executable, os.path.join(directorio_base, 'Caso base', 'simulacion_casobase_test.py')],
        cwd=directorio_base,
        capture_output=True,
        text=True,
        timeout=600  # 10 minutos máximo
    )
    
    print(resultado.stdout)
    
    if resultado.returncode != 0:
        print(f"\n❌ Error en caso base:")
        print(resultado.stderr)
        sys.exit(1)
    
    tiempo_casobase = time.time() - inicio_casobase
    print(f"\n✅ Caso base completado en {tiempo_casobase:.2f} segundos")
    
except subprocess.TimeoutExpired:
    print("\n❌ Tiempo límite excedido para caso base")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error ejecutando caso base: {e}")
    sys.exit(1)

# -------------------------
# 2. EJECUTAR MODELO DE OPTIMIZACIÓN
# -------------------------

print("\n" + "="*80)
print("📍 PASO 2/3: EJECUTANDO MODELO DE OPTIMIZACIÓN")
print("="*80)

inicio_modelo = time.time()

try:
    resultado = subprocess.run(
        [sys.executable, os.path.join(directorio_base, 'capstone model', 'model_test.py')],
        cwd=directorio_base,
        capture_output=True,
        text=True,
        timeout=600  # 10 minutos máximo
    )
    
    print(resultado.stdout)
    
    if resultado.returncode != 0:
        print(f"\n❌ Error en modelo de optimización:")
        print(resultado.stderr)
        print("\nContinuando sin resultados del modelo...")
        modelo_exitoso = False
    else:
        tiempo_modelo = time.time() - inicio_modelo
        print(f"\n✅ Modelo completado en {tiempo_modelo:.2f} segundos")
        modelo_exitoso = True
    
except subprocess.TimeoutExpired:
    print("\n⚠️  Tiempo límite excedido para modelo de optimización")
    print("Continuando sin resultados del modelo...")
    modelo_exitoso = False
except Exception as e:
    print(f"\n⚠️  Error ejecutando modelo: {e}")
    print("Continuando sin resultados del modelo...")
    modelo_exitoso = False

# -------------------------
# 3. COMPARAR RESULTADOS
# -------------------------

if modelo_exitoso:
    print("\n" + "="*80)
    print("📍 PASO 3/3: COMPARANDO RESULTADOS")
    print("="*80)
    
    try:
        resultado = subprocess.run(
            [sys.executable, os.path.join(directorio_base, 'comparar_resultados.py')],
            cwd=directorio_base,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(resultado.stdout)
        
        if resultado.returncode != 0:
            print(f"\n⚠️  Advertencia al comparar resultados:")
            print(resultado.stderr)
        else:
            print("\n✅ Comparación completada")
        
    except Exception as e:
        print(f"\n⚠️  Error al comparar resultados: {e}")
else:
    print("\n⚠️  Saltando comparación (modelo no completado)")

# -------------------------
# RESUMEN FINAL
# -------------------------

print("\n" + "="*80)
print("🎉 EJECUCIÓN COMPLETADA")
print("="*80)

print("\n📁 Archivos generados:")

archivos_esperados = [
    'resultados_casobase_test.txt',
    'resultados_modelo_test.txt',
    'comparacion_modelo_vs_casobase.txt'
]

for archivo in archivos_esperados:
    ruta = os.path.join(directorio_base, archivo)
    if os.path.exists(ruta):
        tamano = os.path.getsize(ruta)
        print(f"   ✅ {archivo} ({tamano} bytes)")
    else:
        print(f"   ⚠️  {archivo} (no generado)")

print("\n💡 Próximos pasos:")
print("   1. Revisa los archivos de resultados generados")
print("   2. Analiza las diferencias en KPIs entre ambos enfoques")
print("   3. Si los resultados son satisfactorios, puedes escalar a más zonas/períodos")

print("\n" + "="*80)
