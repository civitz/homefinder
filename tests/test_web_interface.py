"""
Test cases for the web interface search functionality.

This module contains tests that validate the Flask routes and web interface
for the enhanced search functionality.
"""

import pytest
import sys
import os

# Add the project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app


@pytest.fixture
def client():
    """Fixture to provide a test client for the Flask app."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        yield client


class TestWebSearchInterface:
    """Test class for web search interface functionality."""
    
    def test_search_page_loads(self, client):
        """Test that the search page loads successfully."""
        response = client.get('/properties/', follow_redirects=True)
        assert response.status_code == 200
        assert b'Search Properties' in response.data
        
    def test_search_page_contains_new_filters(self, client):
        """Test that the search page contains all new filter fields."""
        response = client.get('/properties/', follow_redirects=True)
        html_content = response.data.decode('utf-8')
        
        # Check for new filter fields
        assert 'min_bedrooms' in html_content
        assert 'min_bathrooms' in html_content
        assert 'neighborhood' in html_content
        assert 'min_year_built' in html_content
        assert 'has_air_conditioning' in html_content
        assert 'has_garage' in html_content
        assert 'min_energy_class' in html_content
        assert 'heating' in html_content
        assert 'min_rooms' in html_content
        
    def test_search_with_new_parameters(self, client):
        """Test that search works with new filter parameters."""
        response = client.get('/properties/?city=Padova&min_bedrooms=2&has_air_conditioning=on', follow_redirects=True)
        assert response.status_code == 200
        
    def test_search_preserves_filter_values(self, client):
        """Test that search results page preserves filter values in form."""
        response = client.get('/properties/?city=Padova&min_bedrooms=2&min_bathrooms=1', follow_redirects=True)
        html_content = response.data.decode('utf-8')
        
        # Check that filter values are preserved
        assert 'value="Padova"' in html_content
        assert 'value="2"' in html_content  # min_bedrooms
        assert 'value="1"' in html_content  # min_bathrooms
        
    def test_api_search_with_new_parameters(self, client):
        """Test that API search works with new filter parameters."""
        response = client.get('/properties/api/search?city=Padova&min_energy_class=B&min_bedrooms=2')
        assert response.status_code == 200
        
        # Check that response is JSON
        assert response.content_type == 'application/json'
        
        # Check that response contains expected data
        data = response.get_json()
        assert 'success' in data
        assert 'results' in data
        assert 'total' in data
        assert 'params' in data
        
        # Check that params contain our filters
        assert data['params']['city'] == 'Padova'
        assert data['params']['min_energy_class'] == 'B'
        assert data['params']['min_bedrooms'] == '2'
        
    def test_api_search_boolean_parameters(self, client):
        """Test that API search handles boolean parameters correctly."""
        response = client.get('/properties/api/search?has_air_conditioning=true&has_garage=false')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] == True
        assert 'results' in data
        
    def test_search_with_all_new_filters(self, client):
        """Test search with all new filter parameters simultaneously."""
        params = {
            'city': 'Padova',
            'min_bedrooms': '2',
            'min_bathrooms': '1',
            'neighborhood': 'Centro',
            'min_year_built': '2000',
            'has_air_conditioning': 'on',
            'has_garage': 'on',
            'min_energy_class': 'B',
            'heating': 'autonomous',
            'min_rooms': '3'
        }
        
        response = client.get('/properties/', query_string=params, follow_redirects=True)
        assert response.status_code == 200
        
        # Verify that the response contains search results
        html_content = response.data.decode('utf-8')
        assert 'Search Results' in html_content
        
    def test_api_search_with_all_new_filters(self, client):
        """Test API search with all new filter parameters simultaneously."""
        params = {
            'city': 'Padova',
            'min_bedrooms': '2',
            'min_bathrooms': '1',
            'neighborhood': 'Centro',
            'min_year_built': '2000',
            'has_air_conditioning': 'true',
            'has_garage': 'true',
            'min_energy_class': 'B',
            'heating': 'autonomous',
            'min_rooms': '3'
        }
        
        response = client.get('/properties/api/search', query_string=params)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] == True
        assert isinstance(data['results'], list)
        assert data['total'] >= 0
        
        # Verify all parameters are in the response
        for key, value in params.items():
            assert data['params'][key] == value


class TestWebSearchEdgeCases:
    """Test edge cases for web search functionality."""
    
    def test_search_with_empty_parameters(self, client):
        """Test that search works when parameters are empty."""
        response = client.get('/properties/?city=&min_bedrooms=&min_bathrooms=', follow_redirects=True)
        assert response.status_code == 200
        
    def test_search_with_invalid_parameters(self, client):
        """Test that search handles invalid parameters gracefully."""
        response = client.get('/properties/?city=Padova&min_bedrooms=invalid&min_bathrooms=not_a_number', follow_redirects=True)
        assert response.status_code == 200
        
    def test_api_search_with_invalid_parameters(self, client):
        """Test that API search handles invalid parameters gracefully."""
        response = client.get('/properties/api/search?min_bedrooms=invalid&min_bathrooms=not_a_number')
        assert response.status_code == 200
        
        data = response.get_json()
        # Should still succeed but might have fewer results
        assert 'success' in data
        assert 'results' in data
        
    def test_search_with_very_large_numbers(self, client):
        """Test that search handles very large numbers."""
        response = client.get('/properties/?min_bedrooms=100&min_bathrooms=50&min_rooms=100', follow_redirects=True)
        assert response.status_code == 200
        
        # Should return empty or minimal results but not crash
        html_content = response.data.decode('utf-8')
        assert 'Search Results' in html_content
        
    def test_energy_class_case_insensitive(self, client):
        """Test that energy class filtering is case insensitive."""
        # Test lowercase
        response = client.get('/properties/api/search?min_energy_class=b')
        assert response.status_code == 200
        
        # Test uppercase
        response = client.get('/properties/api/search?min_energy_class=B')
        assert response.status_code == 200
        
        # Both should return the same number of results
        data1 = response.get_json()
        response = client.get('/properties/api/search?min_energy_class=b')
        data2 = response.get_json()
        
        assert data1['total'] == data2['total']