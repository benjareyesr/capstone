"""
DIAGNÓSTICO DETALLADO DEL MODELO
Verificar qué está pasando con las variables y[i,j,t,a]
"""

import pandas as pd
import numpy as np
import gurobipy as gp
from gurobipy import GRB
import math
import sys

sys.path.append('/Users/benjaminreyes/UC/capstone-3')
from parametros_matrices import obtener_distancia, obtener_tiempo, obtener_ingreso, normalizar_zona

print("="*80)
print("🔍 DIAGNÓSTICO DETALLADO DEL MODELO")
print("="*80)

# Configuración pequeña para análisis
ZONAS_TEST = [87, 116, 137, 151, 128]  # 5 zonas
A_TEST = 10  # 10 vehículos
Tr_TEST = 4  # 4 períodos

AUTONOMIA_VEHICULO = 350
TIEMPO_RECARGA = 110
PORCENTAJE_DEMANDA = 0.05
PERIODO_SIMULACION = 15

PERIODO_INICIO = 32  # 8:00 AM
PERIODO_FIN = 36     # 9:00 AM

print(f"\n📍 Configuración de diagnóstico:")
print(f"   • Zonas: {len(ZONAS_TEST)} - {ZONAS_TEST}")
print(f"   • Vehículos: {A_TEST}")
print(f"   • Períodos: {Tr_TEST}")

# Cargar demanda
print("\n📊 Cargando demanda...")
df_all = pd.read_parquet('/Users/benjaminreyes/UC/capstone-3/Datos/df_all_procesado.parquet')
df_all['pickup_datetime'] = pd.to_datetime(df_all['pickup_datetime'])
df_all['hora'] = df_all['pickup_datetime'].dt.hour
df_all['minuto'] = df_all['pickup_datetime'].dt.minute

demanda = {}
for t in range(Tr_TEST):
    periodo_global = PERIODO_INICIO + t
    hora = (periodo_global * PERIODO_SIMULACION) // 60
    min_inicio = (periodo_global * PERIODO_SIMULACION) % 60
    hora_fin = (periodo_global * PERIODO_SIMULACION + PERIODO_SIMULACION) // 60
    min_fin = (periodo_global * PERIODO_SIMULACION + PERIODO_SIMULACION) % 60
    
    viajes_periodo = df_all[
        ((df_all['hora'] == hora) & (df_all['minuto'] >= min_inicio)) |
        ((df_all['hora'] == hora_fin) & (df_all['minuto'] < min_fin))
    ]
    
    n_viajes = max(1, int(len(viajes_periodo) * PORCENTAJE_DEMANDA))
    if len(viajes_periodo) > 0:
        viajes_muestra = viajes_periodo.sample(
            n=min(n_viajes, len(viajes_periodo)),
            random_state=123 + periodo_global
        )
    else:
        continue
    
    for _, row in viajes_muestra.iterrows():
        origen = normalizar_zona(int(row['PUlocationID']))
        destino = normalizar_zona(int(row['DOlocationID']))
        
        if origen in ZONAS_TEST and destino in ZONAS_TEST:
            if (origen, destino, t) in demanda:
                demanda[(origen, destino, t)] += 1
            else:
                demanda[(origen, destino, t)] = 1

total_demanda = sum(demanda.values())
print(f"✅ Demanda total: {total_demanda} viajes")
for t in range(Tr_TEST):
    demanda_t = sum(demanda.get((i,j,t), 0) for i in ZONAS_TEST for j in ZONAS_TEST if i != j)
    print(f"   Período {t}: {demanda_t} viajes")

# Construir modelo
print("\n🔧 Construyendo modelo...")
m = gp.Model("diagnostico")
m.setParam('OutputFlag', 0)

Tr_extendido = Tr_TEST + 3

# Variables
y = {}
x = {}
z = {}
s = {}

for t in range(Tr_extendido):
    for i in ZONAS_TEST:
        for j in ZONAS_TEST:
            if i != j:
                for a in range(A_TEST):
                    y[i,j,t,a] = m.addVar(vtype=GRB.BINARY, name=f'y_{i}_{j}_{t}_{a}')
                    x[i,j,t,a] = m.addVar(vtype=GRB.BINARY, name=f'x_{i}_{j}_{t}_{a}')
                    z[i,j,t,a] = m.addVar(vtype=GRB.BINARY, name=f'z_{i}_{j}_{t}_{a}')

