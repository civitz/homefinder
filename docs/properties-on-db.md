# Configurable Notification Text via Web - Implementation Plan

## Overview

This document outlines the implementation of configurable notification text templates for the HomeFinder application. Users will be able to customize the notification message format via the web admin interface.

## 1. Database Schema Changes

### 1.1 New Table: `configurations`

Create a generic configurations table to store global application settings:

```sql
CREATE TABLE IF NOT EXISTS configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,
    config_type TEXT NOT NULL CHECK(config_type IN ('string', 'integer', 'boolean', 'json')),
    config_value TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 1.2 Column Descriptions

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key, auto-incremented |
| `config_key` | TEXT | Unique key for the configuration (e.g., `notification_template`, `notification_enabled`) |
| `config_type` | TEXT | Type of value: `string`, `integer`, `boolean`, or `json` |
| `config_value` | TEXT | The configuration value stored as text |
| `description` | TEXT | Optional description of what this configuration does |
| `is_active` | BOOLEAN | Whether this configuration is active |
| `created_at` | TEXT | ISO timestamp of creation |
| `updated_at` | TEXT | ISO timestamp of last update |

### 1.3 Initial Configurations

On first run, create default configurations:

| config_key | config_type | config_value | description |
|------------|-------------|--------------|-------------|
| `notification_enabled` | boolean | `true` | Whether notifications are enabled globally |
| `notification_template` | json | (see below) | Default notification message template |

#### Default Notification Template (JSON)

```json
{
  "template": "🏠 *New Property Alert* 🏠\n\n🔔 *Subscription*: {subscription_name}\n\n📍 *{title}*\n🏢 *Agency*: {agency}\n💰 *Price*: €{price}\n📏 *Size*: {size} m²\n📍 *Location*: {location}\n🔗 *Details*: {url}\n📝 *Description*: {description}",
  "placeholders": {
    "title": "Property title",
    "agency": "Agency name",
    "price": "Price in euros (formatted with thousands separator)",
    "size": "Property size in square meters",
    "location": "City and neighborhood",
    "url": "Original property URL",
    "subscription_name": "Name of the notification subscription",
    "description": "Property description (truncated to 100 chars)",
    "internal_url": "HomeFinder internal property detail URL"
  },
  "enabled_placeholders": ["title", "agency", "price", "size", "location", "url", "subscription_name", "description", "internal_url"]
}
```

## 2. Data Models

### 2.1 New Dataclass: `Configuration`

Add to `models.py`:

```python
from dataclasses import dataclass
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum

class ConfigType(Enum):
    """Configuration value types."""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    JSON = "json"

@dataclass
class Configuration:
    """Data model for application configurations."""
    config_key: str
    config_type: ConfigType
    config_value: str
    description: Optional[str] = None
    is_active: bool = True
    id: Optional[int] = None
    created_at: str = ""
    updated_at: str = ""

    def get_typed_value(self) -> Any:
        """Return the config value cast to its proper type."""
        if self.config_type == ConfigType.BOOLEAN:
            return self.config_value.lower() in ('true', '1', 'yes')
        elif self.config_type == ConfigType.INTEGER:
            return int(self.config_value)
        elif self.config_type == ConfigType.JSON:
            import json
            return json.loads(self.config_value)
        else:
            return self.config_value

    def set_typed_value(self, value: Any) -> None:
        """Set the config value from a typed value."""
        if self.config_type == ConfigType.BOOLEAN:
            self.config_value = str(bool(value)).lower()
        elif self.config_type == ConfigType.INTEGER:
            self.config_value = str(int(value))
        elif self.config_type == ConfigType.JSON:
            import json
            self.config_value = json.dumps(value)
        else:
            self.config_value = str(value)
