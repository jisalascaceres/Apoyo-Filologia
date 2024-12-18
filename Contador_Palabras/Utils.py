import pandas as pd
import numpy as np  
from pdf2image import convert_from_path
import pytesseract
from nltk.tokenize import word_tokenize
import Levenshtein
import os
import cv2
from fpdf import FPDF


def Quitar_Tildes(texto):
      # Función que elimina tildes, dieresis, virgullillas y demás artefactos encontrados en vocales.
  # No tenemos en cuenta lás mayusculas, porque el textp siempre se pasa todo a minúsculas.

    texto = texto.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
    texto = texto.replace('à','a').replace('è','e').replace('ì','i').replace('ò','o').replace('ù','u')
    texto = texto.replace('â','a').replace('ê','e').replace('î','i').replace('ô','o').replace('û','u')
    texto = texto.replace('ã','a').replace('õ','o').replace('ã','a').replace('õ','o')
    texto = texto.replace('ä','a').replace('ë','e').replace('ï','i').replace('ö','o').replace('ü','u')
    return texto


def read_words(path):
    """
    Esta funcion lee las palabras que se encuentran en la primera hoja de un excel y crea un dataframe con ellas y el count a cero.
    """
    if path.endswith('.csv'):
        df = pd.read_csv(path,sep=',')
        df = df.dropna()
        words = df.values.tolist()
        words = [word[0] for word in words]
    elif path.endswith('.xlsx'):
        df = pd.read_excel(path, sheet_name = 0)
        df = df.dropna()
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
        words[i] = words[i].lower().replace(',','').replace('.','').replace(' ','').replace('\n','')
        words[i] = Quitar_Tildes(words[i])

    count = np.zeros(len(words))

    df_words = pd.DataFrame({'words':words, 'count':count})
    return df_words

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
    # Esta función busca substrings dentro de una palabra que sea coincidencia
    min_distance = float('inf')
    found_substring = None

    for start in range(len(input_string)):
        for end in range(start + 1, len(input_string) + 1):
            substring = input_string[start:end]
            current_distance = levenshtein_distance(substring, target_word)

            if current_distance < min_distance and current_distance <= max_distance:
                min_distance = current_distance
                found_substring = substring

    return found_substring, min_distance


def perform_ocr(image_path,language = 'spa_old'):
    text = pytesseract.image_to_string(image_path,lang = language)
    return text



# Función que guarda el texto extraido en un nuevo PDF
def save_text_as_pdf(book, output_filename="output.pdf"):
    pdf = FPDF()
    
    # Iterate through all pages (each book entry)
    for idx, page_text in book:
        page_text = page_text.replace('\n',' ')      
        pdf.add_page()  # Add a new page for each book entry
        pdf.set_font("Arial", size=10)  # Set font type and size
  
        
        # Write all the text for this page into the current PDF page
        pdf.multi_cell(190, 10, txt=page_text, border=0)
    
    # Save the PDF
    try:
          pdf.output(output_filename)
          print(f"PDF saved as: {output_filename}")
    except:
          print('Error al generar el PDF, seguirá el proceso sin guardar el resultado de la digitalización.')
          
          
def levenshtein_distance(word1, word2):
    return Levenshtein.distance(word1, word2)

def count_words_with_levenshtein(words, target_word, max_distance=2,find_in_substrings=True):
  # a esta función le llega la lista de palabras, la palabra en cuestión que buscamos y la distancia máxima que queremos considerar coincidencia.
  # Además, le llega un argumento que nos dice si queremos encontrar substrings o palabras completas, es decir, si queremos considerar para la búsqueda fragmentos de palabras.
  # Esto es muy útil si buscamos verbos o adjetivos que pueden estar convertidos en adverbios de modo, o para hacer mas robusto el sistema a no detectar un espacio
  # Sin embargo, si le estamos haciendo la búsqueda a un PDF ya digitalizado puede dar errores.

    count = 0
    coincidences = []
    # Iteramos por todas las palabras insertadas
    
    for word in words:
      # Si queremos buscar en substrings, aplicamos la funcion
      if find_in_substrings:
        word,distance = find_substring_with_distance(word, target_word, max_distance)

      else:
        # Si no, simplemente calculamos la distancia de cada palabra con la que buscamos.
        distance = levenshtein_distance(word,target_word)
        
        # la guardamos si es exacta y estamos buscando coincidencias exactas
      if distance == 0 and max_distance == 0:
        word = word
        # o si no es exacta pero menor que la distancia maxima y estamos buscnado no exactas.
        # Si guardamos las exactas aqui, algunas palabras las guardariamos dos veces.
      elif distance <= max_distance and not distance==0:
        word = word
      else:
        word = None

      if word is not None:
          count += 1
          coincidences.append(word)

    return count, coincidences
    
def PostProcess_text(text):
    # Función que realiza un post-procesado al texto antes de pasar a leerlo
    # Pasamos el texto a minúsculas
    text = text.lower()
    # Quitamos signos de puntuación.
    text = text.replace(',',' ').replace('.',' ').replace('-\n','').replace('\n',' ')
    # Quitamos tildes, diéresis y algunas cosas más
    text = Quitar_Tildes(text)

    # Tokenizamos el texto
    text = word_tokenize(text)
    return text
