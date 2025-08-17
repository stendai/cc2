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

"""
Rozszerzenie modułu db.py o operacje CRUD dla tabeli fx_rates
Punkt 6: Implementacja fx_rates (struktura + podstawowe operacje CRUD)

DODAJ te funkcje do istniejącego pliku db.py
"""

# ================================
# OPERACJE CRUD DLA FX_RATES
# ================================

def insert_fx_rate(date, code='USD', rate=None, source='NBP'):
    """
    Dodanie kursu waluty do bazy
    
    Args:
        date: str lub datetime - data kursu (YYYY-MM-DD)
        code: str - kod waluty (domyślnie USD)
        rate: float - kurs waluty
        source: str - źródło kursu (domyślnie NBP)
    
    Returns:
        bool: True jeśli sukces
    """
    if rate is None:
        st.error("Kurs waluty jest wymagany")
        return False
        
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Konwersja daty do stringa jeśli potrzeba
            if hasattr(date, 'strftime'):
                date = date.strftime('%Y-%m-%d')
            
            cursor.execute("""
                INSERT OR REPLACE INTO fx_rates (date, code, rate, source)
                VALUES (?, ?, ?, ?)
            """, (date, code, rate, source))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Błąd dodawania kursu waluty: {e}")
            if conn:
                conn.close()
            return False
    
    return False

def get_fx_rate(date, code='USD'):
    """
    Pobranie kursu waluty na określoną datę
    
    Args:
        date: str lub datetime - data kursu
        code: str - kod waluty
    
    Returns:
        dict lub None: {'date': str, 'code': str, 'rate': float, 'source': str}
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Konwersja daty do stringa jeśli potrzeba  
            if hasattr(date, 'strftime'):
                date = date.strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT date, code, rate, source, created_at
                FROM fx_rates 
                WHERE date = ? AND code = ?
            """, (date, code))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'date': row[0],
                    'code': row[1], 
                    'rate': float(row[2]),
                    'source': row[3],
                    'created_at': row[4]
                }
                
        except Exception as e:
            st.error(f"Błąd pobierania kursu waluty: {e}")
            if conn:
                conn.close()
    
    return None

def get_latest_fx_rate(code='USD', before_date=None):
    """
    Pobranie najnowszego kursu waluty (opcjonalnie przed określoną datą)
    
    Args:
        code: str - kod waluty
        before_date: str lub datetime - znajdź najnowszy kurs przed tą datą
    
    Returns:
        dict lub None: {'date': str, 'code': str, 'rate': float, 'source': str}
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            if before_date:
                # Konwersja daty do stringa jeśli potrzeba
                if hasattr(before_date, 'strftime'):
                    before_date = before_date.strftime('%Y-%m-%d')
                    
                cursor.execute("""
                    SELECT date, code, rate, source, created_at
                    FROM fx_rates 
                    WHERE code = ? AND date <= ?
                    ORDER BY date DESC
                    LIMIT 1
                """, (code, before_date))
            else:
                cursor.execute("""
                    SELECT date, code, rate, source, created_at
                    FROM fx_rates 
                    WHERE code = ?
                    ORDER BY date DESC
                    LIMIT 1
                """, (code,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'date': row[0],
                    'code': row[1],
                    'rate': float(row[2]),
                    'source': row[3],
                    'created_at': row[4]
                }
                
        except Exception as e:
            st.error(f"Błąd pobierania najnowszego kursu: {e}")
            if conn:
                conn.close()
    
    return None

def get_fx_rates_range(start_date, end_date, code='USD'):
    """
    Pobranie kursów waluty z określonego zakresu dat
    
    Args:
        start_date: str lub datetime - data początkowa
        end_date: str lub datetime - data końcowa  
        code: str - kod waluty
    
    Returns:
        list: Lista słowników z kursami
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Konwersja dat do stringów jeśli potrzeba
            if hasattr(start_date, 'strftime'):
                start_date = start_date.strftime('%Y-%m-%d')
            if hasattr(end_date, 'strftime'):
                end_date = end_date.strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT date, code, rate, source, created_at
                FROM fx_rates 
                WHERE code = ? AND date BETWEEN ? AND ?
                ORDER BY date DESC
            """, (code, start_date, end_date))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'date': row[0],
                'code': row[1],
                'rate': float(row[2]), 
                'source': row[3],
                'created_at': row[4]
            } for row in rows]
            
        except Exception as e:
            st.error(f"Błąd pobierania kursów z zakresu: {e}")
            if conn:
                conn.close()
    
    return []

def delete_fx_rate(date, code='USD'):
    """
    Usunięcie kursu waluty z określonej daty
    
    Args:
        date: str lub datetime - data kursu
        code: str - kod waluty
    
    Returns:
        bool: True jeśli sukces
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Konwersja daty do stringa jeśli potrzeba
            if hasattr(date, 'strftime'):
                date = date.strftime('%Y-%m-%d')
            
            cursor.execute("""
                DELETE FROM fx_rates 
                WHERE date = ? AND code = ?
            """, (date, code))
            
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            return rows_affected > 0
            
        except Exception as e:
            st.error(f"Błąd usuwania kursu waluty: {e}")
            if conn:
                conn.close()
    
    return False

