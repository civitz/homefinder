"""
Test data loader for scraper tests.

This module provides functionality to discover and load test cases from YAML files
in the examples directory, making it easy to add new test cases by simply adding
HTML and YAML files.
"""

import yaml
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import Contract, Riscaldamento


class TestDataLoader:
    """Load and manage test data for scraper tests from YAML files."""

    def __init__(self, base_dir: Path = Path("examples")):
        self.base_dir = base_dir
        self.test_cases = self._discover_test_cases()

    def _discover_test_cases(self) -> List[Dict[str, Any]]:
        """Discover all test cases from the examples directory."""
        test_cases = []

        # Find all YAML files in examples directory
        for yaml_file in self.base_dir.rglob("*.yaml"):
            # Look for corresponding HTML file
            html_file = yaml_file.with_suffix(".html")
            if html_file.exists():
                test_case = self._load_test_case(html_file, yaml_file)
                if test_case:
                    test_cases.append(test_case)

        return test_cases

    def _load_test_case(self, html_file: Path, yaml_file: Path) -> Optional[Dict[str, Any]]:
        """Load a test case from HTML and YAML files."""
        try:
            # Load YAML data
            with open(yaml_file, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)

            # Determine scraper class based on website
            website = html_file.parts[html_file.parts.index("examples") + 1]

            if "tettorossoimmobiliare.it" in website:
                from scraper import TettorossoScraper
                scraper_class = TettorossoScraper
            elif "galileoimmobiliare.it" in website:
                from scraper import GalileoScraper
                scraper_class = GalileoScraper
            else:
                return None

            # Convert YAML data to expected format
            expected_data = self._convert_yaml_to_expected(yaml_data)

            return {
                "name": f"{website}_{html_file.stem}",
                "scraper_class": scraper_class,
                "html_file": str(html_file),
                "yaml_file": str(yaml_file),
                "expected": expected_data
            }

        except Exception as e:
            print(f"Error loading test case {yaml_file}: {e}")
            return None

    def _convert_yaml_to_expected(self, yaml_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert YAML data to the expected test format."""
        expected = {}

        # Map YAML fields to expected test fields
        field_mapping = {
            "title": "title",
            "price": "price", 
            "bedrooms": "bedrooms",
            "bathrooms": "bathrooms",
            "square_meters": "square_meters",
            "code": "agency_listing_id",
            "year": "year_built",
            "energy_class": "energy_class",
            "elevator": "has_elevator",
            "garage": "has_garage",
            "contract": "contract_type",
            "city": "city",
            "neighborhood": "neighborhood",
            "heating": "heating"
        }

        for yaml_field, expected_field in field_mapping.items():
            if yaml_field in yaml_data:
                value = yaml_data[yaml_field]
                
                # Convert to appropriate types
                if expected_field in ["bedrooms", "bathrooms", "square_meters", "year_built"]:
                    expected[expected_field] = int(value) if value is not None else None
                elif expected_field in ["price"]:
                    expected[expected_field] = float(value) if value is not None else 0.0
                elif expected_field in ["has_elevator", "has_garage"]:
                    expected[expected_field] = bool(value) if value is not None else None
                elif expected_field == "contract_type":
                    expected[expected_field] = Contract.from_string(str(value))
                elif expected_field == "heating":
                    if value:
                        expected[expected_field] = Riscaldamento.from_string(str(value))
                    else:
                        expected[expected_field] = None
                else:
                    expected[expected_field] = value

        return expected


def load_test_data() -> List[Dict[str, Any]]:
    """Load all test cases from examples directory."""
    loader = TestDataLoader()
    return loader.test_cases


if __name__ == "__main__":
    # Test the loader
    loader = TestDataLoader()
    print(f"Found {len(loader.test_cases)} test cases:")
    for case in loader.test_cases:
        print(f"  - {case['name']}: {case['html_file']}")