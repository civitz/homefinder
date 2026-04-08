# Virtualhost Configuration for Notification URLs

## Overview
This document outlines the implementation plan for making notification URLs configurable through a virtualhost setting stored in the database.

## Requirements

### Core Requirements
1. **Property name**: `virtualhost`
2. **Default value**: `null` in database
3. **Fallback behavior**: When virtualhost is null, automatically use `http://localhost:<FLASK_PORT>`
4. **Direct usage**: When virtualhost has a value, use the full string directly
5. **No separate protocol property**: Protocol is included in the virtualhost string if needed
6. **FLASK_PORT usage**: Ensure main.py uses the FLASK_PORT configuration

## Implementation Plan

### 1. Database Configuration Changes

**File**: `database.py`
**Method**: `_ensure_configurations_table()` around line 1553-1566

```python
# Add to defaults list
defaults = [
    # ... existing defaults ...
    (
        "virtualhost",
        "string",
        None,  # NULL default value
        "Virtualhost for internal URLs in notifications (full URL or hostname:port). If null, uses localhost:FLASK_PORT",
    ),
]
```

### 2. Notification Service Changes

**File**: `notification_service.py`

#### Import Addition
```python
# Add at top of file
from config import FLASK_PORT
```

#### New Method
```python
def _get_virtualhost_url(self) -> str:
    """Get virtualhost URL for internal links.
    
    Returns:
        Full URL string for internal links in notifications
    """
    try:
        config = self.db_manager.get_config("virtualhost")
        if config and config.config_value:
            # If virtualhost is configured, use it directly
            virtualhost = config.config_value.strip()
            # If it starts with http:// or https://, use as-is
            if virtualhost.startswith(('http://', 'https://')):
                return virtualhost
            else:
                # Assume it's hostname:port format, add http://
                return f"http://{virtualhost}"
    except Exception as e:
        self.logger.warning(f"Could not get virtualhost configuration: {e}")

    # Fallback: use localhost with FLASK_PORT
    return f"http://localhost:{FLASK_PORT}"
```

#### Update Existing Method
```python
def _format_notification_message(self, listing: Listing, subscription_name: str = "") -> str:
    """Format a notification message for a listing using configurable template."""
    try:
        template = self._get_notification_template()
        if not template:
            template = self._get_default_template()

        agency_name = listing.get_agency_name(self.db_manager)

        # Use configurable virtualhost URL
        internal_url = f"{self._get_virtualhost_url()}/properties/{listing.id}"

        location = listing.city
        if listing.neighborhood:
            location += f", {listing.neighborhood}"

        description = ""
        if listing.description:
            description = listing.description[:100]
            if len(listing.description) > 100:
                description += "..."

        placeholders = {
            "title": listing.title,
            "agency": agency_name,
            "price": f"{listing.price:,.0f}",
            "size": str(listing.square_meters) if listing.square_meters else "N/A",
            "location": location,
            "url": listing.url,
            "subscription_name": subscription_name,
            "description": description,
            "internal_url": internal_url,
        }

        message = template
        for key, value in placeholders.items():
            placeholder = "{" + key + "}"
            message = message.replace(placeholder, str(value))

        return message

    except Exception as e:
        self.logger.error(f"Error formatting notification message: {e}")
        return self._get_default_message(listing, subscription_name)
```

### 3. Main.py Changes

**File**: `main.py` line 181

**Current**:
```python
create_app().run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
```

**Change to**:
```python
from config import FLASK_PORT
# ...
create_app().run(host="0.0.0.0", port=FLASK_PORT, debug=True, use_reloader=False)
```

### 4. Configuration Management (Optional UI)

**File**: `main_views.py`

Add virtualhost configuration to the configuration management UI:
- Add form field for "virtualhost" configuration
- Allow setting/updating the virtualhost value
- Show current value in configuration list
- Provide examples: `"example.com:8080"` or `"https://myapp.example.com"`

## Testing Strategy

### Test Cases

1. **Null Configuration (Default)**
   - Verify URL becomes `http://localhost:5000/properties/123`
   - Test with different `FLASK_PORT` values (e.g., 8080)
   - Expected: `http://localhost:8080/properties/123`

2. **Hostname:Port Format**
   - Set virtualhost to `"example.com:8080"`
   - Verify URL becomes `http://example.com:8080/properties/123`

3. **Full URL Format**
   - Set virtualhost to `"https://myapp.example.com"`
   - Verify URL becomes `https://myapp.example.com/properties/123`

4. **Edge Cases**
   - Empty string configuration → should fallback
   - Whitespace-only string → should fallback after strip()
   - Invalid formats → should be used as-is (no validation)

### Test Methods

1. **Unit Tests**: Test `_get_virtualhost_url()` method with various inputs
2. **Integration Tests**: Test full notification generation pipeline
3. **Manual Testing**: Verify actual Telegram notifications contain correct URLs
4. **Regression Testing**: Ensure existing functionality remains unchanged

## Backward Compatibility

- **Existing installations**: Will have `null` virtualhost by default
- **Behavior**: Remains exactly the same as current implementation
- **No breaking changes**: All existing code continues to work
- **Gradual migration**: Administrators can configure virtualhost when needed

## Deployment Steps

1. **Update database initialization** with new configuration
2. **Update notification service** logic
3. **Update main.py** to use FLASK_PORT
4. **Add UI configuration** (optional)
5. **Run comprehensive tests**
6. **Deploy to production**

## Examples

### Configuration Examples

```bash
# Set virtualhost to custom domain with port
sqlite3 properties.db "INSERT OR REPLACE INTO configurations (config_key, config_type, config_value, description) VALUES ('virtualhost', 'string', 'myapp.example.com:8080', 'Custom virtualhost')"

# Set virtualhost to full HTTPS URL
sqlite3 properties.db "INSERT OR REPLACE INTO configurations (config_key, config_type, config_value, description) VALUES ('virtualhost', 'string', 'https://secure.example.com', 'HTTPS virtualhost')"

# Reset to default (null)
sqlite3 properties.db "UPDATE configurations SET config_value = NULL WHERE config_key = 'virtualhost'"
```

### Expected Results

| Virtualhost Config | FLASK_PORT | Resulting URL |
|-------------------|------------|-------------------------------|
| `null` | 5000 | `http://localhost:5000/properties/123` |
| `null` | 8080 | `http://localhost:8080/properties/123` |
| `"example.com"` | 5000 | `http://example.com/properties/123` |
| `"example.com:8080"` | 5000 | `http://example.com:8080/properties/123` |
| `"https://secure.com"` | 5000 | `https://secure.com/properties/123` |

## Files to Modify

1. `database.py` - Add virtualhost to default configurations
2. `notification_service.py` - Implement configurable URL logic
3. `main.py` - Use FLASK_PORT for Flask app
4. `main_views.py` - (Optional) Add UI configuration

## Timeline Estimate

- **Implementation**: 1-2 hours
- **Testing**: 1 hour
- **Deployment**: 30 minutes
- **Total**: ~3 hours

## Rollback Plan

If issues arise:
1. Revert code changes
2. Remove virtualhost configuration from database if added
3. Restart application
4. Verify notifications work with original hardcoded URLs

## Success Criteria

✅ Notifications contain correct internal URLs based on configuration
✅ Default behavior matches current implementation (localhost:5000)
✅ Custom virtualhost configurations are respected
✅ No breaking changes to existing functionality
✅ Configuration can be easily changed through database or UI