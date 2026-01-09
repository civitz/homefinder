import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from datetime import datetime
import re

from models import Listing, Contract, Riscaldamento
from config import USER_AGENT, REQUEST_TIMEOUT, MAX_RETRIES


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


class TettorossoScraper(BaseScraper):
    """Scraper for Tettorosso Immobiliare website."""
    
    def __init__(self):
        super().__init__(
            base_url="https://www.tettorossoimmobiliare.it",
            name="tettorosso"
        )
        self.session.headers.update({
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
        all_spans = soup.find_all('span')
        for span in all_spans:
            if '€' in span.get_text():
                return self._clean_price(span.get_text())
         
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
        location_element = soup.find('span', class_='immc__value')
        if location_element:
            location_text = location_element.get_text(strip=True)
            if 'Padova' in location_text:
                # Extract city (first part before |)
                parts = location_text.split('|')
                if parts:
                    return parts[0].strip()
         
        return "Padova"  # Default to Padova for Tettorosso
    
    def _extract_neighborhood(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract neighborhood information."""
        location_element = soup.find('span', class_='immc__value')
        if location_element:
            location_text = location_element.get_text(strip=True)
            if '|' in location_text:
                # Extract neighborhood (second part after |)
                parts = location_text.split('|')
                if len(parts) > 1:
                    return parts[1].strip()
         
        return None
    
    def _extract_bedrooms(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of bedrooms."""
        bedrooms_element = soup.find('span', class_='immc__value')
        if bedrooms_element and bedrooms_element.get_text(strip=True).isdigit():
            return int(bedrooms_element.get_text(strip=True))
         
        return None
    
    def _extract_bathrooms(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of bathrooms."""
        # Look for bathrooms in the details table or features
        all_td = soup.find_all('td')
        for td in all_td:
            if 'bagni' in td.get_text().lower():
                text = td.get_text(strip=True)
                numbers = re.findall(r'\d+', text)
                if numbers:
                    return int(numbers[0])
         
        return None
    
    def _extract_square_meters(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract square meters."""
        mq_element = soup.find('span', class_='immc__value')
        if mq_element:
            text = mq_element.get_text(strip=True)
            if 'm²' in text or 'mq' in text:
                return self._clean_square_meters(text)
         
        return None
    
    def _extract_year_built(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract year built."""
        all_td = soup.find_all('td')
        for td in all_td:
            text = td.get_text(strip=True)
            if text.isdigit() and len(text) == 4:
                return int(text)
         
        return None
    
    def _extract_energy_class(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract energy class."""
        energy_element = soup.find('span', class_='classeen')
        if energy_element:
            return energy_element.get_text(strip=True)
         
        return None
    
    def _extract_has_elevator(self, soup: BeautifulSoup) -> Optional[bool]:
        """Extract elevator information."""
        all_td = soup.find_all('td')
        for td in all_td:
            if 'ascensore' in td.get_text().lower():
                return True
        return False
    
    def _extract_heating(self, soup: BeautifulSoup) -> Optional[Riscaldamento]:
        """Extract heating type."""
        all_td = soup.find_all('td')
        for td in all_td:
            if 'riscaldamento' in td.get_text().lower():
                text = td.get_text(strip=True)
                return Riscaldamento.from_string(text)
         
        return None
    
    def _extract_agency_listing_id(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract agency listing ID."""
        all_td = soup.find_all('td')
        for td in all_td:
            text = td.get_text(strip=True)
            if text.startswith('iv'):
                return text
          
        return None


class GalileoScraper(BaseScraper):
    """Scraper for Galileo Immobiliare website."""
    
    def __init__(self):
        super().__init__(
            base_url="https://www.galileoimmobiliare.it",
            name="galileo"
        )
    
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
            agency="Galileo Immobiliare",
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
        listing.has_garage = self._extract_has_garage(soup)
        listing.agency_listing_id = self._extract_agency_listing_id(soup)
        listing.raw_html_file = source
        
        return listing
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract property title."""
        title_element = soup.find('h1')
        if title_element:
            return title_element.get_text(strip=True)
        
        # Fallback to meta title
        meta_title = soup.find('title')
        if meta_title:
            return meta_title.get_text(strip=True)
        
        return "Unknown Property"
    
    def _extract_price(self, soup: BeautifulSoup) -> float:
        """Extract property price."""
        price_element = soup.find('li', class_='item-price')
        if price_element:
            price_text = price_element.get_text(strip=True)
            return self._clean_price(price_text)
        
         # Alternative location in details
        all_strong = soup.find_all('strong')
        for strong in all_strong:
            if 'Prezzo' in strong.get_text():
                span_tag = strong.find_next('span')
                if span_tag:
                    price_text = span_tag.get_text(strip=True)
                    return self._clean_price(price_text)
        
        return 0.0
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract property description."""
        desc_element = soup.find('div', class_='block-content-wrap')
        if desc_element:
            # Find the paragraph within the description block
            paragraph = desc_element.find('p')
            if paragraph:
                return paragraph.get_text(separator='\n', strip=True)
        
        return ""
    
    def _extract_contract_type(self, soup: BeautifulSoup) -> Contract:
        """Extract contract type (sell/rent)."""
        contract_element = soup.find('a', class_='label-status')
        if contract_element:
            contract_text = contract_element.get_text(strip=True).lower()
            return Contract.from_string(contract_text)
        
        # Fallback to checking URL or other indicators
        return Contract.SELL
    
    def _extract_city(self, soup: BeautifulSoup) -> str:
        """Extract city information."""
        city_element = soup.find('li', class_='detail-city')
        if city_element:
            city_span = city_element.find('span')
            if city_span:
                return city_span.get_text(strip=True)
        
        # Fallback to address
        address_element = soup.find('address', class_='item-address')
        if address_element:
            address_text = address_element.get_text(strip=True)
            # Extract city from address (usually contains 'Padova')
            if 'Padova' in address_text:
                return 'Padova'
        
        return "Padova"  # Default to Padova
    
    def _extract_neighborhood(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract neighborhood information."""
        neighborhood_element = soup.find('li', class_='detail-area')
        if neighborhood_element:
            neighborhood_span = neighborhood_element.find('span')
            if neighborhood_span:
                return neighborhood_span.get_text(strip=True)
        
        return None
    
    def _extract_bedrooms(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of bedrooms."""
        # Look in overview section first
        bedrooms_element = soup.find('li', class_='h-beds')
        if bedrooms_element:
            strong_tag = bedrooms_element.find_previous('strong')
            if strong_tag:
                bedrooms_text = strong_tag.get_text(strip=True)
                try:
                    return int(bedrooms_text)
                except ValueError:
                    pass
        
        # Alternative: look in details list
        all_li = soup.find_all('li')
        for li in all_li:
            strong_tag = li.find('strong')
            if strong_tag and 'Camere' in strong_tag.get_text():
                span_tag = li.find('span')
                if span_tag:
                    try:
                        return int(span_tag.get_text(strip=True))
                    except ValueError:
                        pass
        
        return None
    
    def _extract_bathrooms(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of bathrooms."""
        # Look in overview section first
        bathrooms_element = soup.find('li', class_='h-baths')
        if bathrooms_element:
            strong_tag = bathrooms_element.find_previous('strong')
            if strong_tag:
                bathrooms_text = strong_tag.get_text(strip=True)
                try:
                    return int(bathrooms_text)
                except ValueError:
                    pass
        
        # Alternative: look in details list
        all_li = soup.find_all('li')
        for li in all_li:
            strong_tag = li.find('strong')
            if strong_tag and 'Bagni' in strong_tag.get_text():
                span_tag = li.find('span')
                if span_tag:
                    try:
                        return int(span_tag.get_text(strip=True))
                    except ValueError:
                        pass
        
        return None
    
    def _extract_square_meters(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract square meters."""
        # Look in overview section first
        mq_element = soup.find('li', class_='h-area')
        if mq_element:
            strong_tag = mq_element.find_previous('strong')
            if strong_tag:
                mq_text = strong_tag.get_text(strip=True)
                return self._clean_square_meters(mq_text)
        
        # Alternative: look in details list
        all_li = soup.find_all('li')
        for li in all_li:
            strong_tag = li.find('strong')
            if strong_tag and 'Dimensione' in strong_tag.get_text():
                span_tag = li.find('span')
                if span_tag:
                    mq_text = span_tag.get_text(strip=True)
                    return self._clean_square_meters(mq_text)
        
        return None
    
    def _extract_year_built(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract year built."""
        # Look for year in details
        all_li = soup.find_all('li')
        for li in all_li:
            strong_tag = li.find('strong')
            if strong_tag and 'Anno' in strong_tag.get_text():
                span_tag = li.find('span')
                if span_tag:
                    year_text = span_tag.get_text(strip=True)
                    try:
                        return int(year_text)
                    except ValueError:
                        pass
        
        return None
    
    def _extract_energy_class(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract energy class."""
        all_li = soup.find_all('li')
        for li in all_li:
            strong_tag = li.find('strong')
            if strong_tag and 'Classe energetica' in strong_tag.get_text():
                span_tag = li.find('span')
                if span_tag:
                    return span_tag.get_text(strip=True)
        
        return None
    
    def _extract_has_elevator(self, soup: BeautifulSoup) -> Optional[bool]:
        """Extract elevator information."""
        # Check if elevator is mentioned in features
        all_features = soup.find_all('a', href=True)
        for feature in all_features:
            href = feature.get('href', '')
            if href and 'ascensore' in href:
                return True
        return False
    
    def _extract_heating(self, soup: BeautifulSoup) -> Optional[Riscaldamento]:
        """Extract heating type."""
        # Check for autonomous heating in features
        all_features = soup.find_all('a', href=True)
        for feature in all_features:
            href = feature.get('href', '')
            if href and 'riscaldamento' in href:
                heating_text = feature.get_text(strip=True)
                return Riscaldamento.from_string(heating_text)
        
        return None
    
    def _extract_has_garage(self, soup: BeautifulSoup) -> Optional[bool]:
        """Extract garage information."""
        # Look in overview section first
        garage_element = soup.find('li', class_='h-garage')
        if garage_element:
            strong_tag = garage_element.find_previous('strong')
            if strong_tag:
                garage_text = strong_tag.get_text(strip=True)
                return garage_text.lower() == 'sì'
        
        # Alternative: look in details list
        all_li = soup.find_all('li')
        for li in all_li:
            strong_tag = li.find('strong')
            if strong_tag and 'Garage' in strong_tag.get_text():
                span_tag = li.find('span')
                if span_tag:
                    garage_text = span_tag.get_text(strip=True)
                    return garage_text.lower() == 'sì'
        
        return None
    
    def _extract_agency_listing_id(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract agency listing ID."""
        # Look for ID in overview section
        id_element = soup.find('div', class_='block-title-wrap')
        if id_element:
            strong_tag = id_element.find('strong')
            if strong_tag and 'ID:' in strong_tag.get_text():
                span_tag = strong_tag.find_next('span')
                if span_tag:
                    return span_tag.get_text(strip=True)
        
        # Alternative: look in details list
        all_li = soup.find_all('li')
        for li in all_li:
            strong_tag = li.find('strong')
            if strong_tag and 'ID:' in strong_tag.get_text():
                span_tag = li.find('span')
                if span_tag:
                    return span_tag.get_text(strip=True)
        
        return None
    
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