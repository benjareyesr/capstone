# SIMULACIÓN RIDE-HAILING CON VEHÍCULOS ELÉCTRICOS Y ESTACIONES DE CARGA
# Implementación del caso base

import numpy as np
import pandas as pd
import datetime
from collections import defaultdict
import random
from typing import Dict, List, Tuple
import math
import matplotlib.pyplot as plt
import sys
import os

# Importar las matrices de parámetros
sys.path.append('../')
from parametros_matrices import obtener_distancia, obtener_tiempo, obtener_ingreso, ZONAS_MANHATTAN, normalizar_zona

# Parámetros del sistema
NUMERO_VEHICULOS = 300  # Número de vehículos en la flota
AUTONOMIA_VEHICULO = 350 # km
TIEMPO_RECARGA = 110  # minutos
# NOTA: Los tiempos de viaje se obtienen directamente de las matrices según horario (valle 0-7, punta 16-20, normal resto)
PORCENTAJE_DEMANDA = 0.05  # 5% de la demanda total
COSTO_REUBICACION_MULTIPLIER = 1.25  # 25% adicional para reubicación sin pasajero
PERIODO_SIMULACION = 15  # minutos por periodo

# SEMILLAS PARA REPRODUCIBILIDAD
SEMILLA_POSICIONES_INICIALES = 42  # Para posiciones iniciales de vehículos
SEMILLA_BASE_VIAJES = 123  # Base para muestreo de viajes (se combina con período)

# Parámetros de estaciones de carga - Solo 6 en zonas centrales
ZONAS_ESTACIONES_CARGA = [87, 116, 137, 151, 128, 186]  # Solo 6 estaciones en zonas con demanda
CAPACIDAD_MAXIMA_ESTACION = 55  # 55 vehículos máximos por estación

