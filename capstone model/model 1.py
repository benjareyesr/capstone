from gurobipy import Model, GRB, quicksum
m = Model("modelo V1")

# -------------------------
# PARÁMETROS
# -------------------------

import parametros as p  

# -------------------------
# VARIABLES
# -------------------------


y = m.addVars(p.N, p.N, p.T+p.tmax, p.A, vtype=GRB.BINARY, name="y") # el auto A viaja de i a j el inicio del tiempo t
x = m.addVars(p.N, p.N, p.T+p.tmax, p.A, vtype=GRB.BINARY, name="x") # el auto A viaja de i a j al inicio del tiempo t
pos = m.addVars(p.N, p.T, p.A, vtype=GRB.BINARY, name="y") # el auto A se encuentra en la posicion i al inicio del periodo t




# -------------------------
# FUNCIÓN OBJETIVO
# -------------------------

m.setObjective(quicksum(y[i,j,t,a]*p.Pviaje[i][j][t]
                        for i in range(p.N) 
                        for j in range(p.N)
                        for a in range(p.A) 
                        for t in range(p.T) ) - quicksum(x[i,j,t,a]*p.Creub[i][j][t]
                                                         for i in range(p.N) 
                                                         for j in range(p.N) 
                                                         for a in range(p.A)
                                                         for t in range(p.T)), GRB.MAXIMIZE)

# -------------------------
# RESTRICCIONES
# -------------------------
# 

# satisfacer la demanda

for i in range(p.N):
    for t in range(p.T):
        for j in range(p.N):
            m.addConstr(quicksum(y[i,j,t,a] 
                                 for a in range(p.A)) ==(p.Dem[i][j][t]))
        
# un auto solo puede viajar a un lugar a la vez

for a in range(p.A):
    for t in range(p.T):
        m.addConstr(quicksum(y[i,j,t,a] 
                             for i in range(p.N)
                             for j in range(p.N))<=1)

for a in range(p.A):
    for i in range(p.N):
        for j in range(p.N):
            for t in range(p.T):
                    1+(1-y[i,j,t,a])*100000>=quicksum(y[o,k,t+ti,a] 
                                                      for ti in range(p.Tbtw[i][j])
                                                      for k in range(p.N)
                                                      for o in range (p.N))


# si un auto está en un lugar su siguiente viaje emieza en el mismo lugar
####### revisar ######## no puede salir ningun auto porque las posiciones iniciales no cuantan como un ingreso



for a in range(p.A):
    for t in range(p.T):
        for j in range(p.N):
            m.addConstr(quicksum(y[i,j,ti+1,a] 
                                for ti in range(t)
                                for i in range(p.N))>=quicksum(y[j,k,ti+1,a]
                                                               for ti in range(t+1)
                                                               for k in range(p.N)))
            
for a in range(p.A):
    for t in range(p.T):
        for j in range(p.N):
            m.addConstr(quicksum(y[i,j,ti+1,a] 
                                 for ti in range(t)
                                 for i in range(p.N))<=quicksum(y[j,k,ti+1,a]
                                                                for ti in range(t)
                                                                for k in range(p.N))+1)

# un auto debe cargarse antes de quedarse sin bateria

# 

# 

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
        for j in range(p.N):
            for t in range(p.T):
                for a in range(p.A):
                    print(f"y[{i,j,t,a}] = {y[i,j,t,a].x}")