```

## 3. DatabaseManager Methods

### 3.1 New Methods to Add

Add these methods to `database.py`:

#### `_ensure_configurations_table()`

```python
def _ensure_configurations_table(self) -> None:
    """Ensure configurations table exists and has default values."""
    try:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT NOT NULL UNIQUE,
                    config_type TEXT NOT NULL CHECK(config_type IN ('string', 'integer', 'boolean', 'json')),
                    config_value TEXT NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Insert default configurations if they don't exist
            defaults = [
                ('notification_enabled', 'boolean', 'true', 'Whether notifications are enabled globally'),
                ('notification_template', 'json', self._get_default_notification_template_json(), 'Default notification message template'),
            ]
            
            for key, type_, value, desc in defaults:
                cursor.execute("""
                    INSERT OR IGNORE INTO configurations (config_key, config_type, config_value, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (key, type_, value, desc, datetime.now().isoformat(), datetime.now().isoformat()))
            
            conn.commit()
            self.logger.info("Ensured configurations table exists with defaults")
            
    except sqlite3.Error as e:
        self.logger.error(f"Error ensuring configurations table: {e}")
        raise
```

#### `_get_default_notification_template_json()`

```python
def _get_default_notification_template_json(self) -> str:
    """Get the default notification template as JSON string."""
    import json
    return json.dumps({
        "template": "🏠 *New Property Alert* 🏠\n\n🔔 *Subscription*: {subscription_name}\n\n📍 *{title}*\n🏢 *Agency*: {agency}\n💰 *Price*: €{price}\n📏 *Size*: {size} m²\n📍 *Location*: {location}\n🔗 *Details*: {url}\n📝 *Description*: {description}",
        "placeholders": {
            "title": "Property title",
            "agency": "Agency name",
            "price": "Price in euros (formatted with thousands separator)",
            "size": "Property size in square meters",
            "location": "City and neighborhood",
            "url": "Original property URL",
            "subscription_name": "Name of the notification subscription",
            "description": "Property description (truncated to 100 chars)",
            "internal_url": "HomeFinder internal property detail URL"
        }
    })
```

#### `save_config(config: Configuration) -> int`

```python
def save_config(self, config: Configuration) -> int:
    """Save a configuration to the database."""
    try:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            # Check if config already exists
            cursor.execute("SELECT id FROM configurations WHERE config_key = ?", (config.config_key,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE configurations SET 
                        config_type = ?,
                        config_value = ?,
                        description = ?,
                        is_active = ?,
                        updated_at = ?
                    WHERE config_key = ?
                """, (
                    config.config_type.value,
                    config.config_value,
                    config.description,
                    config.is_active,
                    now,
                    config.config_key
                ))
                conn.commit()
                self.logger.info(f"Updated configuration: {config.config_key}")
                return existing[0]
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO configurations (config_key, config_type, config_value, description, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    config.config_key,
                    config.config_type.value,
                    config.config_value,
                    config.description,
                    config.is_active,
                    now,
                    now
                ))
                conn.commit()
                config_id = cursor.lastrowid
                self.logger.info(f"Inserted new configuration: {config_key}")
                return config_id
                
    except sqlite3.Error as e:
        self.logger.error(f"Error saving configuration {config.config_key}: {e}")
        return -1
```

#### `get_config(config_key: str) -> Optional[Configuration]`

```python
def get_config(self, config_key: str) -> Optional[Configuration]:
    """Get a configuration by key."""
    try:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, config_key, config_type, config_value, description, is_active, created_at, updated_at
                FROM configurations 
                WHERE config_key = ?
            """, (config_key,))
            row = cursor.fetchone()
            
            if row:
                return Configuration(
                    id=row[0],
                    config_key=row[1],
                    config_type=ConfigType(row[2]),
                    config_value=row[3],
                    description=row[4],
                    is_active=bool(row[5]),
                    created_at=row[6],
                    updated_at=row[7]
                )
            return None
            
    except sqlite3.Error as e:
        self.logger.error(f"Error getting configuration {config_key}: {e}")
        return None
```

#### `get_all_configs() -> List[Configuration]`

```python
def get_all_configs(self) -> List[Configuration]:
    """Get all configurations."""
    try:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, config_key, config_type, config_value, description, is_active, created_at, updated_at
                FROM configurations 
                ORDER BY config_key
            """)
            rows = cursor.fetchall()
            
            configs = []
            for row in rows:
                configs.append(Configuration(
                    id=row[0],
                    config_key=row[1],
                    config_type=ConfigType(row[2]),
                    config_value=row[3],
                    description=row[4],
                    is_active=bool(row[5]),
                    created_at=row[6],
                    updated_at=row[7]
                ))
            return configs
            
    except sqlite3.Error as e:
        self.logger.error(f"Error getting all configurations: {e}")
        return []
