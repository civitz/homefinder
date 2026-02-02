"""
Test cases for the enhanced search functionality.

This module contains tests that validate the new search filters work correctly
with proper minimum value logic, energy class hierarchy, and fuzzy neighborhood searching.
"""

import pytest
import sys
import os
from datetime import datetime

# Add the project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import DatabaseManager
from models import Listing, Contract, Riscaldamento


@pytest.fixture
def db_manager():
    """Fixture to provide a DatabaseManager instance."""
    return DatabaseManager()


@pytest.fixture
def sample_listings(db_manager):
    """Fixture to create sample listings for testing."""
    # Create sample listings with various attributes for testing
    listings = [
        Listing(
            title="Test Property 1",
            agency_id=1,
            url="http://example.com/prop1",
            description="A test property",
            contract_type=Contract.SELL,
            price=200000.0,
            city="Padova",
            neighborhood="Centro Storico",
            bedrooms=2,
            bathrooms=1,
            square_meters=80,
            year_built=2010,
            has_air_conditioning=True,
            has_garage=False,
            energy_class="B",
            heating=Riscaldamento.AUTONOMOUS,
            rooms=4
        ),
        Listing(
            title="Test Property 2",
            agency_id=1,
            url="http://example.com/prop2",
            description="Another test property",
            contract_type=Contract.RENT,
            price=1000.0,
            city="Padova",
            neighborhood="Zona Stazione",
            bedrooms=3,
            bathrooms=2,
            square_meters=100,
            year_built=2015,
            has_air_conditioning=True,
            has_garage=True,
            energy_class="A4",
            heating=Riscaldamento.CENTRALIZED,
            rooms=5
        ),
        Listing(
            title="Test Property 3",
            agency_id=2,
            url="http://example.com/prop3",
            description="Property without some features",
            contract_type=Contract.SELL,
            price=150000.0,
            city="Vicenza",
            neighborhood="Centro",
            bedrooms=1,
            bathrooms=1,
            square_meters=60,
            year_built=1995,
            has_air_conditioning=False,
            has_garage=False,
            energy_class="D",
            heating=Riscaldamento.UNKNOWN,
            rooms=3
        )
    ]
    
    # Save listings to database
    for listing in listings:
        db_manager.save_listing(listing)
    
    return listings


