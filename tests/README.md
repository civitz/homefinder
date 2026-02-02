# HomeFinder Test Suite

This directory contains the comprehensive test suite for the HomeFinder application.

## Test Files

### `test_search.py`
Comprehensive tests for the enhanced search functionality:

- **`TestSearchFilters`**: Tests individual filter functionality
  - `test_min_bedrooms_filter`: Tests minimum bedrooms filtering
  - `test_min_bathrooms_filter`: Tests minimum bathrooms filtering
  - `test_neighborhood_fuzzy_search`: Tests fuzzy neighborhood search
  - `test_min_year_built_filter`: Tests year built filtering
  - `test_boolean_filters`: Tests air conditioning and garage filters
  - `test_energy_class_hierarchy`: Tests energy class hierarchy (A4 > A3 > ... > G)
  - `test_heating_filter`: Tests heating type filtering
  - `test_min_rooms_filter`: Tests minimum rooms filtering
  - `test_combined_filters`: Tests multiple filters working together
  - `test_null_value_inclusion`: Tests that NULL values are properly included

- **`TestSearchIntegration`**: Integration tests with real database data
  - `test_search_with_existing_data`: Tests search with existing database
  - `test_energy_class_hierarchy_with_real_data`: Tests hierarchy with real data

### `test_web_interface.py`
Tests for the web interface and API endpoints:

- **`TestWebSearchInterface`**: Tests web search interface
  - `test_search_page_loads`: Tests that search page loads
  - `test_search_page_contains_new_filters`: Tests new filter fields are present
  - `test_search_with_new_parameters`: Tests search with new parameters
  - `test_search_preserves_filter_values`: Tests filter value preservation
  - `test_api_search_with_new_parameters`: Tests API search functionality
  - `test_api_search_boolean_parameters`: Tests boolean parameter handling
  - `test_search_with_all_new_filters`: Tests all filters simultaneously
  - `test_api_search_with_all_new_filters`: Tests API with all filters

- **`TestWebSearchEdgeCases`**: Tests edge cases and error handling
  - `test_search_with_empty_parameters`: Tests empty parameter handling
  - `test_search_with_invalid_parameters`: Tests invalid parameter handling
  - `test_api_search_with_invalid_parameters`: Tests API invalid parameters
  - `test_search_with_very_large_numbers`: Tests large number handling
  - `test_energy_class_case_insensitive`: Tests case-insensitive energy class

### `test_scrapers.py`
Tests for the web scraping functionality:

- `test_scraper_full_parsing`: Tests scraper parsing against YAML expectations
- `test_yaml_files_exist`: Tests that all HTML files have corresponding YAML files
- `test_yaml_files_valid`: Tests that all YAML files are valid

### `test_data.py`
Test data loader for scraper tests:

- Provides functionality to discover and load test cases from YAML files
- Converts YAML data to expected test format
- Handles field mapping and type conversion

## Running Tests

To run all tests:
```bash
python -m pytest tests/ -v
```

To run specific test files:
```bash
python -m pytest tests/test_search.py -v
python -m pytest tests/test_web_interface.py -v
python -m pytest tests/test_scrapers.py -v
```

## Test Coverage

The test suite provides comprehensive coverage of:

1. **Database Search Functionality**: All new filters are thoroughly tested
2. **Web Interface**: Both HTML and API endpoints are tested
3. **Edge Cases**: Invalid inputs, empty parameters, and large numbers
4. **Integration**: Tests with real database data
5. **Scraper Functionality**: Existing scraper tests are maintained

## Key Features Tested

- **Energy Class Hierarchy**: A4 > A3 > A2 > A1 > A > B > C > D > E > F > G
- **Fuzzy Neighborhood Search**: Partial matching with SQLite LIKE
- **NULL Value Inclusion**: Properties without values are included in results
- **Minimum Value Logic**: All numeric filters use >= for proper minimum filtering
- **Boolean Filters**: Proper checkbox handling
- **Combined Filters**: Multiple filters work together correctly
- **Case Insensitivity**: Energy class filtering is case insensitive
- **Error Handling**: Graceful handling of invalid inputs

## Test Data

The `test_data.py` module loads test cases from the `examples/` directory, where each website has:
- HTML files with example property listings
- YAML files with expected parsed results

This allows easy addition of new test cases by simply adding HTML/YAML file pairs.