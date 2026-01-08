from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import re


class Contract(Enum):
    """Property contract types."""
    SELL = "sell"
    RENT = "rent"

    @classmethod
    def from_string(cls, value: str) -> 'Contract':
        """Convert string to Contract enum."""
        value = value.lower()
        if "vendita" in value or "sell" in value:
            return cls.SELL
        elif "affitto" in value or "rent" in value:
            return cls.RENT
        else:
            # Default to sell if unknown
            return cls.SELL


class Riscaldamento(Enum):
    """Heating types."""
    AUTONOMOUS = "autonomous"
    CENTRALIZED = "centralized"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> 'Riscaldamento':
        """Convert string to Riscaldamento enum."""
        value = value.lower()
        if "autonomo" in value or "autonomous" in value:
            return cls.AUTONOMOUS
        elif "centralizzato" in value or "centralized" in value:
            return cls.CENTRALIZED
        else:
            return cls.UNKNOWN


@dataclass
class Listing:
    """Main data model for property listings."""
    
    # Basic information
    title: str
    agency: str
    url: str
    description: str
    
    # Financial information
    contract_type: Contract
    price: float
    
    # Location information
    city: str
    neighborhood: Optional[str] = None
    address: Optional[str] = None
    
    # Physical characteristics
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    square_meters: Optional[int] = None
    floor: Optional[str] = None
    year_built: Optional[int] = None
    
    # Features
    has_elevator: Optional[bool] = None
    heating: Optional[Riscaldamento] = None
    has_air_conditioning: Optional[bool] = None
    has_garage: Optional[bool] = None
    is_furnished: Optional[bool] = None
    
    # Energy information
    energy_class: Optional[str] = None
    energy_consumption: Optional[float] = None
    
    # Additional features
    features: Optional[List[str]] = None
    
    # Metadata
    scrape_date: datetime = datetime.now()
    publication_date: Optional[datetime] = None
    raw_html_file: Optional[str] = None
    code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert listing to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "agency": self.agency,
            "url": self.url,
            "description": self.description,
            "contract_type": self.contract_type.value,
            "price": self.price,
            "city": self.city,
            "neighborhood": self.neighborhood,
            "address": self.address,
            "rooms": self.rooms,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "square_meters": self.square_meters,
            "floor": self.floor,
            "year_built": self.year_built,
            "has_elevator": self.has_elevator,
            "heating": self.heating.value if self.heating else None,
            "has_air_conditioning": self.has_air_conditioning,
            "has_garage": self.has_garage,
            "is_furnished": self.is_furnished,
            "energy_class": self.energy_class,
            "energy_consumption": self.energy_consumption,
            "features": self.features,
            "scrape_date": self.scrape_date.isoformat(),
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "raw_html_file": self.raw_html_file,
            "code": self.code
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Listing':
        """Create listing from dictionary."""
        return cls(
            title=data["title"],
            agency=data["agency"],
            url=data["url"],
            description=data["description"],
            contract_type=Contract(data["contract_type"]),
            price=data["price"],
            city=data["city"],
            neighborhood=data.get("neighborhood"),
            address=data.get("address"),
            rooms=data.get("rooms"),
            bedrooms=data.get("bedrooms"),
            bathrooms=data.get("bathrooms"),
            square_meters=data.get("square_meters"),
            floor=data.get("floor"),
            year_built=data.get("year_built"),
            has_elevator=data.get("has_elevator"),
            heating=Riscaldamento(data["heating"]) if data.get("heating") else None,
            has_air_conditioning=data.get("has_air_conditioning"),
            has_garage=data.get("has_garage"),
            is_furnished=data.get("is_furnished"),
            energy_class=data.get("energy_class"),
            energy_consumption=data.get("energy_consumption"),
            features=data.get("features"),
            scrape_date=datetime.fromisoformat(data["scrape_date"]),
            publication_date=datetime.fromisoformat(data["publication_date"]) if data.get("publication_date") else None,
            raw_html_file=data.get("raw_html_file"),
            code=data.get("code")
        )

    def clean_price(self, price_str: str) -> float:
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

    def clean_square_meters(self, mq_str: str) -> Optional[int]:
        """Clean and convert square meters string to integer."""
        if not mq_str:
            return None
        
        # Extract numbers only
        numbers = re.findall(r'\d+', mq_str)
        if numbers:
            return int(numbers[0])
        return None