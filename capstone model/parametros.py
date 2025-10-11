import sys
import os
import pandas as pd
import numpy as np

# Agregar el directorio padre al path para importar parametros_matrices
sys.path.append('/Users/jmatas/Documents/capstone')
from parametros_matrices import (ZONAS_MANHATTAN, ZONA_A_INDICE, INDICE_A_ZONA, N_ZONAS,
                                MATRIZ_DISTANCIAS, MATRIZ_TIEMPOS_NORMAL, MATRIZ_TIEMPOS_PUNTA, 
                                MATRIZ_TIEMPOS_VALLE, MATRIZ_INGRESOS)

# PARÁMETROS PRINCIPALES (COMPLETOS - ALINEADOS CON CASO BASE)
N = 67  # 67 zonas (todas las zonas de Manhattan)
A = 300  # 300 vehículos (igual al caso base)

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

# PARÁMETROS TEMPORALES (COMPLETOS)
Tr = 96  # 96 períodos = 24 horas completas (igual al caso base)
PERIODO_SIMULACION = 15  # minutos por periodo (igual al caso base)

# CARGAR DEMANDA REAL
def cargar_demanda_real():
    """Carga la demanda real del archivo parquet y la estructura por periodos"""
    # Intentar cargar archivo completo primero, si no existe usar el reducido
    archivo_completo = '/Users/jmatas/Documents/capstone/Datos/df_all_procesado.parquet'
    archivo_reducido = '/Users/jmatas/Documents/capstone/Datos/df_all_reducido_github.parquet'
    
    try:
        df_all = pd.read_parquet(archivo_completo)
        print("Usando archivo completo: df_all_procesado.parquet")
    except FileNotFoundError:
        try:
            df_all = pd.read_parquet(archivo_reducido)
            print("Usando archivo reducido: df_all_reducido_github.parquet")
        except FileNotFoundError:
            raise FileNotFoundError("No se encontró ningún archivo de datos (ni completo ni reducido)")
    
    df_all['pickup_datetime'] = pd.to_datetime(df_all['pickup_datetime'])
    
    # Porcentaje de demanda igual al caso base
    PORCENTAJE_DEMANDA = 0.05
    
    # Crear matriz de demanda [zona_origen][zona_destino][periodo]
    demanda = np.zeros((N, N, Tr))
    
    # Procesar por periodos (simplificado para optimización - usar un día tipo)
    fecha_ejemplo = pd.Timestamp('2024-09-15')  # Día ejemplo - misma fecha del caso base
    
    for periodo in range(Tr):
        hora = (periodo * PERIODO_SIMULACION) // 60
        min_inicio = (periodo * PERIODO_SIMULACION) % 60
        
        fecha_inicio = fecha_ejemplo + pd.Timedelta(hours=hora, minutes=min_inicio)
        fecha_fin = fecha_inicio + pd.Timedelta(minutes=PERIODO_SIMULACION)
        
        viajes_periodo = df_all[
            (df_all['pickup_datetime'] >= fecha_inicio) & 
            (df_all['pickup_datetime'] <= fecha_fin)
        ]
        
        # Aplicar porcentaje de demanda
        n_viajes = max(1, int(len(viajes_periodo) * PORCENTAJE_DEMANDA))
        if len(viajes_periodo) > 0:
            viajes_muestra = viajes_periodo.sample(n=min(n_viajes, len(viajes_periodo)), random_state=123+periodo)
        else:
            viajes_muestra = viajes_periodo
            
        # Contar viajes por par origen-destino
        for _, row in viajes_muestra.iterrows():
            origen_id = int(row['PUlocationID'])
            destino_id = int(row['DOlocationID'])
            
            # Solo procesar si ambas zonas están en Manhattan
            if origen_id in ZONA_A_INDICE and destino_id in ZONA_A_INDICE:
                i = ZONA_A_INDICE[origen_id]
                j = ZONA_A_INDICE[destino_id]
                demanda[i][j][periodo] += 1
    
    return demanda