```

#### `delete_config(config_key: str) -> bool`

```python
def delete_config(self, config_key: str) -> bool:
    """Delete a configuration by key."""
    try:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM configurations WHERE config_key = ?", (config_key,))
            conn.commit()
            
            if cursor.rowcount > 0:
                self.logger.info(f"Deleted configuration: {config_key}")
                return True
            return False
            
    except sqlite3.Error as e:
        self.logger.error(f"Error deleting configuration {config_key}: {e}")
        return False
```

## 4. NotificationService Changes

### 4.1 Update `_format_notification_message()`

Modify `notification_service.py` to use the configurable template:

```python
def _format_notification_message(
    self, listing: Listing, subscription_name: str = ""
) -> str:
    """Format a notification message for a listing using configurable template."""
    try:
        # Get template from configuration
        template_data = self._get_notification_template()
        template = template_data.get("template", self._get_default_template())
        
        # Get agency name
        agency_name = listing.get_agency_name(self.db_manager)
        
        # Get internal URL (property detail page in HomeFinder)
        internal_url = f"http://localhost:5000/properties/{listing.id}"
        
        # Build location string
        location = listing.city
        if listing.neighborhood:
            location += f", {listing.neighborhood}"
        
        # Build description (truncated)
        description = ""
        if listing.description:
            description = listing.description[:100]
            if len(listing.description) > 100:
                description += "..."
        
        # Prepare placeholder values
        placeholders = {
            "title": listing.title,
            "agency": agency_name,
            "price": f"{listing.price:,.0f}",
            "size": str(listing.square_meters) if listing.square_meters else "N/A",
            "location": location,
            "url": listing.url,
            "subscription_name": subscription_name,
            "description": description,
            "internal_url": internal_url
        }
        
        # Replace placeholders in template
        message = template
        for key, value in placeholders.items():
            placeholder = f"{{{key}}}"
            message = message.replace(placeholder, str(value))
        
        return message
        
    except Exception as e:
        self.logger.error(f"Error formatting notification message: {e}")
        # Fallback to default format
        return self._get_default_message(listing, subscription_name)

def _get_notification_template(self) -> Dict[str, Any]:
    """Get notification template from configuration."""
    try:
        config = self.db_manager.get_config("notification_template")
        if config and config.config_type == ConfigType.JSON:
            return config.get_typed_value()
    except Exception as e:
        self.logger.warning(f"Could not get notification template: {e}")
    return {}

def _get_default_template(self) -> str:
    """Get hardcoded default template as fallback."""
    return (
        "🏠 *New Property Alert* 🏠\n\n"
        "🔔 *Subscription*: {subscription_name}\n\n"
        "📍 *{title}*\n"
        "🏢 *Agency*: {agency}\n"
        "💰 *Price*: €{price}\n"
        "📏 *Size*: {size} m²\n"
        "📍 *Location*: {location}\n"
        "🔗 *Details*: {url}\n"
        "📝 *Description*: {description}"
    )
```

## 5. Web Admin Interface

### 5.1 New Routes (views/main_views.py)

#### `/admin/configurations` (GET)

Display all configurations in a table:

```python
@main_bp.route('/admin/configurations')
def admin_configurations():
    """Configuration management page."""
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager()
        configs = db_manager.get_all_configs()
        return render_template('admin_configurations.html', configs=configs)
    except Exception as e:
        current_app.logger.error(f"Error loading configurations: {e}")
        flash(f"Error: {e}", "error")
        return redirect(url_for('main.admin'))
