"""
CASO BASE FIFO - VERSIÓN EXPANDIDA
Misma configuración que el modelo expandido para comparación justa
"""

import numpy as np
import pandas as pd
from collections import defaultdict
import random
from typing import Dict, List
import math
import sys
import time

sys.path.append('/Users/benjaminreyes/UC/capstone-3')
from parametros_matrices import obtener_distancia, obtener_tiempo, obtener_ingreso, normalizar_zona

print("="*80)
print("🚀 CASO BASE FIFO - VERSIÓN EXPANDIDA")
print("="*80)

# MISMOS PARÁMETROS QUE MODELO EXPANDIDO
ZONAS_TEST = [87, 116, 137, 151, 128, 186, 162, 163, 164, 68, 90, 100, 107, 113, 114]
ZONA_TEST_A_INDICE = {zona_id: idx for idx, zona_id in enumerate(ZONAS_TEST)}

print(f"\n📍 Configuración EXPANDIDA:")
print(f"   • Zonas: {len(ZONAS_TEST)} zonas")
print(f"   • Zonas específicas: {ZONAS_TEST}")

NUMERO_VEHICULOS = 60
AUTONOMIA_VEHICULO = 350
TIEMPO_RECARGA = 110
PORCENTAJE_DEMANDA = 0.05
COSTO_REUBICACION_MULTIPLIER = 1.25
PERIODO_SIMULACION = 15

PERIODO_INICIO = 32  # 8:00 AM
PERIODO_FIN = 48     # 12:00 PM
PERIODOS_SIMULACION = PERIODO_FIN - PERIODO_INICIO

print(f"   • Vehículos: {NUMERO_VEHICULOS}")
print(f"   • Períodos: {PERIODOS_SIMULACION} (8:00 AM - 12:00 PM)")
print(f"   • Duración: 4 horas")

SEMILLA_POSICIONES_INICIALES = 42
SEMILLA_BASE_VIAJES = 123

# Estaciones de carga en las zonas del test
ZONAS_ESTACIONES_CARGA = [87, 116, 137, 151, 128, 186]
CAPACIDAD_MAXIMA_ESTACION = 55

print(f"   • Estaciones de carga: {ZONAS_ESTACIONES_CARGA}")

