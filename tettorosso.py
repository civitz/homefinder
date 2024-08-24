from bs4 import BeautifulSoup, NavigableString
import scrapy
import re
import sys
from scrapy.item import Item, Field
from enum import Enum
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

class Contratto(Enum):
    AFFITTO = 1
    VENDITA = 2

class Riscaldamento(Enum):
    AUTONOMO = 1
    CENTRALIZZATO = 2

class Casetta(scrapy.Item):
    titolo=scrapy.Field() 
    agenzia=scrapy.Field()
    url=scrapy.Field()
    descrizione=scrapy.Field()
    contratto=scrapy.Field()
    prezzo=scrapy.Field()
    classe=scrapy.Field()
    locali=scrapy.Field()
    mq=scrapy.Field()
    piano=scrapy.Field()
    riscaldamento=scrapy.Field()
    condizionatore=scrapy.Field()
    ascensore=scrapy.Field()
    garage=scrapy.Field()
    arredato=scrapy.Field()
    anno=scrapy.Field()
    note=scrapy.Field() 

def tettorosso_extract_from_table(the_table: NavigableString, field_name, is_number: bool):
    field_text=the_table.find(text=field_name)
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

class TettorossoSpider(scrapy.Spider):
    name = "tettorosso"
    allowed_domains = ["tettorossoimmobiliare.it"]
    start_urls = ["https://www.tettorossoimmobiliare.it/immobili.php?start=0&ascdesc=&azione=list&id_categorianews=1&order_by=&comune=&zona=&vendita_affitto=vendita&categoria=&camere=&codice=&prezzo_da=&prezzo_a="]

    
    

    def parse(self, response):
        list=response.css("div.property_item div.image a::attr(href)").getall()
        to_follow=[x for x in list if "wishlist" not in x]
        # get  "next page" by looking at element with class "fa fa-chevron-right"
        next_pages = response.css("a:has(> i)::attr(href)").getall() # Get the href of the "Next Page" button
        filtered = [x for x in next_pages if "immobili.php" in x]
        if len(filtered) > 0:
            yield scrapy.Request(filtered[-1], callback=self.parse)
        yield from response.follow_all(to_follow, self.parse_single)

    def parse_single(self, response):
        print('parse_single for '+ response.url)
        item = Casetta()
        item['url'] = response.url
        item['agenzia'] = 'Tettorosso'
        item['contratto']= Contratto.VENDITA

        soup=BeautifulSoup(response.body, 'html.parser')
        item['titolo'] = soup.find('title').string.replace(' | Tetto Rosso Immobiliare', '')
        carattdiv=soup.find(id="caratt")
        carattdiv.find(class_='property-d-table').replace_with()
        item['descrizione'] = carattdiv.text.strip()
        # item['descrizione'] = response.xpath('//div[@id="caratt"]/*[not(div)]').get()
        classe_string=response.css('.bgimg::attr(style)').get()
        item['classe'] = 'N/a'
        if classe_string:
            m = re.search(r'.*classe_energetica/([A-G][1-5]?)\.png.*', classe_string)
            if m:
                item['classe'] = m.group(1)
        # parse elements from property-d-table
        soup=BeautifulSoup(response.body, 'html.parser')
        tabella=soup.find(id="caratt").find(class_='property-d-table').find('tbody')
        #print(tabella)
        item['prezzo'] = tettorosso_extract_from_table(the_table=tabella, field_name="Prezzo", is_number=True)
        item['piano'] = tettorosso_extract_from_table(the_table=tabella, field_name="Piano", is_number=False)
        item['mq'] = tettorosso_extract_from_table(the_table=tabella, field_name="Metri quadri", is_number=True)
        item['anno'] = tettorosso_extract_from_table(the_table=tabella, field_name="Anno di costruzione", is_number=True)
        ambienti=tettorosso_extract_from_table(the_table=tabella, field_name="Ambienti", is_number=True)
        if ambienti is not None and ambienti is not "":
            item['garage'] = "garage" in ambienti
        comfort=tettorosso_extract_from_table(the_table=tabella, field_name="Comfort", is_number=True)
        if comfort is not None and comfort is not "":
            item['ascensore'] = "ascensore" in comfort
            item['condizionatore'] = "aria condizionata" in comfort or "condizionatore" in comfort
            item['riscaldamento'] = Riscaldamento.AUTONOMO if "riscaldamento autonomo" in comfort else Riscaldamento.CENTRALIZZATO if "riscaldamento centralizzato" in comfort else None
        item['note'] = f'Comfort: {comfort}; Ambienti: {ambienti}' 
        print(item)
        pass

settings = get_project_settings()
process = CrawlerProcess(settings)
process.crawl(TettorossoSpider)
process.start()  # the script will block here until all crawling jobs are finished

# deal with sqlite results