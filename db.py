"""
Moduł bazy danych SQLite dla Covered Call Dashboard
Punkt 3: Podstawowe połączenie z bazą danych
"""

import sqlite3
import os
from datetime import datetime
import streamlit as st

# Ścieżka do bazy danych
DB_PATH = "portfolio.db"

def get_connection():
    """
    Utworzenie połączenia z bazą danych SQLite
    Returns: sqlite3.Connection
    """
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Umożliwia dostęp do kolumn po nazwie
        return conn
    except Exception as e:
        st.error(f"Błąd połączenia z bazą danych: {e}")
        return None

def init_database():
    """
    Inicjalizacja bazy danych - sprawdzenie czy istnieje
    """
    conn = get_connection()
    if conn:
        try:
            # Test połączenia - utworzenie prostej tabeli testowej
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_info (
                    id INTEGER PRIMARY KEY,
                    version TEXT,
                    created_at TIMESTAMP,
                    last_updated TIMESTAMP
                )
            """)
            
            # Sprawdź czy istnieje rekord z wersją
            cursor.execute("SELECT COUNT(*) FROM app_info")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Pierwszy start - dodaj rekord wersji
                cursor.execute("""
                    INSERT INTO app_info (version, created_at, last_updated)
                    VALUES (?, ?, ?)
                """, ("0.1", datetime.now(), datetime.now()))
                conn.commit()
                
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Błąd inicjalizacji bazy danych: {e}")
            if conn:
                conn.close()
            return False
    
    return False

def get_app_info():
    """
    Pobiera informacje o aplikacji z bazy danych
    Returns: dict lub None
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM app_info ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'version': row['version'],
                    'created_at': row['created_at'],
                    'last_updated': row['last_updated']
                }
        except Exception as e:
            st.error(f"Błąd pobierania informacji z bazy: {e}")
            if conn:
                conn.close()
    
    return None

def test_database_connection():
    """
    Test połączenia z bazą danych dla debugowania
    Returns: dict z informacjami o statusie
    """
    result = {
        'db_exists': os.path.exists(DB_PATH),
        'db_size': 0,
        'connection_ok': False,
        'tables_count': 0,
        'app_info': None
    }
    
    if result['db_exists']:
        result['db_size'] = os.path.getsize(DB_PATH)
    
    conn = get_connection()
    if conn:
        try:
            result['connection_ok'] = True
            
            # Policz tabele
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            result['tables_count'] = cursor.fetchone()[0]
            
            # Pobierz info o aplikacji
            result['app_info'] = get_app_info()
            
            conn.close()
            
        except Exception as e:
            st.error(f"Błąd testu bazy danych: {e}")
            if conn:
                conn.close()
    
    return result