# Clases del simulador (copiadas del original)
class Vehiculo:
    def __init__(self, vehiculo_id: int, zona_inicial: int):
        self.id = vehiculo_id
        self.zona_actual = zona_inicial
        self.bateria_actual = AUTONOMIA_VEHICULO
        self.estado = "disponible"
        self.tiempo_fin_actividad = 0
        self.viaje_actual = None
        self.tiempo_inicio_carga = 0
        self.estacion_carga_asignada = None
        self.kilometros_recorridos = 0
        self.ingresos_generados = 0
        self.viajes_atendidos = 0
        self.veces_cargado = 0
    
    def puede_realizar_viaje_completo(self, zona_origen: int, zona_destino: int) -> bool:
        distancia_viaje = obtener_distancia(zona_origen, zona_destino)
        estacion_mas_cercana = self.encontrar_estacion_mas_cercana_desde(zona_destino)
        
        if estacion_mas_cercana is None:
            return False
        
        distancia_a_estacion = obtener_distancia(zona_destino, estacion_mas_cercana)
        distancia_total = distancia_viaje + distancia_a_estacion
        
        return self.bateria_actual >= distancia_total
    
    def encontrar_estacion_mas_cercana_desde(self, zona: int):
        estacion_mas_cercana = None
        distancia_minima = float('inf')
        
        for zona_estacion in ZONAS_ESTACIONES_CARGA:
            distancia = obtener_distancia(zona, zona_estacion)
            if distancia < distancia_minima:
                distancia_minima = distancia
                estacion_mas_cercana = zona_estacion
        
        return estacion_mas_cercana
    
    def necesita_cargar(self) -> bool:
        UMBRAL_BATERIA_CRITICA = 9.0
        return self.bateria_actual <= UMBRAL_BATERIA_CRITICA
    
    def puede_llegar_a_estacion(self, zona_estacion: int) -> bool:
        distancia_estimada = obtener_distancia(self.zona_actual, zona_estacion)
        return self.bateria_actual >= distancia_estimada
    
    def iniciar_viaje(self, viaje, periodo_actual: int):
        self.estado = "en_viaje"
        self.viaje_actual = viaje
        self.tiempo_fin_actividad = periodo_actual + viaje['duracion_periodos']
    
    def finalizar_viaje(self):
        if self.viaje_actual:
            self.zona_actual = self.viaje_actual['zona_destino']
            self.bateria_actual -= self.viaje_actual['distancia_km']
            self.kilometros_recorridos += self.viaje_actual['distancia_km']
            self.ingresos_generados += self.viaje_actual['ingreso']
            self.viajes_atendidos += 1
        
        self.estado = "disponible"
        self.viaje_actual = None
    
    def iniciar_viaje_a_estacion(self, zona_estacion: int, periodo_actual: int):
        distancia = obtener_distancia(self.zona_actual, zona_estacion)
        duracion_minutos = obtener_tiempo(self.zona_actual, zona_estacion, 'normal')
        periodos_adicionales = max(1, math.floor(duracion_minutos / PERIODO_SIMULACION))
        
        self.estado = "yendo_a_cargar"
        self.estacion_carga_asignada = zona_estacion
        self.tiempo_fin_actividad = periodo_actual + periodos_adicionales
        
        self.bateria_actual -= distancia
        self.kilometros_recorridos += distancia
    
    def iniciar_carga(self, periodo_actual: int):
        self.estado = "cargando"
        self.tiempo_inicio_carga = periodo_actual
        periodos_carga = math.ceil(TIEMPO_RECARGA / PERIODO_SIMULACION)
        self.tiempo_fin_actividad = periodo_actual + periodos_carga
    
    def finalizar_carga(self):
        self.bateria_actual = AUTONOMIA_VEHICULO
        self.estado = "disponible"
        self.veces_cargado += 1
        if self.estacion_carga_asignada:
            self.zona_actual = self.estacion_carga_asignada
            self.estacion_carga_asignada = None

class Viaje:
    def __init__(self, viaje_data: dict, periodo_inicio: int):
        self.zona_origen = normalizar_zona(int(viaje_data['PUlocationID']))
        self.zona_destino = normalizar_zona(int(viaje_data['DOlocationID']))
        self.periodo_inicio = periodo_inicio
        self.distancia_km = obtener_distancia(self.zona_origen, self.zona_destino)
        self.duracion_periodos = self.calcular_duracion_periodos(periodo_inicio)
        self.ingreso = obtener_ingreso(self.zona_origen, self.zona_destino)
        self.atendido = False
    
    def calcular_duracion_periodos(self, periodo: int) -> int:
        hora_actual = (periodo * PERIODO_SIMULACION) // 60
        tipo_hora = self.obtener_tipo_hora(hora_actual)
        duracion_minutos = obtener_tiempo(self.zona_origen, self.zona_destino, tipo_hora)
        periodos_adicionales = math.floor(duracion_minutos / PERIODO_SIMULACION)
        return periodos_adicionales
    
    def obtener_tipo_hora(self, hora: int) -> str:
        if 16 <= hora <= 20:
            return 'punta'
        elif 0 <= hora <= 7:
            return 'valle'
        else:
            return 'normal'