def get_fx_rates_stats():
    """
    Pobranie statystyk tabeli fx_rates
    
    Returns:
        dict: Statystyki tabeli
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Liczba rekordów
            cursor.execute("SELECT COUNT(*) FROM fx_rates")
            total_count = cursor.fetchone()[0]
            
            # Najstarszy i najnowszy kurs
            cursor.execute("""
                SELECT MIN(date) as oldest, MAX(date) as newest
                FROM fx_rates
            """)
            date_range = cursor.fetchone()
            
            # Liczba walut
            cursor.execute("SELECT COUNT(DISTINCT code) FROM fx_rates")
            currencies_count = cursor.fetchone()[0]
            
            # Ostatni kurs USD
            latest_usd = get_latest_fx_rate('USD')
            
            conn.close()
            
            return {
                'total_records': total_count,
                'oldest_date': date_range[0],
                'newest_date': date_range[1], 
                'currencies_count': currencies_count,
                'latest_usd_rate': latest_usd['rate'] if latest_usd else None,
                'latest_usd_date': latest_usd['date'] if latest_usd else None
            }
            
        except Exception as e:
            st.error(f"Błąd pobierania statystyk fx_rates: {e}")
            if conn:
                conn.close()
    
    return {
        'total_records': 0,
        'oldest_date': None,
        'newest_date': None,
        'currencies_count': 0, 
        'latest_usd_rate': None,
        'latest_usd_date': None
    }

# ================================
# ROZSZERZONE TESTY BAZY DANYCH 
# ================================

def test_fx_rates_operations():
    """
    Test operacji CRUD na tabeli fx_rates
    
    Returns:
        dict: Wyniki testów
    """
    results = {
        'fx_table_exists': False,
        'insert_test': False, 
        'get_test': False,
        'latest_test': False,
        'delete_test': False,
        'stats_test': False
    }
    
    try:
        # Import structure.py dla tworzenia tabel
        import structure
        
        # Test tworzenia tabeli
        conn = get_connection()
        if conn:
            results['fx_table_exists'] = structure.create_fx_rates_table(conn)
            conn.close()
        
        # Test dodawania kursu
        if results['fx_table_exists']:
            results['insert_test'] = insert_fx_rate('2025-01-15', 'USD', 4.2345, 'NBP')
        
        # Test pobierania kursu
        if results['insert_test']:
            rate = get_fx_rate('2025-01-15', 'USD')
            results['get_test'] = rate is not None and rate['rate'] == 4.2345
        
        # Test najnowszego kursu
        if results['get_test']:
            latest = get_latest_fx_rate('USD')
            results['latest_test'] = latest is not None and latest['rate'] == 4.2345
            
        # Test statystyk
        if results['latest_test']:
            stats = get_fx_rates_stats()
            results['stats_test'] = stats['total_records'] > 0
        
        # Test usuwania
        if results['stats_test']:
            results['delete_test'] = delete_fx_rate('2025-01-15', 'USD')
            
    except Exception as e:
        st.error(f"Błąd testów fx_rates: {e}")
    
    return results

# DODAJ te funkcje na koniec pliku db.py

# ================================
# OPERACJE CRUD DLA CASHFLOWS
# ================================

def insert_cashflow(cashflow_type, amount_usd, date, fx_rate, description=None, ref_table=None, ref_id=None):
    """
    Dodanie przepływu pieniężnego do bazy
    
    Args:
        cashflow_type: str - typ operacji (deposit, withdrawal, option_premium, etc.)
        amount_usd: float - kwota w USD (znak zgodny z przepływem)
        date: str lub datetime - data operacji
        fx_rate: float - kurs PLN/USD
        description: str - opis operacji
        ref_table: str - tabela źródłowa
        ref_id: int - ID rekordu źródłowego
    
    Returns:
        int lub None: ID dodanego rekordu lub None jeśli błąd
    """
    if amount_usd == 0:
        st.error("Kwota nie może być zerowa")
        return None
        
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Konwersja daty do stringa jeśli potrzeba
            if hasattr(date, 'strftime'):
                date = date.strftime('%Y-%m-%d')
            
            # Wylicz kwotę PLN
            amount_pln = round(amount_usd * fx_rate, 2)
            
            cursor.execute("""
                INSERT INTO cashflows (type, amount_usd, date, fx_rate, amount_pln, 
                                     description, ref_table, ref_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cashflow_type, amount_usd, date, fx_rate, amount_pln, 
                  description, ref_table, ref_id))
            
            cashflow_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return cashflow_id
            
        except Exception as e:
            st.error(f"Błąd dodawania cashflow: {e}")
            if conn:
                conn.close()
            return None
    
    return None

def get_cashflow(cashflow_id):
    """
    Pobranie pojedynczego cashflow po ID
    
    Args:
        cashflow_id: int - ID cashflow
    
    Returns:
        dict lub None: Dane cashflow
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, type, amount_usd, date, fx_rate, amount_pln,
                       description, ref_table, ref_id, created_at, updated_at
                FROM cashflows 
                WHERE id = ?
            """, (cashflow_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'type': row[1],
                    'amount_usd': float(row[2]),
                    'date': row[3],
                    'fx_rate': float(row[4]),
                    'amount_pln': float(row[5]),
                    'description': row[6],
                    'ref_table': row[7],
                    'ref_id': row[8],
                    'created_at': row[9],
                    'updated_at': row[10]
                }
                
        except Exception as e:
            st.error(f"Błąd pobierania cashflow: {e}")
            if conn:
                conn.close()
    
    return None

