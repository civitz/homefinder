#!/usr/bin/env python3
"""
Database module for storing property listings
Uses SQLite for local storage
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import DATABASE_PATH, LOG_FILE
from scraper import Casetta

# Set up logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PropertyDatabase:
    """
    Database interface for property listings
    """

    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        """
        Initialize the database with required tables
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create properties table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS properties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titolo TEXT NOT NULL,
                    agenzia TEXT NOT NULL,
                    url TEXT UNIQUE,
                    descrizione TEXT,
                    contratto TEXT,
                    prezzo INTEGER,
                    classe TEXT,
                    locali INTEGER,
                    mq INTEGER,
                    piano TEXT,
                    riscaldamento TEXT,
                    condizionatore BOOLEAN,
                    ascensore BOOLEAN,
                    garage BOOLEAN,
                    arredato BOOLEAN,
                    anno INTEGER,
                    note TEXT,
                    scrape_date TEXT NOT NULL,
                    publication_date TEXT,
                    raw_html_file TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """)

                # Create index for faster searches
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_url ON properties(url)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_contratto ON properties(contratto)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_prezzo ON properties(prezzo)"
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mq ON properties(mq)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_locali ON properties(locali)"
                )

                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")

        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    def _casetta_to_db_dict(self, casetta: Casetta) -> Dict[str, Any]:
        """
        Convert Casetta object to database-friendly dictionary
        """
        data = casetta.to_dict()
        data["created_at"] = datetime.now().isoformat()
        data["updated_at"] = datetime.now().isoformat()
        return data

    def insert_or_update_property(self, casetta: Casetta) -> bool:
        """
        Insert a new property or update existing one based on URL

        Args:
            casetta: Casetta object to insert/update

        Returns:
            True if successful, False otherwise
        """
        try:
            data = self._casetta_to_db_dict(casetta)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if property already exists
                cursor.execute(
                    "SELECT id FROM properties WHERE url = ?", (casetta.url,)
                )
                existing = cursor.fetchone()

                if existing:
                    # Update existing property
                    data["updated_at"] = datetime.now().isoformat()

                    # Build update query dynamically
                    set_clause = ", ".join(
                        [f"{key} = ?" for key in data.keys() if key != "id"]
                    )
                    values = [data[key] for key in data.keys() if key != "id"]
                    values.append(casetta.url)

                    query = f"""
                    UPDATE properties 
                    SET {set_clause}, updated_at = ? 
                    WHERE url = ?
                    """
                    # Remove the extra updated_at from values since it's in the SET clause
                    values = values[:-1] + [data["updated_at"]] + [casetta.url]

                    cursor.execute(query, values)
                    logger.info(f"Updated property: {casetta.titolo}")
                else:
                    # Insert new property
                    columns = ", ".join(data.keys())
                    placeholders = ", ".join(["?"] * len(data))

                    query = f"""
                    INSERT INTO properties ({columns}) 
                    VALUES ({placeholders})
                    """

                    cursor.execute(query, list(data.values()))
                    logger.info(f"Inserted new property: {casetta.titolo}")

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error inserting/updating property {casetta.url}: {str(e)}")
            return False

    def insert_or_update_properties(self, properties: List[Casetta]) -> int:
        """
        Insert or update multiple properties

        Args:
            properties: List of Casetta objects

        Returns:
            Number of successfully processed properties
        """
        success_count = 0

        for property_data in properties:
            if self.insert_or_update_property(property_data):
                success_count += 1

        logger.info(
            f"Processed {success_count}/{len(properties)} properties successfully"
        )
        return success_count

    def get_all_properties(self) -> List[Dict[str, Any]]:
        """
        Get all properties from database

        Returns:
            List of property dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # Return rows as dictionaries
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM properties ORDER BY created_at DESC")
                results = cursor.fetchall()

                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting all properties: {str(e)}")
            return []

    def get_property_by_id(self, property_id: int) -> Optional[Dict[str, Any]]:
        """
        Get property by ID

        Args:
            property_id: ID of the property

        Returns:
            Property dictionary or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM properties WHERE id = ?", (property_id,))
                result = cursor.fetchone()

                return dict(result) if result else None

        except Exception as e:
            logger.error(f"Error getting property {property_id}: {str(e)}")
            return None

    def search_properties(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Search properties with various filters

        Args:
            **kwargs: Filter parameters (e.g., contratto='VENDITA', prezzo_min=100000)

        Returns:
            List of matching property dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Build query dynamically
                query = "SELECT * FROM properties WHERE 1=1"
                params = []

                # Add filters
                if "contratto" in kwargs:
                    query += " AND contratto = ?"
                    params.append(kwargs["contratto"])

                if "prezzo_min" in kwargs:
                    query += " AND prezzo >= ?"
                    params.append(kwargs["prezzo_min"])

                if "prezzo_max" in kwargs:
                    query += " AND prezzo <= ?"
                    params.append(kwargs["prezzo_max"])

                if "mq_min" in kwargs:
                    query += " AND mq >= ?"
                    params.append(kwargs["mq_min"])

                if "locali_min" in kwargs:
                    query += " AND locali >= ?"
                    params.append(kwargs["locali_min"])

                if "classe" in kwargs:
                    query += " AND classe = ?"
                    params.append(kwargs["classe"])

                if "search_text" in kwargs:
                    search_term = f"%{kwargs['search_text']}%"
                    query += " AND (titolo LIKE ? OR descrizione LIKE ?)"
                    params.extend([search_term, search_term])

                # Add ordering
                query += " ORDER BY created_at DESC"

                cursor.execute(query, params)
                results = cursor.fetchall()

                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error searching properties: {str(e)}")
            return []

    def get_property_count(self) -> int:
        """
        Get total number of properties in database

        Returns:
            Number of properties
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM properties")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting property count: {str(e)}")
            return 0

    def get_recent_properties(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recently added/updated properties

        Args:
            limit: Maximum number of properties to return

        Returns:
            List of recent property dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                SELECT * FROM properties 
                ORDER BY updated_at DESC 
                LIMIT ?
                """,
                    (limit,),
                )

                results = cursor.fetchall()
                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting recent properties: {str(e)}")
            return []

    def clear_database(self) -> bool:
        """
        Clear all properties from database (for testing)

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM properties")
                conn.commit()
                logger.info("Database cleared successfully")
                return True
        except Exception as e:
            logger.error(f"Error clearing database: {str(e)}")
            return False


# Global database instance
db = PropertyDatabase()

if __name__ == "__main__":
    # Test the database
    print(f"Database path: {DATABASE_PATH}")
    print(f"Total properties: {db.get_property_count()}")

    # Test search
    results = db.search_properties(contratto="VENDITA")
    print(f"VENDITA properties: {len(results)}")

    # Test recent
    recent = db.get_recent_properties(5)
    print(f"Recent properties: {len(recent)}")