```

#### `/admin/configurations` (POST)

Save a new or updated configuration:

```python
@main_bp.route('/admin/configurations', methods=['POST'])
def admin_config_save():
    """Save configuration."""
    try:
        from database import DatabaseManager, Configuration
        from models import ConfigType
        import json
        
        db_manager = DatabaseManager()
        
        config_key = request.form.get('config_key', '').strip()
        config_type = request.form.get('config_type', 'string').strip()
        config_value = request.form.get('config_value', '').strip()
        description = request.form.get('description', '').strip()
        
        if not config_key:
            flash("Configuration key is required", "error")
            return redirect(url_for('main.admin_configurations'))
        
        # Validate based on type
        if config_type == 'integer':
            try:
                int(config_value)
            except ValueError:
                flash("Invalid integer value", "error")
                return redirect(url_for('main.admin_configurations'))
        elif config_type == 'boolean':
            config_value = 'true' if config_value in ('true', '1', 'yes', 'on') else 'false'
        elif config_type == 'json':
            try:
                json.loads(config_value)
            except json.JSONDecodeError:
                flash("Invalid JSON value", "error")
                return redirect(url_for('main.admin_configurations'))
        
        config = Configuration(
            config_key=config_key,
            config_type=ConfigType(config_type),
            config_value=config_value,
            description=description,
            is_active=True
        )
        
        db_manager.save_config(config)
        flash(f"Configuration '{config_key}' saved successfully", "success")
        
    except Exception as e:
        current_app.logger.error(f"Error saving configuration: {e}")
        flash(f"Error: {e}", "error")
        
    return redirect(url_for('main.admin_configurations'))
```

#### `/admin/configurations/delete/<key>` (POST)

Delete a configuration:

```python
@main_bp.route('/admin/configurations/delete/<key>', methods=['POST'])
def admin_config_delete(key: str):
    """Delete configuration."""
    try:
        from database import DatabaseManager
        
        if request.form.get('confirm') != 'true':
            flash("Please confirm deletion", "warning")
            return redirect(url_for('main.admin_configurations'))
        
        db_manager = DatabaseManager()
        
        # Prevent deletion of critical configs
        protected_keys = ['notification_enabled', 'notification_template']
        if key in protected_keys:
            flash(f"Cannot delete protected configuration: {key}", "error")
            return redirect(url_for('main.admin_configurations'))
        
        if db_manager.delete_config(key):
            flash(f"Configuration '{key}' deleted", "success")
        else:
            flash(f"Configuration '{key}' not found", "warning")
            
    except Exception as e:
        current_app.logger.error(f"Error deleting configuration: {e}")
        flash(f"Error: {e}", "error")
        
    return redirect(url_for('main.admin_configurations'))
