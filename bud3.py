# -*- coding: cp1250 -*-
#
# skrypt generalizacji kartograficznej budynków z wykorzystaniem przekątnych obiektu
#
#### UWAGI ####
#
# skrypt nie działa dla multipoligonów oraz niektórych poligonów z enklawami, wypisuje id pominiętych budynków dla których wsytąpił błąd
# parametry programu do podania:
#    tolerancja - tolerancja kątowa wykorzystywana przy czyszczeniu poligonu z punktow
#             k - ilosc odcinanych wierzcholkow w iteracji
#            k2 - docelowa ilosc wierzcholkow w wyniku
# id_field_name - nazwa pola z tabeli atrybutów z unikalnym ID 

import arcpy
from math import sqrt, atan, acos, cos, sin, pi

arcpy.env.overwriteOutput = True



#### FUNKCJE #####


            
### liczenie azymutu
def az(p,q):
    try:
        dy = q[1]-p[1]
        dx = q[0]-p[0]
        if dx == 0:
            czwartak = 0
            if dy>0:
                azymut=100
            if dy<0:
                azymut=300                
        else:
            czwartak=atan(float(abs(dy))/float(abs(dx)))
            czwartak=czwartak*200/math.pi
            if dx>0:
                if dy>0:
                    azymut = czwartak
                if dy<0:
                    azymut = 400 - czwartak
                if dy==0:
                    azymut = 0
            if dx<0:
                if dy>0:
                    azymut = 200 - czwartak
                if dy<0:
                    azymut = 200 + czwartak
                if dy==0:
                    azymut = 200
        return azymut
    except Exception, err:
        arcpy.AddError("blad azymut")
        arcpy.AddError(sys.exc_traceback.tb_lineno)
        arcpy.AddError(err.message)
    finally:
        del(dx,dy,czwartak)
        


### funkcja czytająca geometrię
def czytaj2(geometria):
    try:
        lista = []
        i = 0
        for part in geometria:
            for pnt in part:
                if pnt:
                    lista.append([pnt.X, pnt.Y])
        i += 1
        return lista
    finally:
        del(i, part, pnt, geometria, lista)



### funkcja licząca kąt między azymutami
def angle(az1,az2):
    angle = az2 - az1
    return(angle)



### funkcja czyszcząca budynek z punktów z zadaną tolerancją kątów (zmienna 'tolerancja' globalna)
### input - lista w postaci [ [X1,Y1] , [X2,Y2], ... , [X1,Y1] ]
### output - wyczyszczona lista w takiej samej postaci
def clear_list(lista1):
    do_wywalenia = []
    for i1 in range(len(lista1)):
        
        poprzedni = i1-1
        nastepny = i1+1
        
        if poprzedni == -1:
            poprzedni = len(lista1)-2

        if nastepny > len(lista1)-1:
            nastepny = 1
            
        angle1=abs(angle(az(lista1[i1],lista1[poprzedni]),az(lista1[i1],lista1[nastepny])))
        
        if (angle1>(200-tolerancja) and angle1<(200+tolerancja)):
            do_wywalenia.append(i1)

    if len(do_wywalenia) == 0:
        return(lista1)
    else:   
        do_wywalenia.reverse()
           
        for index in do_wywalenia:
            lista1.pop(index)

        if do_wywalenia[-1] == 0: lista1.append(lista1[0])

        return(lista1)



### funkcja licząca odległość między punktami
### input - lista w postaci [ [X1,Y1] , [X2,Y2] ]
### output - odległość
def length(a,b):
    length = sqrt((a[1]-b[1])**2+(a[0]-b[0])**2)
    return(length)



### funkcja licząca ilość obiektów na liście między zadanymi indeksami
### input - długość listy , index startowy , index końcowy
### output - liczba
def compute_range(length_of_list,x1,x2):
    if x2 - x1 < 0:
        output_range = length_of_list - x1 - 1 + x2
    else:
        output_range = x2 - x1 - 1
    return(output_range)