def get_cashflows_range(start_date=None, end_date=None, cashflow_type=None, limit=100):
    """
    Pobranie cashflows z określonego zakresu
    
    Args:
        start_date: str lub datetime - data początkowa
        end_date: str lub datetime - data końcowa
        cashflow_type: str - filtr typu operacji
        limit: int - maksymalna liczba rekordów
    
    Returns:
        list: Lista cashflows
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Budowanie zapytania z filtrami
            query = """
                SELECT id, type, amount_usd, date, fx_rate, amount_pln,
                       description, ref_table, ref_id, created_at, updated_at
                FROM cashflows 
                WHERE 1=1
            """
            params = []
            
            if start_date:
                if hasattr(start_date, 'strftime'):
                    start_date = start_date.strftime('%Y-%m-%d')
                query += " AND date >= ?"
                params.append(start_date)
            
            if end_date:
                if hasattr(end_date, 'strftime'):
                    end_date = end_date.strftime('%Y-%m-%d')
                query += " AND date <= ?"
                params.append(end_date)
                
            if cashflow_type:
                query += " AND type = ?"
                params.append(cashflow_type)
            
            query += " ORDER BY date DESC, id DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'id': row[0],
                'type': row[1],
                'amount_usd': float(row[2]),
                'date': row[3],
                'fx_rate': float(row[4]),
                'amount_pln': float(row[5]),
                'description': row[6],
                'ref_table': row[7],
                'ref_id': row[8],
                'created_at': row[9],
                'updated_at': row[10]
            } for row in rows]
            
        except Exception as e:
            st.error(f"Błąd pobierania cashflows: {e}")
            if conn:
                conn.close()
    
    return []

def update_cashflow(cashflow_id, **kwargs):
    """
    Aktualizacja cashflow
    
    Args:
        cashflow_id: int - ID cashflow
        **kwargs: pola do aktualizacji
    
    Returns:
        bool: True jeśli sukces
    """
    if not kwargs:
        return False
        
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Budowanie zapytania UPDATE
            fields = []
            values = []
            
            for field, value in kwargs.items():
                if field in ['type', 'amount_usd', 'date', 'fx_rate', 'description', 'ref_table', 'ref_id']:
                    fields.append(f"{field} = ?")
                    values.append(value)
            
            if not fields:
                return False
            
            # Dodaj updated_at
            fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(cashflow_id)
            
            query = f"UPDATE cashflows SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(query, values)
            
            # Jeśli zmieniono amount_usd lub fx_rate, przelicz amount_pln
            if 'amount_usd' in kwargs or 'fx_rate' in kwargs:
                cashflow = get_cashflow(cashflow_id)
                if cashflow:
                    new_amount_pln = round(cashflow['amount_usd'] * cashflow['fx_rate'], 2)
                    cursor.execute("UPDATE cashflows SET amount_pln = ? WHERE id = ?", 
                                 (new_amount_pln, cashflow_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Błąd aktualizacji cashflow: {e}")
            if conn:
                conn.close()
    
    return False

def delete_cashflow(cashflow_id):
    """
    Usunięcie cashflow
    
    Args:
        cashflow_id: int - ID cashflow
    
    Returns:
        bool: True jeśli sukces
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cashflows WHERE id = ?", (cashflow_id,))
            
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            return rows_affected > 0
            
        except Exception as e:
            st.error(f"Błąd usuwania cashflow: {e}")
            if conn:
                conn.close()
    
    return False

