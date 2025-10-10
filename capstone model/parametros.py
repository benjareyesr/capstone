N=2
A=10

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



Tr=3 # tiempo real
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
