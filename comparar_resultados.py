"""
COMPARACIÓN DE RESULTADOS: MODELO DE OPTIMIZACIÓN VS CASO BASE FIFO
Análisis de KPIs para validación del modelo
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

print("="*80)
print("📊 COMPARACIÓN: MODELO DE OPTIMIZACIÓN VS CASO BASE FIFO")
print("="*80)

# -------------------------
# FUNCIÓN PARA PARSEAR RESULTADOS
# -------------------------

def parsear_resultados(filepath):
    """Lee archivo de resultados y extrae KPIs"""
    kpis = {}
    
    with open(filepath, 'r') as f:
        contenido = f.read()
    
    # Parsear valores numéricos
    import re
    
    # KPI Operacionales
    match = re.search(r'Viajes solicitados:\s*([\d,]+)', contenido)
    if match:
        kpis['viajes_solicitados'] = int(match.group(1).replace(',', ''))
    
    match = re.search(r'Viajes atendidos:\s*([\d,]+)', contenido)
    if match:
        kpis['viajes_atendidos'] = int(match.group(1).replace(',', ''))
    
    match = re.search(r'Tasa de atención:\s*([\d.]+)%', contenido)
    if match:
        kpis['tasa_atencion'] = float(match.group(1))
    
    match = re.search(r'Demanda no atendida:\s*([\d,]+)', contenido)
    if match:
        kpis['demanda_no_atendida'] = int(match.group(1).replace(',', ''))
    else:
        # Calcular si no está explícito
        kpis['demanda_no_atendida'] = kpis.get('viajes_solicitados', 0) - kpis.get('viajes_atendidos', 0)
    
    match = re.search(r'Viajes perdidos por batería:\s*([\d,]+)', contenido)
    if match:
        kpis['viajes_perdidos_bateria'] = int(match.group(1).replace(',', ''))
    
    match = re.search(r'Viajes perdidos por disponibilidad:\s*([\d,]+)', contenido)
    if match:
        kpis['viajes_perdidos_disponibilidad'] = int(match.group(1).replace(',', ''))
    
    match = re.search(r'Reubicaciones:\s*([\d,]+)', contenido)
    if match:
        kpis['reubicaciones'] = int(match.group(1).replace(',', ''))
    else:
        kpis['reubicaciones'] = 0
    
    # KPI Financieros
    match = re.search(r'Ingresos (?:totales|por viajes):\s*\$\s*([\d,.]+)', contenido)
    if match:
        kpis['ingresos_totales'] = float(match.group(1).replace(',', ''))
    
    match = re.search(r'Ingresos promedio[/]vehículo:\s*\$\s*([\d,.]+)', contenido)
    if match:
        kpis['ingresos_promedio_vehiculo'] = float(match.group(1).replace(',', ''))
    
    match = re.search(r'Costos de reubicación:\s*\$\s*([\d,.]+)', contenido)
    if match:
        kpis['costos_reubicacion'] = float(match.group(1).replace(',', ''))
    else:
        kpis['costos_reubicacion'] = 0
    
    match = re.search(r'Beneficio neto:\s*\$\s*([\d,.]+)', contenido)
    if match:
        kpis['beneficio_neto'] = float(match.group(1).replace(',', ''))
    else:
        kpis['beneficio_neto'] = kpis.get('ingresos_totales', 0) - kpis.get('costos_reubicacion', 0)
    
    # KPI de Eficiencia
    match = re.search(r'Kilómetros (?:totales|con pasajeros):\s*([\d,.]+)', contenido)
    if match:
        kpis['km_con_pasajeros'] = float(match.group(1).replace(',', ''))
    
    match = re.search(r'Kilómetros de reubicación:\s*([\d,.]+)', contenido)
    if match:
        kpis['km_reubicacion'] = float(match.group(1).replace(',', ''))
    else:
        kpis['km_reubicacion'] = 0
    
    # Buscar kilómetros totales más específicamente
    matches = re.findall(r'Kilómetros totales:\s*([\d,.]+)', contenido)
    if matches:
        kpis['km_totales'] = float(matches[-1].replace(',', ''))
    elif 'km_con_pasajeros' in kpis:
        kpis['km_totales'] = kpis['km_con_pasajeros'] + kpis.get('km_reubicacion', 0)
    
    match = re.search(r'Km promedio[/]vehículo:\s*([\d,.]+)', contenido)
    if match:
        kpis['km_promedio_vehiculo'] = float(match.group(1).replace(',', ''))
    
    match = re.search(r'Viajes promedio[/]vehículo:\s*([\d.]+)', contenido)
    if match:
        kpis['viajes_promedio_vehiculo'] = float(match.group(1))
    
    # KPI de Carga
    match = re.search(r'(?:Total eventos de carga|Eventos de carga):\s*([\d,]+)', contenido)
    if match:
        kpis['eventos_carga'] = int(match.group(1).replace(',', ''))
    
    match = re.search(r'Cargas promedio[/]vehículo:\s*([\d.]+)', contenido)
    if match:
        kpis['cargas_promedio_vehiculo'] = float(match.group(1))
    
    match = re.search(r'Vehículos sin acceso a carga:\s*([\d,]+)', contenido)
    if match:
        kpis['vehiculos_sin_acceso_carga'] = int(match.group(1).replace(',', ''))
    
    return kpis

# -------------------------
# CARGAR RESULTADOS
# -------------------------

ruta_modelo = '/Users/benjaminreyes/UC/capstone-3/resultados_modelo_test.txt'
ruta_casobase = '/Users/benjaminreyes/UC/capstone-3/resultados_casobase_test.txt'

print("\n📂 Cargando resultados...")

if not os.path.exists(ruta_modelo):
    print(f"❌ No se encontró: {ruta_modelo}")
    print("   Por favor, ejecuta primero: model_test.py")
    exit(1)

if not os.path.exists(ruta_casobase):
    print(f"❌ No se encontró: {ruta_casobase}")
    print("   Por favor, ejecuta primero: simulacion_casobase_test.py")
    exit(1)

kpis_modelo = parsear_resultados(ruta_modelo)
kpis_casobase = parsear_resultados(ruta_casobase)

print("✅ Resultados cargados correctamente\n")

# -------------------------
# CALCULAR DIFERENCIAS Y MEJORAS
# -------------------------

def calcular_mejora(modelo, base):
    """Calcula mejora porcentual del modelo vs base"""
    if base == 0:
        return 0
    return ((modelo - base) / base) * 100

mejoras = {}

# KPIs donde mayor es mejor
for kpi in ['viajes_atendidos', 'tasa_atencion', 'ingresos_totales', 'beneficio_neto', 
            'ingresos_promedio_vehiculo', 'viajes_promedio_vehiculo']:
    if kpi in kpis_modelo and kpi in kpis_casobase:
        mejoras[kpi] = calcular_mejora(kpis_modelo[kpi], kpis_casobase[kpi])

# KPIs donde menor es mejor (invertir signo para que positivo = mejora)
for kpi in ['demanda_no_atendida', 'viajes_perdidos_bateria', 'viajes_perdidos_disponibilidad',
            'vehiculos_sin_acceso_carga', 'km_totales', 'eventos_carga']:
    if kpi in kpis_modelo and kpi in kpis_casobase:
        mejoras[kpi] = -calcular_mejora(kpis_modelo[kpi], kpis_casobase[kpi])

# -------------------------
# IMPRIMIR COMPARACIÓN
# -------------------------

print("="*80)
print("📈 COMPARACIÓN DETALLADA DE KPIs")
print("="*80)

print("\n🚗 KPI OPERACIONALES:")
print(f"{'Métrica':<40} {'Caso Base':<15} {'Modelo Opt.':<15} {'Mejora':<10}")
print("-"*80)

metricas_op = [
    ('Viajes solicitados', 'viajes_solicitados', False),
    ('Viajes atendidos', 'viajes_atendidos', True),
    ('Tasa de atención (%)', 'tasa_atencion', True),
    ('Demanda no atendida', 'demanda_no_atendida', True),
    ('Viajes perdidos (batería)', 'viajes_perdidos_bateria', True),
    ('Viajes perdidos (disponibilidad)', 'viajes_perdidos_disponibilidad', True),
]

for nombre, clave, mostrar_mejora in metricas_op:
    if clave in kpis_casobase and clave in kpis_modelo:
        base = kpis_casobase[clave]
        modelo = kpis_modelo[clave]
        
        if 'tasa' in clave or 'porcentaje' in clave:
            base_str = f"{base:.2f}%"
            modelo_str = f"{modelo:.2f}%"
        elif isinstance(base, float):
            base_str = f"{base:,.2f}"
            modelo_str = f"{modelo:,.2f}"
        else:
            base_str = f"{base:,}"
            modelo_str = f"{modelo:,}"
        
        if mostrar_mejora and clave in mejoras:
            mejora_str = f"{mejoras[clave]:+.2f}%"
        else:
            mejora_str = "-"
        
        print(f"{nombre:<40} {base_str:<15} {modelo_str:<15} {mejora_str:<10}")

print("\n💰 KPI FINANCIEROS:")
print(f"{'Métrica':<40} {'Caso Base':<15} {'Modelo Opt.':<15} {'Mejora':<10}")
print("-"*80)

metricas_fin = [
    ('Ingresos totales ($)', 'ingresos_totales', True),
    ('Ingresos promedio/vehículo ($)', 'ingresos_promedio_vehiculo', True),
    ('Costos de reubicación ($)', 'costos_reubicacion', False),
    ('Beneficio neto ($)', 'beneficio_neto', True),
]

for nombre, clave, mostrar_mejora in metricas_fin:
    if clave in kpis_casobase and clave in kpis_modelo:
        base = kpis_casobase[clave]
        modelo = kpis_modelo[clave]
        
        base_str = f"${base:,.2f}"
        modelo_str = f"${modelo:,.2f}"
        
        if mostrar_mejora and clave in mejoras:
            mejora_str = f"{mejoras[clave]:+.2f}%"
        else:
            mejora_str = "-"
        
        print(f"{nombre:<40} {base_str:<15} {modelo_str:<15} {mejora_str:<10}")

print("\n⚡ KPI DE EFICIENCIA:")
print(f"{'Métrica':<40} {'Caso Base':<15} {'Modelo Opt.':<15} {'Mejora':<10}")
print("-"*80)

metricas_ef = [
    ('Kilómetros totales', 'km_totales', True),
    ('Km promedio/vehículo', 'km_promedio_vehiculo', False),
    ('Viajes promedio/vehículo', 'viajes_promedio_vehiculo', True),
    ('Reubicaciones', 'reubicaciones', False),
]

for nombre, clave, mostrar_mejora in metricas_ef:
    if clave in kpis_casobase and clave in kpis_modelo:
        base = kpis_casobase[clave]
        modelo = kpis_modelo[clave]
        
        if isinstance(base, float):
            base_str = f"{base:,.2f}"
            modelo_str = f"{modelo:,.2f}"
        else:
            base_str = f"{base:,}"
            modelo_str = f"{modelo:,}"
        
        if mostrar_mejora and clave in mejoras:
            mejora_str = f"{mejoras[clave]:+.2f}%"
        else:
            mejora_str = "-"
        
        print(f"{nombre:<40} {base_str:<15} {modelo_str:<15} {mejora_str:<10}")

print("\n🔋 KPI DE CARGA:")
print(f"{'Métrica':<40} {'Caso Base':<15} {'Modelo Opt.':<15} {'Mejora':<10}")
print("-"*80)

metricas_carga = [
    ('Eventos de carga', 'eventos_carga', True),
    ('Cargas promedio/vehículo', 'cargas_promedio_vehiculo', False),
    ('Vehículos sin acceso a carga', 'vehiculos_sin_acceso_carga', True),
]

for nombre, clave, mostrar_mejora in metricas_carga:
    if clave in kpis_casobase and clave in kpis_modelo:
        base = kpis_casobase[clave]
        modelo = kpis_modelo[clave]
        
        if isinstance(base, float):
            base_str = f"{base:,.2f}"
            modelo_str = f"{modelo:,.2f}"
        else:
            base_str = f"{base:,}"
            modelo_str = f"{modelo:,}"
        
        if mostrar_mejora and clave in mejoras:
            mejora_str = f"{mejoras[clave]:+.2f}%"
        else:
            mejora_str = "-"
        
        print(f"{nombre:<40} {base_str:<15} {modelo_str:<15} {mejora_str:<10}")

# -------------------------
# RESUMEN EJECUTIVO
# -------------------------

print("\n" + "="*80)
print("🎯 RESUMEN EJECUTIVO")
print("="*80)

# Mejoras principales
mejoras_principales = [
    ('Tasa de atención', 'tasa_atencion', '%'),
    ('Ingresos totales', 'ingresos_totales', '$'),
    ('Viajes atendidos', 'viajes_atendidos', 'viajes'),
    ('Demanda no atendida', 'demanda_no_atendida', 'viajes'),
]

print("\n📊 Mejoras del Modelo de Optimización vs Caso Base FIFO:\n")

for nombre, clave, unidad in mejoras_principales:
    if clave in kpis_modelo and clave in kpis_casobase:
        base = kpis_casobase[clave]
        modelo = kpis_modelo[clave]
        diferencia = modelo - base
        
        if clave in mejoras:
            mejora_pct = mejoras[clave]
            
            if unidad == '%':
                print(f"   • {nombre}: {base:.2f}% → {modelo:.2f}% ({mejora_pct:+.2f}%)")
            elif unidad == '$':
                print(f"   • {nombre}: ${base:,.2f} → ${modelo:,.2f} ({mejora_pct:+.2f}%)")
            else:
                print(f"   • {nombre}: {base:,} → {modelo:,} ({mejora_pct:+.2f}%)")

# Calcular KPIs derivados
if 'ingresos_totales' in kpis_modelo and 'viajes_atendidos' in kpis_modelo:
    if kpis_modelo['viajes_atendidos'] > 0:
        ingreso_por_viaje_modelo = kpis_modelo['ingresos_totales'] / kpis_modelo['viajes_atendidos']
    else:
        ingreso_por_viaje_modelo = 0
        
    if kpis_casobase['viajes_atendidos'] > 0:
        ingreso_por_viaje_base = kpis_casobase['ingresos_totales'] / kpis_casobase['viajes_atendidos']
    else:
        ingreso_por_viaje_base = 0
    
    print(f"\n💡 Insights adicionales:")
    print(f"   • Ingreso promedio por viaje:")
    print(f"     - Caso Base: ${ingreso_por_viaje_base:.2f}")
    print(f"     - Modelo Opt: ${ingreso_por_viaje_modelo:.2f}")

# -------------------------
# GUARDAR COMPARACIÓN
# -------------------------

with open('/Users/benjaminreyes/UC/capstone-3/comparacion_modelo_vs_casobase.txt', 'w') as f:
    f.write("COMPARACIÓN: MODELO DE OPTIMIZACIÓN VS CASO BASE FIFO\n")
    f.write("="*80 + "\n\n")
    
    f.write("KPI OPERACIONALES:\n")
    for nombre, clave, _ in metricas_op:
        if clave in kpis_casobase and clave in kpis_modelo:
            f.write(f"  {nombre}:\n")
            f.write(f"    Caso Base: {kpis_casobase[clave]}\n")
            f.write(f"    Modelo: {kpis_modelo[clave]}\n")
            if clave in mejoras:
                f.write(f"    Mejora: {mejoras[clave]:+.2f}%\n")
            f.write("\n")
    
    f.write("\nKPI FINANCIEROS:\n")
    for nombre, clave, _ in metricas_fin:
        if clave in kpis_casobase and clave in kpis_modelo:
            f.write(f"  {nombre}:\n")
            f.write(f"    Caso Base: ${kpis_casobase[clave]:,.2f}\n")
            f.write(f"    Modelo: ${kpis_modelo[clave]:,.2f}\n")
            if clave in mejoras:
                f.write(f"    Mejora: {mejoras[clave]:+.2f}%\n")
            f.write("\n")
    
    f.write("\nKPI DE EFICIENCIA:\n")
    for nombre, clave, _ in metricas_ef:
        if clave in kpis_casobase and clave in kpis_modelo:
            f.write(f"  {nombre}:\n")
            f.write(f"    Caso Base: {kpis_casobase[clave]:,}\n")
            f.write(f"    Modelo: {kpis_modelo[clave]:,}\n")
            if clave in mejoras:
                f.write(f"    Mejora: {mejoras[clave]:+.2f}%\n")
            f.write("\n")

print("\n💾 Comparación guardada en: comparacion_modelo_vs_casobase.txt")
print("\n" + "="*80)
print("✅ ANÁLISIS COMPLETADO")
print("="*80)