for t in range(Tr_extendido):
    for i in ZONAS_TEST:
        for j in ZONAS_TEST:
            if i != j:
                s[i,j,t] = m.addVar(vtype=GRB.INTEGER, lb=0, name=f's_{i}_{j}_{t}')

m.update()

# Objetivo
obj = gp.quicksum(
    obtener_ingreso(i, j) * y[i,j,t+1,a] if t+1 < Tr_extendido else 0
    for t in range(Tr_TEST)
    for i in ZONAS_TEST
    for j in ZONAS_TEST if i != j
    for a in range(A_TEST)
)

penalizacion = 0.1
obj -= penalizacion * gp.quicksum(
    s[i,j,t+1] if t+1 < Tr_extendido else 0
    for t in range(Tr_TEST)
    for i in ZONAS_TEST
    for j in ZONAS_TEST if i != j
)

m.setObjective(obj, GRB.MAXIMIZE)

# Restricciones
for t in range(Tr_TEST):
    for i in ZONAS_TEST:
        for j in ZONAS_TEST:
            if i != j:
                tiempo_viaje = math.ceil(obtener_tiempo(i, j, 'normal') / PERIODO_SIMULACION)
                if t + tiempo_viaje < Tr_extendido:
                    for a in range(A_TEST):
                        m.addConstr(y[i,j,t,a] + z[i,j,t,a] <= x[i,j,t+tiempo_viaje,a])

for t in range(1, Tr_TEST):
    for j in ZONAS_TEST:
        for a in range(A_TEST):
            llegadas = gp.quicksum(x[i,j,t,a] for i in ZONAS_TEST if i != j)
            salidas = gp.quicksum(y[j,k,t,a] + z[j,k,t,a] for k in ZONAS_TEST if k != j)
            m.addConstr(llegadas == salidas)

for t in range(Tr_TEST):
    if t + 1 < Tr_extendido:
        for i in ZONAS_TEST:
            for j in ZONAS_TEST:
                if i != j and (i,j,t) in demanda:
                    m.addConstr(
                        gp.quicksum(y[i,j,t,a] for a in range(A_TEST)) + s[i,j,t+1] >= demanda[(i,j,t)]
                    )

for t in range(Tr_TEST):
    for a in range(A_TEST):
        total_viajes = gp.quicksum(
            y[i,j,t,a] + z[i,j,t,a]
            for i in ZONAS_TEST
            for j in ZONAS_TEST if i != j
        )
        m.addConstr(total_viajes <= 1)

for i in ZONAS_TEST:
    for j in ZONAS_TEST:
        if i != j:
            for a in range(A_TEST):
                m.addConstr(x[i,j,0,a] == 0)

m.update()

# Optimizar
print("🚀 Optimizando...")
m.setParam('TimeLimit', 60)
m.setParam('MIPGap', 0.10)
m.optimize()

