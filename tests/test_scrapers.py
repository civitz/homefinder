"""
Scraper tests using YAML-based test data.

This module contains tests that validate the scraper functionality against
real-world examples stored as HTML files with corresponding YAML files
describing the expected parsed results.
"""

import pytest
import yaml
from pathlib import Path
from tests.test_data import load_test_data
from models import Listing


@pytest.mark.parametrize("test_case", load_test_data(), ids=[case["name"] for case in load_test_data()])
def test_scraper_full_parsing(test_case):
    """Test that scrapers correctly parse example HTML files against YAML expectations."""
    
    # Load HTML content
    with open(test_case["html_file"], 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Create scraper instance
    scraper = test_case["scraper_class"]()

    # Parse HTML
    listing = scraper._parse_html(html_content, test_case["html_file"])

    # Validate against expected data
    expected = test_case["expected"]

    # Check all expected fields
    for field_name, expected_value in expected.items():
        if expected_value is None:
            # Field should not be present or should be None
            actual_value = getattr(listing, field_name, None)
            assert actual_value is None, (
                f"Field {field_name} should be None but got {actual_value}"
            )
        else:
            # Field should match expected value
            actual_value = getattr(listing, field_name)
            assert actual_value == expected_value, (
                f"Field {field_name} mismatch: "
                f"expected {expected_value} ({type(expected_value)}), "
                f"got {actual_value} ({type(actual_value)})"
            )

    # Additional validations that should apply to all listings
    assert listing.agency == scraper.__class__.__name__.replace("Scraper", " Immobiliare")
    assert listing.url == test_case["html_file"]
    assert listing.raw_html_file == test_case["html_file"]
    assert isinstance(listing, Listing)


def test_yaml_files_exist():
    """Test that all HTML files in examples have corresponding YAML files."""
    examples_dir = Path("examples")
    
    # Find all HTML files
    html_files = list(examples_dir.rglob("*.html"))
    
    # Check each HTML file has a corresponding YAML file
    missing_yaml = []
    for html_file in html_files:
        yaml_file = html_file.with_suffix(".yaml")
        if not yaml_file.exists():
            missing_yaml.append(str(html_file))
    
    assert len(missing_yaml) == 0, (
        f"The following HTML files are missing corresponding YAML files: {missing_yaml}"
    )


def test_yaml_files_valid():
    """Test that all YAML files in examples are valid and can be loaded."""
    examples_dir = Path("examples")
    
    # Find all YAML files
    yaml_files = list(examples_dir.rglob("*.yaml"))
    
    # Try to load each YAML file
    invalid_yaml = []
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
        except Exception as e:
            invalid_yaml.append(f"{yaml_file}: {e}")
    
    assert len(invalid_yaml) == 0, (
        f"The following YAML files are invalid: {invalid_yaml}"
    )