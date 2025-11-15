from gurobipy import Model, GRB, quicksum, LinExpr
m = Model("MODELO NUEVO MEJORADO")

# --------------------------------------------------
# PARÁMETROS
# --------------------------------------------------

import parametros_matrices_nuevo as pm 
# p contiene p.T, p.N, p.A, p.E, p.d, p.Dem, p.Pviaje, p.Creub, p.mapa_llegadas, etc.
p = pm.cargar_parametros_modelo(T_total=3, fecha_dia_str='2024-09-15')
# Extraer variables para acceso más fácil
N, T, A = p['N'], p['T'], p['A']
E_min = p['E_min']
Tchg = p['Tchg']
mapa_llegadas_viaje = p['mapa_llegadas']  # Estructuras de datos pre-calculadas

# --------------------------------------------------
# VARIABLES
# --------------------------------------------------

# Viajes con cliente
y = m.addVars(N, N, T, A, vtype=GRB.BINARY, name="y")

# Reubicación normal (para demanda) -> CON costo
z_dem = m.addVars(N, N, T, A, vtype=GRB.BINARY, name="z_dem")

# Reubicación para ir a cargar -> SIN costo
z_carga = m.addVars(N, N, T, A, vtype=GRB.BINARY, name="z_carga")

# Espera
esp = m.addVars(N, T, A, vtype=GRB.BINARY, name="esp")

# Inicio de carga
ch = m.addVars(N, T, A, vtype=GRB.BINARY, name="ch")

# Demanda no servida
s = m.addVars(N, N, T, vtype=GRB.INTEGER, name="s")

# Posición de los autos
pos = m.addVars(N, T, A, vtype=GRB.BINARY, name="pos")

# Batería
carga = m.addVars(T+1, A, vtype=GRB.CONTINUOUS, lb=0, ub=p['Cargamax'], name="carga")

# 1 si el vehículo termina carga al inicio del periodo t
finCarga = m.addVars(T+1, A, vtype=GRB.BINARY, name="finCarga")

# 1 si el vehículo tiene batería "alta" (>= umbral) en t, es para identificar los autos 
# con baja bateria (bHigh=0) para mandarlos a cargar
bHigh = m.addVars(T, A, vtype=GRB.BINARY, name="bHigh")

# --------------------------------------------------
# FUNCIÓN OBJETIVO
# --------------------------------------------------

m.setObjective(
    # Ingresos por viajes con cliente
    quicksum(
        y[i, j, t, a] * p['Pviaje'][i][j][t]
        for i in range(N)
        for j in range(N)
        for a in range(A)
        for t in range(T)
    )
    # Costo por reubicación normal (z_dem)
    - quicksum(
        z_dem[i, j, t, a] * p['Creub'][i][j][t]
        for i in range(N)
        for j in range(N)
        for a in range(A)
        for t in range(T)
    )
    # Penalización por demanda no servida
    - quicksum(
        s[i, j, t] * 0.5
        for i in range(N)
        for j in range(N)
        for t in range(T)
    ),
    GRB.MAXIMIZE
)

# -------------------------
# RESTRICCIONES
# -------------------------

# 1) Vehículo inicia en un nodo (posición inicial)
for a in range(A):
    m.addConstr(quicksum(pos[i, 0, a] for i in range(N)) == 1)

# 2) Carga inicial al máximo
for a in range(A):
    m.addConstr(carga[0, a] == p['Cargamax'])

# 3) Satisfacer la demanda (viajes atendidos + no atendidos = Demanda)
for i in range(N):
    for t in range(T):
        for j in range(N):
            m.addConstr(
                quicksum(y[i, j, t, a] for a in range(A)) + s[i, j, t] == p['Dem'][i, j, t]
            )

# 4) Un auto solo puede hacer una acción por periodo
for t in range(T):
    for a in range(A):
        m.addConstr(
            quicksum(pos[i, t, a] for i in range(N)) <= 1
        )

# 5) Relación acciones - posición: si hace algo, debe estar en algún nodo
for t in range(T):
    for a in range(A):
        m.addConstr(
            quicksum(
                y[i, j, t, a] +
                z_dem[i, j, t, a] +
                z_carga[i, j, t, a]
                for i in range(N) for j in range(N)
            )
            + quicksum(esp[i, t, a] + ch[i, t, a] for i in range(N))
            == quicksum(pos[i, t, a] for i in range(N))
        )