class Vehiculo:    
    def __init__(self, vehiculo_id: int, zona_inicial: int):
        self.id = vehiculo_id
        self.zona_actual = zona_inicial
        self.bateria_actual = AUTONOMIA_VEHICULO  # km restantes
        self.estado = "disponible"  # disponible, en_viaje, cargando, yendo_a_cargar
        self.tiempo_fin_actividad = 0  # periodo en que termina actividad actual
        self.viaje_actual = None
        self.tiempo_inicio_carga = 0
        self.estacion_carga_asignada = None  # zona de estación donde va/está cargando
        self.kilometros_recorridos = 0
        self.ingresos_generados = 0
        self.viajes_atendidos = 0
        self.veces_cargado = 0
    
    def puede_realizar_viaje_completo(self, zona_origen: int, zona_destino: int) -> bool:
        # Verifica si el vehículo puede hacer el viaje completo y llegar a una estación de carga
        # 1) Distancia del viaje solicitado
        distancia_viaje = self.calcular_distancia_manhattan(zona_origen, zona_destino)
        
        # 2) Encontrar estación más cercana desde el destino del viaje
        estacion_mas_cercana = self.encontrar_estacion_mas_cercana_desde(zona_destino)
        if estacion_mas_cercana is None:
            return False  # No hay estaciones accesibles
        
        # 3) Distancia desde destino del viaje hasta la estación más cercana
        distancia_a_estacion = self.calcular_distancia_manhattan(zona_destino, estacion_mas_cercana)
        
        # 4) Total necesario
        distancia_total = distancia_viaje + distancia_a_estacion
        
        return self.bateria_actual >= distancia_total
    
    def encontrar_estacion_mas_cercana_desde(self, zona: int) -> int:
        # Encuentra la estación de carga más cercana desde una zona específica
        estacion_mas_cercana = None
        distancia_minima = float('inf')
        
        for zona_estacion in ZONAS_ESTACIONES_CARGA:
            distancia = self.calcular_distancia_manhattan(zona, zona_estacion)
            if distancia < distancia_minima:
                distancia_minima = distancia
                estacion_mas_cercana = zona_estacion
        
        return estacion_mas_cercana
    
    def calcular_autonomia_minima_requerida(self) -> float:
        # Calcula la autonomía mínima necesaria para llegar a una estación desde la posición actual
        estacion_mas_cercana = self.encontrar_estacion_mas_cercana_desde(self.zona_actual)
        if estacion_mas_cercana is None:
            return 50.0  # Valor conservador
        
        distancia_a_estacion = self.calcular_distancia_manhattan(self.zona_actual, estacion_mas_cercana)
        return distancia_a_estacion 
    
    def necesita_cargar(self) -> bool:
        UMBRAL_BATERIA_CRITICA = 8.0
        return self.bateria_actual <= UMBRAL_BATERIA_CRITICA
    
    def puede_llegar_a_estacion(self, zona_estacion: int) -> bool:
        # Verifica si puede llegar a una estación de carga específica
        distancia_estimada = self.calcular_distancia_manhattan(self.zona_actual, zona_estacion)
        return self.bateria_actual >= distancia_estimada
    
    def calcular_distancia_manhattan(self, zona_origen: int, zona_destino: int) -> float:
        # Calcula distancia real entre zonas usando las matrices de parámetros
        return obtener_distancia(zona_origen, zona_destino)
    
    def iniciar_viaje(self, viaje, periodo_actual: int):
        # Iniciar un viaje
        self.estado = "en_viaje"
        self.viaje_actual = viaje
        self.tiempo_fin_actividad = periodo_actual + viaje['duracion_periodos']
        
    def finalizar_viaje(self):
        # Finalizar el viaje actual
        if self.viaje_actual:
            # Actualizar posición
            self.zona_actual = self.viaje_actual['zona_destino']
            # Consumir la batería
            self.bateria_actual -= self.viaje_actual['distancia_km']
            # Registrar estadísticas
            self.kilometros_recorridos += self.viaje_actual['distancia_km']
            self.ingresos_generados += self.viaje_actual['ingreso']
            self.viajes_atendidos += 1
            
        self.estado = "disponible"
        self.viaje_actual = None
    
    def iniciar_viaje_a_estacion(self, zona_estacion: int, periodo_actual: int):
        # Iniciar viaje hacia estación de carga
        distancia = self.calcular_distancia_manhattan(self.zona_actual, zona_estacion)
        
        # Usar tiempos reales de las matrices (asumir horario normal para viajes a estaciones)
        duracion_minutos = obtener_tiempo(self.zona_actual, zona_estacion, 'normal')
        periodos_adicionales = math.floor(duracion_minutos / PERIODO_SIMULACION)
        
        # CORREGIDO: Garantizar que el viaje a estación dure al menos 1 período
        if periodos_adicionales == 0:
            periodos_adicionales = 1
        
        self.estado = "yendo_a_cargar"
        self.estacion_carga_asignada = zona_estacion
        self.tiempo_fin_actividad = periodo_actual + periodos_adicionales
        
        # Consumir batería del viaje hacia la estación
        self.bateria_actual -= distancia
        self.kilometros_recorridos += distancia
        
    def iniciar_carga(self, periodo_actual: int):
        # Iniciar proceso de carga en la estación
        self.estado = "cargando"
        self.tiempo_inicio_carga = periodo_actual
        
        # Carga por el número completo de períodos necesarios
        # 45 minutos / 15 minutos = 3 períodos completos
        periodos_carga = math.ceil(TIEMPO_RECARGA / PERIODO_SIMULACION)
        self.tiempo_fin_actividad = periodo_actual + periodos_carga
        
    def finalizar_carga(self):
        # Finalizar la carga, restaura batería al máximo
        self.bateria_actual = AUTONOMIA_VEHICULO
        self.estado = "disponible"
        self.veces_cargado += 1
        # Se queda en la zona de la estación de carga
        if self.estacion_carga_asignada:
            self.zona_actual = self.estacion_carga_asignada
            self.estacion_carga_asignada = None