class SimuladorRideHailing:
    def __init__(self):
        self.vehiculos = self.inicializar_flota()
        self.estaciones_carga = self.inicializar_estaciones()
        self.kpis = {
            'viajes_solicitados': 0,
            'viajes_atendidos': 0,
            'ingresos_totales': 0,
            'km_totales': 0,
            'viajes_perdidos_bateria': 0,
            'viajes_perdidos_disponibilidad': 0,
            'vehiculos_sin_acceso_carga': 0,
        }
    
    def inicializar_estaciones(self) -> Dict[int, Dict]:
        estaciones = {}
        for zona in ZONAS_ESTACIONES_CARGA:
            estaciones[zona] = {
                'capacidad_maxima': CAPACIDAD_MAXIMA_ESTACION,
                'vehiculos_cargando': 0,
                'cola_espera': []
            }
        return estaciones
    
    def inicializar_flota(self) -> List[Vehiculo]:
        random.seed(SEMILLA_POSICIONES_INICIALES)
        np.random.seed(SEMILLA_POSICIONES_INICIALES)
        
        vehiculos = []
        
        # Distribuir vehículos uniformemente en todas las zonas
        vehiculos_por_zona = NUMERO_VEHICULOS // len(ZONAS_TEST)
        vehiculos_restantes = NUMERO_VEHICULOS % len(ZONAS_TEST)
        
        vehiculo_id = 0
        for idx, zona in enumerate(ZONAS_TEST):
            n_vehiculos = vehiculos_por_zona
            if idx < vehiculos_restantes:
                n_vehiculos += 1
            
            for _ in range(n_vehiculos):
                vehiculos.append(Vehiculo(vehiculo_id, zona))
                vehiculo_id += 1
        
        return vehiculos
    
    def cargar_viajes_periodo(self, periodo_global: int, df_all: pd.DataFrame) -> List[Viaje]:
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
                random_state=SEMILLA_BASE_VIAJES + periodo_global
            )
        else:
            return []
        
        viajes = []
        for _, row in viajes_muestra.iterrows():
            origen_id = normalizar_zona(int(row['PUlocationID']))
            destino_id = normalizar_zona(int(row['DOlocationID']))
            
            if origen_id in ZONAS_TEST and destino_id in ZONAS_TEST:
                viaje = Viaje(row, periodo_global)
                viajes.append(viaje)
        
        return viajes
    
    def asignar_viajes_fifo(self, viajes: List[Viaje], periodo_actual: int):
        for viaje in viajes:
            vehiculos_disponibles = [
                v for v in self.vehiculos
                if v.estado == "disponible" and v.zona_actual == viaje.zona_origen
            ]
            
            if vehiculos_disponibles:
                vehiculo = vehiculos_disponibles[0]
                
                if vehiculo.puede_realizar_viaje_completo(viaje.zona_origen, viaje.zona_destino):
                    vehiculo.iniciar_viaje({
                        'zona_destino': viaje.zona_destino,
                        'distancia_km': viaje.distancia_km,
                        'duracion_periodos': viaje.duracion_periodos,
                        'ingreso': viaje.ingreso
                    }, periodo_actual)
                    viaje.atendido = True
                    self.kpis['viajes_atendidos'] += 1
                    self.kpis['ingresos_totales'] += viaje.ingreso
                else:
                    self.kpis['viajes_perdidos_bateria'] += 1
            else:
                self.kpis['viajes_perdidos_disponibilidad'] += 1
        
        self.kpis['viajes_solicitados'] += len(viajes)
    
    def actualizar_vehiculos(self, periodo_actual: int):
        for vehiculo in self.vehiculos:
            if vehiculo.estado in ["en_viaje", "yendo_a_cargar"]:
                if periodo_actual >= vehiculo.tiempo_fin_actividad:
                    if vehiculo.estado == "en_viaje":
                        vehiculo.finalizar_viaje()
                    elif vehiculo.estado == "yendo_a_cargar":
                        if vehiculo.estacion_carga_asignada in self.estaciones_carga:
                            estacion = self.estaciones_carga[vehiculo.estacion_carga_asignada]
                            if estacion['vehiculos_cargando'] < estacion['capacidad_maxima']:
                                vehiculo.iniciar_carga(periodo_actual)
                                estacion['vehiculos_cargando'] += 1
            
            elif vehiculo.estado == "cargando":
                if periodo_actual >= vehiculo.tiempo_fin_actividad:
                    if vehiculo.estacion_carga_asignada in self.estaciones_carga:
                        self.estaciones_carga[vehiculo.estacion_carga_asignada]['vehiculos_cargando'] -= 1
                    vehiculo.finalizar_carga()
    
    def gestionar_carga(self, periodo_actual: int):
        for vehiculo in self.vehiculos:
            if vehiculo.estado == "disponible" and vehiculo.necesita_cargar():
                estacion_cercana = vehiculo.encontrar_estacion_mas_cercana_desde(vehiculo.zona_actual)
                
                if estacion_cercana and vehiculo.puede_llegar_a_estacion(estacion_cercana):
                    vehiculo.iniciar_viaje_a_estacion(estacion_cercana, periodo_actual)
                else:
                    self.kpis['vehiculos_sin_acceso_carga'] += 1
    
    def ejecutar_simulacion(self):
        print("\n🔄 Cargando datos...")
        df_all = pd.read_parquet('/Users/benjaminreyes/UC/capstone-3/Datos/df_all_procesado.parquet')
        df_all['pickup_datetime'] = pd.to_datetime(df_all['pickup_datetime'])
        df_all['hora'] = df_all['pickup_datetime'].dt.hour
        df_all['minuto'] = df_all['pickup_datetime'].dt.minute
        
        print("🚀 Iniciando simulación...")
        inicio = time.time()
        
        for periodo_local in range(PERIODOS_SIMULACION):
            periodo_global = PERIODO_INICIO + periodo_local
            
            if periodo_local % 4 == 0:
                hora = (periodo_global * PERIODO_SIMULACION) // 60
                minuto = (periodo_global * PERIODO_SIMULACION) % 60
                print(f"   Período {periodo_local+1}/{PERIODOS_SIMULACION} - {hora:02d}:{minuto:02d}")
            
            self.actualizar_vehiculos(periodo_local)
            self.gestionar_carga(periodo_local)
            viajes = self.cargar_viajes_periodo(periodo_global, df_all)
            self.asignar_viajes_fifo(viajes, periodo_local)
        
        tiempo_sim = time.time() - inicio
        print(f"✅ Simulación completada en {tiempo_sim:.2f} segundos")
        
        self.calcular_kpis_finales()
    
    def calcular_kpis_finales(self):
        self.kpis['porcentaje_viajes_atendidos'] = (
            (self.kpis['viajes_atendidos'] / max(1, self.kpis['viajes_solicitados'])) * 100
        )
        
        for vehiculo in self.vehiculos:
            self.kpis['km_totales'] += vehiculo.kilometros_recorridos
        
        self.kpis['km_promedio_por_vehiculo'] = self.kpis['km_totales'] / NUMERO_VEHICULOS
        self.kpis['ingresos_promedio_por_vehiculo'] = self.kpis['ingresos_totales'] / NUMERO_VEHICULOS
        self.kpis['viajes_promedio_por_vehiculo'] = sum(v.viajes_atendidos for v in self.vehiculos) / NUMERO_VEHICULOS
        self.kpis['cargas_promedio_por_vehiculo'] = sum(v.veces_cargado for v in self.vehiculos) / NUMERO_VEHICULOS
        self.kpis['total_eventos_carga'] = sum(v.veces_cargado for v in self.vehiculos)
        
        # Calcular vehículos activos
        vehiculos_activos = sum(1 for v in self.vehiculos if v.viajes_atendidos > 0)
        self.kpis['vehiculos_activos'] = vehiculos_activos
    
    def imprimir_resultados(self):
        print("\n" + "="*80)
        print("📊 RESULTADOS CASO BASE (FIFO) - VERSIÓN EXPANDIDA")
        print("="*80)
        
        print("\n🚗 KPI OPERACIONALES:")
        print(f"   • Viajes solicitados: {self.kpis['viajes_solicitados']:,}")
        print(f"   • Viajes atendidos: {self.kpis['viajes_atendidos']:,}")
        print(f"   • Tasa de atención: {self.kpis['porcentaje_viajes_atendidos']:.2f}%")
        print(f"   • Viajes perdidos por batería: {self.kpis['viajes_perdidos_bateria']:,}")
        print(f"   • Viajes perdidos por disponibilidad: {self.kpis['viajes_perdidos_disponibilidad']:,}")
        
        print("\n💰 KPI FINANCIEROS:")
        print(f"   • Ingresos totales: ${self.kpis['ingresos_totales']:,.2f}")
        print(f"   • Ingresos promedio/vehículo: ${self.kpis['ingresos_promedio_por_vehiculo']:,.2f}")
        
        print("\n⚡ KPI DE EFICIENCIA:")
        print(f"   • Kilómetros totales: {self.kpis['km_totales']:,.2f} km")
        print(f"   • Km promedio/vehículo: {self.kpis['km_promedio_por_vehiculo']:,.2f} km")
        print(f"   • Viajes promedio/vehículo: {self.kpis['viajes_promedio_por_vehiculo']:.2f}")
        
        print("\n🔋 KPI DE CARGA:")
        print(f"   • Total eventos de carga: {self.kpis['total_eventos_carga']:,}")
        print(f"   • Cargas promedio/vehículo: {self.kpis['cargas_promedio_por_vehiculo']:.2f}")
        print(f"   • Vehículos sin acceso a carga: {self.kpis['vehiculos_sin_acceso_carga']:,}")
        
        print(f"\n🚗 USO DE FLOTA:")
        print(f"   • Vehículos activos: {self.kpis['vehiculos_activos']}/{NUMERO_VEHICULOS} ({(self.kpis['vehiculos_activos']/NUMERO_VEHICULOS)*100:.1f}%)")
        
        print("\n" + "="*80)
    
    def guardar_resultados(self):
        with open('/Users/benjaminreyes/UC/capstone-3/resultados_casobase_expandido.txt', 'w') as f:
            f.write("RESULTADOS CASO BASE (FIFO) - VERSIÓN EXPANDIDA\n")
            f.write("="*80 + "\n\n")
            f.write(f"CONFIGURACIÓN:\n")
            f.write(f"  Zonas: {len(ZONAS_TEST)}\n")
            f.write(f"  Vehículos: {NUMERO_VEHICULOS}\n")
            f.write(f"  Períodos: {PERIODOS_SIMULACION} (4 horas)\n\n")
            f.write("KPI OPERACIONALES:\n")
            f.write(f"  Viajes solicitados: {self.kpis['viajes_solicitados']:,}\n")
            f.write(f"  Viajes atendidos: {self.kpis['viajes_atendidos']:,}\n")
            f.write(f"  Tasa de atención: {self.kpis['porcentaje_viajes_atendidos']:.2f}%\n")
            f.write(f"  Viajes perdidos por batería: {self.kpis['viajes_perdidos_bateria']:,}\n")
            f.write(f"  Viajes perdidos por disponibilidad: {self.kpis['viajes_perdidos_disponibilidad']:,}\n\n")
            f.write("KPI FINANCIEROS:\n")
            f.write(f"  Ingresos totales: ${self.kpis['ingresos_totales']:,.2f}\n")
            f.write(f"  Ingresos promedio/vehículo: ${self.kpis['ingresos_promedio_por_vehiculo']:,.2f}\n\n")
            f.write("KPI DE EFICIENCIA:\n")
            f.write(f"  Kilómetros totales: {self.kpis['km_totales']:,.2f} km\n")
            f.write(f"  Km promedio/vehículo: {self.kpis['km_promedio_por_vehiculo']:.2f} km\n")
            f.write(f"  Viajes promedio/vehículo: {self.kpis['viajes_promedio_por_vehiculo']:.2f}\n\n")
            f.write("KPI DE CARGA:\n")
            f.write(f"  Eventos de carga: {self.kpis['total_eventos_carga']:,}\n")
            f.write(f"  Cargas promedio/vehículo: {self.kpis['cargas_promedio_por_vehiculo']:.2f}\n")
            f.write(f"  Vehículos sin acceso a carga: {self.kpis['vehiculos_sin_acceso_carga']:,}\n\n")
            f.write("USO DE FLOTA:\n")
            f.write(f"  Vehículos activos: {self.kpis['vehiculos_activos']}/{NUMERO_VEHICULOS}\n")
        
        print(f"💾 Resultados guardados en: resultados_casobase_expandido.txt")

# Ejecutar
if __name__ == "__main__":
    simulador = SimuladorRideHailing()
    simulador.ejecutar_simulacion()
    simulador.imprimir_resultados()
    simulador.guardar_resultados()
    
    print("\n✅ SIMULACIÓN COMPLETADA")
    print("="*80)
