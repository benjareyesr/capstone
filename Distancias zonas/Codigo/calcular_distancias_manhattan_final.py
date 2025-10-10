import pandas as pd
import geopandas as gpd

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
        
    zonas = []
    for _, row in manhattan_proj.iterrows():
        zonas.append({
            'LocationID': int(row['LocationID']),
            'zone': row['zone'],
            'x_meters': row['x_meters'],
            'y_meters': row['y_meters']
        })

    # Velocidades promedio en km/h
    velocidad_normal = 25    # Velocidad promedio
    velocidad_punta = 20     # Hora punta (más lento)
    velocidad_valle = 30     # Hora valle (más rápido)
    
    # Tarifas de taxi en USD
    tarifa_fija = 5.5        # USD fijo por viaje
    tarifa_por_km = 3.7      # USD por kilómetro

    distancias = []    
    for i, zona_origen in enumerate(zonas):
        for zona_destino in zonas:
            # Distancia Manhattan exacta (usando coordenadas proyectadas en metros)
            x_diff = abs(zona_origen['x_meters'] - zona_destino['x_meters'])
            y_diff = abs(zona_origen['y_meters'] - zona_destino['y_meters'])
            distancia_manhattan_exacta = (x_diff + y_diff) / 1000  # convertir a km
            
            # Calcular duraciones en minutos usando distancia Manhattan exacta
            duracion_normal = (distancia_manhattan_exacta / velocidad_normal) * 60  # minutos
            duracion_punta = (distancia_manhattan_exacta / velocidad_punta) * 60    # minutos
            duracion_valle = (distancia_manhattan_exacta / velocidad_valle) * 60    # minutos
            
            # Calcular ingreso por viaje
            ingreso_viaje = tarifa_fija + (distancia_manhattan_exacta * tarifa_por_km)
            
            distancias.append({
                'origen_id': zona_origen['LocationID'],
                'origen_zona': zona_origen['zone'],
                'destino_id': zona_destino['LocationID'],
                'destino_zona': zona_destino['zone'],
                'distancia_km': round(distancia_manhattan_exacta, 3),
                'duracion_normal_min': round(duracion_normal, 1),
                'duracion_hora_punta_min': round(duracion_punta, 1),
                'duracion_hora_valle_min': round(duracion_valle, 1),
                'ingreso_viaje_usd': round(ingreso_viaje, 2)
            })
        
        if (i + 1) % 10 == 0:
            print(f"Procesadas {i + 1}/{len(zonas)} zonas...")
    
    # Crear DataFrame y guardar en CSV
    df_distancias = pd.DataFrame(distancias)
    csv_file = 'distancias_manhattan_zonas_con_tiempo_ingreso.csv'
    df_distancias.to_csv(csv_file, index=False)
    print(f"\nArchivo guardado: {csv_file}")

    return df_distancias

if __name__ == "__main__":
    resultados = calcular_distancias_manhattan()
    print("Listo!!")