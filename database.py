import sqlite3
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from datetime import datetime
from dataclasses import dataclass

from models import Listing
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


class DatabaseManager:
    """Database manager for property listings."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_FILE
        self.logger = logging.getLogger(__name__)
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Initialize database and create tables if they don't exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create agencies table
                cursor.execute('''
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
                ''')
                
                # Create listings table (updated to use agency_id instead of agency)
                cursor.execute('''
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
                         FOREIGN KEY (agency_id) REFERENCES agencies(id)
                     )
                 ''')
                 
                # Create indexes for better search performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_city ON listings(city)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_price ON listings(price)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract ON listings(contract_type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_square_meters ON listings(square_meters)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_agency ON listings(agency_id)')
                 
                 # Create scrape_history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scrape_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        source TEXT NOT NULL,
                        listings_count INTEGER,
                        duration_seconds REAL
                    )
                ''')

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
                cursor.execute('SELECT id, name, website_url, phone, email, address, created_at, updated_at FROM agencies WHERE id = ?', (agency_id,))
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
                        updated_at=row[7]
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
                cursor.execute('SELECT id, name, website_url, phone, email, address, created_at, updated_at FROM agencies WHERE name = ?', (agency_name,))
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
                        updated_at=row[7]
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
                cursor.execute('SELECT id, name, website_url, phone, email, address, created_at, updated_at FROM agencies ORDER BY name')
                rows = cursor.fetchall()
                
                agencies = []
                for row in rows:
                    agencies.append(Agency(
                        id=row[0],
                        name=row[1],
                        website_url=row[2],
                        phone=row[3],
                        email=row[4],
                        address=row[5],
                        created_at=row[6],
                        updated_at=row[7]
                    ))
                
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
                cursor.execute('SELECT id FROM listings WHERE url = ?', (listing.url,))
                existing = cursor.fetchone()
                
                if existing:
                     # Update existing listing
                     update_query = '''
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
                             agency_listing_id = ?
                         WHERE url = ?
                     '''
                     
                     cursor.execute(update_query, (
                         listing_dict['title'],
                         listing_dict['agency_id'],
                         listing_dict['description'],
                         listing_dict['contract_type'],
                         listing_dict['price'],
                         listing_dict['city'],
                         listing_dict['neighborhood'],
                         listing_dict['address'],
                         listing_dict['rooms'],
                         listing_dict['bedrooms'],
                         listing_dict['bathrooms'],
                         listing_dict['square_meters'],
                         listing_dict['floor'],
                         listing_dict['year_built'],
                         listing_dict['has_elevator'],
                         listing_dict['heating'],
                         listing_dict['has_air_conditioning'],
                         listing_dict['has_garage'],
                         listing_dict['is_furnished'],
                         listing_dict['energy_class'],
                         listing_dict['energy_consumption'],
                         str(listing_dict['features']) if listing_dict['features'] else None,
                         listing_dict['scrape_date'],
                         listing_dict['publication_date'],
                         listing_dict['raw_html_file'],
                         listing_dict['agency_listing_id'],
                         listing.url
                     ))
                     
                     self.logger.info(f"Updated existing listing: {listing.url}")
                else:
                     # Insert new listing
                     insert_query = '''
                         INSERT INTO listings (
                             title, agency_id, url, description, contract_type, price, city, 
                             neighborhood, address, rooms, bedrooms, bathrooms, square_meters, 
                             floor, year_built, has_elevator, heating, has_air_conditioning, 
                             has_garage, is_furnished, energy_class, energy_consumption, 
                              features, scrape_date, publication_date, raw_html_file, agency_listing_id
                          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                     '''
                     
                     cursor.execute(insert_query, (
                         listing_dict['title'],
                         listing_dict['agency_id'],
                         listing_dict['url'],
                         listing_dict['description'],
                         listing_dict['contract_type'],
                         listing_dict['price'],
                         listing_dict['city'],
                         listing_dict['neighborhood'],
                         listing_dict['address'],
                         listing_dict['rooms'],
                         listing_dict['bedrooms'],
                         listing_dict['bathrooms'],
                         listing_dict['square_meters'],
                         listing_dict['floor'],
                         listing_dict['year_built'],
                         listing_dict['has_elevator'],
                         listing_dict['heating'],
                         listing_dict['has_air_conditioning'],
                         listing_dict['has_garage'],
                         listing_dict['is_furnished'],
                         listing_dict['energy_class'],
                         listing_dict['energy_consumption'],
                         str(listing_dict['features']) if listing_dict['features'] else None,
                         listing_dict['scrape_date'],
                         listing_dict['publication_date'],
                         listing_dict['raw_html_file'],
                          listing_dict['agency_listing_id']
                     ))
                     
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

    def update_listing(self, listing_id: int, update_data: Dict[str, Any]) -> bool:
        """Update a listing by ID with transaction support."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Begin transaction
                cursor.execute('BEGIN TRANSACTION')
                
                # Build update query dynamically based on provided fields
                update_fields = []
                update_values = []
                
                # Define which fields are editable (excluding URL, agency, scrape_date, ID)
                editable_fields = [
                    'title', 'description', 'contract_type', 'price', 'city', 'neighborhood',
                    'address', 'rooms', 'bedrooms', 'bathrooms', 'square_meters', 'floor',
                    'year_built', 'has_elevator', 'heating', 'has_air_conditioning', 'has_garage',
                    'is_furnished', 'energy_class', 'energy_consumption', 'features',
                    'publication_date', 'raw_html_file', 'agency_listing_id'
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
                    cursor.execute('ROLLBACK')
                    return False
                
                # Build and execute update query
                update_query = f"""
                    UPDATE listings 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """
                update_values.append(listing_id)
                
                cursor.execute(update_query, update_values)
                
                # Commit transaction
                cursor.execute('COMMIT')
                
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
                cursor.execute('SELECT * FROM listings WHERE url = ?', (url,))
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
                cursor.execute('SELECT * FROM listings WHERE id = ?', (listing_id,))
                row = cursor.fetchone()
                  
                if row:
                    return self._row_to_listing(row)
                  
                return None
                  
        except sqlite3.Error as e:
            self.logger.error(f"Error fetching listing by ID {listing_id}: {e}")
            return None
    
    def search_listings(self, **kwargs) -> List[Listing]:
        """Search listings with various filters."""
        try:
            query = 'SELECT * FROM listings WHERE 1=1'
            params = []
            
            # Add filters based on kwargs
            if 'city' in kwargs and kwargs['city']:
                query += ' AND city = ?'
                params.append(kwargs['city'])
                
            if 'min_price' in kwargs and kwargs['min_price']:
                query += ' AND price >= ?'
                params.append(kwargs['min_price'])
                
            if 'max_price' in kwargs and kwargs['max_price']:
                query += ' AND price <= ?'
                params.append(kwargs['max_price'])
                
            if 'min_size' in kwargs and kwargs['min_size']:
                query += ' AND square_meters >= ?'
                params.append(kwargs['min_size'])
                
            if 'contract_type' in kwargs and kwargs['contract_type']:
                query += ' AND contract_type = ?'
                params.append(kwargs['contract_type'])
            
            if 'agency_id' in kwargs and kwargs['agency_id']:
                query += ' AND agency_id = ?'
                params.append(kwargs['agency_id'])
            
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
                cursor.execute('SELECT * FROM listings')
                rows = cursor.fetchall()
                
                return [self._row_to_listing(row) for row in rows]
                
        except sqlite3.Error as e:
            self.logger.error(f"Error fetching all listings: {e}")
            return []
    
    def _row_to_listing(self, row: tuple) -> Listing:
        """Convert database row to Listing object."""
        # Map row to listing fields
        listing_data = {
               'id': row[0],
               'title': row[1],
               'url': row[2],
              'description': row[3],
              'contract_type': row[4],
              'price': row[5],
              'city': row[6],
              'neighborhood': row[7],
              'address': row[8],
              'rooms': row[9],
              'bedrooms': row[10],
              'bathrooms': row[11],
              'square_meters': row[12],
              'floor': row[13],
              'year_built': row[14],
              'has_elevator': row[15],
              'heating': row[16],
              'has_air_conditioning': row[17],
              'has_garage': row[18],
              'is_furnished': row[19],
              'energy_class': row[20],
              'energy_consumption': row[21],
              'features': row[22],
              'scrape_date': row[23],
              'publication_date': row[24],
              'raw_html_file': row[25],
              'agency_listing_id': row[26],
              'modify_date': row[27],
              'agency_id': row[28]
          }
        
        # Convert features from string back to list
        if listing_data['features']:
            try:
                # Simple parsing - this would need to be more robust for complex cases
                listing_data['features'] = listing_data['features'].strip('[]').split(', ')
            except:
                listing_data['features'] = []
        
        return Listing.from_dict(listing_data)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                 
                # Get total count
                cursor.execute('SELECT COUNT(*) FROM listings')
                total = cursor.fetchone()[0]
                  
                # Get average price
                cursor.execute('SELECT AVG(price) FROM listings')
                avg_price = cursor.fetchone()[0] or 0
                  
                # Get average size
                cursor.execute('SELECT AVG(square_meters) FROM listings WHERE square_meters IS NOT NULL')
                avg_size = cursor.fetchone()[0] or 0
                  
                # Get last updated
                cursor.execute('SELECT MAX(scrape_date) FROM listings')
                last_updated = cursor.fetchone()[0]
                  
                return {
                    'total_properties': total,
                    'average_price': round(avg_price, 2),
                    'average_size': round(avg_size, 2),
                    'last_updated': last_updated
                }
                  
        except sqlite3.Error as e:
            self.logger.error(f"Error getting stats: {e}")
            return {
                'total_properties': 0,
                'average_price': 0,
                'average_size': 0,
                'last_updated': None
            }

    def get_price_distribution(self) -> Dict[str, Any]:
        """Get price distribution data for histogram."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Define price ranges for sell properties (in euros)
                sell_ranges = [
                    (0, 50000), (50000, 100000), (100000, 150000), (150000, 200000),
                    (200000, 250000), (250000, 300000), (300000, 500000), (500000, 1000000)
                ]
                
                # Define price ranges for rent properties (in euros)
                rent_ranges = [
                    (0, 300), (300, 500), (500, 700), (700, 900), (900, 1200),
                    (1200, 1500), (1500, 2000), (2000, 3000)
                ]
                
                # Get sell price distribution
                sell_distribution = []
                for min_price, max_price in sell_ranges:
                    cursor.execute('''
                        SELECT COUNT(*) FROM listings 
                        WHERE contract_type LIKE "%SELL%" AND price >= ? AND price < ?
                    ''', (min_price, max_price))
                    count = cursor.fetchone()[0]
                    sell_distribution.append(count)
                
                # Get rent price distribution
                rent_distribution = []
                for min_price, max_price in rent_ranges:
                    cursor.execute('''
                        SELECT COUNT(*) FROM listings 
                        WHERE contract_type LIKE "%RENT%" AND price >= ? AND price < ?
                    ''', (min_price, max_price))
                    count = cursor.fetchone()[0]
                    rent_distribution.append(count)
                
                return {
                    'sell': {
                        'ranges': [f"€{min_price/1000:.0f}k-€{max_price/1000:.0f}k" for min_price, max_price in sell_ranges],
                        'counts': sell_distribution
                    },
                    'rent': {
                        'ranges': [f"€{min_price}-€{max_price}" for min_price, max_price in rent_ranges],
                        'counts': rent_distribution
                    }
                }
                
        except sqlite3.Error as e:
            self.logger.error(f"Error getting price distribution: {e}")
            return {
                'sell': {'ranges': [], 'counts': []},
                'rent': {'ranges': [], 'counts': []}
            }

    def clear_all_listings(self) -> int:
        """Remove all listings from the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get count before deletion
                cursor.execute('SELECT COUNT(*) FROM listings')
                count_before = cursor.fetchone()[0]
                
                # Delete all listings
                cursor.execute('DELETE FROM listings')
                
                conn.commit()
                
                self.logger.info(f"Cleared all listings from database. Removed {count_before} listings.")
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
                cursor.execute('SELECT COUNT(*) FROM scrape_history')
                count = cursor.fetchone()[0]
                
                if count > MAX_SCRAPE_HISTORY_ENTRIES:
                    # Calculate how many to delete
                    to_delete = count - MAX_SCRAPE_HISTORY_ENTRIES
                    
                    # Delete oldest entries (keep newest)
                    cursor.execute('''
                        DELETE FROM scrape_history 
                        WHERE id IN (
                            SELECT id FROM scrape_history 
                            ORDER BY timestamp ASC 
                            LIMIT ?
                        )
                    ''', (to_delete,))
                    
                    self.logger.info(f"Cleaned up scrape history: deleted {to_delete} oldest entries")
                    
                conn.commit()
                
        except sqlite3.Error as e:
            self.logger.error(f"Error cleaning up scrape history: {e}")

    def log_scrape_run(self, source: str, listings_count: int, duration_seconds: float) -> None:
        """Log a scrape run to the scrape history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert new scrape record
                cursor.execute('''
                    INSERT INTO scrape_history (timestamp, source, listings_count, duration_seconds)
                    VALUES (?, ?, ?, ?)
                ''', (datetime.now().isoformat(), source, listings_count, duration_seconds))
                
                conn.commit()
                
                # Clean up old entries
                self._cleanup_scrape_history()
                
                self.logger.info(f"Logged scrape run: {source} - {listings_count} listings in {duration_seconds:.1f}s")
                
        except sqlite3.Error as e:
            self.logger.error(f"Error logging scrape run: {e}")

    def get_last_scrape_time(self) -> Optional[datetime]:
        """Get the timestamp of the last scrape run."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT timestamp FROM scrape_history 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''')
                
                row = cursor.fetchone()
                if row:
                    return datetime.fromisoformat(row[0])
                return None
                
        except sqlite3.Error as e:
            self.logger.error(f"Error getting last scrape time: {e}")
            return None

    def get_scrape_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent scrape history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT timestamp, source, listings_count, duration_seconds 
                    FROM scrape_history 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                
                history = []
                for row in rows:
                    history.append({
                        'timestamp': row[0],
                        'source': row[1],
                        'listings_count': row[2],
                        'duration_seconds': row[3]
                    })
                
                return history
                
        except sqlite3.Error as e:
            self.logger.error(f"Error getting scrape history: {e}")
            return []