import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from datetime import datetime
import re

from models import Listing, Contract, Riscaldamento
from config import USER_AGENT, REQUEST_TIMEOUT, MAX_RETRIES


class TettorossoScraper:
    """Scraper for Tettorosso Immobiliare website."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def _clean_price(self, price_str: str) -> float:
        """Clean and convert price string to float."""
        if not price_str:
            return 0.0
        
        # Remove currency symbols and thousands separators
        price_str = price_str.replace("€", "").replace(".", "").replace(",", ".").strip()
        
        # Extract numbers only
        numbers = re.findall(r'\d+\.?\d*', price_str)
        if numbers:
            return float(numbers[0])
        return 0.0
    
    def _clean_square_meters(self, mq_str: str) -> Optional[int]:
        """Clean and convert square meters string to integer."""
        if not mq_str:
            return None
        
        # Extract numbers only
        numbers = re.findall(r'\d+', mq_str)
        if numbers:
            return int(numbers[0])
        return None
    
    def scrape_html_file(self, file_path: Path) -> Optional[Listing]:
        """Scrape a single HTML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            return self._parse_html(html_content, str(file_path))
        
        except Exception as e:
            self.logger.error(f"Error scraping {file_path}: {e}")
            return None
    
    def _parse_html(self, html_content: str, source: str) -> Listing:
        """Parse HTML content and extract property data."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract basic information
        title = self._extract_title(soup)
        price = self._extract_price(soup)
        description = self._extract_description(soup)
        contract_type = self._extract_contract_type(soup)
        city = self._extract_city(soup)
        
        # Create listing object with all required parameters
        listing = Listing(
            title=title,
            agency="Tettorosso Immobiliare",
            url=source,  # Use file path as URL for examples
            description=description,
            contract_type=contract_type,
            price=price,
            city=city
        )
        
        # Set optional parameters
        listing.neighborhood = self._extract_neighborhood(soup)
        listing.bedrooms = self._extract_bedrooms(soup)
        listing.bathrooms = self._extract_bathrooms(soup)
        listing.square_meters = self._extract_square_meters(soup)
        listing.year_built = self._extract_year_built(soup)
        listing.energy_class = self._extract_energy_class(soup)
        listing.has_elevator = self._extract_has_elevator(soup)
        listing.heating = self._extract_heating(soup)
        listing.agency_listing_id = self._extract_agency_listing_id(soup)
        listing.raw_html_file = source
        
        return listing
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract property title."""
        title_element = soup.find('h1', class_='h3')
        if title_element:
            return title_element.get_text(strip=True)
        
        # Fallback to meta title
        meta_title = soup.find('title')
        if meta_title:
            return meta_title.get_text(strip=True)
        
        return "Unknown Property"
    
    def _extract_price(self, soup: BeautifulSoup) -> float:
        """Extract property price."""
        price_element = soup.find('span', class_='immc__value')
        if price_element and '€' in price_element.get_text():
            price_text = price_element.get_text(strip=True)
            return self._clean_price(price_text)
         
        # Alternative location
        price_element = soup.find(lambda tag: tag.name == 'span' and '€' in tag.get_text())
        if price_element:
            return self._clean_price(price_element.get_text())
        
        return 0.0
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract property description."""
        desc_element = soup.find('div', class_='textviewmore')
        if desc_element:
            return desc_element.get_text(separator='\n', strip=True)
        
        return ""
    
    def _extract_contract_type(self, soup: BeautifulSoup) -> Contract:
        """Extract contract type (sell/rent)."""
        # Check URL or title for contract type indicators
        title = self._extract_title(soup)
        return Contract.from_string(title)
    
    def _extract_city(self, soup: BeautifulSoup) -> str:
        """Extract city information."""
        location_element = soup.find('span', class_='immc__value', string=lambda text: 'Padova' in text if text else False)
        if location_element:
            location_text = location_element.get_text(strip=True)
            # Extract city (first part before |)
            parts = location_text.split('|')
            if parts:
                return parts[0].strip()
        
        return "Padova"  # Default to Padova for Tettorosso
    
    def _extract_neighborhood(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract neighborhood information."""
        location_element = soup.find('span', class_='immc__value', string=lambda text: '|' in text if text else False)
        if location_element:
            location_text = location_element.get_text(strip=True)
            # Extract neighborhood (second part after |)
            parts = location_text.split('|')
            if len(parts) > 1:
                return parts[1].strip()
        
        return None
    
    def _extract_bedrooms(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of bedrooms."""
        bedrooms_element = soup.find('span', class_='immc__value', string=lambda text: text and text.isdigit() if text else False)
        if bedrooms_element:
            return int(bedrooms_element.get_text(strip=True))
        
        return None
    
    def _extract_bathrooms(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of bathrooms."""
        # Look for bathrooms in the details table or features
        bathrooms_element = soup.find(lambda tag: tag.name == 'td' and 'bagni' in tag.get_text().lower())
        if bathrooms_element:
            text = bathrooms_element.get_text(strip=True)
            numbers = re.findall(r'\d+', text)
            if numbers:
                return int(numbers[0])
        
        return None
    
    def _extract_square_meters(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract square meters."""
        mq_element = soup.find('span', class_='immc__value', string=lambda text: 'm²' in text or 'mq' in text if text else False)
        if mq_element:
            text = mq_element.get_text(strip=True)
            return self._clean_square_meters(text)
        
        return None
    
    def _extract_year_built(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract year built."""
        year_element = soup.find('td', string=lambda text: text and text.isdigit() and len(text) == 4 if text else False)
        if year_element:
            return int(year_element.get_text(strip=True))
        
        return None
    
    def _extract_energy_class(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract energy class."""
        energy_element = soup.find('span', class_='classeen')
        if energy_element:
            return energy_element.get_text(strip=True)
        
        return None
    
    def _extract_has_elevator(self, soup: BeautifulSoup) -> Optional[bool]:
        """Extract elevator information."""
        comfort_element = soup.find('td', string=lambda text: text and 'ascensore' in text.lower() if text else False)
        return comfort_element is not None
    
    def _extract_heating(self, soup: BeautifulSoup) -> Optional[Riscaldamento]:
        """Extract heating type."""
        comfort_element = soup.find('td', string=lambda text: text and 'riscaldamento' in text.lower() if text else False)
        if comfort_element:
            text = comfort_element.get_text(strip=True)
            return Riscaldamento.from_string(text)
        
        return None
    
    def _extract_agency_listing_id(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract agency listing ID."""
        code_element = soup.find('td', string=lambda text: text and text.startswith('iv') if text else False)
        if code_element:
            return code_element.get_text(strip=True)
         
        return None


class BaseScraper:
    """Base scraper class with common functionality."""
    
    def __init__(self, base_url: str, name: str):
        self.base_url = base_url
        self.name = name
        self.logger = logging.getLogger(f"scraper.{name}")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
        })
    
    def fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL with retries and error handling."""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    self.logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {e}")
                    return None
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
        
        return None
    
    def save_html(self, html_content: str, file_path: Path) -> bool:
        """Save HTML content to file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save HTML to {file_path}: {e}")
            return False