def get_cashflows_stats():
    """
    Statystyki tabeli cashflows
    
    Returns:
        dict: Statystyki
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Podstawowe statystyki
            cursor.execute("SELECT COUNT(*) FROM cashflows")
            total_count = cursor.fetchone()[0]
            
            # Sumy per typ
            cursor.execute("""
                SELECT type, COUNT(*), SUM(amount_usd), SUM(amount_pln)
                FROM cashflows 
                GROUP BY type
                ORDER BY type
            """)
            by_type = cursor.fetchall()
            
            # Zakres dat
            cursor.execute("SELECT MIN(date), MAX(date) FROM cashflows")
            date_range = cursor.fetchone()
            
            # Saldo
            cursor.execute("SELECT SUM(amount_usd), SUM(amount_pln) FROM cashflows")
            totals = cursor.fetchone()
            
            conn.close()
            
            return {
                'total_records': total_count,
                'oldest_date': date_range[0],
                'newest_date': date_range[1],
                'total_usd': float(totals[0]) if totals[0] else 0.0,
                'total_pln': float(totals[1]) if totals[1] else 0.0,
                'by_type': [{
                    'type': row[0],
                    'count': row[1],
                    'sum_usd': float(row[2]) if row[2] else 0.0,
                    'sum_pln': float(row[3]) if row[3] else 0.0
                } for row in by_type]
            }
            
        except Exception as e:
            st.error(f"Błąd statystyk cashflows: {e}")
            if conn:
                conn.close()
    
    return {
        'total_records': 0,
        'oldest_date': None,
        'newest_date': None,
        'total_usd': 0.0,
        'total_pln': 0.0,
        'by_type': []
    }

def test_cashflows_operations():
    """
    Test operacji CRUD na tabeli cashflows
    
    Returns:
        dict: Wyniki testów
    """
    results = {
        'table_exists': False,
        'insert_test': False,
        'get_test': False,
        'update_test': False,
        'delete_test': False,
        'stats_test': False
    }
    
    try:
        import structure
        
        # Test tworzenia tabeli
        conn = get_connection()
        if conn:
            results['table_exists'] = structure.create_cashflows_table(conn)
            conn.close()
        
        # Test dodawania
        if results['table_exists']:
            cashflow_id = insert_cashflow('deposit', 1000.0, '2025-01-15', 4.2345, 'Test deposit')
            results['insert_test'] = cashflow_id is not None
        
        # Test pobierania
        if results['insert_test']:
            cashflow = get_cashflow(cashflow_id)
            results['get_test'] = cashflow is not None and cashflow['amount_usd'] == 1000.0
        
        # Test aktualizacji
        if results['get_test']:
            results['update_test'] = update_cashflow(cashflow_id, description='Updated test deposit')
        
        # Test statystyk
        if results['update_test']:
            stats = get_cashflows_stats()
            results['stats_test'] = stats['total_records'] > 0
        
        # Test usuwania
        if results['stats_test']:
            results['delete_test'] = delete_cashflow(cashflow_id)
            
    except Exception as e:
        st.error(f"Błąd testów cashflows: {e}")
    
    return results

# DODAJ te funkcje na koniec pliku db.py

# ================================
# OPERACJE CRUD DLA LOTS
# ================================

def insert_lot(ticker, quantity, buy_price_usd, buy_date, fx_rate, broker_fee_usd=0.0, reg_fee_usd=0.0):
    """
    Dodanie LOT-a akcji do bazy
    
    Args:
        ticker: str - symbol akcji
        quantity: int - liczba akcji
        buy_price_usd: float - cena zakupu za akcję
        buy_date: str lub datetime - data zakupu
        fx_rate: float - kurs PLN/USD
        broker_fee_usd: float - prowizja brokera
        reg_fee_usd: float - opłaty regulacyjne
    
    Returns:
        int lub None: ID dodanego LOT-a lub None jeśli błąd
    """
    if quantity <= 0:
        st.error("Ilość akcji musi być większa od 0")
        return None
        
    if buy_price_usd <= 0:
        st.error("Cena zakupu musi być większa od 0")
        return None
        
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Konwersja daty do stringa jeśli potrzeba
            if hasattr(buy_date, 'strftime'):
                buy_date = buy_date.strftime('%Y-%m-%d')
            
            # Wylicz koszt całkowity w PLN
            cost_usd = (quantity * buy_price_usd) + broker_fee_usd + reg_fee_usd
            cost_pln = round(cost_usd * fx_rate, 2)
            
            cursor.execute("""
                INSERT INTO lots (ticker, quantity_total, quantity_open, buy_price_usd,
                                broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticker.upper(), quantity, quantity, buy_price_usd, 
                  broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln))
            
            lot_id = cursor.lastrowid
            
            # Automatyczne utworzenie cashflow dla zakupu
            cashflow_id = insert_cashflow(
                cashflow_type='stock_buy',
                amount_usd=-cost_usd,  # Ujemne bo to wydatek
                date=buy_date,
                fx_rate=fx_rate,
                description=f"Zakup {quantity} {ticker.upper()} @ ${buy_price_usd}",
                ref_table='lots',
                ref_id=lot_id
            )
            
            conn.commit()
            conn.close()
            return lot_id
            
        except Exception as e:
            st.error(f"Błąd dodawania LOT-a: {e}")
            if conn:
                conn.close()
            return None
    
    return None

def get_lot(lot_id):
    """
    Pobranie pojedynczego LOT-a po ID
    
    Args:
        lot_id: int - ID LOT-a
    
    Returns:
        dict lub None: Dane LOT-a
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, ticker, quantity_total, quantity_open, buy_price_usd,
                       broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln,
                       created_at, updated_at
                FROM lots 
                WHERE id = ?
            """, (lot_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'ticker': row[1],
                    'quantity_total': row[2],
                    'quantity_open': row[3],
                    'buy_price_usd': float(row[4]),
                    'broker_fee_usd': float(row[5]),
                    'reg_fee_usd': float(row[6]),
                    'buy_date': row[7],
                    'fx_rate': float(row[8]),
                    'cost_pln': float(row[9]),
                    'created_at': row[10],
                    'updated_at': row[11]
                }
                
        except Exception as e:
            st.error(f"Błąd pobierania LOT-a: {e}")
            if conn:
                conn.close()
    
    return None