if m.status == GRB.OPTIMAL or m.SolCount > 0:
    print(f"\n✅ Solución encontrada! Valor objetivo: ${m.objVal:.2f}")
    
    # Análisis detallado
    print("\n" + "="*80)
    print("ANÁLISIS DETALLADO DE VARIABLES")
    print("="*80)
    
    # Contar variables y activas por período
    print("\n📊 Variables y[i,j,t,a] activas por período:")
    for t in range(Tr_extendido):
        count = sum(
            1 for i in ZONAS_TEST
            for j in ZONAS_TEST if i != j
            for a in range(A_TEST)
            if y[i,j,t,a].X > 0.5
        )
        if count > 0:
            periodo_global = PERIODO_INICIO + t
            hora = (periodo_global * PERIODO_SIMULACION) // 60
            minuto = (periodo_global * PERIODO_SIMULACION) % 60
            print(f"   t={t} ({hora:02d}:{minuto:02d}): {count} variables y activas")
    
    # Mostrar viajes específicos
    print("\n🚗 Viajes específicos asignados:")
    viajes_mostrados = 0
    for t in range(Tr_TEST):
        for i in ZONAS_TEST:
            for j in ZONAS_TEST:
                if i != j:
                    for a in range(A_TEST):
                        if y[i,j,t,a].X > 0.5:
                            periodo_global = PERIODO_INICIO + t
                            hora = (periodo_global * PERIODO_SIMULACION) // 60
                            minuto = (periodo_global * PERIODO_SIMULACION) % 60
                            ingreso = obtener_ingreso(i, j)
                            print(f"   Período {t} ({hora:02d}:{minuto:02d}) - Vehículo {a}: Zona {i} → {j} (${ingreso:.2f})")
                            viajes_mostrados += 1
                            if viajes_mostrados >= 10:
                                break
                if viajes_mostrados >= 10:
                    break
            if viajes_mostrados >= 10:
                break
        if viajes_mostrados >= 10:
            break
    
    # Análisis de función objetivo
    print("\n" + "="*80)
    print("ANÁLISIS DE FUNCIÓN OBJETIVO")
    print("="*80)
    
    print("\n🔍 Componente de ingresos (suma sobre t+1):")
    ingresos_por_t1 = {}
    for t in range(Tr_TEST):
        if t+1 < Tr_extendido:
            ingreso_t1 = sum(
                obtener_ingreso(i, j) * y[i,j,t+1,a].X
                for i in ZONAS_TEST
                for j in ZONAS_TEST if i != j
                for a in range(A_TEST)
            )
            if ingreso_t1 > 0:
                ingresos_por_t1[t+1] = ingreso_t1
                print(f"   Ingresos de y[*,*,{t+1},*]: ${ingreso_t1:.2f}")
    
    print("\n🔍 Componente de ingresos (suma sobre t):")
    ingresos_por_t = {}
    for t in range(Tr_TEST):
        ingreso_t = sum(
            obtener_ingreso(i, j) * y[i,j,t,a].X
            for i in ZONAS_TEST
            for j in ZONAS_TEST if i != j
            for a in range(A_TEST)
        )
        if ingreso_t > 0:
            ingresos_por_t[t] = ingreso_t
            print(f"   Ingresos de y[*,*,{t},*]: ${ingreso_t:.2f}")
    
    # KPIs finales
    print("\n" + "="*80)
    print("KPIs CALCULADOS DE DIFERENTES FORMAS")
    print("="*80)
    
    # Forma 1: Contar sobre t
    viajes_forma1 = sum(
        1 for t in range(Tr_TEST)
        for i in ZONAS_TEST
        for j in ZONAS_TEST if i != j
        for a in range(A_TEST)
        if y[i,j,t,a].X > 0.5
    )
    ingresos_forma1 = sum(
        obtener_ingreso(i, j) * y[i,j,t,a].X
        for t in range(Tr_TEST)
        for i in ZONAS_TEST
        for j in ZONAS_TEST if i != j
        for a in range(A_TEST)
    )
    
    # Forma 2: Contar sobre t+1
    viajes_forma2 = sum(
        1 for t in range(Tr_TEST)
        for i in ZONAS_TEST
        for j in ZONAS_TEST if i != j
        for a in range(A_TEST)
        if t+1 < Tr_extendido and y[i,j,t+1,a].X > 0.5
    )
    ingresos_forma2 = sum(
        obtener_ingreso(i, j) * y[i,j,t+1,a].X if t+1 < Tr_extendido else 0
        for t in range(Tr_TEST)
        for i in ZONAS_TEST
        for j in ZONAS_TEST if i != j
        for a in range(A_TEST)
    )
    
    # Demanda no satisfecha
    demanda_no_sat = sum(
        s[i,j,t+1].X if t+1 < Tr_extendido else 0
        for t in range(Tr_TEST)
        for i in ZONAS_TEST
        for j in ZONAS_TEST if i != j
    )
    
    print("\n📊 FORMA 1 - Conteo sobre t (viajes iniciados en período de simulación):")
    print(f"   • Variables y[*,*,t,*] activas (t < {Tr_TEST}): {viajes_forma1}")
    print(f"   • Ingresos: ${ingresos_forma1:.2f}")
    print(f"   • Demanda no satisfecha: {demanda_no_sat:.0f}")
    print(f"   • Viajes atendidos: {total_demanda - demanda_no_sat:.0f}")
    print(f"   • Tasa de servicio: {((total_demanda - demanda_no_sat)/total_demanda)*100:.2f}%")
    
    print("\n📊 FORMA 2 - Conteo sobre t+1 (como está en función objetivo):")
    print(f"   • Variables y[*,*,t+1,*] activas (t < {Tr_TEST}): {viajes_forma2}")
    print(f"   • Ingresos: ${ingresos_forma2:.2f}")
    
    print("\n💡 INTERPRETACIÓN:")
    print("   • La función objetivo usa y[i,j,t+1,a] pero esto es solo indexación")
    print("   • Los viajes REALES se inician en período t")
    print("   • Debemos contar sobre t (Forma 1) para KPIs correctos")
    
else:
    print("❌ No se encontró solución")

print("\n" + "="*80)