### funkcja do budowania listy przekatnych
### input - lista w postaci [ [X1,Y1] , [X2,Y2], ... , [X1,Y1] ]
### output - lista przekątnych w postaci [ [ długość przekątnej , index punktu startowego , index punktu końcowego ] , ... ]
def create_lista_przek(lista1):
    poligon = create_arcpy_polygon(lista1)
    length1 = len(lista1)-1
    lista_przekatnych = []
    for i1 in range(len(lista1)-1):
        for i2 in range(i1+2,len(lista1)-1):
            
            ### sprawdzanie warunku o ilosci odcinanych punktów
            ### musi odcinać DOKŁADNIE k (zdefiniowane w programie) punktów i przy tym musi zostać co namniej k2 (zdefiniowane w programie, u nas równe 4) punkty po potenjalnym odcięciu
            ### jeżeli żadna przekątna nie spełnia warunku to lista przekątnych jest pusta
            
            if (((compute_range(length1,i1,i2) == k) and ((length1 - compute_range(length1,i1,i2)) >= k2)) or ((compute_range(length1,i2,i1) == k) and ((length1 - compute_range(length1,i2,i1)) >= k2))):

                ### sprawdzenie czy przekatna nie przecina poligonu
                
                if not create_arcpy_line([lista1[i1],lista1[i2]]).crosses(poligon):
                    lista_przekatnych.append([length(lista1[i1],lista1[i2]),i1,i2])                
        #if i1 == 0: lista_przekatnych.pop(len(lista_przekatnych)-1)
    return(lista_przekatnych)



### funkcja do wyszukiwania najkrótszej wśród przekątnych
### input - lista przekątnych w postaci [ [ długość przekątnej , index punktu startowego , index punktu końcowego ] , ... ]
### output - przekątna w postaci [ długość przekątnej , index punktu startowego , index punktu końcowego ]
def search_min_przekatna(lista):
    minimum = lista
    for przekatna in lista:
        if przekatna[0] < minimum[0]:
            minimum = przekatna
            
    return(minimum)



### funkcja do szukania najmniejszej przekatnej i tworzenia obiektow: glownego i odciętego
### KORZYSTA Z: search_min_przekatna() , create_lista_przek()
### input - lista współrzędnych budynku w postaci [ [X1,Y1] , [X2,Y2], ... , [X1,Y1] ]
### output - listy obiektu głównego i odciętego w postaci [ [X1,Y1] , [X2,Y2], ... , [X1,Y1] ] oraz najkrószej przekątnej
def delete_points(lista):
    najkrotsza = search_min_przekatna(create_lista_przek(lista))
    object1 = range(najkrotsza[1],najkrotsza[2]+1)+[najkrotsza[1]]
    object1_1 = [lista[index] for index in object1]
    object2 = range(najkrotsza[2],len(lista)-1)+range(0,najkrotsza[1]+1)+[najkrotsza[2]]
    object2_2 = [lista[index] for index in object2]

    ### warunek o wybraniu obiektu do odciecia: odcinana jest część która ma mniejszą powierzchnię
    if create_arcpy_polygon(object2_2).area > create_arcpy_polygon(object1_1).area:
        odciete = object1_1
        glowny = object2_2
    else:
        odciete = object2_2
        glowny = object1_1
    return([glowny,odciete,najkrotsza])
        


### główna funkcja generalizująca
### na zmianę czyszczenie z punktów na liniach (z tolerancją) i usuwanie przekątnymi
### input - budynek w postaci [ [ [X1,Y1] , [X2,Y2], ... , [X1,Y1] ], ID ]
### output - zgeneralizowany budynek w postaci  [ [ [X1,Y1] , [X2,Y2], ... , [X1,Y1] ], ID ] , lista odciętych obiektów w postaci [ [ [ [X1,Y1] , [X2,Y2], ... , [X1,Y1] ] , ID_odcietego ], ID_budynku ]
def generalizacja(budynek):
    
    ID = budynek[1]
    budynek = budynek[0]
    w = len(budynek)-1

    # wyzerowanie (w zasadzie to wyjedynkowanie) licznika odciętych fragmentów
    nr_odcietego = 1

    # wyzerowanie listy odciętyc fragmentów 
    lista_odcietych = []
    
    # sprawdzenie czy lista przykątnych nie jest pusta
    if not len(create_lista_przek(budynek)) == 0:
        
        # pętla dopóki liczba wierzchołków w jest większa od liczby wierzchołków wynikowego obiektu (4)
        while w > k2:
            
            # czyszczenie budynku z punktów na odcinkach przy zadanej tolerancji
            budynek = clear_list(budynek)

            temp_budynek = budynek
            
            w = len(budynek)-1

            # ponowne (po wyczyszczeniu z niepotrzebnych punktów) sprawdzenie czy lista przekątnych nie jest pusta. Jeżeli jest pusta to break (przerwanie) pętli while dla budynku (brak możliwości dalszej generalizacji)
            if not len(create_lista_przek(budynek)) == 0:

                #sprawdzenie warunku 
                if w > k2:
                    
                        # wywołanie funkcji generalizującej
                        # budynek - zgeneralizowny budynek
                        # odcięty - kolejny odcięty fragment
                        # przekatna - przekątna po której odcięto fragment
                        budynek,odciety,przekatna = delete_points(budynek)[0],delete_points(budynek)[1],delete_points(budynek)[2]
                        
                        # sprawdzanie czy odcinany obiekt jest wewnatrz czy na zewnatrz poligonu
                        if create_arcpy_line([temp_budynek[przekatna[1]],temp_budynek[przekatna[2]]]).within(create_arcpy_polygon(temp_budynek)):    
                            odciety = [odciety,nr_odcietego,1]
                        else:
                            odciety = [odciety,nr_odcietego,0]

                        # dodanie odciętego fragmentu do listy odciętych fragmentów
                        lista_odcietych.append(odciety)
                        
                        #dodanie 1 do licznika odciętych fragmentów
                        nr_odcietego = nr_odcietego + 1
            else:
                break
            w = len(budynek)-1

    budynek = [budynek,ID]
    lista_odcietych = [lista_odcietych,ID]
    return(budynek,lista_odcietych)



