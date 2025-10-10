from gurobipy import Model, GRB, quicksum
m = Model("modelo V1")

# -------------------------
# PARÁMETROS
# -------------------------

import parametros as p  

# -------------------------
# VARIABLES
# -------------------------

y = m.addVars(p.N, p.N, p.T, p.A, vtype=GRB.BINARY, name="y") # el auto A viaja de i a j el inicio del tiempo t con un cliente
x = m.addVars(p.N, p.N, p.T, p.A, vtype=GRB.BINARY, name="x") # el auto a llega a j desde i al empezar el periodo t
z = m.addVars(p.N, p.N, p.T, p.A, vtype=GRB.BINARY, name="z") # el auto A viaja de i a j al inicio del tiempo t reub
s = m.addVars(p.N, p.N, p.T, vtype=GRB.INTEGER, name="s") # cantidad de viajes no atendidos de i a j en el tiempo t
pos = m.addVars(p.N, p.T, p.A, vtype=GRB.BINARY, name="pos") # 1 si el vehiculo a se encuentra disponivble en la ubicacion  i al inicio del periodo t
c = m.addVars(p.N, p.T, p.A, vtype=GRB.BINARY, name="c")# si el vehiculo a inicia una carga al inicio del periodo t en el lugar i
poschg = m.addVars(p.N, p.T, p.A, vtype=GRB.BINARY, name="poschg") # si el vehiculo a esta cargandose en el nodo i al inicio del periodo t
carga = m.addVars(p.T, p.A, vtype=GRB.INTEGER, name="carga")# carga de la bateria del auto a al inicio del periodo T
recarga = m.addVars(p.T, p.A, vtype=GRB.INTEGER, name="recarga")# cuanto recarga el auto a al inicio del periodo de tiempo t
ifrecarga = m.addVars(p.T, p.A, vtype=GRB.BINARY, name="ifrecarga")
# -------------------------
# FUNCIÓN OBJETIVO
# -------------------------

m.setObjective(quicksum(y[i,j,t,a]*p.Pviaje[i][j][t]
                        for i in range(p.N) 
                        for j in range(p.N)
                        for a in range(p.A) 
                        for t in range(p.Tr) ) - quicksum(z[i,j,t,a]*p.Creub[i][j][t]
                                                         for i in range(p.N) 
                                                         for j in range(p.N) 
                                                         for a in range(p.A)
                                                         for t in range(p.Tr)) - quicksum(s[i,j,t]*0.1
                                                                                         for i in range(p.N)
                                                                                         for j in range(p.N)
                                                                                         for t in range(p.Tr)) - quicksum(x[i,j,t,a]*0.00000001
                                                                                                                         for i in range(p.N)
                                                                                                                         for j in range(p.N)
                                                                                                                         for t in range(p.Tr)
                                                                                                                         for a in range(p.A)), GRB.MAXIMIZE)

# -------------------------
# RESTRICCIONES
# ------------------------- 

# satisfacer la demanda

for i in range(p.N):
    for t in range(p.Tr):
        for j in range(p.N):
            m.addConstr(quicksum(y[i,j,t,a] 
                                 for a in range(p.A))+s[i,j,t] == (p.Dem[i][j][t]))
        
# disponibilidad y balance

for i in range(p.N):
    for t in range(p.Tr):
        for a in range(p.A):
            m.addConstr(1 + quicksum(x[j,i,ti,a]
                                    for j in range(p.N)
                                    for ti in range(t))-quicksum(y[j,i,ti,a]+z[j,i,ti,a]
                                                                 for j in range(p.N)
                                                                 for ti in range(t))>=pos[i,t,a])
            
for j in range(p.N):
    for t in range(p.T-1):
        for a in range(p.A):
            for k in range(p.N):
                m.addConstr(quicksum(y[i,j,ti,a]+z[i,j,ti,a]
                                    for ti in range(t+1))+p.PosI[j][a]-quicksum(y[j,k,ti,a]+z[j,k,ti,a]
                                                                               for ti in range(t+1))<=1)
                
for j in range(p.N):
    for t in range(p.T-1):
        for a in range(p.A):
            for k in range(p.N):
                m.addConstr(quicksum(y[i,j,ti,a]+z[i,j,ti,a]
                                     for ti in range(t+1))+p.PosI[j][a]-quicksum(y[j,k,ti,a]+z[j,k,ti,a]
                                                                                for ti in range(t+1))>=0)
                
# no solapamiento

for t in range(p.T):
    for a in range(p.A):
        m.addConstr(quicksum(y[i,j,t,a]+z[i,j,t,a]
                    for i in range(p.N)
                    for j in range(p.N))<=1)

# tiempo de viaje

for a in range(p.A):
    for i in range(p.N):
        for j in range(p.N):
            for t in range(p.Tr):
                m.addConstr(1+(1-y[i,j,t,a]-z[i,j,t,a])*100000>=quicksum(y[o,k,t+ti,a]+z[o,k,t+ti,a] 
                                                      for ti in range(p.Tij[i][j][t])
                                                      for k in range(p.N)
                                                      for o in range (p.N)))
                    
for i in range(p.N):
    for j in range(p.N):
        for t in range(p.Tr):
            for a in range(p.A):
                m.addConstr(y[i,j,t,a]+z[i,j,t,a]<=x[i,j,t+p.Tij[i][j][t],a])
               

# necesidad de carga

for a in range(p.A):
    for t in range(p.T):
        m.addConstr(carga[t,a]==p.CargaI[a]-quicksum((y[i,j,ti,a]+z[i,j,ti,a])*p.Dij[i][j]
                                                    for i in range(p.N)
                                                    for j in range(p.N)
                                                    for ti in range(t))+quicksum(recarga[ti,a]
                                                                                 for a in range(p.A)
                                                                                 for ti in range(t)))
# solo se puede recargar en algunos nodos

for a in range(p.A):
    for t in range(p.T):
        for i in range(p.N):
            m.addConstr(pos[i,t,a]*p.posCh[i]*1000000000>=recarga[t,a])

for t in range(p.T):
    for a in range(p.A):
        m.addConstr(ifrecarga[t,a]*10000000000>=recarga[t,a])


for t in range(p.T):
    for a in range(p.A):
        m.addConstr(ifrecarga[t,a]<=recarga[t,a])

# tiempo de recarga
    for t in range(p.Tr):
        for a in range(p.A):
            m.addConstr(1+(1-ifrecarga[t,a])*100000>=quicksum(y[o,k,t+ti,a]+z[o,k,t+ti,a] 
                                                              for ti in range(p.Tchg)
                                                              for k in range(p.N)
                                                              for o in range (p.N)))

# -------------------------
# OPTIMIZAR
# -------------------------
m.optimize()

# -------------------------
# RESULTADOS
# -------------------------
if m.status == GRB.OPTIMAL:
    print(f"Valor óptimo = {m.objVal}")
    for i in range(p.N):
        for t in range(p.T):
            for a in range(p.A):
                print(f"pos[{i,t,a}] = {pos[i,t,a].x}")
