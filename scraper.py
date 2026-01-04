#!/usr/bin/env python3
"""
Main scraping module for Tettorosso Immobiliare
Processes downloaded HTML files and extracts structured data
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from bs4 import BeautifulSoup
from bs4.element import Tag
import re
from enum import Enum
from config import DOWNLOAD_DIR, LOG_FILE, LLM_PROMPT_TEMPLATE
from beautifulsoup import tettorosso_extract_from_table

# Set up logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
    
# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)


class Contratto(Enum):
    AFFITTO = 1
    VENDITA = 2


class Riscaldamento(Enum):
    AUTONOMO = 1
    CENTRALIZZATO = 2


class Casetta:
    """
    Data model for property listings
    """

    def __init__(self):
        self.titolo: str = ""
        self.agenzia: str = "Tettorosso"
        self.url: str = ""
        self.descrizione: str = ""
        self.contratto: Optional[Contratto] = None
        self.prezzo: Optional[int] = None
        self.classe: str = ""
        self.locali: Optional[int] = None
        self.mq: Optional[int] = None
        self.piano: str = ""
        self.riscaldamento: Optional[Riscaldamento] = None
        self.condizionatore: bool = False
        self.ascensore: bool = False
        self.garage: bool = False
        self.arredato: bool = False
        self.anno: Optional[int] = None
        self.note: str = ""
        self.scrape_date: str = datetime.now().isoformat()
        self.publication_date: Optional[str] = None
        self.raw_html_file: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "titolo": self.titolo,
            "agenzia": self.agenzia,
            "url": self.url,
            "descrizione": self.descrizione,
            "contratto": self.contratto.name if self.contratto else None,
            "prezzo": self.prezzo,
            "classe": self.classe,
            "locali": self.locali,
            "mq": self.mq,
            "piano": self.piano,
            "riscaldamento": self.riscaldamento.name if self.riscaldamento else None,
            "condizionatore": self.condizionatore,
            "ascensore": self.ascensore,
            "garage": self.garage,
            "arredato": self.arredato,
            "anno": self.anno,
            "note": self.note,
            "scrape_date": self.scrape_date,
            "publication_date": self.publication_date,
            "raw_html_file": self.raw_html_file,
        }

    def __str__(self):
        return f"Casetta(titolo='{self.titolo}', prezzo={self.prezzo}, mq={self.mq})"


def extract_property_data_from_html(
    html_content: str, file_path: Path
) -> Optional[Casetta]:
    """
    Extract property data from HTML content

    Args:
        html_content: HTML content as string
        file_path: Path to the HTML file (for reference)

    Returns:
        Casetta object with extracted data, or None if parsing fails
    """
    try:
        item = Casetta()
        item.raw_html_file = str(file_path)

        soup = BeautifulSoup(html_content, "html.parser")

        # Extract title
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            item.titolo = title_tag.string.replace(
                " | Tetto Rosso Immobiliare", ""
            ).strip()

        # Extract URL from canonical link or other sources
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            item.url = str(canonical["href"]) if canonical["href"] else ""

        # Extract description from caratt div
        caratt_div = soup.find(id="caratt")
        if caratt_div:
            # Remove the property table to get clean description
            property_table = caratt_div.find(class_="property-d-table")
            if property_table:
                property_table.decompose()  # Remove the table from the tree

            # Get the text content
            description_text = caratt_div.get_text(separator="\n", strip=True)
            # Clean up the description by removing multiple newlines and extra spaces
            description_text = "\n".join(
                line.strip() for line in description_text.split("\n") if line.strip()
            )
            item.descrizione = description_text

        # Extract contract type (AFFITTO/VENDITA)
        contract_tag = soup.find("span", class_="tag")
        if contract_tag:
            contract_text = contract_tag.get_text(strip=True)
            if "AFFITTO" in contract_text.upper():
                item.contratto = Contratto.AFFITTO
            else:
                item.contratto = Contratto.VENDITA

        # Extract structured data from property table
        tabella = soup.find(id="caratt")
        if tabella:
            tabella = tabella.find(class_="property-d-table")
            if tabella:
                tabella = tabella.find("tbody")

        if tabella:
            # Price
            prezzo_result = tettorosso_extract_from_table(
                table=tabella, field_name="Prezzo", is_number=True
            )
            if isinstance(prezzo_result, int):
                item.prezzo = prezzo_result

            # Year
            anno_result = tettorosso_extract_from_table(
                table=tabella, field_name="Anno di costruzione", is_number=True
            )
            if isinstance(anno_result, int):
                item.anno = anno_result

            # Floor
            piano_result = tettorosso_extract_from_table(
                table=tabella, field_name="Piano", is_number=False
            )
            if piano_result:
                item.piano = str(piano_result)

            # Square meters
            mq_result = tettorosso_extract_from_table(
                table=tabella, field_name="Metri quadri", is_number=True
            )
            if isinstance(mq_result, int):
                item.mq = mq_result

            # Rooms
            locali_result = tettorosso_extract_from_table(
                table=tabella, field_name="Camere", is_number=True
            )
            if isinstance(locali_result, int):
                item.locali = locali_result

            # Energy class
            classe_string = soup.find("div", class_="bgimg")
            if classe_string and classe_string.get("style"):
                style_str = (
                    str(classe_string["style"]) if classe_string["style"] else ""
                )
                m = re.search(r".*classe_energetica/([A-G][1-5]?)\.png.*", style_str)
                if m:
                    item.classe = m.group(1)

            # Extract features from Ambienti and Comfort fields
            ambienti = tettorosso_extract_from_table(
                table=tabella, field_name="Ambienti", is_number=False
            )
            comfort = tettorosso_extract_from_table(
                table=tabella, field_name="Comfort", is_number=False
            )

            if ambienti and isinstance(ambienti, str):
                item.garage = "garage" in ambienti.lower()
                item.arredato = "arredato" in ambienti.lower()

            if comfort and isinstance(comfort, str):
                item.ascensore = "ascensore" in comfort.lower()
                item.condizionatore = (
                    "aria condizionata" in comfort.lower()
                    or "condizionatore" in comfort.lower()
                )

                if "riscaldamento autonomo" in comfort.lower():
                    item.riscaldamento = Riscaldamento.AUTONOMO
                elif "riscaldamento centralizzato" in comfort.lower():
                    item.riscaldamento = Riscaldamento.CENTRALIZZATO

            item.note = f"Ambienti: {ambienti}; Comfort: {comfort}"

            # LLM integration placeholder - currently disabled
            # llm_data = extract_with_llm(item.descrizione)
            # if llm_data:
            #     # Merge LLM extracted data with existing data
            #     pass

        return item

    except Exception as e:
        logger.error(f"Error parsing {file_path}: {str(e)}")
        # Create minimal item with title and URL if possible
        try:
            minimal_item = Casetta()
            minimal_item.raw_html_file = str(file_path)
            soup = BeautifulSoup(html_content, "html.parser")
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                minimal_item.titolo = title_tag.string.replace(
                    " | Tetto Rosso Immobiliare", ""
                ).strip()

            canonical = soup.find("link", rel="canonical")
            if canonical and canonical.get("href"):
                minimal_item.url = str(canonical["href"]) if canonical["href"] else ""

            return minimal_item
        except Exception as e2:
            logger.error(f"Failed to create minimal item for {file_path}: {str(e2)}")
            return None


def scrape_all_properties() -> List[Casetta]:
    """
    Scrape all property listings from downloaded website

    Returns:
        List of Casetta objects with extracted data
    """
    logger.info("Starting property scraping")

    if not DOWNLOAD_DIR.exists():
        logger.warning(f"Download directory {DOWNLOAD_DIR} does not exist")
        return []

    # Get all HTML files
    html_files = list(DOWNLOAD_DIR.rglob("immobili/*/index.html"))
    logger.info(f"Found {len(html_files)} HTML files to process")

    properties = []

    for i, file_path in enumerate(html_files, 1):
        try:
            # Skip obvious non-property pages
            file_str = str(file_path)
            if any(
                skip in file_str
                for skip in [
                    "contatti",
                    "privacy",
                    "cookie",
                    "lavora-con-noi",
                    "wishlist",
                ]
            ):
                continue


            logger.info(f"Processing file {i}/{len(html_files)}: {file_path}")

            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Extract property data
            property_data = extract_property_data_from_html(html_content, file_path)

            if property_data:
                properties.append(property_data)
                logger.info(f"Successfully extracted: {property_data.titolo}")
            else:
                logger.warning(f"Failed to extract data from {file_path}")

        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")

    logger.info(f"Finished scraping. Found {len(properties)} properties.")
    return properties


# Placeholder for LLM integration
def extract_with_llm(description: str) -> Dict[str, Any]:
    """
    Placeholder for LLM-based extraction of unstructured data
    Currently returns empty dict, but structured for future implementation
    """
    # This is where Granite LLM integration would go
    # For now, return empty dict
    return {}


if __name__ == "__main__":
    # Test the scraper
    properties = scrape_all_properties()
    print(f"Found {len(properties)} properties")

    for i, prop in enumerate(properties[:3]):  # Show first 3 properties
        print(f"\nProperty {i + 1}:")
        print(f"  Title: {prop.titolo}")
        print(f"  Price: {prop.prezzo}")
        print(f"  Size: {prop.mq} m²")
        print(f"  Rooms: {prop.locali}")
        print(f"  URL: {prop.url}")
