#!/usr/bin/env python3
"""Utility functions for saving property listings as examples."""

import re
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from config import EXAMPLES_DIR


class ExampleUtils:
    """Utility class for handling example files."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.examples_dir = EXAMPLES_DIR
        
    def extract_website_from_url(self, url: str) -> Optional[str]:
        """Extract website name from URL."""
        try:
            parsed_url = urlparse(url)
            if parsed_url.netloc:
                # Remove www. prefix if present
                website = parsed_url.netloc.replace('www.', '')
                return website
            return None
        except Exception as e:
            self.logger.error(f"Error extracting website from URL {url}: {e}")
            return None

    def generate_safe_filename(self, title: str, url: str) -> str:
        """Generate a safe filename from property title and URL."""
        try:
            # Use title as base, fallback to URL path
            filename_base = title if title else url
            
            # Remove special characters and normalize
            filename = re.sub(r'[^\w\s\-]', '', filename_base)
            filename = re.sub(r'\s+', '_', filename.strip())
            filename = filename.lower()
            
            # Limit length to reasonable size
            if len(filename) > 50:
                filename = filename[:50]
            
            # Remove any trailing underscores or dashes
            filename = re.sub(r'[\_\-]+$', '', filename)
            
            return filename if filename else "property"
        except Exception as e:
            self.logger.error(f"Error generating safe filename from {title}: {e}")
            return "property"

    def save_html_example(self, html_content: str, website: str, filename: str) -> bool:
        """Save HTML content to examples directory."""
        try:
            # Create website directory if it doesn't exist
            website_dir = self.examples_dir / website
            website_dir.mkdir(parents=True, exist_ok=True)
            
            # Create HTML file path
            html_file = website_dir / f"{filename}.html"
            
            # Save HTML content
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"Saved HTML example to {html_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving HTML example {filename}.html: {e}")
            return False

    def save_yaml_example(self, property_data: Dict[str, Any], website: str, filename: str) -> bool:
        """Save property data as YAML file to examples directory."""
        try:
            # Create website directory if it doesn't exist
            website_dir = self.examples_dir / website
            website_dir.mkdir(parents=True, exist_ok=True)
            
            # Create YAML file path
            yaml_file = website_dir / f"{filename}.yaml"
            
            # Convert property data to YAML format
            yaml_data = self._convert_property_to_yaml_format(property_data)
            
            # Save YAML content
            with open(yaml_file, 'w', encoding='utf-8') as f:
                yaml.dump(yaml_data, f, sort_keys=False, allow_unicode=True)
            
            self.logger.info(f"Saved YAML example to {yaml_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving YAML example {filename}.yaml: {e}")
            return False

    def _convert_property_to_yaml_format(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert property data to the YAML format used in examples."""
        # Create a new dictionary to hold the YAML data
        yaml_data: Dict[str, Any] = {}
        
        # Add YAML comment header as separate entries (will be filtered out)
        yaml_data['__comment__'] = f'# YAML representation of the {property_data.get("agency", "Unknown")} listing'
        yaml_data['__comment2__'] = f'# {property_data.get("title", "Unknown Property")}'
        
        # Map property fields to YAML format (only include non-None values)
        # We need to handle each field individually to ensure proper typing
        fields_to_copy = [
            'title', 'price', 'location', 'bedrooms', 'bathrooms', 'square_meters',
            'agency_listing_id', 'year_built', 'energy_class', 'floor', 'has_elevator',
            'heating', 'rooms', 'has_garage', 'contract_type', 'agency', 'city', 'neighborhood'
        ]
        
        for field in fields_to_copy:
            value = property_data.get(field)
            if value is not None:
                yaml_data[field] = value
        
        # Handle special field name mappings
        if 'agency_listing_id' in yaml_data:
            yaml_data['code'] = yaml_data.pop('agency_listing_id')
        if 'year_built' in yaml_data:
            yaml_data['year'] = yaml_data.pop('year_built')
        if 'has_elevator' in yaml_data:
            yaml_data['elevator'] = yaml_data.pop('has_elevator')
        if 'has_garage' in yaml_data:
            yaml_data['garage'] = yaml_data.pop('has_garage')
        if 'contract_type' in yaml_data:
            yaml_data['contract'] = yaml_data.pop('contract_type')
        
        # Remove comment keys from final output
        clean_yaml_data = {k: v for k, v in yaml_data.items() if k not in ['__comment__', '__comment2__']}
        
        return clean_yaml_data

    def save_as_example(self, html_content: str, property_data: Dict[str, Any]) -> bool:
        """Save both HTML and YAML files as an example."""
        try:
            # Extract website from URL
            website = self.extract_website_from_url(property_data.get('url', ''))
            if not website:
                self.logger.error("Could not extract website from URL")
                return False
            
            # Generate safe filename
            filename = self.generate_safe_filename(
                property_data.get('title', ''), 
                property_data.get('url', '')
            )
            
            # Save both HTML and YAML files
            html_success = self.save_html_example(html_content, website, filename)
            yaml_success = self.save_yaml_example(property_data, website, filename)
            
            return html_success and yaml_success
            
        except Exception as e:
            self.logger.error(f"Error saving example: {e}")
            return False