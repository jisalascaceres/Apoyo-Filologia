import pandas as pd
import numpy as np  
from pdf2image import convert_from_path
import pytesseract
from nltk.tokenize import word_tokenize
import Levenshtein
import os
import cv2




def read_words(path):
    """
    Esta funcion lee las palabras que se encuentran en la primera hoja de un excel y crea un dataframe con ellas y el count a cero.
    """
    if path.endswith('.csv'):
        df = pd.read_csv(path,sep=',')
        words = df.values.tolist()
        words = [word[0] for word in words]
    elif path.endswith('.xlsx'):
        df = pd.read_excel(path, sheet_name = 0)
        words = df['Unnamed: 0'].tolist()
        #print(df)
    elif path.endswith('.txt'):
        with open(path, 'r') as file:
            words = file.readlines()
            # replace , and ; and . with \n
            words = [word.replace(',','\n').replace(';','\n').replace('.','\n') for word in words]
            # split by \n
            words = [word.split('\n') for word in words]
            # flatten the list
            words = [item for sublist in words for item in sublist]
            # remove empty strings
            words = [word for word in words if word != '']

    else:
        print ('El archivo debe ser un csv, un excel o un txt.')
        return 1
        #raise ValueError("El archivo debe ser un csv, un excel o un txt.")

    for i in range(len(words)):
        words[i] = words[i].lower().replace(',','').replace('.','').replace(' ','')

    count = np.zeros(len(words))

    df_words = pd.DataFrame({'words':words, 'count':count})
    return df_words


def extract_images_from_pdf(pdf_path, start_page, end_page, poppler_path = None):
    """
    Extract images from a PDF file.

    Parameters:
    - pdf_path (str): Path to the PDF file.
    - start_page (int): Starting page number.
    - end_page (int): Ending page number.

    Returns:
    - images (list): List of images.
    """
    images = convert_from_path(pdf_path, dpi = 500, first_page = start_page, last_page = end_page,poppler_path = poppler_path) # poppler path is the path to the poppler bin folder
    return images



def preprocess_images(list_of_images):
    """
    Preprocess a list of images for OCR

    Parameters:
    - list_of_images (list): List of images.

    Returns:
    - images (list): List of images.
    """

    # convert images to grayscale

    images = []
    for image in list_of_images:
        image = image.convert('L')
        images.append(image)
    return images


def find_substring_with_distance(input_string, target_word, max_distance):
    # This function finds the substring of input_string that has the minimum distance to target_word
    min_distance = float('inf')
    found_substring = None

    for start in range(len(input_string)):
        for end in range(start + 1, len(input_string) + 1):
            substring = input_string[start:end]
            current_distance = levenshtein_distance(substring, target_word)

            if current_distance < min_distance and current_distance <= max_distance:
                min_distance = current_distance
                found_substring = substring

    return found_substring


def perform_ocr(image_path,language = 'spa_old'):
    text = pytesseract.image_to_string(image_path,lang = language)
    return text


def levenshtein_distance(word1, word2):
    return Levenshtein.distance(word1, word2)

def count_words_with_levenshtein(words, target_word, max_distance=2,return_coincidences=False):

    count = 0
    coincidences = []
    for word in words:
        word = find_substring_with_distance(word, target_word.lower(), max_distance)
        if word is not None:
            count += 1
            coincidences.append(word)

    if return_coincidences:
        return count, coincidences
    else:

        return count

def preprocess_text(text):
    text = text.lower()
    text = text.replace(',',' ').replace('.',' ').replace('-\n','').replace('\n',' ')
    text = word_tokenize(text)
    return text


def preprocess_csv(path_csv):
    df = pd.read_csv(path_csv, index_col = 0)
    df = df.dropna()
    df['coincidences'] = df['coincidences'].str.split(',')
    df['Page'] = df['Page'].str.split(',')
    return df


from collections import Counter

def combinar_listas(lista_palabras, lista_paginas):
    # Crear un diccionario para almacenar las páginas asociadas a cada palabra
    diccionario_paginas = {}

    # Llenar el diccionario con las páginas asociadas a cada palabra
    for palabra, pagina in zip(lista_palabras, lista_paginas):
        if palabra in diccionario_paginas:
            diccionario_paginas[palabra]['paginas'].append(pagina)
            diccionario_paginas[palabra]['contador'] += 1
        else:
            diccionario_paginas[palabra] = {'paginas': [pagina], 'contador': 1}

    # Crear la lista combinada
    lista_combinada = [f"{palabra} ({', '.join(map(str, info['paginas']))}) [{info['contador']}]" for palabra, info in diccionario_paginas.items()]

    return lista_combinada