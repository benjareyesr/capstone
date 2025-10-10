import pandas as pd
import geopandas as gpd
import numpy as np
from geopy.distance import geodesic
import csv

def calcular_distancias_manhattan():
    taxi_zones = gpd.read_file('Datos/taxi_zones/taxi_zones.shp')
    manhattan_zones = taxi_zones[taxi_zones['borough'] == 'Manhattan'].copy()
    manhattan_zones = manhattan_zones.drop_duplicates(subset=['LocationID']).reset_index(drop=True)
    print(f"Zonas de Manhattan únicas encontradas: {len(manhattan_zones)}")
    
    # Convertir a coordenadas proyectadas en METROS (UTM Zone 18N para NYC)
    manhattan_proj = manhattan_zones.to_crs('EPSG:32618')  # UTM 18N en metros
    manhattan_proj['centroid_proj'] = manhattan_proj.geometry.centroid
    manhattan_proj['x_meters'] = manhattan_proj.centroid_proj.x
    manhattan_proj['y_meters'] = manhattan_proj.centroid_proj.y
    
    # Luego convertir a coordenadas geográficas para distancias geodésicas
    manhattan_geo = manhattan_proj.to_crs('EPSG:4326')
    manhattan_geo['centroid'] = manhattan_geo.geometry.centroid
    manhattan_geo['lon'] = manhattan_geo.centroid.x
    manhattan_geo['lat'] = manhattan_geo.centroid.y
        
    zonas = []
    for i, (_, row_geo) in enumerate(manhattan_geo.iterrows()):
        row_proj = manhattan_proj.iloc[i]
        zonas.append({
            'LocationID': int(row_geo['LocationID']),
            'zone': row_geo['zone'],
            'lat': row_geo['lat'],
            'lon': row_geo['lon'],
            'x_meters': row_proj['x_meters'],
            'y_meters': row_proj['y_meters']
        })

    # Velocidades promedio en km/h según tabla
    velocidad_normal = 25    # Velocidad promedio
    velocidad_punta = 20     # Hora punta (más lento)
    velocidad_valle = 30     # Hora valle (más rápido)

    distancias = []    
    for i, zona_origen in enumerate(zonas):
        for j, zona_destino in enumerate(zonas):
            origen = (zona_origen['lat'], zona_origen['lon'])
            destino = (zona_destino['lat'], zona_destino['lon'])
            
            # Calcular distancia geodésica, línea recta sobre la superficie terrestre
            distancia_geodesica = geodesic(origen, destino).kilometers
            # Distancia Manhattan aproximada (usando factores lat/lon)
            lat_diff = abs(zona_origen['lat'] - zona_destino['lat'])
            lon_diff = abs(zona_origen['lon'] - zona_destino['lon'])
            distancia_manhattan_aprox = (lat_diff * 111) + (lon_diff * 85)
            # Distancia Manhattan exacta (usando coordenadas proyectadas en metros)
            x_diff = abs(zona_origen['x_meters'] - zona_destino['x_meters'])
            y_diff = abs(zona_origen['y_meters'] - zona_destino['y_meters'])
            distancia_manhattan_exacta = (x_diff + y_diff) / 1000  # convertir a km
            
            # Calcular duraciones en minutos usando distancia Manhattan exacta
            duracion_normal = (distancia_manhattan_exacta / velocidad_normal) * 60  # minutos
            duracion_punta = (distancia_manhattan_exacta / velocidad_punta) * 60    # minutos
            duracion_valle = (distancia_manhattan_exacta / velocidad_valle) * 60    # minutos
            
            distancias.append({
                'origen_id': zona_origen['LocationID'],
                'origen_zona': zona_origen['zone'],
                'destino_id': zona_destino['LocationID'],
                'destino_zona': zona_destino['zone'],
                'distancia_geodesica_km': round(distancia_geodesica, 3),
                'distancia_manhattan_aprox_km': round(distancia_manhattan_aprox, 3),
                'distancia_manhattan_exacta_km': round(distancia_manhattan_exacta, 3),
                'duracion_normal_min': round(duracion_normal, 1),
                'duracion_hora_punta_min': round(duracion_punta, 1),
                'duracion_hora_valle_min': round(duracion_valle, 1)
            })
        
        if (i + 1) % 10 == 0:
            print(f"Procesadas {i + 1}/{len(zonas)} zonas...")
    
    # Crear DataFrame y guardar en CSV
    df_distancias = pd.DataFrame(distancias)
    
    # Guardar archivo completo
    csv_file = 'distancias_manhattan_zonas_con_tiempo.csv'
    df_distancias.to_csv(csv_file, index=False)
    print(f"\nArchivo guardado: {csv_file}")
    
    # Crear matrices cuadradas para cada tipo de distancia y tiempo
    matriz_geodesica = df_distancias.pivot(index='origen_id', columns='destino_id', values='distancia_geodesica_km')
    matriz_manhattan_aprox = df_distancias.pivot(index='origen_id', columns='destino_id', values='distancia_manhattan_aprox_km')
    matriz_manhattan_exacta = df_distancias.pivot(index='origen_id', columns='destino_id', values='distancia_manhattan_exacta_km')
    matriz_tiempo_normal = df_distancias.pivot(index='origen_id', columns='destino_id', values='duracion_normal_min')
    matriz_tiempo_punta = df_distancias.pivot(index='origen_id', columns='destino_id', values='duracion_hora_punta_min')
    matriz_tiempo_valle = df_distancias.pivot(index='origen_id', columns='destino_id', values='duracion_hora_valle_min')

    # Guardar matrices
    matriz_geodesica.to_csv('matriz_distancias_geodesicas_final_2.csv')
    matriz_manhattan_aprox.to_csv('matriz_distancias_manhattan_aprox_final_2.csv')
    matriz_manhattan_exacta.to_csv('matriz_distancias_manhattan_exacta_final_2.csv')
    matriz_tiempo_normal.to_csv('matriz_tiempo_normal_min_final_2.csv')
    matriz_tiempo_punta.to_csv('matriz_tiempo_hora_punta_min_final_2.csv')
    matriz_tiempo_valle.to_csv('matriz_tiempo_hora_valle_min_final_2.csv')

    return df_distancias, matriz_geodesica, matriz_manhattan_aprox, matriz_manhattan_exacta, matriz_tiempo_normal, matriz_tiempo_punta, matriz_tiempo_valle

if __name__ == "__main__":
    # Instalar geopy si no está disponible
    try:
        from geopy.distance import geodesic
    except ImportError:
        print("Instalando geopy...")
        import subprocess
        subprocess.run(["pip", "install", "geopy"])
        from geopy.distance import geodesic
    
    resultados = calcular_distancias_manhattan()
    print("Listo!!")