class Viaje:
    # Representa un viaje solicitado
    def __init__(self, viaje_data: dict, periodo_inicio: int):
        # Normalizar zonas para manejar equivalencias (104->103, 105->103)
        self.zona_origen = normalizar_zona(int(viaje_data['PUlocationID'])) 
        self.zona_destino = normalizar_zona(int(viaje_data['DOlocationID'])) 
        self.periodo_inicio = periodo_inicio
        self.distancia_km = self.calcular_distancia_manhattan()
        self.duracion_periodos = self.calcular_duracion_periodos(periodo_inicio)  # Usar periodo, no datos
        self.ingreso = self.calcular_ingreso()
        self.atendido = False
        
    def calcular_distancia_manhattan(self) -> float:
        return obtener_distancia(self.zona_origen, self.zona_destino)
    
    def calcular_duracion_periodos(self, periodo: int) -> int:
        # Calcula duración usando la hora del periodo ACTUAL (cuando se ejecuta el viaje)
        # La demanda viene del periodo anterior, pero el viaje se ejecuta ahora
        
        # Calcular hora del periodo actual (cuando se ejecuta el viaje)
        hora_actual = (periodo * PERIODO_SIMULACION) // 60
        
        # Obtener tipo de hora según la clasificación
        tipo_hora = self.obtener_tipo_hora(hora_actual)
        
        # Usar duración real de las matrices con el tipo de hora del periodo actual
        duracion_minutos = obtener_tiempo(self.zona_origen, self.zona_destino, tipo_hora)
        
        # Cualquier viaje que empiece en un período ocupa ese período completo
        # Si dura más de 15 min, ocupa períodos adicionales
        periodos_adicionales = math.floor(duracion_minutos / PERIODO_SIMULACION)
        
        return periodos_adicionales
    
    def obtener_tipo_hora(self, hora: int) -> str:
        # Obtiene el tipo de hora para buscar en las matrices
        if 16 <= hora <= 20:  # Hora punta (4-8 PM)
            return 'punta'
        elif 0 <= hora <= 7:  # Hora valle (12-7 AM)
            return 'valle'
        else:  # Horario normal (7-16 PM y 20-24 PM)
            return 'normal'
    
    def calcular_ingreso(self) -> float:
        # Calcular ingreso del viaje usando datos reales de las matrices
        return obtener_ingreso(self.zona_origen, self.zona_destino)

