"""
THE KRAKEN DREAMS - Session Database
SQLite database for managing D&D sessions, campaigns, and characters.

This module provides persistent storage for:
- Campaigns (game settings, DM, players)
- Sessions (transcripts, audio files, dates)
- Characters (names, classes, players)
- Locations (places mentioned in sessions)
"""

import os
import sqlite3
import json
from datetime import datetime


class SessionDatabase:
    """
    SQLite database for D&D session management.
    
    Stores campaigns, sessions, characters, and their relationships.
    """
    
    def __init__(self, db_path):
        """
        Initialize the database.
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Connect to the database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return dicts instead of tuples
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Campaigns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                dm_name TEXT,
                start_date TEXT,
                setting TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Characters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                player_name TEXT,
                character_class TEXT,
                race TEXT,
                level INTEGER DEFAULT 1,
                gender TEXT,
                description TEXT,
                avatar_path TEXT,
                campaign_id INTEGER,
                is_npc BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )
        """)
        
        # Sessions table  
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                session_number INTEGER,
                title TEXT,
                date TEXT,
                duration_minutes INTEGER,
                summary TEXT,
                transcript_path TEXT,
                audio_path TEXT,
                segments_path TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )
        """)
        
        # Locations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                location_type TEXT,
                campaign_id INTEGER,
                parent_location_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
                FOREIGN KEY (parent_location_id) REFERENCES locations(id)
            )
        """)
        
        # Session-Character link table (who was in each session)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_characters (
                session_id INTEGER,
                character_id INTEGER,
                PRIMARY KEY (session_id, character_id),
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                FOREIGN KEY (character_id) REFERENCES characters(id)
            )
        """)
        
        # Session-Location link table (locations visited in session)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_locations (
                session_id INTEGER,
                location_id INTEGER,
                PRIMARY KEY (session_id, location_id),
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                FOREIGN KEY (location_id) REFERENCES locations(id)
            )
        """)
        
        self.conn.commit()
    
    # =========================================================================
    # CAMPAIGN OPERATIONS
    # =========================================================================
    
    def create_campaign(self, name, description=None, dm_name=None, setting=None):
        """Create a new campaign."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO campaigns (name, description, dm_name, setting, start_date)
            VALUES (?, ?, ?, ?, ?)
        """, (name, description, dm_name, setting, datetime.now().isoformat()))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_campaign(self, campaign_id):
        """Get a campaign by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        return dict(cursor.fetchone()) if cursor.fetchone() else None
    
    def get_all_campaigns(self):
        """Get all campaigns."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM campaigns ORDER BY updated_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    def update_campaign(self, campaign_id, **kwargs):
        """Update a campaign."""
        valid_fields = ['name', 'description', 'dm_name', 'setting', 'notes']
        updates = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not updates:
            return
        
        updates['updated_at'] = datetime.now().isoformat()
        
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [campaign_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE campaigns SET {set_clause} WHERE id = ?", values)
        self.conn.commit()
    
    def delete_campaign(self, campaign_id):
        """Delete a campaign and all related data."""
        cursor = self.conn.cursor()
        
        # Delete related records first
        cursor.execute("DELETE FROM session_characters WHERE session_id IN (SELECT id FROM sessions WHERE campaign_id = ?)", (campaign_id,))
        cursor.execute("DELETE FROM session_locations WHERE session_id IN (SELECT id FROM sessions WHERE campaign_id = ?)", (campaign_id,))
        cursor.execute("DELETE FROM sessions WHERE campaign_id = ?", (campaign_id,))
        cursor.execute("DELETE FROM characters WHERE campaign_id = ?", (campaign_id,))
        cursor.execute("DELETE FROM locations WHERE campaign_id = ?", (campaign_id,))
        cursor.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
        
        self.conn.commit()
    
    # =========================================================================
    # SESSION OPERATIONS
    # =========================================================================
    
    def create_session(self, campaign_id, title=None, date=None, transcript_path=None, 
                      audio_path=None, segments_path=None, summary=None):
        """Create a new session."""
        # Get next session number
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(session_number) FROM sessions WHERE campaign_id = ?", (campaign_id,))
        result = cursor.fetchone()
        session_number = (result[0] or 0) + 1
        
        date = date or datetime.now().strftime("%Y-%m-%d")
        title = title or f"Session {session_number}"
        
        cursor.execute("""
            INSERT INTO sessions (campaign_id, session_number, title, date, 
                                 transcript_path, audio_path, segments_path, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (campaign_id, session_number, title, date, transcript_path, 
              audio_path, segments_path, summary))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_session(self, session_id):
        """Get a session by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_campaign_sessions(self, campaign_id):
        """Get all sessions for a campaign."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM sessions WHERE campaign_id = ? ORDER BY session_number DESC",
            (campaign_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def update_session(self, session_id, **kwargs):
        """Update a session."""
        valid_fields = ['title', 'date', 'duration_minutes', 'summary', 
                       'transcript_path', 'audio_path', 'segments_path', 'notes']
        updates = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not updates:
            return
        
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [session_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE sessions SET {set_clause} WHERE id = ?", values)
        self.conn.commit()
    
    # =========================================================================
    # CHARACTER OPERATIONS
    # =========================================================================
    
    def create_character(self, name, campaign_id=None, player_name=None, 
                        character_class=None, race=None, is_npc=False, gender=None):
        """Create a new character."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO characters (name, campaign_id, player_name, character_class, 
                                   race, is_npc, gender)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, campaign_id, player_name, character_class, race, is_npc, gender))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_campaign_characters(self, campaign_id, include_npcs=True):
        """Get all characters for a campaign."""
        cursor = self.conn.cursor()
        if include_npcs:
            cursor.execute(
                "SELECT * FROM characters WHERE campaign_id = ? ORDER BY is_npc, name",
                (campaign_id,)
            )
        else:
            cursor.execute(
                "SELECT * FROM characters WHERE campaign_id = ? AND is_npc = 0 ORDER BY name",
                (campaign_id,)
            )
        return [dict(row) for row in cursor.fetchall()]
    
    def link_character_to_session(self, session_id, character_id):
        """Link a character to a session (they attended)."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO session_characters (session_id, character_id) VALUES (?, ?)",
                (session_id, character_id)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass  # Already linked
    
    def get_session_characters(self, session_id):
        """Get all characters in a session."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.* FROM characters c
            JOIN session_characters sc ON c.id = sc.character_id
            WHERE sc.session_id = ?
            ORDER BY c.is_npc, c.name
        """, (session_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    # =========================================================================
    # LOCATION OPERATIONS  
    # =========================================================================
    
    def create_location(self, name, campaign_id=None, location_type=None, 
                       description=None, parent_location_id=None):
        """Create a new location."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO locations (name, campaign_id, location_type, 
                                  description, parent_location_id)
            VALUES (?, ?, ?, ?, ?)
        """, (name, campaign_id, location_type, description, parent_location_id))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_campaign_locations(self, campaign_id):
        """Get all locations for a campaign."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM locations WHERE campaign_id = ? ORDER BY name",
            (campaign_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def link_location_to_session(self, session_id, location_id):
        """Link a location to a session (visited during session)."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO session_locations (session_id, location_id) VALUES (?, ?)",
                (session_id, location_id)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass  # Already linked
    
    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================
    
    def search_sessions(self, query, campaign_id=None):
        """Search sessions by title or summary."""
        cursor = self.conn.cursor()
        search_term = f"%{query}%"
        
        if campaign_id:
            cursor.execute("""
                SELECT * FROM sessions 
                WHERE campaign_id = ? AND (title LIKE ? OR summary LIKE ? OR notes LIKE ?)
                ORDER BY date DESC
            """, (campaign_id, search_term, search_term, search_term))
        else:
            cursor.execute("""
                SELECT * FROM sessions 
                WHERE title LIKE ? OR summary LIKE ? OR notes LIKE ?
                ORDER BY date DESC
            """, (search_term, search_term, search_term))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self, campaign_id=None):
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        if campaign_id:
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE campaign_id = ?", (campaign_id,))
            session_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM characters WHERE campaign_id = ? AND is_npc = 0", (campaign_id,))
            player_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM characters WHERE campaign_id = ? AND is_npc = 1", (campaign_id,))
            npc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM locations WHERE campaign_id = ?", (campaign_id,))
            location_count = cursor.fetchone()[0]
        else:
            cursor.execute("SELECT COUNT(*) FROM campaigns")
            campaign_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM sessions")
            session_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM characters WHERE is_npc = 0")
            player_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM characters WHERE is_npc = 1")
            npc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM locations")
            location_count = cursor.fetchone()[0]
        
        return {
            'campaigns': campaign_count if not campaign_id else 1,
            'sessions': session_count,
            'players': player_count,
            'npcs': npc_count,
            'locations': location_count
        }
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()


def get_database(db_path=None):
    """
    Get a database instance.
    
    Args:
        db_path (str): Optional path. Uses default in APP_DIR if not specified.
        
    Returns:
        SessionDatabase: Database instance
    """
    from .config import APP_DIR
    
    if not db_path:
        db_path = os.path.join(APP_DIR, "kraken_sessions.db")
    
    return SessionDatabase(db_path)