# MATRICES DE TIEMPO POR PERIODO
def generar_tiempos_por_periodo():
    """Genera matriz de tiempos según el horario del período"""
    tiempos = np.zeros((N, N, Tr))
    
    for t in range(Tr):
        hora_periodo = (t * PERIODO_SIMULACION) // 60
        
        # Determinar tipo de hora según el período
        if 0 <= hora_periodo <= 7:  # Valle
            matriz_tiempo = MATRIZ_TIEMPOS_VALLE
        elif 16 <= hora_periodo <= 20:  # Punta
            matriz_tiempo = MATRIZ_TIEMPOS_PUNTA
        else:  # Normal
            matriz_tiempo = MATRIZ_TIEMPOS_NORMAL
            
        # Convertir minutos a períodos (15 min cada uno)
        tiempos[:, :, t] = np.ceil(matriz_tiempo / PERIODO_SIMULACION)
    
    return tiempos

# CARGAR DATOS
print("Cargando demanda real...")
Dem_array = cargar_demanda_real()
print("Generando tiempos por período...")
Tij_array = generar_tiempos_por_periodo()

# CONVERTIR ARRAYS A LISTAS DE LISTAS DE LISTAS (FORMATO REQUERIDO)
print("Convirtiendo a formato de listas...")
Dem = Dem_array.tolist()  # [zona_origen][zona_destino][periodo]

# Convertir Tij a enteros explícitamente
Tij_list = Tij_array.tolist()
Tij = []
for i in range(len(Tij_list)):
    zona_i = []
    for j in range(len(Tij_list[i])):
        periodo_j = []
        for t in range(len(Tij_list[i][j])):
            periodo_j.append(int(Tij_list[i][j][t]))  # Conversión explícita a entero
        zona_i.append(periodo_j)
    Tij.append(zona_i)

# MATRIZ DE DISTANCIAS (SIMPLIFICADA PARA ZONAS SELECCIONADAS)
# MATRIZ DE DISTANCIAS (usar matriz completa)
Dij = MATRIZ_DISTANCIAS.tolist()

# PARÁMETROS DE ESTACIONES DE CARGA (IGUAL AL CASO BASE)
Capchg = 55  # capacidad de autos en las estaciones de carga
Tchg = int(np.ceil(110 / PERIODO_SIMULACION))  # tiempo de carga en períodos (110 min = ~7 períodos)

# ESTACIONES DE CARGA EN LAS MISMAS ZONAS QUE EL CASO BASE
ZONAS_ESTACIONES_CARGA = [87, 116, 137, 151, 128, 186]
posCh = [0] * N  # inicializar todo en 0
for zona_id in ZONAS_ESTACIONES_CARGA:
    if zona_id in ZONA_A_INDICE:
        indice = ZONA_A_INDICE[zona_id]
        posCh[indice] = 1

# ESTACIONES DE CARGA - Todas las zonas seleccionadas tienen estación para simplificar
posCh = [1] * N  # Todas las zonas seleccionadas tienen estación de carga

# PRECIOS Y COSTOS (SIMPLIFICADOS)
def generar_precios_costos():
    """Genera matrices de precios y costos basadas en los datos reales"""
    precios = np.zeros((N, N, Tr))
    costos_reub = np.zeros((N, N, Tr))
    
    # Precio base de viajes desde matriz de ingresos (todas las zonas)
    for i in range(N):
        for j in range(N):
            precio_base = MATRIZ_INGRESOS[i][j]
            costo_base = precio_base * 1.25  # 25% adicional para reubicación
            
            for t in range(Tr):
                precios[i][j][t] = precio_base
                costos_reub[i][j][t] = costo_base
    
    return precios, costos_reub

print("Generando precios y costos...")
Pviaje_array, Creub_array = generar_precios_costos()

# CONVERTIR A FORMATO DE LISTAS
Pviaje = Pviaje_array.tolist()  # [zona_origen][zona_destino][periodo]
Creub = Creub_array.tolist()    # [zona_origen][zona_destino][periodo]