#tworzenie obiektu arcpy.Polyline
def create_arcpy_line(line):
    arcpy_line = arcpy.Polyline(arcpy.Array([arcpy.Point(line[0][0],line[0][1]),arcpy.Point(line[1][0],line[1][1])]))
    return(arcpy_line)



#tworzenie obiektu arcpy.Polygon
def create_arcpy_polygon(polygon):
    arcpy_polygon = arcpy.Polygon(arcpy.Array([arcpy.Point(ppoint[0],ppoint[1]) for ppoint in polygon]))
    return(arcpy_polygon) 



    

######################## PARAMETRY PROGRAMU ########################



#w gradach
tolerancja = 10
#ilosc usunietych wierzcholkow
k=1
#ilosc punktow w wyniku:
k2=4
#nazwa pola z ID w wejsciowym pliku
id_field_name = 'OBJECTID'




######################## ŚCIEŻKA DO SHP ########################

budynki = r'C:\Users\kielbasi\Desktop\studia\SEMESTR9\PPGII\egzamin\Dane.shp'
output_path = r'C:\Users\kielbasi\Desktop\studia\SEMESTR9\PPGII\egzamin'

######################## ŚCIEŻKA DO SHP ########################

### czytanie geometrii
print('Czytam geometrię ...')
print(' ')
kursor_czytania = arcpy.da.SearchCursor(budynki, ['SHAPE@', id_field_name])
lista_budynkow = []
lista_odrzuconych = []
for row_czy in kursor_czytania:
    try:
        geometria = czytaj2(row_czy[0])
        lista2 = [geometria,row_czy[1]]
        lista_budynkow.append(lista2)
    except:
        lista_odrzuconych.append(row_czy[1])



### generalizacja

print('Generalizuję ...')
print(' ')
wynik_lista = []
wynik_lista_odcietych = []
for poligon in lista_budynkow:
    print('Dzialam dla budynku nr ' + str(poligon[1]))
    try:
        wynik_lista.append(generalizacja(poligon)[0])
        wynik_lista_odcietych.append(generalizacja(poligon)[1])
    except:
        lista_odrzuconych.append(poligon[1])

### tworzenie warstw wynikowych
print(' ')
print('Zapisuję pliki ...')
print(' ')
wynik_shp = arcpy.CreateFeatureclass_management(output_path,'wynik.shp','POLYGON',budynki)
wynik_shp_odciete = arcpy.CreateFeatureclass_management(output_path,'wynik_odciete.shp','POLYGON')
arcpy.AddField_management(wynik_shp_odciete,'id_budynku','SHORT')
arcpy.AddField_management(wynik_shp_odciete,'id_odciete','SHORT')
arcpy.AddField_management(wynik_shp_odciete,'In_Out','SHORT')


### pisanie geometrii i uzupełnianie tabeli atrybutów
with arcpy.da.InsertCursor(wynik_shp, ['SHAPE@', id_field_name]) as cursor:
    for poligon in wynik_lista:
        cursor.insertRow([poligon[0],poligon[1]])

with arcpy.da.InsertCursor(wynik_shp_odciete, ['SHAPE@', 'id_budynku', 'id_odciete','In_Out']) as cursor:
    for budynek in wynik_lista_odcietych:
        for odciety in budynek[0]:
            id_budynku = budynek[1]
            cursor.insertRow([odciety[0],id_budynku,odciety[1],odciety[2]])


### wypisanie id budynkow dla ktorych nie przeprowadzono generalizacji (wystapil błąd)
print('Lista id budynków odrzuconych na wskutek wystąpienia błędów: ' + str(lista_odrzuconych))

