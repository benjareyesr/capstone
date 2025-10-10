# Cálculo de Distancias y Tiempos entre Zonas de Manhattan

## 📋 Descripción

Este script calcula distancias Manhattan exactas y tiempos de viaje entre todas las zonas de taxi de Manhattan, incluyendo estimaciones de ingresos por viaje.

## 🎯 Objetivo

Generar una matriz completa de distancias, tiempos y costos entre las 67 zonas únicas de Manhattan para modelos de optimización de rutas de taxi.

## 📊 Datos de Entrada

- **Shapefile**: `Datos/taxi_zones/taxi_zones.shp` - Zonas oficiales de taxi de NYC
- **Filtro**: Solo zonas de Manhattan (67 zonas únicas)

## 🧮 Cálculos Realizados

### Distancias
- **Método**: Distancia Manhattan usando coordenadas proyectadas UTM (EPSG:32618)
- **Fórmula**: `|x1-x2| + |y1-y2|` en metros, convertido a kilómetros
- **Ventaja**: Simula movimiento real por calles en grid de Manhattan

### Tiempos de Viaje
Calculados usando diferentes velocidades según congestión:

| Periodo | Velocidad | Descripción |
|---------|-----------|-------------|
| **Normal** | 25 km/h | Velocidad promedio |
| **Hora Punta** | 20 km/h | Tráfico congestionado |
| **Hora Valle** | 30 km/h | Tráfico fluido |

### Ingresos por Viaje
- **Tarifa fija**: $5.50 USD por viaje
- **Tarifa por distancia**: $3.70 USD por kilómetro
- **Fórmula**: `Ingreso = $5.50 + ($3.70 × distancia_km)`

## 📁 Archivo Generado

**`distancias_manhattan_zonas_con_tiempo_ingreso.csv`**

### Columnas:
- `origen_id` - ID de zona origen
- `origen_zona` - Nombre de zona origen  
- `destino_id` - ID de zona destino
- `destino_zona` - Nombre de zona destino
- `distancia_km` - Distancia Manhattan en kilómetros
- `duracion_normal_min` - Tiempo en minutos (velocidad normal)
- `duracion_hora_punta_min` - Tiempo en minutos (hora punta)
- `duracion_hora_valle_min` - Tiempo en minutos (hora valle)
- `ingreso_viaje_usd` - Ingreso estimado por viaje en USD

### Estadísticas:
- **Total registros**: 4,489 (67 × 67 combinaciones)
- **Rango distancias**: 0 - ~32 km
- **Rango tiempos**: 0 - ~77 minutos
- **Rango ingresos**: $5.50 - ~$124 USD

## 🚀 Uso

```bash
python calcular_distancias_manhattan_final.py
```

## 📈 Aplicaciones

- **Optimización de rutas** de taxi
- **Análisis de rentabilidad** por trayecto
- **Planificación de horarios** según congestión
- **Modelos de pricing** dinámico
- **Asignación eficiente** de vehículos

## 🔧 Dependencias

```bash
pip install pandas geopandas
```

## 📝 Notas Técnicas

- Se eliminan zonas duplicadas por LocationID (ej: islas con mismo ID)
- Coordenadas proyectadas en metros para mayor precisión
- Distancia Manhattan es más realista que geodésica para NYC
- Velocidades basadas en promedios reales de tráfico urbano