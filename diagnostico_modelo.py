"""
Diagnóstico del modelo de optimización
Verifica que las restricciones y función objetivo tengan sentido
"""

from gurobipy import Model, GRB, quicksum
import numpy as np
import sys

sys.path.append('/Users/benjaminreyes/UC/capstone-3')
from parametros_matrices import (ZONAS_MANHATTAN, ZONA_A_INDICE, INDICE_A_ZONA, 
                                MATRIZ_DISTANCIAS, MATRIZ_TIEMPOS_NORMAL, 
                                MATRIZ_INGRESOS)

print("="*80)
print("🔍 DIAGNÓSTICO DEL MODELO DE OPTIMIZACIÓN")
print("="*80)

# Configuración simplificada
ZONAS_TEST = [87, 116, 137]  # Solo 3 zonas
N = 3
A = 5  # Solo 5 vehículos
Tr = 4  # Solo 4 períodos
T = 8  # Tiempo extendido

print(f"\nConfiguración ultra-simplificada:")
print(f"  • Zonas: {ZONAS_TEST}")
print(f"  • Vehículos: {A}")
print(f"  • Períodos: {Tr}")

# Demanda fija simple
Dem = [[[0]*Tr for _ in range(N)] for _ in range(N)]
Dem[0][1][1] = 1  # Un viaje de zona 0 a 1 en periodo 1
Dem[1][2][2] = 1  # Un viaje de zona 1 a 2 en periodo 2

print(f"\nDemanda definida:")
print(f"  • Zona {ZONAS_TEST[0]} -> {ZONAS_TEST[1]} en período 1: 1 viaje")
print(f"  • Zona {ZONAS_TEST[1]} -> {ZONAS_TEST[2]} en período 2: 1 viaje")

# Precios simples
Pviaje = [[[20.0]*Tr for _ in range(N)] for _ in range(N)]
for i in range(N):
    Pviaje[i][i] = [0]*Tr  # No hay viajes intra-zona

Creub = [[[25.0]*Tr for _ in range(N)] for _ in range(N)]

# Tiempos y distancias
Tij = [[[1]*Tr for _ in range(N)] for _ in range(N)]  # Todos los viajes tardan 1 período
for i in range(N):
    Tij[i][i] = [0]*Tr

Dij = [[5.0]*N for _ in range(N)]  # 5 km entre zonas
for i in range(N):
    Dij[i][i] = 0

# Posiciones iniciales - todos en zona 0
PosI = [[0]*A for _ in range(N)]
for a in range(A):
    PosI[0][a] = 1

# Carga
CargaI = [350] * A
Cargamax = 350

# Sin estaciones de carga para simplificar
posCh = [0] * N
Tchg = 7

print("\n📝 Creando modelo...")
m = Model("diagnostico")

# Variables
y = m.addVars(N, N, T, A, vtype=GRB.BINARY, name="y")
x = m.addVars(N, N, T, A, vtype=GRB.BINARY, name="x")
z = m.addVars(N, N, T, A, vtype=GRB.BINARY, name="z")
s = m.addVars(N, N, T, vtype=GRB.INTEGER, name="s")

# FUNCIÓN OBJETIVO - VERSIÓN ORIGINAL (sin t+1)
print("\n📊 Probando VERSIÓN ORIGINAL de función objetivo...")
m.setObjective(
    quicksum(y[i,j,t,a]*Pviaje[i][j][t]
             for i in range(N) 
             for j in range(N)
             for a in range(A) 
             for t in range(Tr))
    - quicksum(z[i,j,t,a]*Creub[i][j][t]
               for i in range(N) 
               for j in range(N) 
               for a in range(A)
               for t in range(Tr))
    - quicksum(s[i,j,t]*0.1  # Penalización moderada
               for i in range(N)
               for j in range(N)
               for t in range(Tr)),
    GRB.MAXIMIZE
)

# RESTRICCIONES BÁSICAS
print("   Agregando restricciones básicas...")

# Satisfacer demanda - VERSIÓN ORIGINAL
for i in range(N):
    for t in range(Tr):
        for j in range(N):
            m.addConstr(quicksum(y[i,j,t,a] for a in range(A)) + s[i,j,t] == Dem[i][j][t])

# No solapamiento
for t in range(T):
    for a in range(A):
        m.addConstr(quicksum(y[i,j,t,a]+z[i,j,t,a] for i in range(N) for j in range(N)) <= 1)

# Balance simple (sin restricciones de batería)
for i in range(N):
    for t in range(1, Tr):
        for a in range(A):
            llegadas = quicksum(y[k,i,ti,a] + z[k,i,ti,a] for k in range(N) for ti in range(t))
            salidas = quicksum(y[i,k,ti,a] + z[i,k,ti,a] for k in range(N) for ti in range(t))
            m.addConstr(PosI[i][a] + llegadas >= salidas)

# Optimizar
m.setParam('OutputFlag', 1)
m.setParam('TimeLimit', 30)

print("\n🚀 Optimizando VERSIÓN ORIGINAL...")
print("="*80)
m.optimize()