def get_lots_by_ticker(ticker, only_open=False):
    """
    Pobranie LOT-ów dla określonego tickera (w kolejności FIFO)
    
    Args:
        ticker: str - symbol akcji
        only_open: bool - tylko LOT-y z quantity_open > 0
    
    Returns:
        list: Lista LOT-ów w kolejności FIFO (najstarsze pierwsze)
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            query = """
                SELECT id, ticker, quantity_total, quantity_open, buy_price_usd,
                       broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln,
                       created_at, updated_at
                FROM lots 
                WHERE ticker = ?
            """
            
            if only_open:
                query += " AND quantity_open > 0"
            
            # FIFO: sortuj po dacie zakupu, potem po ID
            query += " ORDER BY buy_date, id"
            
            cursor.execute(query, (ticker.upper(),))
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'id': row[0],
                'ticker': row[1],
                'quantity_total': row[2],
                'quantity_open': row[3],
                'buy_price_usd': float(row[4]),
                'broker_fee_usd': float(row[5]),
                'reg_fee_usd': float(row[6]),
                'buy_date': row[7],
                'fx_rate': float(row[8]),
                'cost_pln': float(row[9]),
                'created_at': row[10],
                'updated_at': row[11]
            } for row in rows]
            
        except Exception as e:
            st.error(f"Błąd pobierania LOT-ów dla {ticker}: {e}")
            if conn:
                conn.close()
    
    return []

def get_available_quantity(ticker):
    """
    Sprawdzenie dostępnej ilości akcji dla tickera (suma quantity_open)
    
    Args:
        ticker: str - symbol akcji
    
    Returns:
        int: Dostępna ilość akcji
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(quantity_open), 0)
                FROM lots 
                WHERE ticker = ?
            """, (ticker.upper(),))
            
            result = cursor.fetchone()[0]
            conn.close()
            return int(result)
            
        except Exception as e:
            st.error(f"Błąd sprawdzania dostępności {ticker}: {e}")
            if conn:
                conn.close()
    
    return 0

def update_lot_quantity(lot_id, new_quantity_open):
    """
    Aktualizacja quantity_open LOT-a (np. po sprzedaży)
    
    Args:
        lot_id: int - ID LOT-a
        new_quantity_open: int - nowa ilość otwarta
    
    Returns:
        bool: True jeśli sukces
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Sprawdź obecne dane LOT-a
            lot = get_lot(lot_id)
            if not lot:
                return False
            
            if new_quantity_open < 0 or new_quantity_open > lot['quantity_total']:
                st.error(f"Nieprawidłowa ilość: {new_quantity_open} (dozwolone: 0-{lot['quantity_total']})")
                return False
            
            cursor.execute("""
                UPDATE lots 
                SET quantity_open = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_quantity_open, lot_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Błąd aktualizacji LOT-a: {e}")
            if conn:
                conn.close()
    
    return False

def get_lots_stats():
    """
    Statystyki tabeli lots
    
    Returns:
        dict: Statystyki
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Podstawowe statystyki
            cursor.execute("SELECT COUNT(*) FROM lots")
            total_lots = cursor.fetchone()[0]
            
            # Statystyki per ticker
            cursor.execute("""
                SELECT ticker, 
                       COUNT(*) as lots_count,
                       SUM(quantity_total) as total_shares,
                       SUM(quantity_open) as open_shares,
                       SUM(cost_pln) as total_cost_pln
                FROM lots 
                GROUP BY ticker
                ORDER BY ticker
            """)
            by_ticker = cursor.fetchall()
            
            # Sumy całkowite
            cursor.execute("""
                SELECT SUM(quantity_total), SUM(quantity_open), SUM(cost_pln)
                FROM lots
            """)
            totals = cursor.fetchone()
            
            conn.close()
            
            return {
                'total_lots': total_lots,
                'total_shares': int(totals[0]) if totals[0] else 0,
                'open_shares': int(totals[1]) if totals[1] else 0,
                'total_cost_pln': float(totals[2]) if totals[2] else 0.0,
                'by_ticker': [{
                    'ticker': row[0],
                    'lots_count': row[1],
                    'total_shares': row[2],
                    'open_shares': row[3],
                    'total_cost_pln': float(row[4])
                } for row in by_ticker]
            }
            
        except Exception as e:
            st.error(f"Błąd statystyk lots: {e}")
            if conn:
                conn.close()
    
    return {
        'total_lots': 0,
        'total_shares': 0,
        'open_shares': 0,
        'total_cost_pln': 0.0,
        'by_ticker': []
    }

def test_lots_operations():
    """
    Test operacji CRUD na tabeli lots
    
    Returns:
        dict: Wyniki testów
    """
    results = {
        'table_exists': False,
        'insert_test': False,
        'get_test': False,
        'quantity_test': False,
        'fifo_test': False,
        'update_test': False,
        'stats_test': False
    }
    
    try:
        import structure
        
        # Test tworzenia tabeli
        conn = get_connection()
        if conn:
            results['table_exists'] = structure.create_lots_table(conn)
            # WYCZYŚĆ dane testowe
            cursor = conn.cursor()
            cursor.execute("DELETE FROM lots WHERE ticker = 'AAPL'")
            conn.commit()
            conn.close()
        
        # Test dodawania LOT-a (bez cashflow - uproszczony)
        if results['table_exists']:
            conn = get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO lots (ticker, quantity_total, quantity_open, buy_price_usd,
                                    broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ('AAPL', 100, 100, 150.50, 1.0, 0.5, '2025-01-15', 4.2345, 640.0))
                lot_id = cursor.lastrowid
                conn.commit()
                conn.close()
                results['insert_test'] = lot_id is not None
        
        # Test pobierania LOT-a
        if results['insert_test']:
            lot = get_lot(lot_id)
            results['get_test'] = lot is not None and lot['ticker'] == 'AAPL'
        
        # Test sprawdzania dostępności
        if results['get_test']:
            available = get_available_quantity('AAPL')
            st.write(f"DEBUG: available quantity = {available}, expected = 100")
            results['quantity_test'] = available == 100
        
        # Test FIFO - dodaj drugi LOT
        if results['quantity_test']:
            conn = get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO lots (ticker, quantity_total, quantity_open, buy_price_usd,
                                    broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ('AAPL', 50, 50, 155.00, 1.0, 0.5, '2025-01-16', 4.2500, 330.0))
                lot_id_2 = cursor.lastrowid
                conn.commit()
                conn.close()
                
                lots = get_lots_by_ticker('AAPL', only_open=True)
                st.write(f"DEBUG: lots count = {len(lots)}")
                if len(lots) >= 2:
                    st.write(f"DEBUG: lot1 date = {lots[0]['buy_date']}, lot2 date = {lots[1]['buy_date']}")
                results['fifo_test'] = (len(lots) == 2 and 
                                      lots[0]['buy_date'] <= lots[1]['buy_date'])
        
        # Test aktualizacji quantity_open
        if results['fifo_test']:
            results['update_test'] = update_lot_quantity(lot_id, 75)  # Sprzedano 25 akcji
        
        # Test statystyk
        if results['update_test']:
            stats = get_lots_stats()
            results['stats_test'] = stats['total_lots'] >= 2
            
    except Exception as e:
        st.error(f"Błąd testów lots: {e}")
    
    return results
    
# DODAJ te funkcje na koniec pliku db.py

# ================================
# OPERACJE CRUD DLA STOCK_TRADES (FIFO)
# ================================

def sell_stock_fifo(ticker, quantity, sell_price_usd, sell_date, fx_rate, broker_fee_usd=0.0, reg_fee_usd=0.0):
    """
    Sprzedaż akcji z automatycznym rozbiciem FIFO po LOT-ach
    
    Args:
        ticker: str - symbol akcji
        quantity: int - ilość do sprzedaży
        sell_price_usd: float - cena sprzedaży za akcję
        sell_date: str lub datetime - data sprzedaży
        fx_rate: float - kurs PLN/USD
        broker_fee_usd: float - prowizja brokera
        reg_fee_usd: float - opłaty regulacyjne
    
    Returns:
        int lub None: ID trade'u lub None jeśli błąd
    """
    if quantity <= 0:
        st.error("Ilość do sprzedaży musi być większa od 0")
        return None
        
    if sell_price_usd <= 0:
        st.error("Cena sprzedaży musi być większa od 0")
        return None
    
    # Sprawdź dostępność akcji
    available = get_available_quantity(ticker)
    if available < quantity:
        st.error(f"Niewystarczająca ilość {ticker}: dostępne {available}, potrzebne {quantity}")
        return None
    
    # Pobierz LOT-y FIFO
    lots = get_lots_by_ticker(ticker, only_open=True)
    if not lots:
        st.error(f"Brak otwartych LOT-ów dla {ticker}")
        return None
    
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Konwersja daty do stringa jeśli potrzeba
            if hasattr(sell_date, 'strftime'):
                sell_date = sell_date.strftime('%Y-%m-%d')
            
            # Wylicz proceeds
            gross_proceeds_usd = quantity * sell_price_usd
            net_proceeds_usd = gross_proceeds_usd - broker_fee_usd - reg_fee_usd
            proceeds_pln = round(net_proceeds_usd * fx_rate, 2)
            
            # Przygotuj rozbicie FIFO
            remaining_qty = quantity
            fifo_splits = []
            total_cost_pln = 0.0
            
            for lot in lots:
                if remaining_qty <= 0:
                    break
                
                # Ile akcji z tego LOT-a
                qty_from_lot = min(remaining_qty, lot['quantity_open'])
                
                # Proporcjonalny koszt z tego LOT-a
                cost_per_share_pln = lot['cost_pln'] / lot['quantity_total']
                cost_part_pln = round(qty_from_lot * cost_per_share_pln, 2)
                
                # Proporcjonalna prowizja
                commission_ratio = qty_from_lot / quantity
                commission_part_usd = round((broker_fee_usd + reg_fee_usd) * commission_ratio, 2)
                commission_part_pln = round(commission_part_usd * fx_rate, 2)
                
                fifo_splits.append({
                    'lot_id': lot['id'],
                    'qty_from_lot': qty_from_lot,
                    'cost_part_pln': cost_part_pln,
                    'commission_part_usd': commission_part_usd,
                    'commission_part_pln': commission_part_pln
                })
                
                total_cost_pln += cost_part_pln
                remaining_qty -= qty_from_lot
            
            if remaining_qty > 0:
                conn.close()
                st.error(f"Nie udało się pokryć całej sprzedaży (brakuje {remaining_qty})")
                return None
            
            # Wylicz P/L
            pl_pln = round(proceeds_pln - total_cost_pln, 2)
            
            # Zapisz główny trade
            cursor.execute("""
                INSERT INTO stock_trades (ticker, quantity, sell_price_usd, sell_date, fx_rate,
                                        broker_fee_usd, reg_fee_usd, proceeds_pln, cost_pln, pl_pln)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticker.upper(), quantity, sell_price_usd, sell_date, fx_rate,
                  broker_fee_usd, reg_fee_usd, proceeds_pln, total_cost_pln, pl_pln))
            
            trade_id = cursor.lastrowid
            
            # Zapisz splits i aktualizuj LOT-y
            for split in fifo_splits:
                cursor.execute("""
                    INSERT INTO stock_trade_splits (trade_id, lot_id, qty_from_lot, 
                                                  cost_part_pln, commission_part_usd, commission_part_pln)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (trade_id, split['lot_id'], split['qty_from_lot'], 
                      split['cost_part_pln'], split['commission_part_usd'], split['commission_part_pln']))
                
                # Aktualizuj quantity_open w LOT-ie
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_open = quantity_open - ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (split['qty_from_lot'], split['lot_id']))
            
            conn.commit()
            conn.close()
            
            # Utwórz cashflow dla sprzedaży
            cashflow_id = insert_cashflow(
                cashflow_type='stock_sell',
                amount_usd=net_proceeds_usd,  # Dodatnie bo to przychód
                date=sell_date,
                fx_rate=fx_rate,
                description=f"Sprzedaż {quantity} {ticker.upper()} @ ${sell_price_usd}",
                ref_table='stock_trades',
                ref_id=trade_id
            )
            
            return trade_id
            
        except Exception as e:
            st.error(f"Błąd sprzedaży akcji: {e}")
            if conn:
                conn.close()
            return None
    
    return None

