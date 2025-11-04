# Pruebas del Modelo de Optimización vs Caso Base FIFO

Este directorio contiene scripts para probar y comparar el modelo de optimización contra el caso base FIFO en un subconjunto reducido de zonas y períodos.

## 📋 Descripción

El modelo de optimización busca distribuir de manera óptima los vehículos autónomos en Manhattan, mientras que el caso base FIFO asigna vehículos de manera secuencial (First In, First Out).

### Parámetros de Prueba

- **Zonas**: 10 zonas de Manhattan con mayor demanda
  - [87, 116, 137, 151, 128, 186, 162, 163, 164, 68]
- **Vehículos**: 50 (reducido de 300)
- **Períodos**: 24 períodos de 15 minutos (6:00 AM - 12:00 PM)
- **Estaciones de carga**: 6 zonas [87, 116, 137, 151, 128, 186]

## 🚀 Ejecución Rápida

### Opción 1: Ejecutar todo automáticamente

```bash
cd /Users/benjaminreyes/UC/capstone-3
python ejecutar_pruebas.py
```

Este script ejecutará:
1. ✅ Caso base FIFO
2. ✅ Modelo de optimización
3. ✅ Comparación de resultados

### Opción 2: Ejecutar componentes individualmente

```bash
# 1. Ejecutar caso base FIFO
python "Caso base/simulacion_casobase_test.py"

# 2. Ejecutar modelo de optimización (requiere Gurobi)
python "capstone model/model_test.py"

# 3. Comparar resultados
python comparar_resultados.py
```

## 📊 KPIs Evaluados

Los scripts comparan ambos modelos en base a:

### 🚗 KPI Operacionales
- Viajes solicitados
- Viajes atendidos
- Tasa de atención (%)
- Demanda no atendida
- Viajes perdidos por batería
- Viajes perdidos por disponibilidad

### 💰 KPI Financieros
- Ingresos totales ($)
- Ingresos promedio por vehículo
- Costos de reubicación (solo modelo)
- Beneficio neto

### ⚡ KPI de Eficiencia
- Kilómetros totales
- Km promedio por vehículo
- Viajes promedio por vehículo
- Reubicaciones (solo modelo)

### 🔋 KPI de Carga
- Eventos de carga
- Cargas promedio por vehículo
- Vehículos sin acceso a carga

## 📁 Archivos Generados

Después de la ejecución, se generan:

1. **`resultados_casobase_test.txt`**: KPIs del caso base FIFO
2. **`resultados_modelo_test.txt`**: KPIs del modelo de optimización
3. **`comparacion_modelo_vs_casobase.txt`**: Comparación detallada con mejoras porcentuales

## 🔧 Requisitos

### Python
- Python 3.8+
- pandas
- numpy

### Modelo de Optimización (adicional)
- gurobipy (con licencia válida)

### Datos
- Archivo parquet con datos históricos de viajes:
  `/Users/benjaminreyes/UC/capstone-3/Datos/df_all_procesado.parquet`

## ⚙️ Configuración del Modelo de Optimización

El modelo utiliza Gurobi con los siguientes parámetros:
- **TimeLimit**: 300 segundos (5 minutos)
- **MIPGap**: 0.05 (5% de gap aceptable)

Estos parámetros pueden ajustarse en `capstone model/model_test.py`:

```python
m.setParam('TimeLimit', 300)  # segundos
m.setParam('MIPGap', 0.05)    # gap
```

## 📈 Interpretación de Resultados

### Mejoras Esperadas del Modelo vs Caso Base

El modelo de optimización debería mostrar mejoras en:
- ✅ **Mayor tasa de atención**: Más viajes atendidos
- ✅ **Mayores ingresos**: Mejor selección de viajes rentables
- ✅ **Mejor eficiencia**: Menos km desperdiciados
- ✅ **Menor demanda insatisfecha**: Optimización de asignaciones

### Ejemplo de Salida

```
📊 COMPARACIÓN DETALLADA DE KPIs
================================================================================

🚗 KPI OPERACIONALES:
Métrica                                  Caso Base       Modelo Opt.     Mejora    
--------------------------------------------------------------------------------
Viajes atendidos                         120             145             +20.83%
Tasa de atención (%)                     75.00%          90.63%          +20.84%
Demanda no atendida                      40              15              +62.50%
...
```

## 🔍 Solución de Problemas

### Error: "gurobipy no encontrado"
- Instala Gurobi: `pip install gurobipy`
- Verifica tu licencia: `gurobi_cl --license`

### Error: "No se encontró df_all_procesado.parquet"
- Verifica que el archivo de datos existe en la ruta especificada
- Ejecuta el script de preparación de datos si es necesario

### Tiempo de ejecución largo
- Reduce el número de zonas o períodos en los scripts de prueba
- Aumenta el MIPGap para soluciones más rápidas (pero menos óptimas)

## 📝 Notas

- Los scripts usan **semillas fijas** (random seeds) para reproducibilidad
- La demanda es el **5% de la demanda real** para acelerar pruebas
- Los resultados son **comparables** porque ambos usan las mismas zonas, períodos y demanda

## 🚀 Escalamiento

Una vez validado con este subconjunto, puedes escalar:

1. Aumentar número de zonas (actualmente 10 → 67 zonas completas)
2. Aumentar número de períodos (actualmente 24 → 96 para día completo)
3. Aumentar número de vehículos (actualmente 50 → 300)

Para escalar, modifica los parámetros en:
- `capstone model/model_test.py`
- `Caso base/simulacion_casobase_test.py`

## 📧 Contacto

Para preguntas sobre el modelo, consulta la documentación del proyecto principal en la raíz del repositorio.