# 6) Las acciones solo se pueden hacer si el auto está posicionado en ese nodo
for t in range(T):
    for a in range(A):
        for i in range(N):
            # Viajes con cliente desde i
            m.addConstr(
                quicksum(y[i, j, t, a] for j in range(N)) <= pos[i, t, a]
            )
            # Reubicación normal desde i
            m.addConstr(
                quicksum(z_dem[i, j, t, a] for j in range(N)) <= pos[i, t, a]
            )
            # Reubicación para carga desde i
            m.addConstr(
                quicksum(z_carga[i, j, t, a] for j in range(N)) <= pos[i, t, a]
            )
            # Espera en i
            m.addConstr(esp[i, t, a] <= pos[i, t, a])
            # Inicio de carga en i
            m.addConstr(ch[i, t, a] <= pos[i, t, a])

# -------------------------
# 7) Balance de flujo de posición (pos)
# -------------------------

for a in range(A):
    for i in range(N):
        for t in range(T - 1):
            k_llegada = t + 1

            # Salidas desde i en t
            salidas_svc = quicksum(y[i, j, t, a] for j in range(N) if i != j)
            salidas_reb = quicksum(
                z_dem[i, j, t, a] + z_carga[i, j, t, a]
                for j in range(N) if i != j
            )
            salida_chg = ch[i, t, a]

            # Llegadas a i en k_llegada = t+1

            # Llegadas por viajes con cliente
            llegv = LinExpr()
            for j in range(N):
                if i == j:
                    continue
                clave_viaje = (j, i, k_llegada)
                lista_k_inicio = mapa_llegadas_viaje.get(clave_viaje, [])
                if lista_k_inicio:
                    llegv.add(
                        quicksum(
                            y[j, i, k_start, a]
                            for k_start in lista_k_inicio
                        )
                    )

            # Llegadas por reubicación (normal + para carga)
            llegr = LinExpr()
            for j in range(N):
                if i == j:
                    continue
                clave_viaje = (j, i, k_llegada)
                lista_k_inicio = mapa_llegadas_viaje.get(clave_viaje, [])
                if lista_k_inicio:
                    llegr.add(
                        quicksum(
                            z_dem[j, i, k_start, a] + z_carga[j, i, k_start, a]
                            for k_start in lista_k_inicio
                        )
                    )

            # Llegadas por fin de carga
            llegc = LinExpr()
            k_inicio_carga = k_llegada - Tchg
            if k_inicio_carga >= 0 and i in p['E']:
                llegc = ch[i, k_inicio_carga, a]

            m.addConstr(
                pos[i, k_llegada, a]
                == pos[i, t, a]
                - salidas_svc
                - salidas_reb
                - salida_chg
                + llegv
                + llegr
                + llegc
            )

# -------------------------
# 8) Evolución de la carga (C5) - Big-M
# -------------------------

print("Construyendo restricción de evolución de carga (C5) - Big-M...")

M_GRANDE = p['Cargamax'] + 1.0

for a in range(A):
    for t in range(T):

        # Gasto de batería por viajes y reubicaciones en t
        gasto_viaje_t = LinExpr()
        for i in range(N):
            for j in range(N):
                if i == j:
                    continue
                gasto_viaje_t.add(
                    (y[i, j, t, a]
                     + z_dem[i, j, t, a]
                     + z_carga[i, j, t, a]) * p['d'][i, j]
                )

        ecuacion_base = carga[t, a] - gasto_viaje_t

        k_llegada = t + 1
        k_inicio_carga = k_llegada - Tchg

        if k_inicio_carga >= 0:
            m.addConstr(
                finCarga[k_llegada, a] ==
                quicksum(ch[i, k_inicio_carga, a] for i in p['E'])
            )
        else:
            m.addConstr(finCarga[k_llegada, a] == 0)

        # Si NO termina carga: carga[t+1] = ecuacion_base
        m.addConstr(
            carga[t+1, a] <= ecuacion_base + M_GRANDE * finCarga[k_llegada, a],
            name=f"EvolCarga_Techo_{a}_{t}"
        )
        m.addConstr(
            carga[t+1, a] >= ecuacion_base - M_GRANDE * finCarga[k_llegada, a],
            name=f"EvolCarga_Piso_{a}_{t}"
        )

        # Si SÍ termina carga: carga[t+1] = Cargamax
        m.addConstr(
            carga[t+1, a] <= p['Cargamax'] + M_GRANDE * (1 - finCarga[k_llegada, a]),
            name=f"EvolCarga_ResetTecho_{a}_{t}"
        )
        m.addConstr(
            carga[t+1, a] >= p['Cargamax'] - M_GRANDE * (1 - finCarga[k_llegada, a]),
            name=f"EvolCarga_ResetPiso_{a}_{t}"
        )

print("Restricción de evolución de carga completada.")

