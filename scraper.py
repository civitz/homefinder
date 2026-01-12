import requests
import time
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from datetime import datetime
import re

# Import for poison pill (will be passed from main)
from typing import Any

from models import Listing, Contract, Riscaldamento
from config import USER_AGENT, REQUEST_TIMEOUT, MAX_RETRIES, REQUEST_DELAY_MS, DOWNLOAD_DIR


class BaseScraper:
    """Base scraper class with common functionality."""
    
    def __init__(self, base_url: str, name: str, request_delay_ms: Optional[int] = None, stop_signal: Any = None):
        self.base_url = base_url
        self.name = name
        self.logger = logging.getLogger(f"scraper.{name}")
        self.session = requests.Session()
        self.request_delay_ms = request_delay_ms if request_delay_ms is not None else REQUEST_DELAY_MS
        self.stop_signal = stop_signal
        self.session.headers.update({
            'User-Agent': USER_AGENT,
        })

    def _should_stop(self) -> bool:
        """Check if scraper should stop gracefully due to poison pill."""
        if self.stop_signal and self.stop_signal.load():
            self.logger.info("Poison pill detected, stopping gracefully after current listing")
            return True
        return False
    
    def fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL with retries and error handling."""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                
                 # Add delay after successful request (except on retry attempts)
                if attempt == 0 and self.request_delay_ms > 0:
                    delay_seconds = self.request_delay_ms / 1000.0
                    self.logger.debug(f"Adding {self.request_delay_ms}ms delay before next request")
                    time.sleep(delay_seconds)
                    
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
    
    def __init__(self, request_delay_ms: Optional[int] = None, stop_signal: Any = None):
        super().__init__(
            base_url="https://www.tettorossoimmobiliare.it",
            name="tettorosso",
            request_delay_ms=request_delay_ms,
            stop_signal=stop_signal
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
             agency_id=2,  # Tettorosso Immobiliare
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
        # Look for the bedrooms in the sidebar info list
        # Find the list item with the bedroom icon (ic-letto)
        bedroom_li = soup.find('li')
        if bedroom_li:
            # Look for the icon that indicates bedrooms
            bedroom_icon = bedroom_li.find('span', class_='ic-letto')
            if bedroom_icon:
                # Get the value from the immc__value span in the same li
                value_span = bedroom_li.find('span', class_='immc__value')
                if value_span and value_span.get_text(strip=True).isdigit():
                    return int(value_span.get_text(strip=True))
        
        # Alternative: look for all list items and find the one with "Camere" label
        all_li = soup.find_all('li')
        for li in all_li:
            label_span = li.find('span', class_='immc__label')
            if label_span and 'Camere' in label_span.get_text(strip=True):
                value_span = li.find('span', class_='immc__value')
                if value_span and value_span.get_text(strip=True).isdigit():
                    return int(value_span.get_text(strip=True))
        
        return None
    
    def _extract_bathrooms(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of bathrooms."""
        # Look for the bathrooms in the sidebar info list
        # Find the list item with the bathroom icon (ic-bagno)
        bathroom_li = soup.find('li')
        if bathroom_li:
            # Look for the icon that indicates bathrooms
            bathroom_icon = bathroom_li.find('span', class_='ic-bagno')
            if bathroom_icon:
                # Get the value from the immc__value span in the same li
                value_span = bathroom_li.find('span', class_='immc__value')
                if value_span and value_span.get_text(strip=True).isdigit():
                    return int(value_span.get_text(strip=True))
        
        # Alternative: look for all list items and find the one with "Bagni" label
        all_li = soup.find_all('li')
        for li in all_li:
            label_span = li.find('span', class_='immc__label')
            if label_span and 'Bagni' in label_span.get_text(strip=True):
                value_span = li.find('span', class_='immc__value')
                if value_span and value_span.get_text(strip=True).isdigit():
                    return int(value_span.get_text(strip=True))
        
        # Fallback: look for bathrooms in the details table or features
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
        # Look for the square meters in the sidebar info list
        # Find the list item with the mq icon (ic-mq)
        mq_li = soup.find('li')
        if mq_li:
            # Look for the icon that indicates square meters
            mq_icon = mq_li.find('span', class_='ic-mq')
            if mq_icon:
                # Get the value from the immc__value span in the same li
                value_span = mq_li.find('span', class_='immc__value')
                if value_span:
                    text = value_span.get_text(strip=True)
                    return self._clean_square_meters(text)
        
        # Alternative: look for all list items and find the one with "Metri quadri" label
        all_li = soup.find_all('li')
        for li in all_li:
            label_span = li.find('span', class_='immc__label')
            if label_span and 'Metri quadri' in label_span.get_text(strip=True):
                value_span = li.find('span', class_='immc__value')
                if value_span:
                    text = value_span.get_text(strip=True)
                    return self._clean_square_meters(text)
        
        # Fallback: look for any immc__value span with m² or mq
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
    
    def _extract_has_garage(self, soup: BeautifulSoup) -> Optional[bool]:
        """Extract garage information."""
        # Look for garage in the details table
        all_td = soup.find_all('td')
        for td in all_td:
            if 'garage' in td.get_text().lower():
                return True
        
        # Look for garage in the "Ambienti" (environments) section
        all_tr = soup.find_all('tr')
        for tr in all_tr:
            th = tr.find('th')
            if th and 'Ambienti' in th.get_text(strip=True):
                td = tr.find('td')
                if td and 'garage' in td.get_text().lower():
                    return True
        
        return None

    def _extract_agency_listing_id(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract agency listing ID."""
        all_td = soup.find_all('td')
        for td in all_td:
            text = td.get_text(strip=True)
            if text.startswith('iv'):
                return text
            
        return None

    def scrape_live_listings(self) -> List[Listing]:
        """Scrape live listings from the website using AJAX pagination."""
        listings = []
        
        try:
            # First, fetch the main listings page to get the nonce and initial data
            listings_page_url = f"{self.base_url}/immobili/"
            self.logger.info(f"Fetching Tettorosso listings page: {listings_page_url}")
            html_content = self.fetch_url(listings_page_url)
            
            if not html_content:
                self.logger.warning(f"Failed to fetch Tettorosso listings page: {listings_page_url}")
                return listings
            
            # Extract nonce from the page (required for AJAX calls)
            soup = BeautifulSoup(html_content, 'html.parser')
            imsearch_element = soup.find('div', id='imsearch')
            
            # Try to get nonce from data-nonce attribute
            nonce = None
            if imsearch_element:
                nonce = imsearch_element.get('data-nonce')
            
            # If not found in data-nonce, try to extract from JavaScript
            if not nonce:
                # Look for nonce in script tags
                script_tags = soup.find_all('script')
                for script in script_tags:
                    script_content = script.string
                    if script_content and 'nonce' in script_content:
                        # Try to extract nonce from JavaScript
                        import re
                        nonce_match = re.search(r'nonce["\']?\s*:\s*["\']([^"\']+)["\']', script_content)
                        if nonce_match:
                            nonce = nonce_match.group(1)
                            break
            
            if not nonce:
                self.logger.error("Could not find nonce for AJAX requests")
                return listings
            
            # Use AJAX to fetch properties page by page
            current_page = 1
            has_more_pages = True
            
            while has_more_pages:
                self.logger.info(f"Fetching Tettorosso properties - Page {current_page}")
                
                # Call the WordPress AJAX endpoint to get properties
                ajax_url = f"{self.base_url}/wp-admin/admin-ajax.php?action=sf_get_immobili"
                
                # Prepare form data for the AJAX request
                form_data = {
                    'paged': str(current_page),
                    'order': 'DESC',
                    'orderby': 'date',
                    'posts_per_page': '6',  # Default per page
                    'nonce': nonce,
                    'filters': '[]',  # No filters for initial scrape
                    'gim_category': '8',  # Residenziale (default)
                    'comune': '',
                    'zona': '',
                    'gim_types_res': '',
                    'gim_types_com': '',
                    'filter_locali': '',
                    'filter_locali_comparison': '=',
                    'riferimento': '',
                    'gim_source': '',
                    'gim_contract': '',
                    'min_mq': '',
                    'max_mq': '',
                    'min_price': '',
                    'max_price': ''
                }
                
                try:
                    # Make POST request to AJAX endpoint
                    response = self.session.post(ajax_url, data=form_data, timeout=REQUEST_TIMEOUT)
                    response.raise_for_status()
                    
                    ajax_data = response.json()
                    
                    if not ajax_data.get('success'):
                        self.logger.warning(f"AJAX request failed for page {current_page}")
                        has_more_pages = False
                        break
                    
                    # Extract property listings HTML from response
                    properties_html = ajax_data.get('data', {}).get('elements', '')
                    if not properties_html:
                        self.logger.info("No more properties found")
                        has_more_pages = False
                        break
                    
                    # Parse the HTML to extract individual property links
                    properties_soup = BeautifulSoup(properties_html, 'html.parser')
                    property_links = []
                    
                    # Find all property links in the returned HTML
                    # Tettorosso property links have class 'imm__link' or similar
                    link_elements = properties_soup.find_all('a', href=True)
                    
                    for element in link_elements:
                        href = element.get('href', '')
                        # Ensure href is a string
                        if not isinstance(href, str):
                            continue
                            
                        # Filter for individual property detail pages
                        # Tettorosso uses /immobili/<property-slug>/ pattern
                        if href and '/immobili/' in href and href.count('/') >= 3:
                            # Skip the main listings page and pagination links
                            if (href.endswith('/immobili/') or 
                                '/immobili/page/' in href or 
                                href == '/immobili/'):
                                continue
                            
                            # Make absolute URL
                            if not href.startswith('http'):
                                href = f"{self.base_url}{href}" if href.startswith('/') else f"{self.base_url}/{href}"
                            
                            if href not in property_links:
                                property_links.append(href)
                    
                    self.logger.info(f"Found {len(property_links)} property links on page {current_page}")
                    
                    if not property_links:
                        has_more_pages = False
                        break
                    
                    # Scrape each property page
                    for link in property_links:
                        try:
                            property_html = self.fetch_url(link)
                            if property_html:
                                # Save HTML to file for reference
                                file_name = f"tettorosso_{hash(link)}.html"
                                file_path = DOWNLOAD_DIR / file_name
                                self.save_html(property_html, file_path)
                                
                                # Parse the HTML
                                listing = self._parse_html(property_html, link)
                                if listing:
                                    listings.append(listing)
                                    self.logger.info(f"Successfully scraped Tettorosso: {listing.title}")
                                else:
                                    self.logger.warning(f"Failed to parse Tettorosso property: {link}")
                            else:
                                self.logger.warning(f"Failed to fetch Tettorosso property page: {link}")
                         
                            # Check poison pill after each listing
                            if self._should_stop():
                                    break
                        
                        except Exception as e:
                            self.logger.error(f"Error scraping Tettorosso {link}: {e}")
                    
                    # Check if there are more pages
                    total_pages = ajax_data.get('data', {}).get('pages', 0)
                    if current_page >= total_pages:
                        has_more_pages = False
                        self.logger.info(f"Reached last page ({current_page}/{total_pages})")
                    
                    # Check poison pill after each page
                    if self._should_stop():
                        has_more_pages = False
                        break
                    
                    current_page += 1
                    
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"AJAX request failed for page {current_page}: {e}")
                    has_more_pages = False
                    break
                    
        except Exception as e:
            self.logger.error(f"Fatal error in Tettorosso scraping: {e}")
        
        return listings


class GalileoScraper(BaseScraper):
    """Scraper for Galileo Immobiliare website."""
    
    def __init__(self, request_delay_ms: Optional[int] = None, stop_signal: Any = None):
        super().__init__(
            base_url="https://www.galileoimmobiliare.it",
            name="galileo",
            request_delay_ms=request_delay_ms,
            stop_signal=stop_signal
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
             agency_id=1,  # Galileo Immobiliare
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
        # Look for ID in overview section - the ID is in a div with strong:ID: text
        all_divs = soup.find_all('div', class_='block-title-wrap')
        for div in all_divs:
            strong_tag = div.find('strong')
            if strong_tag and 'ID:' in strong_tag.get_text():
                # The ID value is in the text after the strong tag
                id_text = div.get_text().strip()
                if 'ID:' in id_text:
                    # Extract the ID number after "ID:"
                    id_value = id_text.split('ID:')[-1].strip()
                    return id_value
         
        # Alternative: look for hidden input field with property_id
        property_id_input = soup.find('input', {'name': 'property_id'})
        if property_id_input:
            return property_id_input.get('value', '').strip() if property_id_input.get('value') else None
         
        # Alternative: look in details list
        all_li = soup.find_all('li')
        for li in all_li:
            strong_tag = li.find('strong')
            if strong_tag and 'ID:' in strong_tag.get_text():
                span_tag = li.find('span')
                if span_tag:
                    return span_tag.get_text(strip=True)
         
        return None

    def scrape_live_listings(self) -> List[Listing]:
        """Scrape live listings from the website."""
        listings = []
        
        # Scrape both sell and rent listings
        listing_types = ['immobile', 'affitto']
        
        for listing_type in listing_types:
            page = 1
            has_more_pages = True
            
            while has_more_pages:
                # Fetch the listings page
                listings_page_url = f"{self.base_url}/{listing_type}/"
                if page > 1:
                    listings_page_url = f"{self.base_url}/{listing_type}/page/{page}/"
                
                self.logger.info(f"Fetching page {page} for {listing_type}")
                html_content = self.fetch_url(listings_page_url)
                
                if not html_content:
                    self.logger.warning(f"No more pages found for {listing_type}")
                    has_more_pages = False
                    break
                    
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find all property listing links
                property_links = []
                listing_elements = soup.find_all('a')
                
                for element in listing_elements:
                    href = element.get('href', '')
                    # Ensure href is a string
                    if not isinstance(href, str):
                        continue
                    # Filter for property detail pages
                    # Exclude pagination pages and main listing pages
                    if href and f'/{listing_type}/' in href and href.count('/') > 2 and '/page/' not in href and not href.endswith(f'/{listing_type}/'):
                         if not href.startswith('http'):
                             href = f"{self.base_url}{href}" if href.startswith('/') else f"{self.base_url}/{href}"
                         if href not in property_links:
                             property_links.append(href)
                
                if not property_links:
                    has_more_pages = False
                    break
                
                self.logger.info(f"Found {len(property_links)} property links on page {page}")
                
                # Scrape each property page
                for link in property_links:
                    try:
                        property_html = self.fetch_url(link)
                        if property_html:
                            # Save HTML to file for reference
                            file_name = f"galileo_{hash(link)}.html"
                            file_path = DOWNLOAD_DIR / file_name
                            self.save_html(property_html, file_path)
                            
                            # Parse the HTML
                            listing = self._parse_html(property_html, link)
                            if listing:
                                listings.append(listing)
                                self.logger.info(f"Successfully scraped: {listing.title}")
                        
                        # Check poison pill after each listing
                        if self._should_stop():
                            break
                    
                    except Exception as e:
                        self.logger.error(f"Error scraping {link}: {e}")
                
                # Check if there are more pages (Galileo uses pagination)
                next_page_link = soup.find('a', class_='next')
                if not next_page_link:
                    has_more_pages = False
                
                 # Check poison pill after each page
                if self._should_stop():
                    has_more_pages = False
                    break
                
                page += 1
        
        return listings
    
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