class SimuladorRideHailing:
    # Simulador principal
    def __init__(self, datos_viajes: pd.DataFrame = None):
        self.datos_viajes = datos_viajes  # Opcional, se carga dinámicamente
        self.df_all = None  # Dataset real se carga cuando se necesita
        self.vehiculos = self.inicializar_flota()
        self.estaciones_carga = self.inicializar_estaciones()
        self.kpis = {
            'viajes_solicitados': 0,
            'viajes_atendidos': 0,
            'ingresos_totales': 0,
            'km_totales': 0,
            'tiempo_total_servicio': 0,
            'tiempo_total_carga': 0,
            'tiempo_total_ocioso': 0,
            'viajes_perdidos_bateria': 0,
            'viajes_perdidos_disponibilidad': 0,
            'vehiculos_sin_acceso_carga': 0,
            'tiempo_total_yendo_a_cargar': 0
        }
        self.estado_por_periodo = []
        
    def inicializar_estaciones(self) -> Dict[int, Dict]:
        # Inicializar las estaciones de carga con capacidad y ocupación
        estaciones = {}
        for zona in ZONAS_ESTACIONES_CARGA:
            estaciones[zona] = {
                'capacidad_maxima': CAPACIDAD_MAXIMA_ESTACION,
                'vehiculos_cargando': 0,
                'cola_espera': []
            }
        return estaciones
        
    def inicializar_flota(self) -> List[Vehiculo]:
        # Inicializar la flota de vehículos distribuida en zonas de Manhattan
        # FIJAR SEMILLA para reproducibilidad de posiciones iniciales
        np.random.seed(SEMILLA_POSICIONES_INICIALES)
        
        vehiculos = []
        
        # Para debugging: posicionar vehículos en zonas con demanda conocida
        # Zonas con alta demanda histórica en horarios nocturnos
        zonas_estrategicas = [234, 239, 87, 116, 148, 137]  # Incluye estaciones de carga
        
        for i in range(NUMERO_VEHICULOS):
            # Usar zonas estratégicas para los primeros vehículos
            if i < len(zonas_estrategicas):
                zona_inicial = zonas_estrategicas[i]
            else:
                # Resto aleatorio
                zona_inicial = np.random.choice(ZONAS_MANHATTAN)
            
            vehiculo = Vehiculo(i, zona_inicial)
            vehiculos.append(vehiculo)
            
        return vehiculos
    
    def obtener_viajes_periodo(self, periodo: int, fecha: datetime.date) -> List[Viaje]:
        """Obtiene viajes que inician en el periodo específico desde datos reales"""
        
        # Cargar datos reales si no están cargados
        if not hasattr(self, 'df_all') or self.df_all is None:
            self.df_all = pd.read_parquet('../Datos/df_all_reducido_github.parquet')
            self.df_all['pickup_datetime'] = pd.to_datetime(self.df_all['pickup_datetime'])
        
        # Calcular hora del periodo ANTERIOR (la demanda se materializa en el periodo siguiente)
        # Periodo 0 (00:00-00:15) usa demanda de 23:45-00:00 del día anterior
        # Periodo 1 (00:15-00:30) usa demanda de 00:00-00:15
        periodo_demanda = periodo - 1
        
        if periodo_demanda < 0:
            # Para el primer periodo, usar demanda del último periodo del día anterior
            hora_demanda = 23
            min_demanda = 45
            fecha_demanda = fecha - datetime.timedelta(days=1)
        else:
            hora_demanda = (periodo_demanda * PERIODO_SIMULACION) // 60
            min_demanda = (periodo_demanda * PERIODO_SIMULACION) % 60
            fecha_demanda = fecha
        
        # Filtrar viajes del periodo de demanda (15 minutos exactos)
        fecha_inicio = pd.Timestamp(fecha_demanda) + pd.Timedelta(hours=hora_demanda, minutes=min_demanda)
        fecha_fin = fecha_inicio + pd.Timedelta(minutes=PERIODO_SIMULACION)  # +15 minutos exactos
        
        viajes_periodo_raw = self.df_all[
            (self.df_all['pickup_datetime'] >= fecha_inicio) & 
            (self.df_all['pickup_datetime'] <= fecha_fin)
        ].copy()
        
        # Aplicar el porcentaje de demanda para reducir la escala
        n_viajes_total = len(viajes_periodo_raw)
        n_viajes_simulacion = max(1, int(n_viajes_total * PORCENTAJE_DEMANDA))
        
        if n_viajes_total > 0:
            # Muestrear aleatoriamente los viajes con semilla fija para reproducibilidad
            # Usar SEMILLA_BASE_VIAJES + período para variación entre períodos pero reproducibilidad total
            semilla = SEMILLA_BASE_VIAJES + periodo
            viajes_muestra = viajes_periodo_raw.sample(n=min(n_viajes_simulacion, n_viajes_total), random_state=semilla)
        else:
            viajes_muestra = viajes_periodo_raw
        
        # Convertir a objetos Viaje
        viajes_periodo = []
        for _, row in viajes_muestra.iterrows():
            viaje_data = {
                'PUlocationID': int(row['PUlocationID']),  # Corregido: 'l' minúscula
                'DOlocationID': int(row['DOlocationID']),  # Corregido: 'l' minúscula
                'pickup_datetime': row['pickup_datetime'],  # datetime object
                'trip_time': None  # Se calculará automáticamente
            }
            viaje = Viaje(viaje_data, periodo)
            viajes_periodo.append(viaje)
        
        return viajes_periodo
    
    def obtener_vehiculos_disponibles_zona(self, zona: int) -> List[Vehiculo]:
        # Obtiene vehículos disponibles en una zona específica, para así ver cuántos vehículos tengo en una zona para iniciar viajes
        return [v for v in self.vehiculos 
                if v.zona_actual == zona and v.estado == "disponible"]
    
    def encontrar_estacion_disponible(self, vehiculo: Vehiculo) -> int:
        # Encuentra la estación de carga más cercana con capacidad disponible
        estaciones_accesibles = []
        
        for zona_estacion in ZONAS_ESTACIONES_CARGA:
            if vehiculo.puede_llegar_a_estacion(zona_estacion):
                capacidad_disponible = (self.estaciones_carga[zona_estacion]['capacidad_maxima'] - 
                                      self.estaciones_carga[zona_estacion]['vehiculos_cargando'])
                if capacidad_disponible > 0:
                    distancia = vehiculo.calcular_distancia_manhattan(vehiculo.zona_actual, zona_estacion)
                    estaciones_accesibles.append((zona_estacion, distancia))
        
        if estaciones_accesibles:
            # Ordenar por distancia y retornar la más cercana
            estaciones_accesibles.sort(key=lambda x: x[1])
            return estaciones_accesibles[0][0]
        
        return None
    
    def asignar_viajes_optimizado(self, viajes: List[Viaje], periodo: int):
        # Asigna viajes con lógica simple pero efectiva:
        # - Viajes largos → vehículos con más batería
        # - Viajes cortos → vehículos con menos batería (pero suficiente)
        
        # Gestión optimizada de asignación de viajes
        
        # Obtener todos los vehículos disponibles
        vehiculos_disponibles = [v for v in self.vehiculos if v.estado == "disponible"]
        
        # Procesar viajes uno por uno (FIFO - First In, First Out)
        for viaje in viajes:
            # Buscar vehículos en la zona de origen que puedan hacer el viaje
            vehiculos_capaces = []
            
            for vehiculo in vehiculos_disponibles:
                # Debe estar en la zona de origen y poder completar el viaje
                if vehiculo.zona_actual == viaje.zona_origen:
                    if vehiculo.puede_realizar_viaje_completo(viaje.zona_origen, viaje.zona_destino):
                        vehiculos_capaces.append(vehiculo)
            
            if vehiculos_capaces:
                # LÓGICA DE OPTIMIZACIÓN SIMPLE:
                # Para viajes largos (>3km): elegir vehículo con MÁS batería
                # Para viajes cortos (≤3km): elegir vehículo con MENOS batería (pero suficiente)
                
                if viaje.distancia_km > 3.0:
                    # Viaje largo → vehículo con más batería
                    vehiculo_elegido = max(vehiculos_capaces, key=lambda v: v.bateria_actual)
                else:
                    # Viaje corto → vehículo con menos batería (pero que pueda completarlo)
                    vehiculo_elegido = min(vehiculos_capaces, key=lambda v: v.bateria_actual)
                
                # Asignar el viaje
                viaje_info = {
                    'zona_origen': viaje.zona_origen,
                    'zona_destino': viaje.zona_destino,
                    'distancia_km': viaje.distancia_km,
                    'duracion_periodos': viaje.duracion_periodos,
                    'ingreso': viaje.ingreso
                }
                
                vehiculo_elegido.iniciar_viaje(viaje_info, periodo)
                viaje.atendido = True
                
                # Remover vehículo de disponibles para no reasignarlo
                vehiculos_disponibles.remove(vehiculo_elegido)
                
                # Actualizar estadísticas
                self.kpis['viajes_atendidos'] += 1
                self.kpis['ingresos_totales'] += viaje.ingreso
        
        # Actualizar contador total de viajes solicitados
        self.kpis['viajes_solicitados'] += len(viajes)
        
        # Clasificar viajes no atendidos por razón
        # IMPORTANTE: Necesitamos evaluar la situación AL MOMENTO del viaje, no después
        viajes_no_atendidos = [v for v in viajes if not v.atendido]
        
        # Volver a obtener la lista inicial de vehículos disponibles
        vehiculos_inicialmente_disponibles = [v for v in self.vehiculos if v.estado == "disponible"]
        
        for viaje in viajes_no_atendidos:
            # Buscar vehículos que ESTABAN en la zona ANTES de las asignaciones
            vehiculos_en_zona = [v for v in vehiculos_inicialmente_disponibles 
                               if v.zona_actual == viaje.zona_origen]
            
            if not vehiculos_en_zona:
                self.kpis['viajes_perdidos_disponibilidad'] += 1
            else:
                # Verificar si alguno tenía batería suficiente
                vehiculos_con_bateria = [v for v in vehiculos_en_zona
                                       if v.puede_realizar_viaje_completo(viaje.zona_origen, viaje.zona_destino)]
                
                if vehiculos_con_bateria:
                    # HAY ERROR: había vehículos capaces pero no se asignó (clasificar como error del sistema)
                    self.kpis['viajes_perdidos_disponibilidad'] += 1
                else:
                    # Había vehículos en zona pero sin batería suficiente
                    self.kpis['viajes_perdidos_bateria'] += 1
    
    def gestionar_carga_vehiculos(self, periodo: int):
        # Gestiona el proceso de carga de vehículos que necesitan batería
        
        # PRIMERO: Vehículos que están EN estaciones de carga y necesitan cargar
        for vehiculo in self.vehiculos:
            if (vehiculo.estado == "disponible" and 
                vehiculo.zona_actual in ZONAS_ESTACIONES_CARGA and 
                vehiculo.bateria_actual < 3.0):  # Menos de 3km
                
                # Está en una estación y necesita cargar
                zona_estacion = vehiculo.zona_actual
                if (self.estaciones_carga[zona_estacion]['vehiculos_cargando'] < 
                    self.estaciones_carga[zona_estacion]['capacidad_maxima']):
                    
                    # Hay espacio, iniciar carga inmediatamente
                    self.estaciones_carga[zona_estacion]['vehiculos_cargando'] += 1
                    vehiculo.iniciar_carga(periodo)
        
        # SEGUNDO: Vehículos que necesitan ir a estaciones de carga
        vehiculos_necesitan_carga = [v for v in self.vehiculos 
                                   if v.estado == "disponible" and v.necesita_cargar() 
                                   and v.zona_actual not in ZONAS_ESTACIONES_CARGA]
        
        for vehiculo in vehiculos_necesitan_carga:
            estacion_disponible = self.encontrar_estacion_disponible(vehiculo)
            
            if estacion_disponible:
                # Enviar vehículo a la estación
                vehiculo.iniciar_viaje_a_estacion(estacion_disponible, periodo)
            else:
                # No hay estaciones disponibles o accesibles
                self.kpis['vehiculos_sin_acceso_carga'] += 1
    
    def registrar_estado_periodo(self, periodo: int):
        # Registrar el estado del sistema en el periodo
        vehiculos_por_estado = {
            'disponibles': len([v for v in self.vehiculos if v.estado == "disponible"]),
            'en_viaje': len([v for v in self.vehiculos if v.estado == "en_viaje"]),
            'cargando': len([v for v in self.vehiculos if v.estado == "cargando"]),
            'yendo_a_cargar': len([v for v in self.vehiculos if v.estado == "yendo_a_cargar"])
        }
        
        # Calcular ocupación de estaciones
        estaciones_ocupacion = {}
        for zona, info in self.estaciones_carga.items():
            estaciones_ocupacion[f'estacion_{zona}'] = info['vehiculos_cargando']
        
        estado = {
            'periodo': periodo,
            'vehiculos_disponibles': vehiculos_por_estado['disponibles'],
            'vehiculos_en_viaje': vehiculos_por_estado['en_viaje'],
            'vehiculos_cargando': vehiculos_por_estado['cargando'],
            'vehiculos_yendo_a_cargar': vehiculos_por_estado['yendo_a_cargar'],
            'bateria_promedio': np.mean([v.bateria_actual for v in self.vehiculos]),
            'vehiculos_bateria_critica': len([v for v in self.vehiculos if v.bateria_actual <= 20])
        }
        estado.update(estaciones_ocupacion)
        self.estado_por_periodo.append(estado)
    
    def calcular_kpis_finales(self):
        # Calcular KPIs finales de la simulación
        self.kpis['porcentaje_viajes_atendidos'] = (
            (self.kpis['viajes_atendidos'] / max(1, self.kpis['viajes_solicitados'])) * 100
        )
        
        # Estadísticas por vehículo
        for vehiculo in self.vehiculos:
            self.kpis['km_totales'] += vehiculo.kilometros_recorridos
        
        # Promedios
        self.kpis['km_promedio_por_vehiculo'] = self.kpis['km_totales'] / NUMERO_VEHICULOS
        self.kpis['ingresos_promedio_por_vehiculo'] = self.kpis['ingresos_totales'] / NUMERO_VEHICULOS
        self.kpis['viajes_promedio_por_vehiculo'] = sum(v.viajes_atendidos for v in self.vehiculos) / NUMERO_VEHICULOS
        self.kpis['cargas_promedio_por_vehiculo'] = sum(v.veces_cargado for v in self.vehiculos) / NUMERO_VEHICULOS
        
        # Estadísticas de carga
        self.kpis['total_eventos_carga'] = sum(v.veces_cargado for v in self.vehiculos)
        
        return self.kpis
    
    def ejecutar_simulacion(self, fecha_inicio: datetime.date, periodos_total: int):
        # Ejecutar la simulación completa
        print(f"Iniciando simulación para {periodos_total} periodos...")
        print(f"Configuración: {NUMERO_VEHICULOS} vehículos, {PORCENTAJE_DEMANDA*100}% de demanda")
        print(f"Estaciones de carga en zonas: {ZONAS_ESTACIONES_CARGA}")
        print(f"🎲 Semillas: Posiciones={SEMILLA_POSICIONES_INICIALES}, Viajes_base={SEMILLA_BASE_VIAJES}")
        
        for periodo in range(periodos_total):
            
            # PRIMERO: Finalizar actividades que terminan al inicio de este período
            # CORRECCIÓN: Solo finalizar cargas al principio, viajes se finalizan al final
            if periodo > 0:
                for vehiculo in self.vehiculos:
                    if vehiculo.tiempo_fin_actividad == periodo:
                        if vehiculo.estado == "cargando":
                            # Liberar espacio en la estación
                            zona_estacion = vehiculo.zona_actual
                            if zona_estacion in self.estaciones_carga:
                                self.estaciones_carga[zona_estacion]['vehiculos_cargando'] -= 1
                            vehiculo.finalizar_carga()
                        elif vehiculo.estado == "yendo_a_cargar":
                            # Llegó a la estación, iniciar carga si hay espacio
                            zona_estacion = vehiculo.estacion_carga_asignada
                            if zona_estacion in self.estaciones_carga:
                                if (self.estaciones_carga[zona_estacion]['vehiculos_cargando'] < 
                                    self.estaciones_carga[zona_estacion]['capacidad_maxima']):
                                    # Hay espacio, iniciar carga
                                    self.estaciones_carga[zona_estacion]['vehiculos_cargando'] += 1
                                    vehiculo.zona_actual = zona_estacion
                                    vehiculo.iniciar_carga(periodo)
                                else:
                                    # No hay espacio, el vehículo se queda disponible
                                    vehiculo.estado = "disponible"
                                    vehiculo.zona_actual = zona_estacion
                                    vehiculo.estacion_carga_asignada = None
            
            # SEGUNDO: Gestionar carga de vehículos disponibles
            # Esto permite que vehículos que terminaron viajes vayan a cargar
            if periodo > 0:  # No en el primer período
                self.gestionar_carga_vehiculos(periodo)
            
            # TERCERO: Obtener y asignar viajes del periodo actual
            viajes_periodo = self.obtener_viajes_periodo(periodo, fecha_inicio)
            self.asignar_viajes_optimizado(viajes_periodo, periodo)
            
            # CUARTO: Finalizar VIAJES que terminan en este período (al final)
            for vehiculo in self.vehiculos:
                if vehiculo.tiempo_fin_actividad == periodo and vehiculo.estado == "en_viaje":
                    vehiculo.finalizar_viaje()
            
            # QUINTO: Registrar estado
            self.registrar_estado_periodo(periodo)
        
        # Calcular KPIs finales
        self.calcular_kpis_finales()
        print("Simulación completada.")
        
        return self.kpis, self.estado_por_periodo