# -------------------------
# 9) Restricciones de carga: ch solo en estaciones, capacidad estaciones
# -------------------------

zonas_todas = range(N)
zonas_sin_estacion = [i for i in zonas_todas if i not in p['E']]

# ch solo en estaciones
for i in zonas_sin_estacion:
    for t in range(T):
        for a in range(A):
            ch[i, t, a].UB = 0

# Capacidad de estaciones
for i in p['E']:
    for t in range(T):
        inicio_ventana = max(0, t - Tchg + 1)
        autos_cargando = quicksum(
            ch[i, t_prima, a]
            for a in range(A)
            for t_prima in range(inicio_ventana, t + 1)
        )
        m.addConstr(autos_cargando <= p['CapEstacion'])

# -------------------------
# 10) Restricciones de energía para viajes y reubicaciones
# -------------------------

# Viajes con cliente: requieren distancia + reserva (6 km)
m.addConstrs(
    (carga[t, a] >= (p['d'][i, j] + 6) * y[i, j, t, a]
     for t in range(T)
     for a in range(A)
     for i in range(N)
     for j in range(N) if i != j),
)

# Reubicaciones (normal + para carga): solo requieren distancia
m.addConstrs(
    (carga[t, a] >= (p['d'][i, j] + 6) * z_dem[i, j, t, a]
     for t in range(T)
     for a in range(A)
     for i in range(N)
     for j in range(N) if i != j),
)

m.addConstrs(
    (carga[t, a] >= p['d'][i, j] * z_carga[i, j, t, a]
     for t in range(T)
     for a in range(A)
     for i in range(N)
     for j in range(N) if i != j),
)

# -------------------------
# 11) Batería alta / baja (bHigh) y lógica de acciones
# -------------------------

M = p['Cargamax']  # 350 aprox
UMBRAL_ALTA = 10   # puedes cambiar este a otro valor si quieres

# Relación carga - bHigh: si bHigh = 1 => carga >= UMBRAL_ALTA
for t in range(T):
    for a in range(A):
        m.addConstr(
            carga[t, a] >= UMBRAL_ALTA - M * (1 - bHigh[t, a])
        )
        #m.addConstr(
            #carga[t, a] <= (UMBRAL_ALTA - 1) + M * bHigh[t, a]
        #)
# Con batería baja (bHigh = 0):
#  - no puede hacer viajes con cliente
#  - no puede esperar
#  - no puede usar reubicación normal (z_dem)
#  - reubicación para carga (z_carga) solo cuando bHigh = 0

for t in range(T):
    for a in range(A):
        # Viajes con cliente solo si bHigh = 1
        m.addConstr(
            quicksum(
                y[i, j, t, a] for i in range(N) for j in range(N) if i != j
            ) <= bHigh[t, a]
        )
        # Espera solo si bHigh = 1
        m.addConstr(
            quicksum(esp[i, t, a] for i in range(N)) <= bHigh[t, a]
        )
        # Reubicación normal (con costo) solo si bHigh = 1
        m.addConstr(
            quicksum(
                z_dem[i, j, t, a] for i in range(N) for j in range(N) if i != j
            ) <= bHigh[t, a]
        )
        # Reubicación para carga solo si bHigh = 0
        m.addConstr(
            quicksum(
                z_carga[i, j, t, a] for i in range(N) for j in range(N) if i != j
            ) <= 1 - bHigh[t, a]
        )

# Reubicación para carga: solo puede ir a nodos que son estaciones
# (destino j debe estar en p['E'])
destinos_sin_estacion = [j for j in range(N) if j not in p['E']]
for i in range(N):
    for j in destinos_sin_estacion:
        for t in range(T):
            for a in range(A):
                z_carga[i, j, t, a].UB = 0

# -------------------------
# OPTIMIZAR
# -------------------------
m.optimize()




















# -------------------------
# 7. ANÁLISIS DE RESULTADOS (VERSIÓN DETALLADA)
# -------------------------
ZONAS_MANHATTAN = [
    4, 12, 13, 24, 41, 42, 43, 45, 48, 50, 68, 74, 75, 79, 87, 88, 90, 100, 
    103, 107, 113, 114, 116, 120, 125, 127, 128, 137, 140, 141, 142, 143, 144, 
    148, 151, 152, 153, 158, 161, 162, 163, 164, 166, 170, 186, 194, 202, 209, 
    211, 224, 229, 230, 231, 232, 233, 234, 236, 237, 238, 239, 243, 244, 246, 
    249, 261, 262, 263
]
ZONAS_EQUIVALENTES = {104: 103, 105: 103}
def normalizar_zona(zona_id):
    return ZONAS_EQUIVALENTES.get(zona_id, zona_id)