def get_stock_trade(trade_id):
    """
    Pobranie szczegółów sprzedaży z rozbiciem po LOT-ach
    
    Args:
        trade_id: int - ID trade'u
    
    Returns:
        dict lub None: Dane trade'u z splits
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Główne dane trade'u
            cursor.execute("""
                SELECT id, ticker, quantity, sell_price_usd, sell_date, fx_rate,
                       broker_fee_usd, reg_fee_usd, proceeds_pln, cost_pln, pl_pln, created_at
                FROM stock_trades 
                WHERE id = ?
            """, (trade_id,))
            
            trade_row = cursor.fetchone()
            if not trade_row:
                conn.close()
                return None
            
            # Rozbicie po LOT-ach
            cursor.execute("""
                SELECT s.id, s.lot_id, s.qty_from_lot, s.cost_part_pln, 
                       s.commission_part_usd, s.commission_part_pln,
                       l.buy_date, l.buy_price_usd
                FROM stock_trade_splits s
                JOIN lots l ON s.lot_id = l.id
                WHERE s.trade_id = ?
                ORDER BY l.buy_date, l.id
            """, (trade_id,))
            
            splits_rows = cursor.fetchall()
            conn.close()
            
            return {
                'id': trade_row[0],
                'ticker': trade_row[1],
                'quantity': trade_row[2],
                'sell_price_usd': float(trade_row[3]),
                'sell_date': trade_row[4],
                'fx_rate': float(trade_row[5]),
                'broker_fee_usd': float(trade_row[6]),
                'reg_fee_usd': float(trade_row[7]),
                'proceeds_pln': float(trade_row[8]),
                'cost_pln': float(trade_row[9]),
                'pl_pln': float(trade_row[10]),
                'created_at': trade_row[11],
                'splits': [{
                    'split_id': row[0],
                    'lot_id': row[1],
                    'qty_from_lot': row[2],
                    'cost_part_pln': float(row[3]),
                    'commission_part_usd': float(row[4]),
                    'commission_part_pln': float(row[5]),
                    'lot_buy_date': row[6],
                    'lot_buy_price_usd': float(row[7])
                } for row in splits_rows]
            }
            
        except Exception as e:
            st.error(f"Błąd pobierania trade: {e}")
            if conn:
                conn.close()
    
    return None

def get_stock_trades_summary(ticker=None, start_date=None, end_date=None):
    """
    Pobranie podsumowania sprzedaży
    
    Args:
        ticker: str - filtr tickera
        start_date: str - data początkowa
        end_date: str - data końcowa
    
    Returns:
        list: Lista trade'ów
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            query = """
                SELECT id, ticker, quantity, sell_price_usd, sell_date, 
                       proceeds_pln, cost_pln, pl_pln
                FROM stock_trades 
                WHERE 1=1
            """
            params = []
            
            if ticker:
                query += " AND ticker = ?"
                params.append(ticker.upper())
            
            if start_date:
                query += " AND sell_date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND sell_date <= ?"
                params.append(end_date)
            
            query += " ORDER BY sell_date DESC, id DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'id': row[0],
                'ticker': row[1],
                'quantity': row[2],
                'sell_price_usd': float(row[3]),
                'sell_date': row[4],
                'proceeds_pln': float(row[5]),
                'cost_pln': float(row[6]),
                'pl_pln': float(row[7])
            } for row in rows]
            
        except Exception as e:
            st.error(f"Błąd pobierania podsumowania: {e}")
            if conn:
                conn.close()
    
    return []