```

#### `/admin/notifications/template/test` (POST)

Test notification template:

```python
@main_bp.route('/admin/notifications/template/test', methods=['POST'])
def admin_notification_template_test():
    """Test notification template with sample data."""
    try:
        from database import DatabaseManager
        from notification_service import NotificationEngine, TelegramService
        import json
        
        db_manager = DatabaseManager()
        
        # Get template from request or database
        template_json = request.form.get('template_json', '')
        if template_json:
            template_data = json.loads(template_json)
            template = template_data.get('template', '')
        else:
            config = db_manager.get_config('notification_template')
            if config:
                template_data = config.get_typed_value()
                template = template_data.get('template', '')
            else:
                return jsonify({'success': False, 'message': 'No template found'}), 400
        
        # Create sample listing data for preview
        sample_data = {
            'title': 'Beautiful Apartment in City Center',
            'agency': 'Tettorosso Immobiliare',
            'price': '150,000',
            'size': '85',
            'location': 'Padova, Centro',
            'url': 'https://example.com/property/123',
            'subscription_name': 'My Search',
            'description': 'Spacious 3-room apartment with modern amenities...',
            'internal_url': 'http://localhost:5000/properties/123'
        }
        
        # Replace placeholders
        message = template
        for key, value in sample_data.items():
            message = message.replace(f'{{{key}}}', str(value))
        
        return jsonify({'success': True, 'message': message}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error testing template: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
```

### 5.2 New Templates

#### `templates/admin_configurations.html`

```html
{% extends "base.html" %}

{% block title %}HomeFinder - Configuration Management{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <h1 class="display-4 mb-4">Configuration Management</h1>
        <p class="lead">Manage application settings and notification templates.</p>
    </div>
</div>

<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h5 class="card-title mb-0">Application Configurations</h5>
            </div>
            <div class="card-body">
                {% if configs %}
                <div class="table-responsive">
                    <table class="table table-striped table-hover">
                        <thead>
                            <tr>
                                <th>Key</th>
                                <th>Type</th>
                                <th>Value</th>
                                <th>Description</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for config in configs %}
                            <tr>
                                <td><code>{{ config.config_key }}</code></td>
                                <td><span class="badge bg-secondary">{{ config.config_type.value }}</span></td>
                                <td>
                                    <small>
                                        {% if config.config_type.value == 'json' %}
                                        <button class="btn btn-sm btn-outline-secondary" 
                                                onclick="showJsonValue('{{ config.config_key }}', {{ config.config_value }})">
                                            View JSON
                                        </button>
                                        {% else %}
                                        {{ config.config_value[:50] }}{% if config.config_value|length > 50 %}...{% endif %}
                                        {% endif %}
                                    </small>
                                </td>
                                <td>{{ config.description or '-' }}</td>
                                <td>
                                    <span class="badge bg-{{ 'success' if config.is_active else 'secondary' }}">
                                        {{ "Active" if config.is_active else "Inactive" }}
                                    </span>
                                </td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary" 
                                            onclick="editConfig('{{ config.config_key }}', '{{ config.config_type.value }}', '{{ config.config_value|escapejs }}', '{{ config.description|escapejs if config.description else '' }}')">
                                        Edit
                                    </button>
                                    {% if config.config_key not in ['notification_enabled', 'notification_template'] %}
                                    <button class="btn btn-sm btn-outline-danger"
                                            onclick="deleteConfig('{{ config.config_key }}')">
                                        Delete
                                    </button>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <p class="text-muted">No configurations found.</p>
                {% endif %}
                
                <button class="btn btn-primary mt-3" onclick="showAddModal()">
                    <i class="bi bi-plus-circle"></i> Add Configuration
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Add/Edit Modal -->
<div class="modal fade" id="configModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="configModalTitle">Add Configuration</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form method="POST" action="{{ url_for('main.admin_config_save') }}">
                <div class="modal-body">
                    <div class="mb-3">
                        <label for="config_key" class="form-label">Configuration Key</label>
                        <input type="text" class="form-control" id="config_key" name="config_key" required>
                        <div class="form-text">Unique key for this configuration (e.g., notification_template)</div>
                    </div>
                    <div class="mb-3">
                        <label for="config_type" class="form-label">Type</label>
                        <select class="form-select" id="config_type" name="config_type" onchange="toggleValueField()">
                            <option value="string">String</option>
                            <option value="integer">Integer</option>
                            <option value="boolean">Boolean</option>
                            <option value="json">JSON</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label for="config_value" class="form-label">Value</label>
                        <textarea class="form-control" id="config_value" name="config_value" rows="5" required></textarea>
                        <div class="form-text" id="valueHelp">Enter the configuration value</div>
                    </div>
                    <div class="mb-3">
                        <label for="description" class="form-label">Description</label>
                        <input type="text" class="form-control" id="description" name="description">
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save Configuration</button>
                </div>
            </form>
        </div>
    </div>
</div>

<!-- JSON Viewer Modal -->
<div class="modal fade" id="jsonModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="jsonModalTitle">JSON Value</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <pre id="jsonContent" class="bg-light p-3"></pre>
            </div>
        </div>
    </div>
</div>

{% endblock %}

{% block scripts %}
{{ super() }}
<script>
let isEditing = false;

function showAddModal() {
    isEditing = false;
    document.getElementById('configModalTitle').textContent = 'Add Configuration';
    document.getElementById('config_key').disabled = false;
    document.getElementById('config_key').value = '';
    document.getElementById('config_type').value = 'string';
    document.getElementById('config_value').value = '';
    document.getElementById('description').value = '';
    toggleValueField();
    new bootstrap.Modal(document.getElementById('configModal')).show();
}

function editConfig(key, type, value, description) {
    isEditing = true;
    document.getElementById('configModalTitle').textContent = 'Edit Configuration';
    document.getElementById('config_key').value = key;
    document.getElementById('config_key').disabled = true;
    document.getElementById('config_type').value = type;
    document.getElementById('config_value').value = value;
    document.getElementById('description').value = description;
    toggleValueField();
    new bootstrap.Modal(document.getElementById('configModal')).show();
}

function toggleValueField() {
    const type = document.getElementById('config_type').value;
    const help = document.getElementById('valueHelp');
    const valueField = document.getElementById('config_value');
    
    if (type === 'json') {
        valueField.setAttribute('rows', '10');
        help.textContent = 'Enter valid JSON';
    } else if (type === 'boolean') {
        valueField.setAttribute('rows', '1');
        valueField.value = 'true';
        help.textContent = 'Enter true or false';
    } else if (type === 'integer') {
        valueField.setAttribute('rows', '1');
        help.textContent = 'Enter a number';
    } else {
        valueField.setAttribute('rows', '3');
        help.textContent = 'Enter the configuration value';
    }
}

function showJsonValue(key, jsonStr) {
    document.getElementById('jsonModalTitle').textContent = 'JSON Value: ' + key;
    document.getElementById('jsonContent').textContent = JSON.stringify(JSON.parse(jsonStr), null, 2);
    new bootstrap.Modal(document.getElementById('jsonModal')).show();
}

function deleteConfig(key) {
    if (confirm('Are you sure you want to delete configuration: ' + key + '?')) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/admin/configurations/delete/' + key;
        
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'confirm';
        input.value = 'true';
        
        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
    }
}
</script>
{% endblock %}
```

#### `templates/admin_notification_settings.html`

This is a dedicated page for notification-specific settings with a user-friendly template editor:

```html
{% extends "base.html" %}

