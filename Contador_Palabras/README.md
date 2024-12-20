### Contador de palabras.

Esta carpeta contiene todo lo necesario para ejecutar en Google Colab el cuaderno "contador_palabras.ipynb".

### Errores encontrados

Hay determinados PDFs que no empiezan o terminan por la página 1 o su final, sino que tienen una numeración diferente. 
Por ejemplo, el libro "nuevodescubrimie00acuuoft" no empieza por la página 1 sino por la I, la página 1 no aparece hasta las XXXIII, es decir, que en realidad la 1 es la 33.
Esto provoca que cuando automáticamente definamos el final del libro, que es la página numerada 280, en realidad no lea todo el libro, pos la página final es 280 + XXXIII.
Esto solo pasa en unos pocos PDFs
