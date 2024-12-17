
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

def Perform_word_count(path_pdf, path_csv, start_page = 1, end_page = -1, max_distance = 2, return_coincidences = True, path_output= None, formato = '.csv',
                       number_of_returns = 'Uno',folder = False,language = 'spa'):
    # Control de errores

    # print ('---------------------------------------------------')

    print ('Iniciando análisis de texto...')
    # print ('Parámetros:')
    print ('PDF: ', path_pdf)
    # print ('Archivo de entrada: ', path_csv)
    # print ('Página inicial: ', start_page)
    # print ('Página final: ', end_page)
    # print ('Distancia máxima: ', max_distance)
    # print ('Devolver coincidencias: ', return_coincidences)
    # print ('Archivo de salida: ', path_output)
    # print ('Formato de archivo de salida: ', formato)
    # print ('Número de retornos: ', number_of_returns)
    # print ('Modo folder?: ', folder)

    # print ('---------------------------------------------------')


    if start_page < 1:
        print ('La página inicial debe ser mayor que 0, se establece el parámetro a 1.')
        start_page = 1
    if end_page <= start_page and end_page != -1:
        print ('La página final debe ser mayor que la inicial, puede insertar -1 para indicar que es la última página del documento.')
        return 1
        #raise ValueError("La página final debe ser mayor que la inicial, puede insertar -1 para indicar que es la última página del documento.")
    if max_distance <= 0:
        print ('La distancia máxima debe ser mayor que 0.')
        return 1
        #raise ValueError("La distancia máxima debe ser mayor que 0.")
    if path_output != None:
        if formato not in ['.csv','.xlsx','.txt']:
            print ('El formato de archivo de salida no es válido, se establece el formato a .csv')
            formato = '.csv'

    # calculate the number of pages of the pdf
    with open(path_pdf, 'rb') as file:
        pdf_reader = PdfReader(file)
        num_pages = len(pdf_reader.pages)

    if end_page > num_pages or end_page == -1:
        print ('La página final debe ser menor que el número de páginas del pdf, que es {}, se establece el parámetro a este último.'.format(num_pages))
        end_page = num_pages

    print ('Número de páginas del PDF: ', num_pages)
    print ('Leyendo desde la página {} hasta la página {}'.format(start_page,end_page))
    #print ('Poppler path: ', poppler_path)
    # extract images from pdf

    try:
        images = convert_from_path(path_pdf, size = 800, first_page = start_page, last_page=end_page,poppler_path='/usr/bin')
    except Exception as e:
        #print the error
        print (e)
        print ('Error al extraer las imágenes del PDF.')
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

    print('Buscando palabras...')

    try:
        df_words = read_words(path_csv)
    except:
        print ('Error al leer el archivo de entrada de palabras.')
        return 1
        #raise ValueError("Error al leer el archivo de entrada.")

    for i in range(len(book)):
        book[i][1] = preprocess_text(book[i][1])


    if return_coincidences:
        df_words['coincidences'] = np.nan
        df_words['Page'] = np.nan

    for index, row in df_words.iterrows():
        if return_coincidences:
            counter = 0
            coincidences = []
            page_numbers = []
            for page in book:
                count,coincidence = count_words_with_levenshtein(page[1], row['words'], max_distance,return_coincidences)
                counter += count
                coincidences.extend(coincidence)
                page_numbers.extend([page[0]]*len(coincidence))


            coincidences = np.array(coincidences)
                # Convertir el array de coincidencias en un string
            coincidences = ','.join(coincidences)
                # return the page where the word was found
            page_numbers = np.array(page_numbers)
            page_numbers = page_numbers.astype(str)
            page_numbers = ','.join(page_numbers)

            df_words.loc[index, 'Page'] = page_numbers
            df_words.loc[index, 'count'] = counter
            df_words.loc[index, 'coincidences'] = coincidences

        else:

            for page in book:
                count = 0
                count = count_words_with_levenshtein(page[1], row['words'], max_distance,return_coincidences)
                count += count
            df_words.loc[index, 'count'] = count


    print ('Guardando resultados...')
    df_words = df_words.dropna()
    df_new = pd.DataFrame(columns = ['Palabra','Coincidencias exactas','Coincidencias no exactas'])
    for index, row in df_words.iterrows():
        non_exact = []
        coincidentes = row['coincidences']
        coincidentes = coincidentes.split(',')
        pages = row['Page']
        pages = pages.split(',')

        coincidencias = combinar_listas(coincidentes,pages)

        df_new.loc[index,'Palabra'] = row['words']

        for coincidencia in coincidencias:
            objetivo = df_words.loc[index, 'words']
            #print ('Objetivo:',objetivo)
            #print (coincidencias)

            palabra = coincidencia.split(' ')[0]
            if levenshtein_distance(palabra, objetivo) == 0:
                df_new.loc[index,'Coincidencias exactas'] = coincidencia

            else:
                non_exact.append(coincidencia)

        if number_of_returns == 'Todas':
            df_new.loc[index,'Coincidencias no exactas'] = non_exact
        elif number_of_returns == 'Uno':
            if len(non_exact) > 0:
                df_new.loc[index,'Coincidencias no exactas'] = random.choice(non_exact)
            else:
                df_new.loc[index,'Coincidencias no exactas'] = ''
        elif number_of_returns == 'Dos':
            if len(non_exact) > 0:
                if len(non_exact) < 2:
                    df_new.loc[index,'Coincidencias no exactas'] = non_exact
                else:
                    aux = []
                    aux.append(random.choice(non_exact))
                    aux.append(random.choice(non_exact))
                    df_new.loc[index,'Coincidencias no exactas'] = aux


            else:
                df_new.loc[index,'Coincidencias no exactas'] = ''

        else:
            # Else es Ninguno
            df_new.loc[index,'Coincidencias no exactas'] = ''




    # if you put the format also in the name of the file, delete it.add()

    if path_output != None:
        if '.' in path_output:
            path_output = path_output.split('.')[:-1]
            path_output = '.'.join(path_output)
            path_output = path_output
    else:
        path_output = 'output'

    # if we are perfoming the analysis for a folder, we add the name of the pdf to the output file, to avoid overwriting

    if folder:
        path_output = path_output+'_'+ path_pdf.split('\\')[-1].split('.')[0]

    # save the file in the desired format

    if formato == '.csv':
        df_new.to_csv(path_output + '.csv')

    if formato == '.xlsx':
        df_new.to_excel(path_output+'.xlsx')

    if formato == '.txt':
        df_new.to_csv(path_output+ '.txt',sep='\t')

    print ('Archivo guardado en: ', path_output + formato)