def test_stock_trades_operations():
    """
    Test operacji sprzedaży FIFO
    
    Returns:
        dict: Wyniki testów
    """
    results = {
        'tables_exist': False,
        'setup_lots': False,
        'sell_test': False,
        'fifo_test': False,
        'get_trade_test': False
    }
    
    try:
        import structure
        
        # Test tworzenia tabel
        conn = get_connection()
        if conn:
            results['tables_exist'] = (structure.create_stock_trades_table(conn) and 
                                     structure.create_stock_trade_splits_table(conn))
            # Wyczyść testowe dane
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stock_trades WHERE ticker = 'MSFT'")
            cursor.execute("DELETE FROM stock_trade_splits WHERE trade_id IN (SELECT id FROM stock_trades WHERE ticker = 'MSFT')")
            cursor.execute("DELETE FROM lots WHERE ticker = 'MSFT'")
            conn.commit()
            conn.close()
        
        # Setup - dodaj testowe LOT-y
        if results['tables_exist']:
            conn = get_connection()
            if conn:
                cursor = conn.cursor()
                # LOT 1: 100 akcji @ $200
                cursor.execute("""
                    INSERT INTO lots (ticker, quantity_total, quantity_open, buy_price_usd,
                                    broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ('MSFT', 100, 100, 200.0, 1.0, 0.5, '2025-01-10', 4.2000, 8400.0))
                lot1_id = cursor.lastrowid
                
                # LOT 2: 50 akcji @ $210
                cursor.execute("""
                    INSERT INTO lots (ticker, quantity_total, quantity_open, buy_price_usd,
                                    broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ('MSFT', 50, 50, 210.0, 1.0, 0.5, '2025-01-12', 4.2100, 4400.0))
                lot2_id = cursor.lastrowid
                
                conn.commit()
                conn.close()
                results['setup_lots'] = True
        
        # Test sprzedaży FIFO (120 akcji - powinno użyć całego LOT1 + 20 z LOT2)
        if results['setup_lots']:
            trade_id = sell_stock_fifo('MSFT', 120, 220.0, '2025-01-15', 4.2500, 2.0, 1.0)
            results['sell_test'] = trade_id is not None
        
        # Test czy FIFO działa poprawnie
        if results['sell_test']:
            trade = get_stock_trade(trade_id)
            if trade and len(trade['splits']) == 2:
                # Sprawdź czy pierwszy split to cały LOT1 (100 akcji)
                split1 = trade['splits'][0]
                split2 = trade['splits'][1]
                results['fifo_test'] = (split1['qty_from_lot'] == 100 and 
                                      split2['qty_from_lot'] == 20 and
                                      split1['lot_buy_date'] <= split2['lot_buy_date'])
        
        # Test pobierania trade'u
        if results['fifo_test']:
            results['get_trade_test'] = trade is not None and trade['pl_pln'] != 0
            
    except Exception as e:
        st.error(f"Błąd testów stock_trades: {e}")
    
    return results
    
# DODAJ te funkcje na koniec pliku db.py

# ================================
# TEST OSTATNICH TABEL (PUNKT 10)
# ================================

# DODAJ te funkcje na koniec pliku db.py

# ================================
# TEST OSTATNICH TABEL (PUNKT 10)
# ================================

def test_final_tables_operations():
    """
    Test operacji na ostatnich tabelach (options_cc, dividends, market_prices)
    
    Returns:
        dict: Wyniki testów
    """
    results = {
        'options_cc_table': False,
        'dividends_table': False,
        'market_prices_table': False,
        'options_insert': False,
        'dividends_insert': False,
        'market_prices_insert': False,
        'schema_complete': False
    }
    
    try:
        import structure
        
        conn = get_connection()
        if conn:
            # Test tworzenia tabel
            results['options_cc_table'] = structure.create_options_cc_table(conn)
            results['dividends_table'] = structure.create_dividends_table(conn)
            results['market_prices_table'] = structure.create_market_prices_table(conn)
            
            cursor = conn.cursor()
            
            # WYCZYŚĆ dane testowe przed dodawaniem nowych
            cursor.execute("DELETE FROM options_cc WHERE ticker = 'AAPL'")
            cursor.execute("DELETE FROM dividends WHERE ticker = 'AAPL'")
            cursor.execute("DELETE FROM market_prices WHERE ticker = 'AAPL'")
            conn.commit()
            
            # Test wstawiania do options_cc
            if results['options_cc_table']:
                try:
                    cursor.execute("""
                        INSERT INTO options_cc (ticker, contracts, strike_usd, premium_sell_usd,
                                              open_date, expiry_date, fx_open, premium_sell_pln)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, ('AAPL', 1, 180.0, 2.50, '2025-01-15', '2025-02-21', 4.2500, 10.63))
                    results['options_insert'] = True
                except Exception as e:
                    st.error(f"Błąd wstawiania options_cc: {e}")
            
            # Test wstawiania do dividends
            if results['dividends_table']:
                try:
                    cursor.execute("""
                        INSERT INTO dividends (ticker, gross_usd, date_paid, fx_rate, 
                                             gross_pln, wht_15_pln, tax_4_pln, net_pln)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, ('AAPL', 0.25, '2025-01-15', 4.2500, 1.06, 0.16, 0.04, 0.86))
                    results['dividends_insert'] = True
                except Exception as e:
                    st.error(f"Błąd wstawiania dividends: {e}")
            
            # Test wstawiania do market_prices
            if results['market_prices_table']:
                try:
                    cursor.execute("""
                        INSERT INTO market_prices (ticker, date, price_usd)
                        VALUES (?, ?, ?)
                    """, ('AAPL', '2025-01-15', 185.50))
                    results['market_prices_insert'] = True
                except Exception as e:
                    st.error(f"Błąd wstawiania market_prices: {e}")
            
            conn.commit()
            
            # Test kompletności schematu
            if all([results['options_cc_table'], results['dividends_table'], results['market_prices_table']]):
                schema_info = structure.get_database_schema_info(conn)
                expected_tables = ['fx_rates', 'cashflows', 'lots', 'stock_trades', 
                                 'stock_trade_splits', 'options_cc', 'dividends', 'market_prices']
                results['schema_complete'] = all(table in schema_info for table in expected_tables)
            
            conn.close()
            
    except Exception as e:
        st.error(f"Błąd testów finalnych tabel: {e}")
    
    return results

def get_database_summary():
    """
    Pobranie podsumowania całej bazy danych
    
    Returns:
        dict: Podsumowanie wszystkich tabel
    """
    conn = get_connection()
    if conn:
        try:
            import structure
            schema_info = structure.get_database_schema_info(conn)
            conn.close()
            
            # Dodaj podsumowanie
            total_tables = len(schema_info)
            total_records = sum(info['records'] for info in schema_info.values())
            
            return {
                'total_tables': total_tables,
                'total_records': total_records,
                'tables': schema_info
            }
            
        except Exception as e:
            st.error(f"Błąd podsumowania bazy: {e}")
            if conn:
                conn.close()
    
    return {
        'total_tables': 0,
        'total_records': 0,
        'tables': {}
    }

def get_database_summary():
    """
    Pobranie podsumowania całej bazy danych
    
    Returns:
        dict: Podsumowanie wszystkich tabel
    """
    conn = get_connection()
    if conn:
        try:
            import structure
            schema_info = structure.get_database_schema_info(conn)
            conn.close()
            
            # Dodaj podsumowanie
            total_tables = len(schema_info)
            total_records = sum(info['records'] for info in schema_info.values())
            
            return {
                'total_tables': total_tables,
                'total_records': total_records,
                'tables': schema_info
            }
            
        except Exception as e:
            st.error(f"Błąd podsumowania bazy: {e}")
            if conn:
                conn.close()
    
    return {
        'total_tables': 0,
        'total_records': 0,
        'tables': {}
    }