# Ejecutar la simulación
if __name__ == "__main__":
    print("SIMULACIÓN RIDE-HAILING CON DATOS REALES")
    print("="*50)
    
    # Cambiar a una fecha con datos disponibles: 15 de septiembre de 2024
    fecha_simulacion = datetime.date(2024, 9, 15)
    
    print(f"📅 Simulando día: {fecha_simulacion}")
    print(f"🔋 Vehículos: {NUMERO_VEHICULOS}")
    print(f"📊 Porcentaje demanda: {PORCENTAJE_DEMANDA*100}%")
    print(f"⏱️  Periodo simulación: {PERIODO_SIMULACION} minutos")
    
    # Inicializar simulador con datos realess
    simulador = SimuladorRideHailing()
    
    # Ejecutar simulación de un día (96 periodos = 24 horas * 4 periodos/hora)
    PERIODOS_TOTALES = 12  # 1 día completo
    kpis, estado_por_periodo = simulador.ejecutar_simulacion(fecha_simulacion, PERIODOS_TOTALES)

    print("\n🎯 ¡Simulación completada con datos reales!")
    
    # MOSTRAR RESULTADOS DE KPI
    print("\n" + "="*60)
    print("📊 RESULTADOS DE KPI - SIMULACIÓN RIDE-HAILING")
    print("="*60)
    
    # KPI Operacionales
    print("\n🚗 KPI OPERACIONALES:")
    print(f"   • Viajes solicitados: {kpis['viajes_solicitados']:,}")
    print(f"   • Viajes atendidos: {kpis['viajes_atendidos']:,}")
    print(f"   • Porcentaje atendidos: {kpis['porcentaje_viajes_atendidos']:.2f}%")
    print(f"   • Viajes perdidos por batería: {kpis['viajes_perdidos_bateria']:,}")
    print(f"   • Viajes perdidos por disponibilidad: {kpis['viajes_perdidos_disponibilidad']:,}")
    
    # KPI Financieros
    print("\n💰 KPI FINANCIEROS:")
    print(f"   • Ingresos totales: ${kpis['ingresos_totales']:,.2f}")
    print(f"   • Ingresos promedio por vehículo: ${kpis['ingresos_promedio_por_vehiculo']:,.2f}")
    
    # KPI de Eficiencia
    print("\n⚡ KPI DE EFICIENCIA:")
    print(f"   • Kilómetros totales: {kpis['km_totales']:,.2f} km")
    print(f"   • Km promedio por vehículo: {kpis['km_promedio_por_vehiculo']:,.2f} km")
    print(f"   • Viajes promedio por vehículo: {kpis['viajes_promedio_por_vehiculo']:.2f}")
    
    # KPI de Carga
    print("\n🔋 KPI DE CARGA:")
    print(f"   • Total eventos de carga: {kpis['total_eventos_carga']:,}")
    print(f"   • Cargas promedio por vehículo: {kpis['cargas_promedio_por_vehiculo']:.2f}")
    print(f"   • Vehículos sin acceso a carga: {kpis['vehiculos_sin_acceso_carga']:,}")
    
    # Resumen ejecutivo
    print("\n" + "="*60)
    print("📈 RESUMEN EJECUTIVO:")
    print(f"   • Eficiencia operacional: {kpis['porcentaje_viajes_atendidos']:.1f}% de viajes atendidos")
    print(f"   • Ingresos por día: ${kpis['ingresos_totales']:,.2f}")
    print(f"   • Ingresos por vehículo/día: ${kpis['ingresos_promedio_por_vehiculo']:,.2f}")
    print(f"   • Productividad: {kpis['viajes_promedio_por_vehiculo']:.1f} viajes/vehículo/día")
    print("="*60)
