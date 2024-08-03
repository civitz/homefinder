
import re

classe_string= '''background-image: url(https://www.tettorossoimmobiliare.it/images/classe_energetica/A4.png);'''
m = re.search(r'.*classe_energetica/([A-G][1-5]?)\.png.*', classe_string)
if m:
    print(m.group(1))