from bs4 import BeautifulSoup, NavigableString
import re


def tettorosso_extract_from_table(table: NavigableString, field_name, is_number: bool):
    field_text=table.find(text=field_name)
    if not field_text:
        return ""
    children=list(field_text.parent.parent.parent.children)
    if len(children) is not 5:
        return ""
    child=children[3]
    if is_number:
        m=re.search(r'[^0-9]*([0-9\.]+)[^0-9]*', child.text)
        if m:
            return int(m.group(1).replace(".",""))
    else:
        return child.text
    

with open('example.html', 'r') as file:
    data = file.read()
    soup=BeautifulSoup(data, 'html.parser')
    tabella=soup.find(id="caratt").find(class_='property-d-table').find('tbody')
    print('-----------------------------')
    print(tabella)
    print('-----------------------------')
    print("Prezzo: "+str(tettorosso_extract_from_table(table=tabella, field_name="Prezzo", is_number=True)))
    print("Anno di costruzione: "+str(tettorosso_extract_from_table(table=tabella, field_name="Anno di costruzione", is_number=True)))
    print("Piano: "+tettorosso_extract_from_table(table=tabella, field_name="Piano", is_number=False))