{% block title %}HomeFinder - Notification Settings{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <h1 class="display-4 mb-4">Notification Settings</h1>
        <p class="lead">Configure how property notifications are sent to your Telegram.</p>
    </div>
</div>

<div class="row mt-4">
    <!-- Enable/Disable Notifications -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header bg-info text-white">
                <h5 class="card-title mb-0">Notification Status</h5>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('main.admin_config_save') }}">
                    <input type="hidden" name="config_key" value="notification_enabled">
                    <input type="hidden" name="config_type" value="boolean">
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" id="notificationEnabled" 
                               name="config_value" value="true" 
                               {% if notification_enabled %}checked{% endif %}
                               onchange="this.form.submit()">
                        <label class="form-check-label" for="notificationEnabled">
                            Enable property notifications
                        </label>
                    </div>
                    <input type="hidden" name="description" value="Whether notifications are enabled globally">
                </form>
            </div>
        </div>
    </div>
    
    <!-- Test Notification -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header bg-success text-white">
                <h5 class="card-title mb-0">Test Notifications</h5>
            </div>
            <div class="card-body">
                <p>Send a test notification to verify your Telegram bot is working.</p>
                <button class="btn btn-success" onclick="sendTestNotification()">
                    <i class="bi bi-send"></i> Send Test Notification
                </button>
                <div id="testResult" class="mt-3"></div>
            </div>
        </div>
    </div>
</div>

<!-- Notification Template Editor -->
<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0">Notification Template</h5>
                <button class="btn btn-sm btn-light" onclick="resetToDefault()">
                    Reset to Default
                </button>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('main.admin_config_save') }}">
                    <input type="hidden" name="config_key" value="notification_template">
                    <input type="hidden" name="config_type" value="json">
                    <input type="hidden" name="description" value="Default notification message template">
                    
                    <div class="mb-3">
                        <label for="templateText" class="form-label">Message Template</label>
                        <textarea class="form-control font-monospace" id="templateText" name="config_value" 
                                  rows="8">{{ template_json }}</textarea>
                        <div class="form-text">
                            Use placeholders like <code>{title}</code>, <code>{price}</code>, etc.
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-primary">
                        <i class="bi bi-save"></i> Save Template
                    </button>
                    <button type="button" class="btn btn-secondary" onclick="previewTemplate()">
                        <i class="bi bi-eye"></i> Preview
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>

<!-- Placeholder Reference -->
<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header bg-secondary text-white">
                <h5 class="card-title mb-0">Available Placeholders</h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>Placeholder</th>
                                <th>Description</th>
                                <th>Example</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td><code>{title}</code></td><td>Property title</td><td>Beautiful Apartment in Centro</td></tr>
                            <tr><td><code>{agency}</code></td><td>Agency name</td><td>Tettorosso Immobiliare</td></tr>
                            <tr><td><code>{price}</code></td><td>Price in euros</td><td>150,000</td></tr>
                            <tr><td><code>{size}</code></td><td>Square meters</td><td>85</td></tr>
                            <tr><td><code>{location}</code></td><td>City and neighborhood</td><td>Padova, Centro</td></tr>
                            <tr><td><code>{url}</code></td><td>Original property URL</td><td>https://example.com/property/123</td></tr>
                            <tr><td><code>{internal_url}</code></td><td>HomeFinder detail URL</td><td>http://localhost:5000/properties/123</td></tr>
                            <tr><td><code>{subscription_name}</code></td><td>Subscription name</td><td>My Search</td></tr>
                            <tr><td><code>{description}</code></td><td>Property description (truncated)</td><td>Spacious 3-room apartment...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Preview Modal -->