INDICE_A_ZONA = {i: zona for i, zona in enumerate(ZONAS_MANHATTAN)}
print("\n--- ANÁLISIS DE LA SOLUCIÓN ÓPTIMA ---")
print(f"Ganancia Neta Óptima: ${m.objVal:.2f}")

# Helper para mapear índice de nodo -> id de zona real
def idx_to_zona(idx):
    try:
        return INDICE_A_ZONA.get(idx, idx)
    except NameError:
        # Por si no está definido el diccionario, devolvemos el índice tal cual
        return idx

try:
    # 0) Batería por auto y período
    print("\n--- Batería por auto y período ---")
    for a in range(A):
        print(f"Auto {a}:")
        for t in range(T):
            soc = carga[t, a].X
            print(f"  t={t}: {soc:.1f} km")
    
    # 1) Línea de tiempo por auto (posición + acción + batería)
    print("\n--- Línea de tiempo por auto ---")
    for a in range(A):
        print(f"\n================  Auto {a}  ================")
        for t in range(T):
            # Posición del auto en t
            pos_idx = None
            for i in range(N):
                if pos[i, t, a].X > 0.5:
                    pos_idx = i
                    break
            if pos_idx is not None:
                zona_pos = idx_to_zona(pos_idx)
                pos_str = f"zona {zona_pos} (índice {pos_idx})"
            else:
                pos_str = "sin posición (pos ~ 0 en todos los nodos)"
            
            soc = carga[t, a].X
            
            # Detectar acción principal (solo una por período por las restricciones)
            accion = "NINGUNA"
            detalle = ""
            
            # 1) Viaje con cliente
            encontrado = False
            for i in range(N):
                for j in range(N):
                    if i == j:
                        continue
                    if y[i, j, t, a].X > 0.5:
                        accion = "SERVICIO"
                        zona_i = idx_to_zona(i)
                        zona_j = idx_to_zona(j)
                        ingreso = p['Pviaje'][i, j, t]
                        detalle = (
                            f"{zona_i}->{zona_j} (i={i}, j={j}, "
                            f"Ingreso=${ingreso:.2f})"
                        )
                        encontrado = True
                        break
                if encontrado:
                    break
            
            # 2) Reubicación normal
            if not encontrado:
                for i in range(N):
                    for j in range(N):
                        if i == j:
                            continue
                        if z_dem[i, j, t, a].X > 0.5:
                            accion = "REUBICACIÓN DEMANDA"
                            zona_i = idx_to_zona(i)
                            zona_j = idx_to_zona(j)
                            costo = p['Creub'][i, j, t]
                            detalle = (
                                f"{zona_i}->{zona_j} (i={i}, j={j}, "
                                f"Costo=${costo:.2f})"
                            )
                            encontrado = True
                            break
                    if encontrado:
                        break
            
            # 3) Reubicación para carga
            if not encontrado:
                for i in range(N):
                    for j in range(N):
                        if i == j:
                            continue
                        if z_carga[i, j, t, a].X > 0.5:
                            accion = "REUBICACIÓN PARA CARGA"
                            zona_i = idx_to_zona(i)
                            zona_j = idx_to_zona(j)
                            detalle = f"{zona_i}->{zona_j} (i={i}, j={j})"
                            encontrado = True
                            break
                    if encontrado:
                        break
            
            # 4) Espera
            if not encontrado:
                for i in range(N):
                    if esp[i, t, a].X > 0.5:
                        accion = "ESPERA"
                        zona_i = idx_to_zona(i)
                        detalle = f"en zona {zona_i} (i={i})"
                        encontrado = True
                        break
            
            # 5) Inicio de carga
            if not encontrado:
                for i in p['E']:
                    if ch[i, t, a].X > 0.5:
                        accion = "INICIO CARGA"
                        zona_i = idx_to_zona(i)
                        detalle = f"en estación {zona_i} (i={i})"
                        encontrado = True
                        break
            
            # 6) Nada (posible si no hay acción en ese período)
            # accion ya queda como "NINGUNA" si no encontró nada
            
            print(
                f"  t={t}: pos={pos_str}, batería={soc:.1f} km, "
                f"acción={accion} {detalle}"
            )

    # 2) Viajes de servicio (resumen "clásico")
    print("\n--- Viajes de Servicio (y) ---")
    viajes_hechos = 0
    for t in range(T):
        for a in range(A):
            for i in range(N):
                for j in range(N):
                    if i == j:
                        continue
                    if y[i, j, t, a].X > 0.5:
                        zona_i = idx_to_zona(i)
                        zona_j = idx_to_zona(j)
                        ingreso = p['Pviaje'][i, j, t]
                        soc_ini = carga[t, a].X
                        print(
                            f"  Auto {a} en t={t}: {zona_i} (i={i}) -> {zona_j} (j={j}) "
                            f"(Ingreso: ${ingreso:.2f}, batería inicio: {soc_ini:.1f} km)"
                        )
                        viajes_hechos += 1
    if viajes_hechos == 0:
        print("  No se realizó ningún viaje de servicio.")

    # 3) Reubicaciones normales (z_dem)
    print("\n--- Reubicaciones normales (z_dem, CON costo) ---")
    reubicaciones_dem = 0
    for t in range(T):
        for a in range(A):
            for i in range(N):
                for j in range(N):
                    if i == j:
                        continue
                    if z_dem[i, j, t, a].X > 0.5:
                        zona_i = idx_to_zona(i)
                        zona_j = idx_to_zona(j)
                        costo = p['Creub'][i, j, t]
                        soc_ini = carga[t, a].X
                        print(
                            f"  Auto {a} en t={t}: {zona_i} (i={i}) -> {zona_j} (j={j}) "
                            f"(Costo: ${costo:.2f}, batería inicio: {soc_ini:.1f} km)"
                        )
                        reubicaciones_dem += 1
    if reubicaciones_dem == 0:
        print("  No se realizó ninguna reubicación normal.")

    # 4) Reubicaciones para carga (z_carga)
    print("\n--- Reubicaciones para CARGA (z_carga, SIN costo FO) ---")
    reubicaciones_carga = 0
    for t in range(T):
        for a in range(A):
            for i in range(N):
                for j in range(N):
                    if i == j:
                        continue
                    if z_carga[i, j, t, a].X > 0.5:
                        zona_i = idx_to_zona(i)
                        zona_j = idx_to_zona(j)
                        soc_ini = carga[t, a].X
                        print(
                            f"  Auto {a} en t={t}: {zona_i} (i={i}) -> {zona_j} (j={j}) "
                            f"(batería inicio: {soc_ini:.1f} km)"
                        )
                        reubicaciones_carga += 1
    if reubicaciones_carga == 0:
        print("  No se realizó ninguna reubicación para carga.")

    # 5) Inicios de carga
    print("\n--- Inicios de Carga (ch) ---")
    cargas_iniciadas = 0
    for t in range(T):
        for a in range(A):
            for i in p['E']:
                if ch[i, t, a].X > 0.5:
                    zona_i = idx_to_zona(i)
                    soc_ini = carga[t, a].X
                    print(
                        f"  Auto {a} en t={t}: INICIÓ CARGA en estación {zona_i} (i={i}), "
                        f"batería inicio: {soc_ini:.1f} km"
                    )
                    cargas_iniciadas += 1
    if cargas_iniciadas == 0:
        print("  No se inició ninguna carga.")

    # 6) Esperas
    print("\n--- Esperas (esp) ---")
    esperas_hechas = 0
    for t in range(T):
        for a in range(A):
            for i in range(N):
                if esp[i, t, a].X > 0.5:
                    zona_i = idx_to_zona(i)
                    soc_ini = carga[t, a].X
                    print(
                        f"  Auto {a} en t={t}: ESPERA en zona {zona_i} (i={i}), "
                        f"batería inicio: {soc_ini:.1f} km"
                    )
                    esperas_hechas += 1
    print(f"  Hubo un total de {esperas_hechas} decisiones de 'esperar'.")

    # 7) Demanda no servida
    print("\n--- Demanda No Servida (s) ---")
    total_no_servida = 0
    for t in range(T):
        for i in range(N):
            for j in range(N):
                if i == j:
                    continue
                val = s[i, j, t].X
                cant = int(round(val))
                if cant > 0:
                    zona_i = idx_to_zona(i)
                    zona_j = idx_to_zona(j)
                    dem_total = p['Dem'][i, j, t]
                    print(
                        f"  t={t}, de zona {zona_i} (i={i}) a zona {zona_j} (j={j}): "
                        f"{cant} viajes no servidos "
                        f"(Demanda total: {dem_total})"
                    )
                    total_no_servida += cant
    print(f"  Total de viajes no servidos: {total_no_servida}")

    # 8) Estado final de batería (tal como está modelado)
    print("\n--- Estado Final de Batería (al inicio de t = T-1) ---")
    for a in range(A):
        print(f"  Auto {a}: {carga[T, a].X:.1f} km")

except Exception as e:
    print(f"\nError al analizar variables (¿quizás el modelo fue infactible?): {e}")