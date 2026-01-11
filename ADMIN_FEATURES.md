# HomeFinder Admin Features

This document describes the new admin features added to HomeFinder.

## Overview

The admin dashboard provides a web interface and API endpoints for managing the HomeFinder application, including:

1. **Force-launch scraping** - Manually trigger property scraping
2. **Remove all properties** - Clear the database of all property listings

## Accessing the Admin Dashboard

### Web Interface

The admin dashboard is accessible at: `http://localhost:5000/admin`

A new "Admin" link has been added to the navigation bar for easy access.

### API Endpoints

Two new API endpoints are available:

- **POST `/api/scrape`** - Trigger manual scraping
- **POST `/api/clear`** - Clear all properties (requires confirmation)

## Features

### 1. Force-Launch Scraping

**Web Interface:**
- Click the "Launch Scraping Now" button on the admin page
- Runs in the background (doesn't block the UI)
- Shows success message when launched

**API Usage:**
```bash
curl -X POST http://localhost:5000/api/scrape
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "started",
    "message": "Scraping launched in background",
    "params": {}
  }
}
```

### 2. Remove All Properties

**Web Interface:**
- Click the "Delete All Properties" button on the admin page
- Requires JavaScript confirmation before proceeding
- Shows success message with count of deleted properties

**API Usage:**
```bash
curl -X POST http://localhost:5000/api/clear \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully removed 16 properties from the database",
  "count": 16
}
```

## Database Statistics

The admin dashboard displays real-time statistics:

- **Total Properties** - Number of properties in the database
- **Average Price** - Average price of all properties
- **Average Size** - Average size in square meters
- **Last Updated** - When the database was last updated

## Implementation Details

### Database Changes

Added `clear_all_listings()` method to `DatabaseManager` class:
- Removes all listings from the database
- Returns the count of deleted properties
- Logs the operation for auditing

### Background Scraper Changes

Enhanced `BackgroundScraper` with global instance management:
- Added `get_background_scraper()` function to retrieve the global instance
- Added `set_background_scraper()` function to set the global instance
- Main application sets the global instance on startup

### New Routes

**Web Routes (in `views/main_views.py`):**
- `GET /admin` - Admin dashboard page
- `POST /admin/scrape` - Trigger manual scraping
- `POST /admin/clear` - Clear all properties (with confirmation)

**API Routes (in `views/api_views.py`):**
- `POST /api/scrape` - Trigger manual scraping via API
- `POST /api/clear` - Clear all properties via API (requires confirmation)

### New Template

Created `templates/admin.html`:
- Responsive Bootstrap-based interface
- Database statistics cards
- Action buttons with appropriate styling
- Confirmation for destructive actions
- API documentation section

## Security Considerations

**Current Implementation:**
- Admin page is publicly accessible (as requested)
- Clear operation requires JavaScript confirmation
- API clear operation requires explicit confirmation flag

**Production Recommendations:**
- Add authentication (basic auth, API keys, or session-based)
- Implement rate limiting for API endpoints
- Add logging for all admin operations
- Consider adding IP restrictions for sensitive operations

## Usage Examples

### Web Interface Workflow

1. Navigate to `/admin`
2. View current database statistics
3. Click "Launch Scraping Now" to update listings
4. Click "Delete All Properties" and confirm to clear database

### API Workflow

```bash
# Check current stats
curl http://localhost:5000/api/stats

# Trigger scraping
curl -X POST http://localhost:5000/api/scrape

# Clear database (with confirmation)
curl -X POST http://localhost:5000/api/clear -H "Content-Type: application/json" -d '{"confirm": true}'
```

## Testing

A comprehensive test script is available at `test_admin_functionality.py`:

```bash
python3 test_admin_functionality.py
```

This tests:
- Database clear functionality
- Background scraper instance management
- Admin route configuration
- API endpoint functionality

## Future Enhancements

Potential improvements for future versions:

1. **Authentication** - Add user authentication for admin access
2. **Operation Logs** - Display recent admin operations on the dashboard
3. **Progress Tracking** - Show real-time progress of scraping operations
4. **Selective Clearing** - Clear properties by date range or source
5. **Export/Import** - Add database export and import functionality
6. **Scheduled Tasks** - Allow scheduling scraping at specific times
7. **Notifications** - Email or webhook notifications for completed operations

## Files Modified

- `database.py` - Added `clear_all_listings()` method
- `background_scraper.py` - Added global instance management
- `main.py` - Set global scraper instance on startup
- `views/main_views.py` - Added admin routes and logic
- `views/api_views.py` - Implemented API endpoints
- `templates/admin.html` - Created admin dashboard template
- `templates/base.html` - Added admin link to navigation

## Files Created

- `test_admin_functionality.py` - Comprehensive test suite
- `ADMIN_FEATURES.md` - This documentation file