if m.status == GRB.OPTIMAL:
    print("\n✅ Solución encontrada!")
    print(f"   Valor objetivo: ${m.objVal:.2f}")
    
    viajes_asignados = 0
    demanda_no_atendida = 0
    
    for i in range(N):
        for j in range(N):
            for t in range(Tr):
                demanda = Dem[i][j][t]
                if demanda > 0:
                    asignados = sum(y[i,j,t,a].X for a in range(A) if y[i,j,t,a].X > 0.5)
                    no_atendidos = s[i,j,t].X if s[i,j,t].X > 0.5 else 0
                    viajes_asignados += asignados
                    demanda_no_atendida += no_atendidos
                    
                    print(f"\n   Demanda zona {ZONAS_TEST[i]} -> {ZONAS_TEST[j]} período {t}:")
                    print(f"      Solicitados: {demanda}")
                    print(f"      Asignados: {int(asignados)}")
                    print(f"      No atendidos: {int(no_atendidos)}")
                    
                    for a in range(A):
                        if y[i,j,t,a].X > 0.5:
                            print(f"      ✓ Vehículo {a} asignado")
    
    print(f"\n📊 Resumen:")
    print(f"   • Total viajes asignados: {int(viajes_asignados)}")
    print(f"   • Total demanda no atendida: {int(demanda_no_atendida)}")
    
else:
    print(f"\n❌ No se encontró solución óptima (estado: {m.status})")

print("\n" + "="*80)
print("\n🔬 Ahora probando VERSIÓN MODIFICADA (con t+1)...")
print("="*80)

# Crear nuevo modelo con versión modificada
m2 = Model("diagnostico_v2")

y2 = m2.addVars(N, N, T, A, vtype=GRB.BINARY, name="y")
x2 = m2.addVars(N, N, T, A, vtype=GRB.BINARY, name="x")
z2 = m2.addVars(N, N, T, A, vtype=GRB.BINARY, name="z")
s2 = m2.addVars(N, N, T, vtype=GRB.INTEGER, name="s")

# FUNCIÓN OBJETIVO - VERSIÓN MODIFICADA (con t+1)
m2.setObjective(
    quicksum(y2[i,j,t+1,a]*Pviaje[i][j][t]
             for i in range(N) 
             for j in range(N)
             for a in range(A) 
             for t in range(Tr-1))  # Nota: Tr-1
    - quicksum(z2[i,j,t,a]*Creub[i][j][t]
               for i in range(N) 
               for j in range(N) 
               for a in range(A)
               for t in range(Tr))
    - quicksum(s2[i,j,t]*0.000000000001  # Penalización extremadamente pequeña
               for i in range(N)
               for j in range(N)
               for t in range(Tr)),
    GRB.MAXIMIZE
)

# RESTRICCIONES - VERSIÓN MODIFICADA
for i in range(N):
    for t in range(Tr):
        for j in range(N):
            m2.addConstr(quicksum(y2[i,j,t,a] for a in range(A)) + s2[i,j,t+1] == Dem[i][j][t])

for t in range(T):
    for a in range(A):
        m2.addConstr(quicksum(y2[i,j,t,a]+z2[i,j,t,a] for i in range(N) for j in range(N)) <= 1)

for i in range(N):
    for t in range(1, Tr):
        for a in range(A):
            llegadas = quicksum(y2[k,i,ti,a] + z2[k,i,ti,a] for k in range(N) for ti in range(t))
            salidas = quicksum(y2[i,k,ti,a] + z2[i,k,ti,a] for k in range(N) for ti in range(t))
            m2.addConstr(PosI[i][a] + llegadas >= salidas)

m2.setParam('OutputFlag', 1)
m2.setParam('TimeLimit', 30)

print("\n🚀 Optimizando VERSIÓN MODIFICADA...")
m2.optimize()

if m2.status == GRB.OPTIMAL:
    print("\n✅ Solución encontrada!")
    print(f"   Valor objetivo: ${m2.objVal:.2f}")
    
    viajes_asignados = 0
    demanda_no_atendida = 0
    
    for i in range(N):
        for j in range(N):
            for t in range(Tr):
                demanda = Dem[i][j][t]
                if demanda > 0:
                    asignados = sum(y2[i,j,t,a].X for a in range(A) if y2[i,j,t,a].X > 0.5)
                    no_atendidos = s2[i,j,t+1].X if s2[i,j,t+1].X > 0.5 else 0
                    viajes_asignados += asignados
                    demanda_no_atendida += no_atendidos
                    
                    print(f"\n   Demanda zona {ZONAS_TEST[i]} -> {ZONAS_TEST[j]} período {t}:")
                    print(f"      Solicitados: {demanda}")
                    print(f"      Asignados: {int(asignados)}")
                    print(f"      No atendidos (en s[i,j,t+1]): {int(no_atendidos)}")
                    
                    for a in range(A):
                        if y2[i,j,t,a].X > 0.5:
                            print(f"      ✓ Vehículo {a} asignado")
    
    print(f"\n📊 Resumen:")
    print(f"   • Total viajes asignados: {int(viajes_asignados)}")
    print(f"   • Total demanda no atendida: {int(demanda_no_atendida)}")
    
    print(f"\n💡 Observación:")
    print(f"   • En función objetivo: y[i,j,t+1,a] (t va de 0 a Tr-2)")
    print(f"   • En restricción: s[i,j,t+1] (t va de 0 a Tr-1)")
    print(f"   • Esto causa desalineamiento entre variables de decisión e incentivos")
    
else:
    print(f"\n❌ No se encontró solución óptima (estado: {m2.status})")

print("\n" + "="*80)
print("✅ DIAGNÓSTICO COMPLETADO")
print("="*80)