<div class="modal fade" id="previewModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Notification Preview</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <pre id="previewContent" class="bg-light p-3 whitespace-pre-wrap"></pre>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>

{% endblock %}

{% block scripts %}
{{ super() }}
<script>
function previewTemplate() {
    const templateText = document.getElementById('templateText').value;
    
    try {
        const templateData = JSON.parse(templateText);
        const template = templateData.template || templateText;
        
        const sampleData = {
            title: 'Beautiful Apartment in City Center',
            agency: 'Tettorosso Immobiliare',
            price: '150,000',
            size: '85',
            location: 'Padova, Centro',
            url: 'https://example.com/property/123',
            subscription_name: 'My Search',
            description: 'Spacious 3-room apartment with modern amenities, close to all services.',
            internal_url: 'http://localhost:5000/properties/123'
        };
        
        let message = template;
        for (const [key, value] of Object.entries(sampleData)) {
            message = message.replace(new RegExp(`{${key}}`, 'g'), value);
        }
        
        document.getElementById('previewContent').textContent = message;
        new bootstrap.Modal(document.getElementById('previewModal')).show();
    } catch (e) {
        alert('Invalid template JSON: ' + e.message);
    }
}

function resetToDefault() {
    if (confirm('Reset template to default? This will overwrite your current template.')) {
        fetch('/admin/configurations/reset-template', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('templateText').value = data.template;
                    alert('Template reset to default');
                } else {
                    alert('Error: ' + data.message);
                }
            });
    }
}

function sendTestNotification() {
    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Sending...';
    
    fetch('/admin/telegram/test', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            const result = document.getElementById('testResult');
            if (data.success) {
                result.innerHTML = '<div class="alert alert-success">' + data.message + '</div>';
            } else {
                result.innerHTML = '<div class="alert alert-danger">' + data.message + '</div>';
            }
        })
        .catch(error => {
            document.getElementById('testResult').innerHTML = '<div class="alert alert-danger">Error: ' + error + '</div>';
        })
        .finally(() => {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-send"></i> Send Test Notification';
        });
}
</script>
{% endblock %}
```

### 5.3 Update Navigation

Add links to the admin navigation in `templates/base.html`:

```html
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('main.admin_configurations') }}">
        <i class="bi bi-gear"></i> Configurations
    </a>
</li>
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('main.admin_notification_settings') }}">
        <i class="bi bi-bell"></i> Notifications
    </a>
</li>
```

## 6. Testing

### 6.1 Unit Tests

#### Test Configuration CRUD

```python
def test_config_crud(temp_db):
    """Test configuration create, read, update, delete."""
    db = DatabaseManager(temp_db)
    
    # Create
    config = Configuration(
        config_key="test_key",
        config_type=ConfigType.STRING,
        config_value="test_value",
        description="Test description"
    )
    config_id = db.save_config(config)
    assert config_id > 0
    
    # Read
    retrieved = db.get_config("test_key")
    assert retrieved is not None
    assert retrieved.config_value == "test_value"
    assert retrieved.config_type == ConfigType.STRING
    
    # Update
    config.config_value = "updated_value"
    db.save_config(config)
    updated = db.get_config("test_key")
    assert updated.config_value == "updated_value"
    
    # Delete
    assert db.delete_config("test_key") is True
    assert db.get_config("test_key") is None
```

#### Test Type Casting

```python
def test_config_type_casting():
    """Test configuration type casting."""
    # Boolean
    config = Configuration("bool_key", ConfigType.BOOLEAN, "true")
    assert config.get_typed_value() is True
    
    config = Configuration("bool_key", ConfigType.BOOLEAN, "false")
    assert config.get_typed_value() is False
    
    # Integer
    config = Configuration("int_key", ConfigType.INTEGER, "123")
    assert config.get_typed_value() == 123
    
    # JSON
    config = Configuration("json_key", ConfigType.JSON, '{"key": "value"}')
    assert config.get_typed_value() == {"key": "value"}
