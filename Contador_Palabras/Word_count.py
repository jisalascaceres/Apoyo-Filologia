
import pandas as pd
import numpy as np
import sys
import random
import pypdf
from tqdm import tqdm
import os
import time
import Levenshtein
from nltk.tokenize import word_tokenize
import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader
from Utils import *
import nltk
nltk.download('punkt_tab')
def Perform_word_count(path_pdf, path_csv, start_page = 1, end_page = -1, max_distance = 2, path_output= None, formato = '.csv',
                       language = 'spa',Aplicar_OCR = True,save_text = False,Aplicar_Conteo=True,Buscar_substrings = False):
    

    # print ('---------------------------------------------------')

    print ('Iniciando análisis de texto...')
    # print ('Parámetros:')
    print ('PDF: ', path_pdf)
    print ('Archivo de entrada: ', path_csv)
    # print ('Página inicial: ', start_page)
    # print ('Página final: ', end_page)
    # print ('Distancia máxima: ', max_distance)
    # print ('Devolver coincidencias: ', return_coincidences)
    # print ('Archivo de salida: ', path_output)
    # print ('Formato de archivo de salida: ', formato)
    # print ('Aplicar_OCR:,Aplicar_OCR)
    

    # print ('---------------------------------------------------')

    # ------------------ Control de los parametros de entrada ------------------

    if start_page < 1:
        print ('La página inicial debe ser mayor que 0, se establece el parámetro a 1.')
        start_page = 1

    if max_distance <= 0:
        print ('La distancia máxima se ha puesto en 0 o menor. Solo se devolveran coincidencias exactas.')
        max_distance = 0

    if path_output != None:
        if formato not in ['.csv','.xlsx','.txt']:
            print ('El formato de archivo de salida no es válido, se establece el formato a .xlsx por defecto')
            formato = '.xlsx'

    assert end_page >= start_page or end_page == -1, "La página final debe ser mayor o igual que la inicial, puede insertar -1 para indicar que es la última página del documento."
    assert os.path.exists(path_pdf), "El archivo de entrada no se ha encontrado."
    assert path_pdf.endswith('.pdf'), "El archivo de entrada debe ser un pdf."
    assert isinstance(start_page,int) and isinstance(max_distance,int), 'Revisa los parametros de página de inicio y distancia'
    assert Aplicar_OCR == True or Aplicar_OCR == False, 'El parámetro Aplicar_OCR debe ser True o False' 
    assert save_text == True or save_text == False, 'El parámetro save_text debe ser True o False'
    assert Aplicar_Conteo == True or Aplicar_Conteo == False, 'El parámetro Aplicar_Conteo debe ser True o False'
    assert Buscar_substrings == True or Buscar_substrings == False, 'El parámetro Buscar_substrings debe ser True o False'
    
    if Aplicar_Conteo:
        assert os.path.exists(path_csv), "El archivo de entrada no se ha encontrado."
    # Calculamos el número de páginas del PDF y asignamos el valor de la última página a este si es necesario.
    with open(path_pdf, 'rb') as file:
        pdf_reader = PdfReader(file)
        num_pages = len(pdf_reader.pages)

    if end_page > num_pages or end_page == -1:
        print ('La página final debe ser menor que el número de páginas del pdf, que es {}, se establece el parámetro a este último.'.format(num_pages))
        end_page = num_pages

    print ('Número de páginas del PDF: ', num_pages)
    print ('Leyendo desde la página {} hasta la página {}'.format(start_page,end_page))

    # -------------- Extracción de las imágenes del PDF y aplicación del OCR ----------------------------------------

    # Caso 1. Hay que aplicar OCR al PDF porque este no viene digitalizado
    if Aplicar_OCR:

      print ('Convirtiendo el PDF a Imágenes para aplicar el OCR.')
      try:
          images = convert_from_path(path_pdf, size = 800, first_page = start_page, last_page=end_page,poppler_path='/usr/bin')
      except Exception as e:
          #print the error
          print (e)
          print ('Error al extraer las hojas del PDF.')
          return 1
          #raise ValueError("Error al extraer las imágenes del PDF.")

      
      images = preprocess_images(images)
      text = ''

      print ('Digitalizando el texto...')
      print ('Esto puede tardar unos minutos, por favor, espere.')
      page_counter = start_page
      book = []
      #print ('tesseract path: ', tesseract_path)
      for image in tqdm(images):
          try:
              text = perform_ocr(image,language=language)
          except Exception as e:
              #print the error
              print (e)
              print ('Error al realizar OCR.')
              return 1
              #raise ValueError("Error al realizar OCR.")
          book.append([page_counter,text])
          page_counter += 1

    # Caso 2. No hay que aplicar OCR al PDF. El texto ya viene digitalizado.
    elif not Aplicar_OCR:
      print ('Leyendo el PDF sin aplicar OCR.')
      book = []
      page_counter = start_page

      with open(path_pdf, 'rb') as file:
          pdf_reader = PdfReader(file)
          for page in tqdm(pdf_reader.pages):
              text = page.extract_text()
              book.append([page_counter,text])
              page_counter += 1

    if save_text:
      print ('Guardando el texto digitalizado...')

      save_text_as_pdf(book, output_filename="output.pdf")

  # ---------------------- Búsqueda de palabras en el texto extraído --------------------------------------

        # Si no se quiere aplicar Conteo, es decir, que solo se quiere realizar el OCR al PDF. Terminamos aqui
    if not Aplicar_Conteo:
      print('Fin de la ejecución, Usted programó que no hubiera conteo de palabras.')
      return 0
    
    print('Buscando palabras...')
    # Leemos las palabras del archivo de entrada.
    try:
        df_words = read_words(path_csv)
    except:
        print ('Error al leer el archivo de entrada de palabras.')
        return 1
        #raise ValueError("Error al leer el archivo de entrada.")





    # Vamos a aplicar un post procesado al texto. Quitamos signos de puntuación, tildes, todo minuscula.  
    for i in range(len(book)):
          book[i][1] = PostProcess_text(book[i][1])

    # Creamos las columnas necesarias en el dataframe. Ahora mismo a parte de estas tiene una ['words'] y ['count']
    total_coincidences = []
    total_pages = []
    total_counter = []
    total_non_exact = []
    total_non_exact_pages = []
    
    # Iteramos en cada fila. Buscando cada palabra.
    print('Iterando por la lista de palabras. Buscandolas en el texto. Esto puede tardar.')
    for index, row in tqdm(df_words.iterrows()):

        # Guardaremos 5 parámetros. 
        # El contador que cuenta cuantas coincidencias exactas ha habido.
        # El lugar y la palabra que es una coincidencia exacta.
        # El lugar y la palabra que es una coincidencia no exacta.

        counter = 0
        coincidences = []
        page_numbers = []
        non_exact_coincidences = []
        pages_non_Exact = []
        
        palabra = row['words']
        # Iteramos por todo el libro, buscando la palabra en cuestión
        for idx,page in enumerate(book):
          
          # Las coincidencias exactas son aquelas con una distancia edit de 0
          count,coincidence = count_words_with_levenshtein(page[1],palabra,0,Buscar_substrings) # Esta función devuelve el número de coincidencias de este tipo y una lista con las coincidencias.
          # las no exactas son aquellas con una distancia menor a la máxima indicada
          _,non_exact_coincidence = count_words_with_levenshtein(page[1], palabra, max_distance,Buscar_substrings)

          # Actualizamos el contador
          counter += count
          coincidences.extend(coincidence)
          page_numbers.extend([page[0]]*len(coincidence)) # La página se pone tantas veces como coincidencias haya habido.
          non_exact_coincidences.extend(non_exact_coincidence)
          pages_non_Exact.extend([page[0]]*len(non_exact_coincidence))


        # Convertimos las listas en strings separadas por una coma. [hola,adios] --> "hola,adios"
        if len(coincidences) == 0:
          coincidences = ''
          page_numbers = ''
        else:
          coincidences = coincidences[0] # las coincidencias exactas son siempre iguales, es la propia palabra.
          page_numbers = set(page_numbers)
          page_numbers = [str(i) for i in page_numbers]
          page_numbers = ','.join(page_numbers) # No necesito en pagina leyó cada instancia en concreto, porque son todas iguales
                
        if len(non_exact_coincidences) == 0:
          non_exact_coincidences = ''
          pages_non_Exact = ''
        else:
          non_exact_coincidences = non_exact_coincidences
          pages_non_Exact = pages_non_Exact

        # Insertamos la información en el dataframe
        total_counter.append(counter)
        total_coincidences.append(coincidences)
        total_pages.append(page_numbers)
        total_non_exact.append(non_exact_coincidences)
        total_non_exact_pages.append(pages_non_Exact)
        
    # Ahora mismo tenemos un dataframe con toda la información.

    print ('Guardando resultados...')
    df_new = pd.DataFrame(columns = ['Palabra','Coincidencias exactas','Coincidencias no exactas'])

    # Vamos a iterar por el dataframe antiguo para insertar los datos en el nuevo ya procesados.
    for index, row in df_words.iterrows():
      # Cogemos toda la info esta palabra
        palabra = row['words']
        coincidencias_exactas = total_coincidences[index]
        pages = total_pages[index]
        non_exact = total_non_exact[index]
        non_exact_Page = total_non_exact_pages[index]
        non_exact_Coincidences = total_non_exact[index]
        counter = total_counter[index]

        if coincidencias_exactas != '':
          coincidencias_exactas = coincidencias_exactas + '(' + pages+ ')' + ' ['+ str(counter) + ']'

        coincidiencias_no_exactas = ''
      
        if non_exact_Coincidences != '':
          for coincidencia_no_Exacta,page_non in zip(non_exact_Coincidences,non_exact_Page):
              coincidiencias_no_exactas += coincidencia_no_Exacta + '(' + str(page_non) + '), '
          
          coincidiencias_no_exactas = coincidiencias_no_exactas[:-2]
            
        
        df_new.loc[index] =  [palabra,coincidencias_exactas,coincidiencias_no_exactas]
  

    # Si pusiste el formato en el path_salida quitalo

    if path_output != None:
        if '.' in path_output:
            path_output = path_output.split('.')[:-1]
            path_output = '.'.join(path_output)
            path_output = path_output
    else:
        path_output = 'output'

    #guardamos el archivo resultante en el formato deseado

    if formato == '.csv':
        df_new.to_csv(path_output + '.csv')

    if formato == '.xlsx':
        df_new.to_excel(path_output+'.xlsx')

    if formato == '.txt':
        df_new.to_csv(path_output+ '.txt',sep='\t')

    print ('Archivo guardado en: ', path_output + formato)