# POSICIONES INICIALES Y CARGAS (SIMPLIFICADAS)
def generar_posiciones_iniciales():
    """Genera posiciones iniciales distribuidas equitativamente"""
    posiciones = np.zeros((N, A))
    
    # Usar misma semilla que caso base para reproducibilidad
    np.random.seed(42)
    
    # Distribuir vehículos equitativamente entre todas las zonas seleccionadas
    vehiculos_por_zona = A // N
    vehiculos_restantes = A % N
    
    vehiculo_actual = 0
    for i in range(N):
        # Asignar vehículos base
        for _ in range(vehiculos_por_zona):
            if vehiculo_actual < A:
                posiciones[i][vehiculo_actual] = 1
                vehiculo_actual += 1
        
        # Asignar vehículos restantes a las primeras zonas
        if i < vehiculos_restantes and vehiculo_actual < A:
            posiciones[i][vehiculo_actual] = 1
            vehiculo_actual += 1
    
    return posiciones

print("Generando posiciones iniciales...")
PosI_array = generar_posiciones_iniciales()

# CONVERTIR A FORMATO DE LISTAS
PosI = PosI_array.tolist()  # [zona][vehiculo]

# CARGAS INICIALES (TODAS CON CARGA COMPLETA)
Cargamax = 350  # máximo de carga (igual al caso base)
CargaI = [Cargamax] * A  # cargas iniciales (todos con carga completa)

# TIEMPO EXTENDIDO
maxAum = max(int(max_en_listas(Tij)), int(Tchg))
T = Tr + maxAum  # tiempo extendido

print(f"Parámetros cargados: {N} zonas, {A} vehículos, {Tr} períodos reales, {T} períodos totales")
print(f"Formato verificado:")
print(f"  - Dem: {type(Dem)} con dimensiones aprox. {len(Dem)}x{len(Dem[0])}x{len(Dem[0][0])}")
print(f"  - Tij: {type(Tij)} con dimensiones aprox. {len(Tij)}x{len(Tij[0])}x{len(Tij[0][0])}")
print(f"  - Pviaje: {type(Pviaje)} con dimensiones aprox. {len(Pviaje)}x{len(Pviaje[0])}x{len(Pviaje[0][0])}")
print(f"  - PosI: {type(PosI)} con dimensiones aprox. {len(PosI)}x{len(PosI[0])}")
print(f"  - CargaI: {type(CargaI)} con longitud {len(CargaI)}")
print(f"  - posCh: {type(posCh)} con longitud {len(posCh)}")
print("¡Todos los parámetros están en formato de listas!")








'''
N=2 #zonas /nodos
A=10 #cantidad de autos

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


Tr=96 # tiempo real
Dem = [[[0,0,0],[1,1,1]],[[1,1,1],[0,0,0]]] # demanda de viajar desde i hasta j al inicio del periodo t
Tij = [[[0,0,0],[1,1,1]],[[1,1,1],[0,0,0]]] # tiempo entre nodos al inicio del periodo t
Dij = [[0,30],[30,0]] # "km" entr i y j
Capchg = 55 # capacidad de autos en las estaciones de carga
Tchg= 2 # tiempo de carga
Pviaje=[[[1,1,1],[1,1,1]],[[1,1,1],[1,1,1]]] # precio asociado a el viaje con un pasajero ijt
Creub=[[[1,1,1],[1,1,1]],[[1,1,1],[1,1,1]]] # costo de reubicar un vehiculo ijt
PosI=[[1,1,1,1,0,0,0,0,0,0],[0,0,0,0,1,1,1,1,1,1]] # posiciones iniciales
CargaI = [350,350,350,350,350,350,350,350,350,350] # cargas iniciales
Cargamax =  350 #maximo de carga
posCh = [1,0] # pocision de los cargadores
maxAum = max_en_listas([Tij, Tchg])
T=3+maxAum # tiempo extendido
'''