```

#### Test Notification Template

```python
def test_notification_template_rendering(sample_listing, temp_db):
    """Test notification message uses configurable template."""
    from notification_service import NotificationEngine, TelegramService
    import json
    
    db = DatabaseManager(temp_db)
    
    # Set custom template
    template_data = {
        "template": "CUSTOM: {title} - €{price}"
    }
    config = Configuration(
        config_key="notification_template",
        config_type=ConfigType.JSON,
        config_value=json.dumps(template_data)
    )
    db.save_config(config)
    
    # Create notification engine
    telegram_service = TelegramService(db, dry_run=True)
    engine = NotificationEngine(db, telegram_service)
    
    # Format message
    message = engine._format_notification_message(sample_listing, "My Search")
    
    assert "CUSTOM:" in message
    assert sample_listing.title in message
```

## 7. Migration Strategy

### 7.1 Backward Compatibility

1. On database initialization, create the `configurations` table
2. Insert default values for `notification_enabled` and `notification_template`
3. Existing notification tables (`telegram_configurations`, `notification_subscriptions`, `notification_history`) remain unchanged
4. The notification service first checks the `configurations` table, falls back to hardcoded defaults if not found

### 7.2 Default Template JSON Structure

```json
{
  "template": "🏠 *New Property Alert* 🏠\n\n🔔 *Subscription*: {subscription_name}\n\n📍 *{title}*\n🏢 *Agency*: {agency}\n💰 *Price*: €{price}\n📏 *Size*: {size} m²\n📍 *Location*: {location}\n🔗 *Details*: {url}\n📝 *Description*: {description}",
  "placeholders": {
    "title": "Property title",
    "agency": "Agency name",
    "price": "Price in euros (formatted with thousands separator)",
    "size": "Property size in square meters",
    "location": "City and neighborhood",
    "url": "Original property URL",
    "subscription_name": "Name of the notification subscription",
    "description": "Property description (truncated to 100 chars)",
    "internal_url": "HomeFinder internal property detail URL"
  },
  "version": "1.0"
}
```

## 8. File Changes Summary

### New Files
- `PROPERTIES_ON_DB.md` (this document)

### Modified Files
1. **`models.py`**
   - Add `ConfigType` enum
   - Add `Configuration` dataclass

2. **`database.py`**
   - Add `_ensure_configurations_table()` method
   - Add `_get_default_notification_template_json()` method
   - Add `save_config()` method
   - Add `get_config()` method
   - Add `get_all_configs()` method
   - Add `delete_config()` method
   - Call `_ensure_configurations_table()` from `initialize_database()`

3. **`notification_service.py`**
   - Modify `_format_notification_message()` to use configurable template
   - Add `_get_notification_template()` helper
   - Add `_get_default_template()` helper

4. **`views/main_views.py`**
   - Add `/admin/configurations` route (GET)
   - Add `/admin/configurations` route (POST)
   - Add `/admin/configurations/delete/<key>` route
   - Add `/admin/notifications/template/test` route
   - Add `/admin/configurations/reset-template` route

5. **New Templates**
   - `templates/admin_configurations.html`
   - `templates/admin_notification_settings.html`

## 9. Implementation Order

1. **Phase 1: Database Layer**
   - Update `models.py` with new dataclass
   - Update `database.py` with new methods
   - Test configuration CRUD operations

2. **Phase 2: Notification Service**
   - Update `notification_service.py` to use templates
   - Test template rendering with placeholders

3. **Phase 3: Admin Interface**
   - Create configuration management routes
   - Create admin templates
   - Add navigation links

4. **Phase 4: Testing & Polish**
   - Run full test suite
   - Manual testing of admin interface
   - Verify backward compatibility

## 10. Security Considerations

1. **Input Validation**: Validate all configuration values based on type
2. **Protected Keys**: Prevent deletion of critical system configurations
3. **JSON Validation**: Ensure JSON templates are valid before saving
4. **XSS Prevention**: Escape user input in templates
5. **Admin Access**: Ensure admin routes are properly protected

## 11. Future Extensibility

The generic `configurations` table allows easy addition of new settings:

- Scraping configuration (intervals, delays)
- Cache settings
- UI preferences
- API keys (encrypted)
- Feature flags
- Rate limiting settings

This provides a unified, maintainable approach to application configuration.
