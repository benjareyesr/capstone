import sys
import os
import pandas as pd
import numpy as np

# PARÁMETROS PRINCIPALES (MÍNIMOS PARA PRUEBA)
ZONAS_SELECCIONADAS = [87, 116, 4, 113, 163, 262]  # Solo 6 zonas
# ZONAS_SELECCIONADAS = [4, 12, 13, 24, 41, 42, 43, 45, 48, 50, 68, 74, 75, 79, 87, 88, 90, 100, 
#   103, 107, 113, 114, 116, 120, 125, 127, 128, 137, 140, 141, 142, 143, 144, 
#   148, 151, 152, 153, 158, 161, 162, 163, 164, 166, 170, 186, 194, 202, 209, 
#   211, 224, 229, 230, 231, 232, 233, 234, 236, 237, 238, 239, 243, 244, 246, 
#   249, 261, 262, 263
#]
N = len(ZONAS_SELECCIONADAS)  # 6 zonas
A = 6

def max_en_listas(x):
    maximo = float('-inf')  # valor inicial muy pequeño
    
    for elem in x:
        if isinstance(elem, list):
            # Si el elemento es otra lista, buscar el máximo dentro de ella recursivamente
            maximo = max(maximo, max_en_listas(elem))
        else:
            # Si es un número (u otro tipo comparable), lo comparamos directamente
            maximo = max(maximo, elem)
    
    return maximo 

# PARÁMETROS TEMPORALES (MÍNIMOS)
Tr = 4  # Solo 4 períodos = 1 hora
PERIODO_SIMULACION = 15  # minutos por periodo

# DEMANDA SINTÉTICA PARA PRUEBA
def crear_demanda_sintetica():
    """Crea demanda sintética para probar el modelo"""
    demanda = np.zeros((N, N, Tr))
    
    # Agregar algunos viajes de prueba
    demanda[0][1][0] = 2  # 2 viajes de zona 0 a zona 1 en período 0
    demanda[1][0][1] = 1  # 1 viaje de zona 1 a zona 0 en período 1
    demanda[0][1][2] = 3  # 3 viajes de zona 0 a zona 1 en período 2
    
    return demanda

print("Generando demanda sintética...")
Dem = crear_demanda_sintetica().tolist()

# TIEMPOS SINTÉTICOS
def crear_tiempos_sinteticos():
    """Crea tiempos sintéticos simples"""
    tiempos = np.zeros((N, N, Tr))
    
    # Tiempos simples: 1 período para viajes entre zonas diferentes, 0 para misma zona
    for i in range(N):
        for j in range(N):
            for t in range(Tr):
                if i == j:
                    tiempos[i][j][t] = 1  # Mínimo 1 período para estar en la misma zona
                else:
                    tiempos[i][j][t] = 2  # 2 períodos para viajar entre zonas
    
    return tiempos

print("Generando tiempos sintéticos...")
Tij_array = crear_tiempos_sinteticos()

# Convertir a enteros explícitamente
Tij = []
for i in range(len(Tij_array)):
    zona_i = []
    for j in range(len(Tij_array[i])):
        periodo_j = []
        for t in range(len(Tij_array[i][j])):
            periodo_j.append(int(Tij_array[i][j][t]))  # Conversión explícita a entero
        zona_i.append(periodo_j)
    Tij.append(zona_i)

# MATRIZ DE DISTANCIAS SINTÉTICA
Dij = [[0, 5], [5, 0]]  # 5 km entre zonas

# PARÁMETROS DE ESTACIONES DE CARGA
Capchg = 55  # capacidad de autos en las estaciones de carga
Tchg = 7  # tiempo de carga en períodos

# TODAS LAS ZONAS TIENEN ESTACIÓN DE CARGA
posCh = [1, 1]  # Ambas zonas tienen estación

# PRECIOS Y COSTOS SINTÉTICOS
def crear_precios_sinteticos():
    """Crea precios sintéticos para prueba"""
    precios = np.zeros((N, N, Tr))
    costos_reub = np.zeros((N, N, Tr))
    
    for i in range(N):
        for j in range(N):
            for t in range(Tr):
                if i != j:
                    precios[i][j][t] = 20.0  # $20 por viaje
                    costos_reub[i][j][t] = 25.0  # $25 por reubicación
                else:
                    precios[i][j][t] = 0.0
                    costos_reub[i][j][t] = 1.0  # Costo mínimo por quedarse
    
    return precios, costos_reub

print("Generando precios sintéticos...")
Pviaje, Creub = crear_precios_sinteticos()
Pviaje = Pviaje.tolist()
Creub = Creub.tolist()

# POSICIONES INICIALES SINTÉTICAS
def crear_posiciones_sinteticas():
    """Distribuye vehículos equitativamente"""
    posiciones = np.zeros((N, A))
    
    # Distribuir vehículos: 2 en cada zona
    for a in range(A):
        zona = a % N  # Alternar entre zonas
        posiciones[zona][a] = 1
    
    return posiciones

print("Generando posiciones iniciales...")
PosI_array = crear_posiciones_sinteticas()

# Convertir a enteros para consistencia (aunque funciona con float)
PosI = []
for i in range(len(PosI_array)):
    fila = []
    for a in range(len(PosI_array[i])):
        fila.append(int(PosI_array[i][a]))  # Conversión a entero
    PosI.append(fila)

# CARGAS INICIALES
Cargamax = 350  # máximo de carga
CargaI = [Cargamax] * A  # cargas iniciales (todos con carga completa)

# TIEMPO EXTENDIDO
maxAum = max(int(max_en_listas(Tij)), int(Tchg))
T = Tr + maxAum  # tiempo extendido

print(f"=== PARÁMETROS DE PRUEBA ===")
print(f"Zonas: {ZONAS_SELECCIONADAS}")
print(f"N={N}, A={A}, Tr={Tr}, T={T}")
print()
print("=== DEMANDA SINTÉTICA ===")
total_demanda = 0
for i in range(N):
    for j in range(N):
        for t in range(Tr):
            if Dem[i][j][t] > 0:
                print(f"Demanda[{i}][{j}][{t}] = {Dem[i][j][t]}")
                total_demanda += Dem[i][j][t]
print(f"Total demanda: {total_demanda}")
print()
print("=== PRECIOS ===")
for i in range(N):
    for j in range(N):
        if i != j:
            print(f"Precio viaje zona {i} -> zona {j}: ${Pviaje[i][j][0]}")
print()
print("=== POSICIONES INICIALES ===")
for i in range(N):
    for a in range(A):
        if PosI[i][a] == 1:
            print(f"Vehículo {a} inicia en zona {i}")