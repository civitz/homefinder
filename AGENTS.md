# HomeFinder Project Context

## What the Project Is

- Web scraping and property finding tool
- Scrapes from various real estate websites
- Initially designed for Tettorosso Immobiliare website
- Downloads property listings and extracts structured data
- Provides searchable interface for Padova area real estate properties

## How the Project Works

Three-step process:

1. **Scrape**: 
   - Periodically downloads listing website pages
   - Extracts structured property data using BeautifulSoup
   - Handles multiple real estate websites

2. **Store**:
   - Stores data in structured SQLite database
   - Maintains comprehensive property information
   - Supports efficient querying and retrieval

3. **Analyze**:
   - Provides web interface for searching properties
   - Enables browsing and filtering of extracted data
   - Offers statistics and analytics features

## Libraries Used

- **BeautifulSoup**: HTML parsing and data extraction
- **requests**: HTTP requests
- **Flask**: Web framework for the user interface
- **Jinja2**: Templating engine for HTML rendering
- **python-dotenv**: Environment variable management
- **logging**: Comprehensive logging throughout the application
- **typing**: Type hints for better code maintainability
- **pathlib**: Filesystem path manipulation
- **enum**: Enumerated types for contract and heating types

## Supported websites

### Tettorosso immobiliare

- Main website: https://www.tettorossoimmobiliare.it/
- Listing page: https://www.tettorossoimmobiliare.it/immobili/
- Type of listings: rent and sell
- Type of page: continuously scrolling page, there is a "CARICA ALTRI IMMOBILI" button if other properties are available

### Galileo immobiliare

- Main website: https://www.galileoimmobiliare.it/
- Listing pages:
  - For rent: https://www.galileoimmobiliare.it/affitto/
  - For sell: https://www.galileoimmobiliare.it/immobile/
- Type of page: paginated results, pages are like this: https://www.galileoimmobiliare.it/immobile/page/<page number starting from 1>/ If page is not available, we get an HTTP 404

## File Structure and Key Functions

### Main Files

#### `config.py`
- Contains configuration constants and paths
- Key variables: `DOWNLOAD_DIR`, `LOG_FILE`

#### `scraper.py`
- Core scraping logic for extracting property data
- Key classes:
  - `Contract`: Enum for property contract types (SELL/RENT)
  - `Riscaldamento`: Enum for heating types (AUTONOMOUS/CENTRALIZED)
  - `Listing`: Main data model for property listings with comprehensive fields

#### `main.py`
- Main application entry point
- Key functions:
  - `main()`: Orchestrates the download-scrape-serve workflow
  - Sets up Flask app

#### `app.py`
- Flask application setup with routes
- Key functions:
  - Creates Flask app instance
  - Registers blueprints and routes


#### `examples/` directory

- One directory per website
- Two files per example:
  - `examples/<websitename>/page1.html` with the content of the page
  - `examples/<websitename>/page1.yaml` with the expected metadata of the page in YAML format

Purpose:
- Produce correct scraper for each site
- YAML files serve as test data and documentation
- Used by automated test suite

### Web Interface Files

#### `templates/` directory
- Contains Jinja2 templates for the web interface
- Key files:
  - `base.html`: Base template with common layout
  - `index.html`: Home page
  - `search.html`: Search interface
  - `property_detail.html`: Detailed property view
  - `stats.html`: Statistics and analytics
  - `about.html`: About page
  - `error.html`: Error page template

#### `static/` directory
- Contains static assets (CSS, JavaScript, images)

### Routes and Views

#### `views/` directory
- Contains Flask view functions
- Key files:
  - `main_views.py`: Main views (home, about, stats)
  - `property_views.py`: Property-related views (search, detail)
  - `api_views.py`: API endpoints for data access

## How to Run the Project

### Prerequisites

1. Use UV and virtualenv for package management
2. Python 3.8 or higher
3. Install required packages: `uv pip install -r requirements.txt`

### Running Tests

To run the test suite:
```bash
source .venv/bin/activate
python -m pytest tests/
```

This validates scraper functionality against example HTML files and YAML expectations.

Run tests before and after every new feature.

Every new feature must be supported by new tests.
In fact: new features should start with a failing test.

### Running the Application

Enable virtualenv and run the application:
```bash
source .venv/bin/activate
python main.py
```
This will automatically:
- Download the website (if not already downloaded)
- Scrape all property data
- Start the Flask web server

### Access the application

- Open browser to `http://localhost:5000`
- Use the search interface to find properties
- Browse individual property details


### Development Mode

```bash
FLASK_ENV=development FLASK_DEBUG=1 python main.py
```

This enables:
- Auto-reloading on code changes
- Debug mode with detailed error pages
- Development logging with verbose output

## Key Features

- **Comprehensive Data Extraction**: Extracts 20+ fields from each property listing
- **Caching**: Respects cache headers to avoid unnecessary downloads
- **Error Handling**: Robust error handling and logging
- **Search Functionality**: Advanced search by location, price, size, etc.
- **Data Export**: Ability to export data to JSON/CSV

## Data Model (Listing)

The main data structure includes:
- Basic info: title, agency, URL, description
- Financial: contract type, price
- Physical: rooms, square meters, floor, year built
- Features: heating, air conditioning, elevator, garage, furnished
- Energy: energy class
- Metadata: scrape date, publication date, raw HTML file reference

## Future Enhancements

- iframe of the original webpage
- edit info in detail page, save as example
- periodic assessment of "is this listing still up?"
- Property comparison tools
- Telegram alerts for new listings with filters
