import sqlite3
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from datetime import datetime
from dataclasses import dataclass
import json

from models import Listing, Configuration, ConfigType
from config import DB_FILE


@dataclass
class Agency:
    """Data model for agencies."""

    id: int
    name: str
    website_url: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class TelegramConfiguration:
    """Data model for Telegram bot configurations."""

    id: Optional[int] = None
    bot_token: str = ""
    bot_name: Optional[str] = None
    chat_id: Optional[str] = None
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""


@dataclass
class NotificationSubscription:
    """Data model for notification subscriptions."""

    id: Optional[int] = None
    user_id: str = ""
    subscription_name: str = ""
    search_filters: Optional[Dict[str, Any]] = None
    telegram_config_id: int = 0
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""


@dataclass
class NotificationHistory:
    """Data model for notification history."""

    id: Optional[int] = None
    listing_id: int = 0
    subscription_id: int = 0
    subscription_name: str = ""
    notification_sent_at: str = ""
    telegram_message_id: Optional[str] = None
    is_successful: bool = False
    error_message: Optional[str] = None


class DatabaseManager:
    """Database manager for property listings."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_FILE
        self.logger = logging.getLogger(__name__)

    def initialize_database(self) -> None:
        """Initialize database and create tables if they don't exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Create agencies table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS agencies (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        website_url TEXT NOT NULL,
                        phone TEXT,
                        email TEXT,
                        address TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)

                # Create raw_html_pages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS raw_html_pages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE NOT NULL,
                        agency_id INTEGER NOT NULL,
                        raw_html TEXT NOT NULL,
                        scrape_date TEXT NOT NULL,
                        is_successful BOOLEAN DEFAULT FALSE,
                        error_message TEXT,
                        FOREIGN KEY (agency_id) REFERENCES agencies(id)
                    )
                """)

                # Create listings table (updated to use agency_id instead of agency)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS listings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        agency_id INTEGER NOT NULL,
                        url TEXT UNIQUE NOT NULL,
                        description TEXT,
                        contract_type TEXT NOT NULL,
                        price REAL NOT NULL,
                        city TEXT NOT NULL,
                        neighborhood TEXT,
                        address TEXT,
                        rooms INTEGER,
                        bedrooms INTEGER,
                        bathrooms INTEGER,
                        square_meters INTEGER,
                        floor TEXT,
                        year_built INTEGER,
                        has_elevator BOOLEAN,
                        heating TEXT,
                        has_air_conditioning BOOLEAN,
                        has_garage BOOLEAN,
                        is_furnished BOOLEAN,
                        energy_class TEXT,
                        energy_consumption REAL,
                        features TEXT,
                        scrape_date TEXT NOT NULL,
                        publication_date TEXT,
                        raw_html_file TEXT,
                        agency_listing_id TEXT,
                        modify_date TEXT,
                        creation_date TEXT NOT NULL,
                        last_verified_date TEXT,
                        is_broken BOOLEAN DEFAULT FALSE,
                        raw_html_page_id INTEGER,
                        FOREIGN KEY (agency_id) REFERENCES agencies(id),
                        FOREIGN KEY (raw_html_page_id) REFERENCES raw_html_pages(id)
                    )
                """)

                # Create indexes for better search performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_city ON listings(city)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_price ON listings(price)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_contract ON listings(contract_type)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_square_meters ON listings(square_meters)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_agency ON listings(agency_id)"
                )

                # Create scrape_history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS scrape_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        source TEXT NOT NULL,
                        listings_count INTEGER,
                        duration_seconds REAL
                    )
                """)

                # Create application_logs table for detailed logging
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS application_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        level TEXT NOT NULL CHECK(level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR')),
                        source TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details TEXT,
                        created_at TEXT NOT NULL
                    )
                """)

                # Create indexes for log queries
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON application_logs(timestamp)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_logs_level ON application_logs(level)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_logs_source ON application_logs(source)"
                )

                # Initialize notification tables
                self._ensure_notification_tables_exist()

                # Initialize configurations table
                self._ensure_configurations_table()

                conn.commit()

        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {e}")
            raise

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(str(self.db_path))

    def get_agency_by_id(self, agency_id: int):
        """Get agency by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, website_url, phone, email, address, created_at, updated_at FROM agencies WHERE id = ?",
                    (agency_id,),
                )
                row = cursor.fetchone()

                if row:
                    return Agency(
                        id=row[0],
                        name=row[1],
                        website_url=row[2],
                        phone=row[3],
                        email=row[4],
                        address=row[5],
                        created_at=row[6],
                        updated_at=row[7],
                    )

                return None

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching agency by ID {agency_id}: {e}")
            return None

    def get_agency_by_name(self, agency_name: str):
        """Get agency by name."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, website_url, phone, email, address, created_at, updated_at FROM agencies WHERE name = ?",
                    (agency_name,),
                )
                row = cursor.fetchone()

                if row:
                    return Agency(
                        id=row[0],
                        name=row[1],
                        website_url=row[2],
                        phone=row[3],
                        email=row[4],
                        address=row[5],
                        created_at=row[6],
                        updated_at=row[7],
                    )

                return None

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching agency by name {agency_name}: {e}")
            return None

    def get_all_agencies(self) -> List[Agency]:
        """Get all agencies."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, website_url, phone, email, address, created_at, updated_at FROM agencies ORDER BY name"
                )
                rows = cursor.fetchall()

                agencies = []
                for row in rows:
                    agencies.append(
                        Agency(
                            id=row[0],
                            name=row[1],
                            website_url=row[2],
                            phone=row[3],
                            email=row[4],
                            address=row[5],
                            created_at=row[6],
                            updated_at=row[7],
                        )
                    )

                return agencies

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching all agencies: {e}")
            return []

    def save_listing(self, listing: Listing) -> int:
        """Save a single listing to database."""
        try:
            listing_dict = listing.to_dict()

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check if listing already exists
                cursor.execute("SELECT id FROM listings WHERE url = ?", (listing.url,))
                existing = cursor.fetchone()

                if existing:
                    # Update existing listing
                    update_query = """
                        UPDATE listings SET 
                            title = ?,
                            agency_id = ?,
                            description = ?,
                            contract_type = ?,
                            price = ?,
                            city = ?,
                            neighborhood = ?,
                            address = ?,
                            rooms = ?,
                            bedrooms = ?,
                            bathrooms = ?,
                            square_meters = ?,
                            floor = ?,
                            year_built = ?,
                            has_elevator = ?,
                            heating = ?,
                            has_air_conditioning = ?,
                            has_garage = ?,
                            is_furnished = ?,
                            energy_class = ?,
                            energy_consumption = ?,
                            features = ?,
                            scrape_date = ?,
                            publication_date = ?,
                            raw_html_file = ?,
                            agency_listing_id = ?,
                            modify_date = ?,
                            creation_date = ?,
                            last_verified_date = ?,
                            is_broken = ?
                        WHERE url = ?
                    """

                    cursor.execute(
                        update_query,
                        (
                            listing_dict["title"],
                            listing_dict["agency_id"],
                            listing_dict["description"],
                            listing_dict["contract_type"],
                            listing_dict["price"],
                            listing_dict["city"],
                            listing_dict["neighborhood"],
                            listing_dict["address"],
                            listing_dict["rooms"],
                            listing_dict["bedrooms"],
                            listing_dict["bathrooms"],
                            listing_dict["square_meters"],
                            listing_dict["floor"],
                            listing_dict["year_built"],
                            listing_dict["has_elevator"],
                            listing_dict["heating"],
                            listing_dict["has_air_conditioning"],
                            listing_dict["has_garage"],
                            listing_dict["is_furnished"],
                            listing_dict["energy_class"],
                            listing_dict["energy_consumption"],
                            str(listing_dict["features"])
                            if listing_dict["features"]
                            else None,
                            listing_dict["scrape_date"],
                            listing_dict["publication_date"],
                            listing_dict["raw_html_file"],
                            listing_dict["agency_listing_id"],
                            listing_dict.get("modify_date"),
                            listing_dict.get("creation_date"),
                            listing_dict.get("last_verified_date"),
                            listing_dict.get("is_broken", False),
                            listing.url,
                        ),
                    )

                    self.logger.info(f"Updated existing listing: {listing.url}")
                else:
                    # Insert new listing
                    insert_query = """
                        INSERT INTO listings (
                            title, agency_id, url, description, contract_type, price, city, 
                            neighborhood, address, rooms, bedrooms, bathrooms, square_meters, 
                            floor, year_built, has_elevator, heating, has_air_conditioning, 
                            has_garage, is_furnished, energy_class, energy_consumption, 
                            features, scrape_date, publication_date, raw_html_file, agency_listing_id,
                            modify_date, creation_date, last_verified_date, is_broken
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """

                    cursor.execute(
                        insert_query,
                        (
                            listing_dict["title"],
                            listing_dict["agency_id"],
                            listing_dict["url"],
                            listing_dict["description"],
                            listing_dict["contract_type"],
                            listing_dict["price"],
                            listing_dict["city"],
                            listing_dict["neighborhood"],
                            listing_dict["address"],
                            listing_dict["rooms"],
                            listing_dict["bedrooms"],
                            listing_dict["bathrooms"],
                            listing_dict["square_meters"],
                            listing_dict["floor"],
                            listing_dict["year_built"],
                            listing_dict["has_elevator"],
                            listing_dict["heating"],
                            listing_dict["has_air_conditioning"],
                            listing_dict["has_garage"],
                            listing_dict["is_furnished"],
                            listing_dict["energy_class"],
                            listing_dict["energy_consumption"],
                            str(listing_dict["features"])
                            if listing_dict["features"]
                            else None,
                            listing_dict["scrape_date"],
                            listing_dict["publication_date"],
                            listing_dict["raw_html_file"],
                            listing_dict["agency_listing_id"],
                            listing_dict.get("modify_date"),
                            listing_dict.get("creation_date"),
                            listing_dict.get("last_verified_date"),
                            listing_dict.get("is_broken", False),
                        ),
                    )

                    self.logger.info(f"Inserted new listing: {listing.url}")

                conn.commit()

                if existing:
                    # Return the existing ID for updates
                    return existing[0]
                else:
                    # Return the newly generated ID for inserts
                    return cursor.lastrowid or -1

        except sqlite3.Error as e:
            self.logger.error(f"Error saving listing {listing.url}: {e}")
            return -1

    def save_listings(self, listings: List[Listing]) -> int:
        """Save multiple listings to database."""
        success_count = 0
        for listing in listings:
            if self.save_listing(listing):
                success_count += 1
        return success_count

    def save_raw_html_page(
        self,
        url: str,
        agency_id: int,
        raw_html: str,
        is_successful: bool = False,
        error_message: Optional[str] = None,
    ) -> int:
        """Save raw HTML page to database.

        Args:
            url: The URL of the page
            agency_id: ID of the agency that owns this listing
            raw_html: The raw HTML content
            is_successful: Whether scraping was successful
            error_message: Error message if scraping failed

        Returns:
            ID of the saved raw HTML page, or -1 on error
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check if this URL already exists
                cursor.execute("SELECT id FROM raw_html_pages WHERE url = ?", (url,))
                existing = cursor.fetchone()

                if existing:
                    # Update existing record
                    update_query = """
                        UPDATE raw_html_pages SET 
                            agency_id = ?,
                            raw_html = ?,
                            scrape_date = ?,
                            is_successful = ?,
                            error_message = ?
                        WHERE url = ?
                    """

                    cursor.execute(
                        update_query,
                        (
                            agency_id,
                            raw_html,
                            datetime.now().isoformat(),
                            is_successful,
                            error_message,
                            url,
                        ),
                    )

                    self.logger.info(f"Updated existing raw HTML page: {url}")
                    conn.commit()
                    return existing[0]
                else:
                    # Insert new record
                    insert_query = """
                        INSERT INTO raw_html_pages 
                            (url, agency_id, raw_html, scrape_date, is_successful, error_message)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """

                    cursor.execute(
                        insert_query,
                        (
                            url,
                            agency_id,
                            raw_html,
                            datetime.now().isoformat(),
                            is_successful,
                            error_message,
                        ),
                    )

                    page_id = cursor.lastrowid or -1
                    self.logger.info(
                        f"Inserted new raw HTML page: {url} (ID: {page_id})"
                    )
                    conn.commit()
                    return page_id

        except sqlite3.Error as e:
            self.logger.error(f"Error saving raw HTML page {url}: {e}")
            return -1

    def update_raw_html_page_success(
        self,
        page_id: int,
        is_successful: bool = True,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update the success status of a raw HTML page.

        Args:
            page_id: ID of the raw HTML page
            is_successful: Whether scraping was successful
            error_message: Error message if scraping failed

        Returns:
            True if update was successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                update_query = """
                    UPDATE raw_html_pages SET 
                        is_successful = ?,
                        error_message = ?
                    WHERE id = ?
                """

                cursor.execute(update_query, (is_successful, error_message, page_id))

                conn.commit()

                if cursor.rowcount > 0:
                    self.logger.info(
                        f"Updated raw HTML page {page_id} success status: {is_successful}"
                    )
                    return True
                else:
                    self.logger.warning(f"No raw HTML page found with ID {page_id}")
                    return False

        except sqlite3.Error as e:
            self.logger.error(f"Error updating raw HTML page {page_id}: {e}")
            return False

    def get_raw_html_page_by_id(self, page_id: int) -> Optional[Dict[str, Any]]:
        """Get raw HTML page by ID.

        Args:
            page_id: ID of the raw HTML page

        Returns:
            Dictionary with page data, or None if not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT id, url, agency_id, raw_html, scrape_date, is_successful, error_message 
                    FROM raw_html_pages 
                    WHERE id = ?
                """,
                    (page_id,),
                )

                row = cursor.fetchone()

                if row:
                    return {
                        "id": row[0],
                        "url": row[1],
                        "agency_id": row[2],
                        "raw_html": row[3],
                        "scrape_date": row[4],
                        "is_successful": bool(row[5]),
                        "error_message": row[6],
                    }

                return None

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching raw HTML page {page_id}: {e}")
            return None

    def update_listing(self, listing_id: int, update_data: Dict[str, Any]) -> bool:
        """Update a listing by ID with transaction support."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Begin transaction
                cursor.execute("BEGIN TRANSACTION")

                # Build update query dynamically based on provided fields
                update_fields = []
                update_values = []

                # Define which fields are editable (excluding URL, agency, scrape_date, ID)
                editable_fields = [
                    "title",
                    "description",
                    "contract_type",
                    "price",
                    "city",
                    "neighborhood",
                    "address",
                    "rooms",
                    "bedrooms",
                    "bathrooms",
                    "square_meters",
                    "floor",
                    "year_built",
                    "has_elevator",
                    "heating",
                    "has_air_conditioning",
                    "has_garage",
                    "is_furnished",
                    "energy_class",
                    "energy_consumption",
                    "features",
                    "publication_date",
                    "raw_html_file",
                    "agency_listing_id",
                ]

                # Add fields that have values in update_data
                for field in editable_fields:
                    if field in update_data and update_data[field] is not None:
                        update_fields.append(f"{field} = ?")
                        update_values.append(update_data[field])

                # Add modify_date to track when the listing was edited
                update_fields.append("modify_date = ?")
                update_values.append(datetime.now().isoformat())

                if not update_fields:
                    # No fields to update
                    cursor.execute("ROLLBACK")
                    return False

                # Build and execute update query
                update_query = f"""
                    UPDATE listings 
                    SET {", ".join(update_fields)}
                    WHERE id = ?
                """
                update_values.append(listing_id)

                cursor.execute(update_query, update_values)

                # Commit transaction
                cursor.execute("COMMIT")

                self.logger.info(f"Updated listing ID {listing_id}")
                return True

        except sqlite3.Error as e:
            self.logger.error(f"Error updating listing {listing_id}: {e}")
            return False

    def get_listing_by_url(self, url: str) -> Optional[Listing]:
        """Get listing by URL."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM listings WHERE url = ?", (url,))
                row = cursor.fetchone()

                if row:
                    return self._row_to_listing(row)

                return None

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching listing by URL {url}: {e}")
            return None

    def get_listing_by_id(self, listing_id: int) -> Optional[Listing]:
        """Get listing by database ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
                row = cursor.fetchone()

                if row:
                    return self._row_to_listing(row)

                return None

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching listing by ID {listing_id}: {e}")
            return None

    def search_listings(self, **kwargs) -> List[Listing]:
        """Search listings with various filters and sorting."""
        try:
            query = "SELECT * FROM listings WHERE 1=1"
            params = []

            # Add filters based on kwargs
            if "city" in kwargs and kwargs["city"]:
                query += " AND city = ?"
                params.append(kwargs["city"])

            if "min_price" in kwargs and kwargs["min_price"]:
                query += " AND price >= ?"
                params.append(kwargs["min_price"])

            if "max_price" in kwargs and kwargs["max_price"]:
                query += " AND price <= ?"
                params.append(kwargs["max_price"])

            if "min_size" in kwargs and kwargs["min_size"]:
                query += " AND square_meters >= ?"
                params.append(kwargs["min_size"])

            if "contract_type" in kwargs and kwargs["contract_type"]:
                query += " AND contract_type = ?"
                params.append(kwargs["contract_type"])

            if "agency_id" in kwargs and kwargs["agency_id"]:
                query += " AND agency_id = ?"
                params.append(kwargs["agency_id"])

            # New filters
            if "min_bedrooms" in kwargs and kwargs["min_bedrooms"]:
                query += " AND (bedrooms >= ? OR bedrooms IS NULL)"
                params.append(kwargs["min_bedrooms"])

            if "min_bathrooms" in kwargs and kwargs["min_bathrooms"]:
                query += " AND (bathrooms >= ? OR bathrooms IS NULL)"
                params.append(kwargs["min_bathrooms"])

            if "neighborhood" in kwargs and kwargs["neighborhood"]:
                query += " AND (neighborhood LIKE ? OR neighborhood IS NULL)"
                params.append(f"%{kwargs['neighborhood']}%")

            if "min_year_built" in kwargs and kwargs["min_year_built"]:
                query += " AND (year_built >= ? OR year_built IS NULL)"
                params.append(kwargs["min_year_built"])

            if "has_air_conditioning" in kwargs and kwargs["has_air_conditioning"]:
                query += (
                    " AND (has_air_conditioning = ? OR has_air_conditioning IS NULL)"
                )
                params.append(True)

            if "has_garage" in kwargs and kwargs["has_garage"]:
                query += " AND (has_garage = ? OR has_garage IS NULL)"
                params.append(True)

            if "min_energy_class" in kwargs and kwargs["min_energy_class"]:
                # Energy class hierarchy: A4=1 (best) to G=11 (worst)
                energy_class_mapping = {
                    "A4": 1,
                    "A3": 2,
                    "A2": 3,
                    "A1": 4,
                    "A": 5,
                    "B": 6,
                    "C": 7,
                    "D": 8,
                    "E": 9,
                    "F": 10,
                    "G": 11,
                }
                target_value = energy_class_mapping.get(
                    kwargs["min_energy_class"].upper(), 11
                )

                query += """
                    AND (
                        energy_class IS NULL
                        OR CASE
                            WHEN energy_class = 'A4' THEN 1
                            WHEN energy_class = 'A3' THEN 2
                            WHEN energy_class = 'A2' THEN 3
                            WHEN energy_class = 'A1' THEN 4
                            WHEN energy_class = 'A' THEN 5
                            WHEN energy_class = 'B' THEN 6
                            WHEN energy_class = 'C' THEN 7
                            WHEN energy_class = 'D' THEN 8
                            WHEN energy_class = 'E' THEN 9
                            WHEN energy_class = 'F' THEN 10
                            WHEN energy_class = 'G' THEN 11
                            ELSE 12
                        END <= ?
                    )
                """
                params.append(target_value)

            if "heating" in kwargs and kwargs["heating"]:
                query += " AND (heating = ? OR heating IS NULL)"
                params.append(kwargs["heating"])

            if "min_rooms" in kwargs and kwargs["min_rooms"]:
                query += " AND (rooms >= ? OR rooms IS NULL)"
                params.append(kwargs["min_rooms"])

            # Add sorting support
            sort_by = kwargs.get("sort_by")
            sort_order = kwargs.get("sort_order", "asc")

            if sort_by:
                # Validate sort_by parameter to prevent SQL injection
                valid_sort_fields = [
                    "scrape_date",
                    "price",
                    "square_meters",
                    "energy_class",
                    "year_built",
                ]
                if sort_by in valid_sort_fields:
                    # Handle energy_class specially since it needs custom ordering
                    if sort_by == "energy_class":
                        query += f" ORDER BY CASE energy_class "
                        query += "WHEN 'A4' THEN 1 WHEN 'A3' THEN 2 WHEN 'A2' THEN 3 WHEN 'A1' THEN 4 "
                        query += "WHEN 'A' THEN 5 WHEN 'B' THEN 6 WHEN 'C' THEN 7 WHEN 'D' THEN 8 "
                        query += "WHEN 'E' THEN 9 WHEN 'F' THEN 10 WHEN 'G' THEN 11 ELSE 12 END"
                    else:
                        query += f" ORDER BY {sort_by}"

                    # Add sort order
                    if sort_order.lower() == "desc":
                        query += " DESC"
                    else:
                        query += " ASC"
                else:
                    # Default sorting by scrape_date if invalid field provided
                    query += " ORDER BY scrape_date DESC"
            else:
                # Default sorting by scrape_date if no sort parameter provided
                query += " ORDER BY scrape_date DESC"

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [self._row_to_listing(row) for row in rows]

        except sqlite3.Error as e:
            self.logger.error(f"Error searching listings: {e}")
            return []

    def get_all_listings(self) -> List[Listing]:
        """Get all listings."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM listings")
                rows = cursor.fetchall()

                return [self._row_to_listing(row) for row in rows]

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching all listings: {e}")
            return []

    def get_listings_since(self, timestamp: str) -> List[Listing]:
        """Get listings added or modified since a specific timestamp."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM listings 
                    WHERE creation_date >= ? 
                    ORDER BY creation_date ASC
                """,
                    (timestamp,),
                )
                rows = cursor.fetchall()

                return [self._row_to_listing(row) for row in rows]

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching listings since {timestamp}: {e}")
            return []

    def _row_to_listing(self, row: tuple) -> Listing:
        """Convert database row to Listing object."""
        # Determine the schema version based on row length
        # Real database (production): 32 columns, agency_id is at index 28
        # New database (tests): 33 columns, agency_id is at index 2
        if len(row) >= 33:
            # New schema: 33 columns
            listing_data = {
                "id": row[0],
                "title": row[1],
                "agency_id": row[2],
                "url": row[3],
                "description": row[4],
                "contract_type": row[5],
                "price": row[6],
                "city": row[7],
                "neighborhood": row[8],
                "address": row[9],
                "rooms": row[10],
                "bedrooms": row[11],
                "bathrooms": row[12],
                "square_meters": row[13],
                "floor": row[14],
                "year_built": row[15],
                "has_elevator": row[16],
                "heating": row[17],
                "has_air_conditioning": row[18],
                "has_garage": row[19],
                "is_furnished": row[20],
                "energy_class": row[21],
                "energy_consumption": row[22],
                "features": row[23],
                "scrape_date": row[24],
                "publication_date": row[25],
                "raw_html_file": row[26],
                "agency_listing_id": row[27],
                "modify_date": row[28],
                "creation_date": row[29],
                "last_verified_date": row[30],
                "is_broken": row[31],
                "raw_html_page_id": row[32],
            }
        else:
            # Old schema: 32 columns (real database)
            listing_data = {
                "id": row[0],
                "title": row[1],
                "url": row[2],
                "description": row[3],
                "contract_type": row[4],
                "price": row[5],
                "city": row[6],
                "neighborhood": row[7],
                "address": row[8],
                "rooms": row[9],
                "bedrooms": row[10],
                "bathrooms": row[11],
                "square_meters": row[12],
                "floor": row[13],
                "year_built": row[14],
                "has_elevator": row[15],
                "heating": row[16],
                "has_air_conditioning": row[17],
                "has_garage": row[18],
                "is_furnished": row[19],
                "energy_class": row[20],
                "energy_consumption": row[21],
                "features": row[22],
                "scrape_date": row[23],
                "publication_date": row[24],
                "raw_html_file": row[25],
                "agency_listing_id": row[26],
                "modify_date": row[27],
                "agency_id": row[28],
                "creation_date": row[29],
                "last_verified_date": row[30],
                "is_broken": row[31],
            }

        # Convert features from string back to list
        if listing_data["features"]:
            try:
                # Simple parsing - this would need to be more robust for complex cases
                listing_data["features"] = (
                    listing_data["features"].strip("[]").split(", ")
                )
            except:
                listing_data["features"] = []

        return Listing.from_dict(listing_data)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get total count
                cursor.execute("SELECT COUNT(*) FROM listings")
                total = cursor.fetchone()[0]

                # Get average price
                cursor.execute("SELECT AVG(price) FROM listings")
                avg_price = cursor.fetchone()[0] or 0

                # Get average size
                cursor.execute(
                    "SELECT AVG(square_meters) FROM listings WHERE square_meters IS NOT NULL"
                )
                avg_size = cursor.fetchone()[0] or 0

                # Get last updated
                cursor.execute("SELECT MAX(scrape_date) FROM listings")
                last_updated = cursor.fetchone()[0]

                return {
                    "total_properties": total,
                    "average_price": round(avg_price, 2),
                    "average_size": round(avg_size, 2),
                    "last_updated": last_updated,
                }

        except sqlite3.Error as e:
            self.logger.error(f"Error getting stats: {e}")
            return {
                "total_properties": 0,
                "average_price": 0,
                "average_size": 0,
                "last_updated": None,
            }

    def get_price_distribution(self) -> Dict[str, Any]:
        """Get price distribution data for histogram."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Define price ranges for sell properties (in euros)
                sell_ranges = [
                    (0, 50000),
                    (50000, 100000),
                    (100000, 150000),
                    (150000, 200000),
                    (200000, 250000),
                    (250000, 300000),
                    (300000, 500000),
                    (500000, 1000000),
                ]

                # Define price ranges for rent properties (in euros)
                rent_ranges = [
                    (0, 300),
                    (300, 500),
                    (500, 700),
                    (700, 900),
                    (900, 1200),
                    (1200, 1500),
                    (1500, 2000),
                    (2000, 3000),
                ]

                # Get sell price distribution
                sell_distribution = []
                for min_price, max_price in sell_ranges:
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM listings 
                        WHERE contract_type LIKE "%SELL%" AND price >= ? AND price < ?
                    """,
                        (min_price, max_price),
                    )
                    count = cursor.fetchone()[0]
                    sell_distribution.append(count)

                # Get rent price distribution
                rent_distribution = []
                for min_price, max_price in rent_ranges:
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM listings 
                        WHERE contract_type LIKE "%RENT%" AND price >= ? AND price < ?
                    """,
                        (min_price, max_price),
                    )
                    count = cursor.fetchone()[0]
                    rent_distribution.append(count)

                return {
                    "sell": {
                        "ranges": [
                            f"€{min_price / 1000:.0f}k-€{max_price / 1000:.0f}k"
                            for min_price, max_price in sell_ranges
                        ],
                        "counts": sell_distribution,
                    },
                    "rent": {
                        "ranges": [
                            f"€{min_price}-€{max_price}"
                            for min_price, max_price in rent_ranges
                        ],
                        "counts": rent_distribution,
                    },
                }

        except sqlite3.Error as e:
            self.logger.error(f"Error getting price distribution: {e}")
            return {
                "sell": {"ranges": [], "counts": []},
                "rent": {"ranges": [], "counts": []},
            }

    def clear_all_listings(self) -> int:
        """Remove all listings from the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get count before deletion
                cursor.execute("SELECT COUNT(*) FROM listings")
                count_before = cursor.fetchone()[0]

                # Delete all listings
                cursor.execute("DELETE FROM listings")

                conn.commit()

                self.logger.info(
                    f"Cleared all listings from database. Removed {count_before} listings."
                )
                return count_before

        except sqlite3.Error as e:
            self.logger.error(f"Error clearing all listings: {e}")
            return -1

    def _cleanup_scrape_history(self) -> None:
        """Clean up scrape history to keep only MAX_SCRAPE_HISTORY_ENTRIES."""
        try:
            from config import MAX_SCRAPE_HISTORY_ENTRIES

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Delete oldest entries if we have more than MAX_SCRAPE_HISTORY_ENTRIES
                cursor.execute("SELECT COUNT(*) FROM scrape_history")
                count = cursor.fetchone()[0]

                if count > MAX_SCRAPE_HISTORY_ENTRIES:
                    # Calculate how many to delete
                    to_delete = count - MAX_SCRAPE_HISTORY_ENTRIES

                    # Delete oldest entries (keep newest)
                    cursor.execute(
                        """
                        DELETE FROM scrape_history 
                        WHERE id IN (
                            SELECT id FROM scrape_history 
                            ORDER BY timestamp ASC 
                            LIMIT ?
                        )
                    """,
                        (to_delete,),
                    )

                    self.logger.info(
                        f"Cleaned up scrape history: deleted {to_delete} oldest entries"
                    )

                conn.commit()

        except sqlite3.Error as e:
            self.logger.error(f"Error cleaning up scrape history: {e}")

    def cleanup_old_logs(self) -> int:
        """Delete log entries older than 1 day. Returns count of deleted entries."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cutoff_time = datetime.now().isoformat()

                cursor.execute("""
                    DELETE FROM application_logs
                    WHERE timestamp < datetime('now', '-1 day')
                """)

                deleted_count = cursor.rowcount
                conn.commit()

                self.logger.info(
                    f"Cleaned up old logs: deleted {deleted_count} entries"
                )
                return deleted_count

        except sqlite3.Error as e:
            self.logger.error(f"Error cleaning up old logs: {e}")
            return 0

    def add_log(
        self,
        level: str,
        source: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a log entry to the database.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            source: Module/component name
            message: Human-readable log message
            details: Optional dictionary with additional context (JSON serialized)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                details_json = json.dumps(details) if details else None

                cursor.execute(
                    """
                    INSERT INTO application_logs 
                    (timestamp, level, source, message, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now().isoformat(),
                        level,
                        source,
                        message,
                        details_json,
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error adding log entry: {e}")

    def get_log_entries(
        self,
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        level: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get log entries with filtering options.

        Args:
            limit: Maximum number of entries to return
            start_date: ISO format start date (inclusive)
            end_date: ISO format end date (inclusive)
            level: Filter by log level
            source: Filter by source
            search: Search text to filter messages

        Returns:
            List of log entries as dictionaries
        """
        try:
            query = "SELECT * FROM application_logs WHERE 1=1"
            params = []

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            if level:
                query += " AND level = ?"
                params.append(level)
            if source:
                query += " AND source = ?"
                params.append(source)
            if search:
                query += " AND message LIKE ?"
                params.append(f"%{search}%")

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

                logs = []
                for row in rows:
                    logs.append(
                        {
                            "id": row[0],
                            "timestamp": row[1],
                            "level": row[2],
                            "source": row[3],
                            "message": row[4],
                            "details": json.loads(row[5]) if row[5] else None,
                            "created_at": row[6],
                        }
                    )
                return logs

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching log entries: {e}")
            return []

    def log_scrape_run(
        self, source: str, listings_count: int, duration_seconds: float
    ) -> None:
        """Log a scrape run to the scrape history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Insert new scrape record
                cursor.execute(
                    """
                    INSERT INTO scrape_history (timestamp, source, listings_count, duration_seconds)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        datetime.now().isoformat(),
                        source,
                        listings_count,
                        duration_seconds,
                    ),
                )

                conn.commit()

                # Clean up old entries
                self._cleanup_scrape_history()

                self.logger.info(
                    f"Logged scrape run: {source} - {listings_count} listings in {duration_seconds:.1f}s"
                )

        except sqlite3.Error as e:
            self.logger.error(f"Error logging scrape run: {e}")

    def get_last_scrape_time(self) -> Optional[datetime]:
        """Get the timestamp of the last scrape run."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT timestamp FROM scrape_history 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)

                row = cursor.fetchone()
                if row:
                    return datetime.fromisoformat(row[0])
                return None

        except sqlite3.Error as e:
            self.logger.error(f"Error getting last scrape time: {e}")
            return None

    # Telegram Configuration Methods
    def _ensure_notification_tables_exist(self) -> None:
        """Ensure notification tables exist in the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Create telegram_configurations table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS telegram_configurations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bot_token TEXT NOT NULL UNIQUE,
                        bot_name TEXT,
                        chat_id TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)

                # Add chat_id column if it doesn't exist (for existing databases)
                try:
                    cursor.execute(
                        "ALTER TABLE telegram_configurations ADD COLUMN chat_id TEXT"
                    )
                    conn.commit()
                    self.logger.info(
                        "Added chat_id column to telegram_configurations table"
                    )
                except sqlite3.Error:
                    # Column already exists or table doesn't exist, which is fine
                    pass

                # Create notification_subscriptions table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notification_subscriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        subscription_name TEXT NOT NULL,
                        search_filters TEXT NOT NULL,
                        telegram_config_id INTEGER NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        FOREIGN KEY (telegram_config_id) REFERENCES telegram_configurations(id) ON DELETE CASCADE
                    )
                """)

                # Add telegram_config_id column if it doesn't exist (for existing databases)
                try:
                    cursor.execute(
                        "ALTER TABLE notification_subscriptions ADD COLUMN telegram_config_id INTEGER"
                    )
                    conn.commit()
                    self.logger.info(
                        "Added telegram_config_id column to notification_subscriptions table"
                    )
                except sqlite3.Error:
                    # Column already exists or table doesn't exist, which is fine
                    pass

                # Handle migration from telegram_chat_id to telegram_config_id (if old schema exists)
                try:
                    # Check if telegram_chat_id column exists
                    cursor.execute("PRAGMA table_info(notification_subscriptions)")
                    columns = [column[1] for column in cursor.fetchall()]

                    if "telegram_chat_id" in columns:
                        # First, drop the foreign key constraint if it exists
                        try:
                            cursor.execute("PRAGMA foreign_keys=OFF")
                            # Recreate the table without the old column
                            cursor.execute("""
                                CREATE TABLE IF NOT EXISTS notification_subscriptions_new (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    user_id TEXT NOT NULL,
                                    subscription_name TEXT NOT NULL,
                                    search_filters TEXT NOT NULL,
                                    telegram_config_id INTEGER NOT NULL,
                                    is_active BOOLEAN DEFAULT TRUE,
                                    created_at TEXT NOT NULL,
                                    updated_at TEXT NOT NULL,
                                    FOREIGN KEY (telegram_config_id) REFERENCES telegram_configurations(id) ON DELETE CASCADE
                                )
                            """)

                            # Copy data from old table to new table
                            cursor.execute("""
                                INSERT INTO notification_subscriptions_new 
                                    (id, user_id, subscription_name, search_filters, telegram_config_id, is_active, created_at, updated_at)
                                SELECT 
                                    id, user_id, subscription_name, search_filters, telegram_chat_id, is_active, created_at, updated_at
                                FROM notification_subscriptions
                            """)

                            # Drop old table and rename new table
                            cursor.execute("DROP TABLE notification_subscriptions")
                            cursor.execute(
                                "ALTER TABLE notification_subscriptions_new RENAME TO notification_subscriptions"
                            )

                            conn.commit()
                            self.logger.info(
                                "Migrated from telegram_chat_id to telegram_config_id"
                            )
                        finally:
                            cursor.execute("PRAGMA foreign_keys=ON")
                except sqlite3.Error as e:
                    self.logger.warning(
                        f"Could not migrate telegram_chat_id column: {e}"
                    )
                    # This is not critical, continue execution

                # Create notification_history table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notification_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        listing_id INTEGER NOT NULL,
                        subscription_id INTEGER NOT NULL,
                        notification_sent_at TEXT NOT NULL,
                        telegram_message_id TEXT,
                        is_successful BOOLEAN DEFAULT FALSE,
                        error_message TEXT,
                        FOREIGN KEY (listing_id) REFERENCES listings(id),
                        FOREIGN KEY (subscription_id) REFERENCES notification_subscriptions(id),
                        UNIQUE(listing_id, subscription_id)
                    )
                """)

                conn.commit()
                self.logger.info("Ensured notification tables exist")

        except sqlite3.Error as e:
            self.logger.error(f"Error ensuring notification tables exist: {e}")
            raise

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
                    (
                        "notification_enabled",
                        "boolean",
                        "true",
                        "Whether notifications are enabled globally",
                    ),
                    (
                        "notification_template",
                        "string",
                        self._get_default_notification_template(),
                        "Default notification message template",
                    ),
                    (
                        "virtualhost",
                        "string",
                        None,
                        "Virtualhost for internal URLs in notifications (full URL or hostname:port). If null, uses localhost:FLASK_PORT",
                    ),
                ]

                for key, type_, value, desc in defaults:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO configurations 
                        (config_key, config_type, config_value, description, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            key,
                            type_,
                            value,
                            desc,
                            datetime.now().isoformat(),
                            datetime.now().isoformat(),
                        ),
                    )

                conn.commit()
                self.logger.info("Ensured configurations table exists with defaults")

        except sqlite3.Error as e:
            self.logger.error(f"Error ensuring configurations table: {e}")
            raise

    def _get_default_notification_template(self) -> str:
        """Get the default notification template as plain string."""
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

    def save_config(self, config: Configuration) -> int:
        """Save a configuration to the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()

                # Check if config already exists
                cursor.execute(
                    "SELECT id FROM configurations WHERE config_key = ?",
                    (config.config_key,),
                )
                existing = cursor.fetchone()

                if existing:
                    # Update existing
                    cursor.execute(
                        """
                        UPDATE configurations SET 
                            config_type = ?,
                            config_value = ?,
                            description = ?,
                            is_active = ?,
                            updated_at = ?
                        WHERE config_key = ?
                    """,
                        (
                            config.config_type.value,
                            config.config_value,
                            config.description,
                            config.is_active,
                            now,
                            config.config_key,
                        ),
                    )
                    conn.commit()
                    self.logger.info(f"Updated configuration: {config.config_key}")
                    return existing[0]
                else:
                    # Insert new
                    cursor.execute(
                        """
                        INSERT INTO configurations 
                        (config_key, config_type, config_value, description, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            config.config_key,
                            config.config_type.value,
                            config.config_value,
                            config.description,
                            config.is_active,
                            now,
                            now,
                        ),
                    )
                    conn.commit()
                    config_id = cursor.lastrowid or -1
                    self.logger.info(f"Inserted new configuration: {config.config_key}")
                    return config_id

        except sqlite3.Error as e:
            self.logger.error(f"Error saving configuration {config.config_key}: {e}")
            return -1

    def get_config(self, config_key: str) -> Optional[Configuration]:
        """Get a configuration by key."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, config_key, config_type, config_value, description, is_active, created_at, updated_at
                    FROM configurations 
                    WHERE config_key = ?
                """,
                    (config_key,),
                )
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
                        updated_at=row[7],
                    )
                return None

        except sqlite3.Error as e:
            self.logger.error(f"Error getting configuration {config_key}: {e}")
            return None

    def get_all_configs(self) -> List[Configuration]:
        """Get all configurations."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, config_key, config_type, config_value, description, is_active, created_at, updated_at
                    FROM configurations 
                    ORDER BY config_key
                """
                )
                rows = cursor.fetchall()

                configs = []
                for row in rows:
                    configs.append(
                        Configuration(
                            id=row[0],
                            config_key=row[1],
                            config_type=ConfigType(row[2]),
                            config_value=row[3],
                            description=row[4],
                            is_active=bool(row[5]),
                            created_at=row[6],
                            updated_at=row[7],
                        )
                    )
                return configs

        except sqlite3.Error as e:
            self.logger.error(f"Error getting all configurations: {e}")
            return []

    def delete_config(self, config_key: str) -> bool:
        """Delete a configuration by key."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM configurations WHERE config_key = ?",
                    (config_key,),
                )
                conn.commit()

                if cursor.rowcount > 0:
                    self.logger.info(f"Deleted configuration: {config_key}")
                    return True
                return False

        except sqlite3.Error as e:
            self.logger.error(f"Error deleting configuration {config_key}: {e}")
            return False

    def save_telegram_config(self, config: TelegramConfiguration) -> int:
        """Save Telegram configuration to database.

        Forces all configurations to use id=1, maintaining single config support.
        For existing databases with multiple configs, keeps the first one and logs warning.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                now = datetime.now().isoformat()
                config_id = 1  # Force id=1

                # Check if configuration already exists with id=1
                cursor.execute(
                    "SELECT id FROM telegram_configurations WHERE id = ?", (config_id,)
                )
                existing_with_id1 = cursor.fetchone()

                if existing_with_id1:
                    # Update existing configuration with id=1
                    update_query = """
                        UPDATE telegram_configurations SET 
                            bot_token = ?,
                            bot_name = ?,
                            chat_id = ?,
                            is_active = ?,
                            updated_at = ?
                        WHERE id = ?
                    """

                    cursor.execute(
                        update_query,
                        (
                            config.bot_token,
                            config.bot_name,
                            config.chat_id,
                            config.is_active,
                            now,
                            config_id,
                        ),
                    )

                    conn.commit()
                    self.logger.info(f"Updated Telegram configuration with id=1")
                    return config_id
                else:
                    # Check if any configuration exists (for migration)
                    cursor.execute("SELECT COUNT(*) FROM telegram_configurations")
                    existing_configs = cursor.fetchone()[0]

                    if existing_configs > 0:
                        # Log warning that we're keeping the first config
                        self.logger.warning(
                            f"Found {existing_configs} existing configuration(s). Keeping first config (id=1) and ignoring others."
                        )

                    # Insert new configuration with id=1
                    insert_query = """
                        INSERT INTO telegram_configurations 
                            (id, bot_token, bot_name, chat_id, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """

                    cursor.execute(
                        insert_query,
                        (
                            config_id,
                            config.bot_token,
                            config.bot_name,
                            config.chat_id,
                            config.is_active,
                            now,
                            now,
                        ),
                    )

                    conn.commit()
                    self.logger.info(f"Inserted new Telegram configuration with id=1")
                    return config_id

        except Exception as e:
            self.logger.error(f"Error saving Telegram configuration: {e}")
            return -1

    def get_all_telegram_configs(self) -> List[TelegramConfiguration]:
        """Get Telegram configurations with id=1 (single config support)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, bot_token, bot_name, chat_id, is_active, created_at, updated_at 
                    FROM telegram_configurations 
                    WHERE id = 1 
                    ORDER BY created_at DESC
                """)
                rows = cursor.fetchall()

                configs = []
                for row in rows:
                    configs.append(
                        TelegramConfiguration(
                            id=row[0],
                            bot_token=row[1],
                            bot_name=row[2],
                            chat_id=row[3],
                            is_active=bool(row[4]),
                            created_at=row[5],
                            updated_at=row[6],
                        )
                    )

                return configs

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching Telegram configs: {e}")
            return []

    def get_active_telegram_configs(self) -> List[TelegramConfiguration]:
        """Get all active Telegram configurations."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, bot_token, bot_name, chat_id, is_active, created_at, updated_at 
                    FROM telegram_configurations 
                    WHERE is_active = TRUE 
                    ORDER BY created_at DESC
                """)
                rows = cursor.fetchall()

                configs = []
                for row in rows:
                    configs.append(
                        TelegramConfiguration(
                            id=row[0],
                            bot_token=row[1],
                            bot_name=row[2],
                            chat_id=row[3],
                            is_active=bool(row[4]),
                            created_at=row[5],
                            updated_at=row[6],
                        )
                    )

                return configs

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching active Telegram configs: {e}")
            return []

    def get_telegram_config_by_id(
        self, config_id: int
    ) -> Optional[TelegramConfiguration]:
        """Get Telegram configuration by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, bot_token, bot_name, chat_id, is_active, created_at, updated_at 
                    FROM telegram_configurations 
                    WHERE id = ?
                """,
                    (config_id,),
                )
                row = cursor.fetchone()

                if row:
                    return TelegramConfiguration(
                        id=row[0],
                        bot_token=row[1],
                        bot_name=row[2],
                        chat_id=row[3],
                        is_active=bool(row[4]),
                        created_at=row[5],
                        updated_at=row[6],
                    )

                return None

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching Telegram config by ID {config_id}: {e}")
            return None

    def delete_telegram_config(self, config_id: int) -> bool:
        """Delete Telegram configuration by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM telegram_configurations WHERE id = ?", (config_id,)
                )
                conn.commit()

                if cursor.rowcount > 0:
                    self.logger.info(f"Deleted Telegram configuration ID {config_id}")
                    return True
                else:
                    self.logger.warning(
                        f"No Telegram configuration found with ID {config_id}"
                    )
                    return False

        except sqlite3.Error as e:
            self.logger.error(f"Error deleting Telegram config {config_id}: {e}")
            return False

    # Notification Subscription Methods
    def get_active_notification_subscriptions(self) -> List[NotificationSubscription]:
        """Get all active notification subscriptions."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, user_id, subscription_name, search_filters, 
                           telegram_config_id, is_active, created_at, updated_at 
                    FROM notification_subscriptions 
                    WHERE is_active = TRUE 
                    ORDER BY created_at DESC
                """)
                rows = cursor.fetchall()

                subscriptions = []
                for row in rows:
                    # Parse search_filters from JSON
                    import json

                    search_filters = json.loads(row[3]) if row[3] else {}

                    subscriptions.append(
                        NotificationSubscription(
                            id=row[0],
                            user_id=row[1],
                            subscription_name=row[2],
                            search_filters=search_filters,
                            telegram_config_id=row[4],
                            is_active=bool(row[5]),
                            created_at=row[6],
                            updated_at=row[7],
                        )
                    )

                return subscriptions

        except Exception as e:
            self.logger.error(f"Error fetching active notification subscriptions: {e}")
            return []

    def get_notification_subscriptions_by_user(
        self, user_id: str
    ) -> List[NotificationSubscription]:
        """Get notification subscriptions for a specific user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, user_id, subscription_name, search_filters, 
                           telegram_config_id, is_active, created_at, updated_at 
                    FROM notification_subscriptions 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC
                """,
                    (user_id,),
                )
                rows = cursor.fetchall()

                subscriptions = []
                for row in rows:
                    # Parse search_filters from JSON
                    import json

                    search_filters = json.loads(row[3]) if row[3] else {}

                    subscriptions.append(
                        NotificationSubscription(
                            id=row[0],
                            user_id=row[1],
                            subscription_name=row[2],
                            search_filters=search_filters,
                            telegram_config_id=row[4],
                            is_active=bool(row[5]),
                            created_at=row[6],
                            updated_at=row[7],
                        )
                    )

                return subscriptions

        except Exception as e:
            self.logger.error(
                f"Error fetching notification subscriptions for user {user_id}: {e}"
            )
            return []

    def delete_notification_subscription(self, subscription_id: int) -> bool:
        """Delete notification subscription by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM notification_subscriptions WHERE id = ?",
                    (subscription_id,),
                )
                conn.commit()

                if cursor.rowcount > 0:
                    self.logger.info(
                        f"Deleted notification subscription ID {subscription_id}"
                    )
                    return True
                else:
                    self.logger.warning(
                        f"No notification subscription found with ID {subscription_id}"
                    )
                    return False

        except sqlite3.Error as e:
            self.logger.error(
                f"Error deleting notification subscription {subscription_id}: {e}"
            )
            return False

    def save_notification_subscription(
        self, subscription: NotificationSubscription
    ) -> int:
        """Save notification subscription to database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                now = datetime.now().isoformat()

                # Convert search_filters to JSON string
                import json

                search_filters_json = json.dumps(subscription.search_filters or {})

                if subscription.id:
                    # Update existing subscription
                    update_query = """
                        UPDATE notification_subscriptions SET 
                            user_id = ?,
                            subscription_name = ?,
                            search_filters = ?,
                            telegram_config_id = ?,
                            is_active = ?,
                            updated_at = ?
                        WHERE id = ?
                    """

                    cursor.execute(
                        update_query,
                        (
                            subscription.user_id,
                            subscription.subscription_name,
                            search_filters_json,
                            subscription.telegram_config_id,
                            subscription.is_active,
                            now,
                            subscription.id,
                        ),
                    )

                    self.logger.info(
                        f"Updated notification subscription: {subscription.subscription_name}"
                    )
                    conn.commit()
                    return subscription.id
                else:
                    # Insert new subscription
                    insert_query = """
                        INSERT INTO notification_subscriptions 
                            (user_id, subscription_name, search_filters, 
                             telegram_config_id, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """

                    cursor.execute(
                        insert_query,
                        (
                            subscription.user_id,
                            subscription.subscription_name,
                            search_filters_json,
                            subscription.telegram_config_id,
                            subscription.is_active,
                            now,
                            now,
                        ),
                    )

                    subscription_id = cursor.lastrowid or -1
                    self.logger.info(
                        f"Inserted new notification subscription: {subscription.subscription_name} (ID: {subscription_id})"
                    )
                    conn.commit()

                    # Check for existing properties that match the subscription filters
                    # and haven't been notified to this subscription yet
                    if subscription.search_filters:
                        self._check_existing_properties_for_subscription(
                            subscription_id, subscription.search_filters
                        )

                    return subscription_id

        except sqlite3.Error as e:
            self.logger.error(f"Error saving notification subscription: {e}")
            return -1

    def _check_existing_properties_for_subscription(
        self, subscription_id: int, search_filters: Optional[Dict[str, Any]]
    ) -> None:
        """Check for existing properties that match the subscription and log notifications if needed."""
        try:
            # Get the subscription to access telegram_config_id
            subscription = self.get_notification_subscription_by_id(subscription_id)
            if not subscription:
                self.logger.warning(f"Subscription {subscription_id} not found")
                return

            # Get all listings that match the search filters
            if search_filters:
                matching_listings = self._find_listings_matching_filters(search_filters)
            else:
                matching_listings = self.get_all_listings()

            if not matching_listings:
                self.logger.info(
                    f"No existing listings match subscription {subscription_id} filters"
                )
                return

            # Check which listings haven't been notified to this subscription yet
            listings_to_notify = []
            for listing in matching_listings:
                # Check if this listing has already been notified to this subscription
                if listing.id is not None:
                    notification_count = (
                        self._get_notification_count_for_listing_subscription(
                            listing.id, subscription_id
                        )
                    )
                    if notification_count == 0:
                        listings_to_notify.append(listing)

            if listings_to_notify:
                self.logger.info(
                    f"Found {len(listings_to_notify)} existing listings to notify for subscription {subscription_id}"
                )

                # Log notifications for these listings (they will be sent by the notification service)
                for listing in listings_to_notify:
                    if listing.id is not None:
                        self.log_notification(
                            listing.id,
                            subscription_id,
                            telegram_message_id=None,  # Will be updated when actually sent
                            is_successful=False,  # Mark as not yet sent
                            error_message="Pending notification for existing property",
                        )

                self.logger.info(
                    f"Queued {len(listings_to_notify)} notifications for existing matching properties"
                )
            else:
                self.logger.info(
                    f"All matching existing listings have already been notified for subscription {subscription_id}"
                )

        except Exception as e:
            self.logger.error(
                f"Error checking existing properties for subscription {subscription_id}: {e}"
            )

    def _find_listings_matching_filters(
        self, search_filters: Optional[Dict[str, Any]]
    ) -> List[Listing]:
        """Find listings that match the given search filters."""
        try:
            if not search_filters:
                # No filters means match all listings
                return self.get_all_listings()

            # Build a dynamic query based on the filters
            query = "SELECT * FROM listings WHERE 1=1"
            params = []

            # Add filter conditions - only if value is not None
            if "city" in search_filters and search_filters["city"] is not None:
                # Handle both None and string 'None' cases
                city_value = search_filters["city"]
                if city_value != "None" and city_value != "":
                    query += " AND city = ?"
                    params.append(city_value)

            if (
                "contract_type" in search_filters
                and search_filters["contract_type"] is not None
            ):
                # Handle both None and string 'None' cases
                contract_type_value = search_filters["contract_type"]
                if contract_type_value != "None" and contract_type_value != "":
                    query += " AND contract_type = ?"
                    # Normalize contract type to lowercase for comparison (enum values are lowercase)
                    contract_type_filter = str(contract_type_value).lower()
                    params.append(contract_type_filter)

            if (
                "min_price" in search_filters
                and search_filters["min_price"] is not None
            ):
                # Handle both None and string 'None' cases
                min_price_value = search_filters["min_price"]
                if min_price_value != "None" and min_price_value != "":
                    query += " AND price >= ?"
                    params.append(float(min_price_value))

            if (
                "max_price" in search_filters
                and search_filters["max_price"] is not None
            ):
                # Handle both None and string 'None' cases
                max_price_value = search_filters["max_price"]
                if max_price_value != "None" and max_price_value != "":
                    query += " AND price <= ?"
                    params.append(float(max_price_value))

            if "min_size" in search_filters and search_filters["min_size"] is not None:
                # Handle both None and string 'None' cases
                min_size_value = search_filters["min_size"]
                if min_size_value != "None" and min_size_value != "":
                    query += " AND square_meters >= ?"
                    params.append(int(min_size_value))

            # Execute the query
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [self._row_to_listing(row) for row in rows]

        except Exception as e:
            self.logger.error(f"Error finding listings matching filters: {e}")
            return []

    def _get_notification_count_for_listing_subscription(
        self, listing_id: int, subscription_id: int
    ) -> int:
        """Get the number of notifications sent for a specific listing and subscription."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM notification_history 
                    WHERE listing_id = ? AND subscription_id = ?
                """,
                    (listing_id, subscription_id),
                )
                count = cursor.fetchone()[0]
                return count or 0

        except sqlite3.Error as e:
            self.logger.error(
                f"Error getting notification count for listing {listing_id}, subscription {subscription_id}: {e}"
            )
            return 0

    def get_notification_subscription_by_id(
        self, subscription_id: int
    ) -> Optional[NotificationSubscription]:
        """Get notification subscription by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, user_id, subscription_name, search_filters, 
                           telegram_config_id, is_active, created_at, updated_at 
                    FROM notification_subscriptions 
                    WHERE id = ?
                """,
                    (subscription_id,),
                )
                row = cursor.fetchone()

                if row:
                    # Parse search_filters from JSON
                    import json

                    search_filters = json.loads(row[3]) if row[3] else {}

                    return NotificationSubscription(
                        id=row[0],
                        user_id=row[1],
                        subscription_name=row[2],
                        search_filters=search_filters,
                        telegram_config_id=row[4],
                        is_active=bool(row[5]),
                        created_at=row[6],
                        updated_at=row[7],
                    )

                return None

        except sqlite3.Error as e:
            self.logger.error(
                f"Error fetching notification subscription by ID {subscription_id}: {e}"
            )
            return None

    def log_notification(
        self,
        listing_id: int,
        subscription_id: int,
        telegram_message_id: Optional[str],
        is_successful: bool,
        error_message: Optional[str] = None,
    ) -> int:
        """Log a notification to the notification history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check if this notification already exists (duplicate prevention)
                cursor.execute(
                    """
                    SELECT id FROM notification_history 
                    WHERE listing_id = ? AND subscription_id = ?
                """,
                    (listing_id, subscription_id),
                )
                existing = cursor.fetchone()

                if existing:
                    # Update existing notification
                    update_query = """
                        UPDATE notification_history SET 
                            telegram_message_id = ?,
                            is_successful = ?,
                            error_message = ?
                        WHERE id = ?
                    """

                    cursor.execute(
                        update_query,
                        (
                            telegram_message_id,
                            is_successful,
                            error_message,
                            existing[0],
                        ),
                    )

                    self.logger.info(
                        f"Updated existing notification for listing {listing_id}, subscription {subscription_id}"
                    )
                    conn.commit()
                    return existing[0]
                else:
                    # Insert new notification
                    insert_query = """
                        INSERT INTO notification_history 
                            (listing_id, subscription_id, notification_sent_at, 
                             telegram_message_id, is_successful, error_message)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """

                    cursor.execute(
                        insert_query,
                        (
                            listing_id,
                            subscription_id,
                            datetime.now().isoformat(),
                            telegram_message_id,
                            is_successful,
                            error_message,
                        ),
                    )

                    notification_id = cursor.lastrowid or -1
                    self.logger.info(
                        f"Logged notification for listing {listing_id}, subscription {subscription_id} (ID: {notification_id})"
                    )
                    conn.commit()
                    return notification_id

        except sqlite3.Error as e:
            self.logger.error(f"Error logging notification: {e}")
            return -1

    def get_notification_count_for_listing(self, listing_id: int) -> int:
        """Get the number of notifications sent for a listing."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM notification_history 
                    WHERE listing_id = ?
                """,
                    (listing_id,),
                )
                count = cursor.fetchone()[0]
                return count or 0

        except sqlite3.Error as e:
            self.logger.error(
                f"Error getting notification count for listing {listing_id}: {e}"
            )
            return 0

    def get_notification_history_for_subscription(
        self, subscription_id: int
    ) -> List[NotificationHistory]:
        """Get notification history for a specific subscription."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT nh.id, nh.listing_id, nh.subscription_id, ns.subscription_name, 
                           nh.notification_sent_at, nh.telegram_message_id, 
                           nh.is_successful, nh.error_message
                    FROM notification_history nh
                    LEFT JOIN notification_subscriptions ns ON nh.subscription_id = ns.id
                    WHERE nh.subscription_id = ?
                    ORDER BY nh.notification_sent_at DESC
                """,
                    (subscription_id,),
                )
                rows = cursor.fetchall()

                history = []
                for row in rows:
                    history.append(
                        NotificationHistory(
                            id=row[0],
                            listing_id=row[1],
                            subscription_id=row[2],
                            subscription_name=row[3] or "",
                            notification_sent_at=row[4],
                            telegram_message_id=row[5],
                            is_successful=bool(row[6]),
                            error_message=row[7],
                        )
                    )

                return history

        except sqlite3.Error as e:
            self.logger.error(
                f"Error getting notification history for subscription {subscription_id}: {e}"
            )
            return []

    # Notification History Methods
    def get_recent_notification_history(
        self, limit: int = 20
    ) -> List[NotificationHistory]:
        """Get recent notification history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT nh.id, nh.listing_id, nh.subscription_id, ns.subscription_name, 
                           nh.notification_sent_at, nh.telegram_message_id, 
                           nh.is_successful, nh.error_message
                    FROM notification_history nh
                    LEFT JOIN notification_subscriptions ns ON nh.subscription_id = ns.id
                    ORDER BY nh.notification_sent_at DESC 
                    LIMIT ?
                """,
                    (limit,),
                )
                rows = cursor.fetchall()

                history = []
                for row in rows:
                    history.append(
                        NotificationHistory(
                            id=row[0],
                            listing_id=row[1],
                            subscription_id=row[2],
                            subscription_name=row[3] or "",
                            notification_sent_at=row[4],
                            telegram_message_id=row[5],
                            is_successful=bool(row[6]),
                            error_message=row[7],
                        )
                    )

                return history

        except sqlite3.Error as e:
            self.logger.error(f"Error getting recent notification history: {e}")
            return []

    def get_pending_notifications(self) -> List[NotificationHistory]:
        """Get all pending notifications that haven't been sent yet."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT nh.id, nh.listing_id, nh.subscription_id, ns.subscription_name, 
                           nh.notification_sent_at, nh.telegram_message_id, 
                           nh.is_successful, nh.error_message
                    FROM notification_history nh
                    LEFT JOIN notification_subscriptions ns ON nh.subscription_id = ns.id
                    WHERE nh.is_successful = FALSE 
                      AND nh.error_message LIKE 'Pending%'
                    ORDER BY nh.notification_sent_at ASC
                """)
                rows = cursor.fetchall()

                history = []
                for row in rows:
                    history.append(
                        NotificationHistory(
                            id=row[0],
                            listing_id=row[1],
                            subscription_id=row[2],
                            subscription_name=row[3] or "",
                            notification_sent_at=row[4],
                            telegram_message_id=row[5],
                            is_successful=bool(row[6]),
                            error_message=row[7],
                        )
                    )

                return history

        except sqlite3.Error as e:
            self.logger.error(f"Error getting pending notifications: {e}")
            return []

    def get_scrape_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent scrape history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT timestamp, source, listings_count, duration_seconds 
                    FROM scrape_history 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """,
                    (limit,),
                )

                rows = cursor.fetchall()

                history = []
                for row in rows:
                    history.append(
                        {
                            "timestamp": row[0],
                            "source": row[1],
                            "listings_count": row[2],
                            "duration_seconds": row[3],
                        }
                    )

                return history

        except sqlite3.Error as e:
            self.logger.error(f"Error getting recent scrape history: {e}")
            return []