class TestSearchFilters:
    """Test class for search filter functionality."""
    
    def test_min_bedrooms_filter(self, db_manager, sample_listings):
        """Test that min_bedrooms filter works correctly."""
        # Test minimum bedrooms = 2
        results = db_manager.search_listings(min_bedrooms=2)
        
        # Should include properties with 2+ bedrooms
        for prop in results:
            assert prop.bedrooms is None or prop.bedrooms >= 2
        
        # Should include sample_listings[0] (2 bedrooms) and sample_listings[1] (3 bedrooms)
        # But not sample_listings[2] (1 bedroom)
        result_urls = [prop.url for prop in results]
        assert sample_listings[0].url in result_urls
        assert sample_listings[1].url in result_urls
        assert sample_listings[2].url not in result_urls
        
    def test_min_bathrooms_filter(self, db_manager, sample_listings):
        """Test that min_bathrooms filter works correctly."""
        results = db_manager.search_listings(min_bathrooms=2)
        
        # Should only include properties with 2+ bathrooms
        for prop in results:
            assert prop.bathrooms is None or prop.bathrooms >= 2
        
        # Should only include sample_listings[1] (2 bathrooms)
        result_urls = [prop.url for prop in results]
        assert sample_listings[1].url in result_urls
        assert sample_listings[0].url not in result_urls
        assert sample_listings[2].url not in result_urls
        
    def test_neighborhood_fuzzy_search(self, db_manager, sample_listings):
        """Test that neighborhood fuzzy search works correctly."""
        # Test "Centro" should match "Centro Storico" and "Centro"
        results = db_manager.search_listings(neighborhood="Centro")
        
        result_urls = [prop.url for prop in results]
        assert sample_listings[0].url in result_urls  # Centro Storico
        assert sample_listings[2].url in result_urls  # Centro
        
        # Test "Stazione" should only match "Zona Stazione"
        results = db_manager.search_listings(neighborhood="Stazione")
        result_urls = [prop.url for prop in results]
        assert sample_listings[1].url in result_urls
        assert sample_listings[0].url not in result_urls
        assert sample_listings[2].url not in result_urls
        
    def test_min_year_built_filter(self, db_manager, sample_listings):
        """Test that min_year_built filter works correctly."""
        # Test year built after 2000
        results = db_manager.search_listings(min_year_built=2000)
        
        # Should only include properties built in 2000 or later
        for prop in results:
            assert prop.year_built is None or prop.year_built >= 2000
        
        # Should include sample_listings[0] (2010) and sample_listings[1] (2015)
        # But not sample_listings[2] (1995)
        result_urls = [prop.url for prop in results]
        assert sample_listings[0].url in result_urls
        assert sample_listings[1].url in result_urls
        assert sample_listings[2].url not in result_urls
        
    def test_boolean_filters(self, db_manager, sample_listings):
        """Test that boolean filters work correctly."""
        # Test air conditioning filter
        results = db_manager.search_listings(has_air_conditioning=True)
        
        # Should only include properties with air conditioning
        for prop in results:
            assert prop.has_air_conditioning is None or prop.has_air_conditioning == True
        
        # Should include sample_listings[0] and sample_listings[1]
        # But not sample_listings[2]
        result_urls = [prop.url for prop in results]
        assert sample_listings[0].url in result_urls
        assert sample_listings[1].url in result_urls
        assert sample_listings[2].url not in result_urls
        
        # Test garage filter
        results = db_manager.search_listings(has_garage=True)
        
        # Should only include properties with garage
        for prop in results:
            assert prop.has_garage is None or prop.has_garage == True
        
        # Should only include sample_listings[1]
        result_urls = [prop.url for prop in results]
        assert sample_listings[1].url in result_urls
        assert sample_listings[0].url not in result_urls
        assert sample_listings[2].url not in result_urls
        
    def test_energy_class_hierarchy(self, db_manager, sample_listings):
        """Test that energy class filtering respects the hierarchy."""
        # Test A4 (best) - should only include properties with A4
        results = db_manager.search_listings(min_energy_class="A4")
        result_urls = [prop.url for prop in results]
        assert sample_listings[1].url in result_urls  # A4
        assert sample_listings[0].url not in result_urls  # B
        assert sample_listings[2].url not in result_urls  # D
        
        # Test B - should include A4 and B (better than or equal to B)
        results = db_manager.search_listings(min_energy_class="B")
        result_urls = [prop.url for prop in results]
        assert sample_listings[0].url in result_urls  # B
        assert sample_listings[1].url in result_urls  # A4
        assert sample_listings[2].url not in result_urls  # D
        
        # Test D - should include A4, B, and D
        results = db_manager.search_listings(min_energy_class="D")
        result_urls = [prop.url for prop in results]
        assert sample_listings[0].url in result_urls  # B
        assert sample_listings[1].url in result_urls  # A4
        assert sample_listings[2].url in result_urls  # D
        
    def test_heating_filter(self, db_manager, sample_listings):
        """Test that heating type filter works correctly."""
        # Test autonomous heating
        results = db_manager.search_listings(heating="autonomous")
        result_urls = [prop.url for prop in results]
        assert sample_listings[0].url in result_urls
        assert sample_listings[1].url not in result_urls
        assert sample_listings[2].url not in result_urls
        
        # Test centralized heating
        results = db_manager.search_listings(heating="centralized")
        result_urls = [prop.url for prop in results]
        assert sample_listings[1].url in result_urls
        assert sample_listings[0].url not in result_urls
        assert sample_listings[2].url not in result_urls
        
    def test_min_rooms_filter(self, db_manager, sample_listings):
        """Test that min_rooms filter works correctly."""
        # Test minimum rooms = 4
        results = db_manager.search_listings(min_rooms=4)
        
        # Should only include properties with 4+ rooms
        for prop in results:
            assert prop.rooms is None or prop.rooms >= 4
        
        # Should include sample_listings[0] (4 rooms) and sample_listings[1] (5 rooms)
        # But not sample_listings[2] (3 rooms)
        result_urls = [prop.url for prop in results]
        assert sample_listings[0].url in result_urls
        assert sample_listings[1].url in result_urls
        assert sample_listings[2].url not in result_urls
        
    def test_combined_filters(self, db_manager, sample_listings):
        """Test that multiple filters work together correctly."""
        # Test combination of filters
        results = db_manager.search_listings(
            city="Padova",
            min_bedrooms=2,
            has_air_conditioning=True,
            min_energy_class="B"
        )
        
        result_urls = [prop.url for prop in results]
        
        # Should include sample_listings[0] (Padova, 2 beds, AC, B energy)
        assert sample_listings[0].url in result_urls
        
        # Should include sample_listings[1] (Padova, 3 beds, AC, A4 energy)
        assert sample_listings[1].url in result_urls
        
        # Should not include sample_listings[2] (Vicenza, 1 bed, no AC, D energy)
        assert sample_listings[2].url not in result_urls
        
        # Verify all results meet all criteria
        for prop in results:
            assert prop.city == "Padova"
            assert prop.bedrooms is None or prop.bedrooms >= 2
            assert prop.has_air_conditioning is None or prop.has_air_conditioning == True
            # Energy class check is more complex due to hierarchy
            if prop.energy_class:
                energy_hierarchy = {'A4': 1, 'A3': 2, 'A2': 3, 'A1': 4, 'A': 5, 'B': 6, 'C': 7, 'D': 8, 'E': 9, 'F': 10, 'G': 11}
                assert energy_hierarchy.get(prop.energy_class, 12) <= 6  # B or better
        
    def test_null_value_inclusion(self, db_manager):
        """Test that filters properly include properties with NULL values."""
        # Create a listing with some NULL values
        null_listing = Listing(
            title="Property with NULLs",
            agency_id=1,
            url="http://example.com/null_prop",
            description="Property with missing data",
            contract_type=Contract.SELL,
            price=100000.0,
            city="Padova",
            neighborhood=None,  # NULL neighborhood
            bedrooms=None,  # NULL bedrooms
            bathrooms=1,
            square_meters=50,
            year_built=None,  # NULL year
            has_air_conditioning=None,  # NULL AC
            has_garage=None,  # NULL garage
            energy_class=None,  # NULL energy class
            heating=None,  # NULL heating
            rooms=None  # NULL rooms
        )
        
        db_manager.save_listing(null_listing)
        
        # Test that NULL values are included in filters
        results = db_manager.search_listings(
            city="Padova",
            min_bedrooms=1,  # Should include NULL
            min_bathrooms=1,
            min_year_built=2000,  # Should include NULL
            has_air_conditioning=True,  # Should include NULL
            has_garage=True,  # Should include NULL
            min_energy_class="C",  # Should include NULL
            min_rooms=1  # Should include NULL
        )
        
        # The NULL listing should be included in results
        result_urls = [prop.url for prop in results]
        assert null_listing.url in result_urls
        
        # Clean up
        db_manager._get_connection().execute("DELETE FROM listings WHERE url = ?", (null_listing.url,))
        db_manager._get_connection().commit()


class TestSearchIntegration:
    """Integration tests for search functionality."""
    
    def test_search_with_existing_data(self, db_manager):
        """Test search functionality with existing database data."""
        # Test that we can search existing data
        all_properties = db_manager.search_listings()
        assert len(all_properties) > 0
        
        # Test city filter
        padova_properties = db_manager.search_listings(city="Padova")
        assert len(padova_properties) > 0
        
        # Test that all results are from Padova
        for prop in padova_properties:
            assert prop.city == "Padova"
        
    def test_energy_class_hierarchy_with_real_data(self, db_manager):
        """Test energy class hierarchy with real database data."""
        # Get properties with energy classes
        properties_with_energy = [
            prop for prop in db_manager.search_listings() 
            if prop.energy_class is not None
        ]
        
        if len(properties_with_energy) > 0:
            # Test that A4 (best) returns fewer or equal results than B
            a4_results = db_manager.search_listings(min_energy_class="A4")
            b_results = db_manager.search_listings(min_energy_class="B")
            
            assert len(a4_results) <= len(b_results)
            
            # Test that G (worst) returns most results
            g_results = db_manager.search_listings(min_energy_class="G")
            assert len(g_results) >= len(b_results)
