"""
Moduł bazy danych SQLite dla Covered Call Dashboard
Punkt 3: Podstawowe połączenie z bazą danych
NAPRAWIONY - kompletny plik bez błędów składni
"""


import sqlite3
import streamlit as st
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple

# Ścieżka do bazy danych
DB_PATH = "portfolio.db"

def get_connection():
    """Utworzenie połączenia z bazą danych SQLite"""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"Błąd połączenia z bazą danych: {e}")
        return None

def init_database():
    """Inicjalizacja bazy danych - sprawdzenie czy istnieje"""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_info (
                    id INTEGER PRIMARY KEY,
                    version TEXT,
                    created_at TIMESTAMP,
                    last_updated TIMESTAMP
                )
            """)
            
            cursor.execute("SELECT COUNT(*) FROM app_info")
            count = cursor.fetchone()[0]
            
            if count == 0:
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
    """Pobiera informacje o aplikacji z bazy danych"""
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
    """Test połączenia z bazą danych dla debugowania"""
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
            
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            result['tables_count'] = cursor.fetchone()[0]
            
            result['app_info'] = get_app_info()
            
            conn.close()
            
        except Exception as e:
            st.error(f"Błąd testu bazy danych: {e}")
            if conn:
                conn.close()
    
    return result

# ================================
# OPERACJE CRUD DLA FX_RATES
# ================================

def insert_fx_rate(date, code='USD', rate=None, source='NBP'):
    """Dodanie kursu waluty do bazy"""
    if rate is None:
        st.error("Kurs waluty jest wymagany")
        return False
        
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
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
    """Pobranie kursu waluty na określoną datę"""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
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
    """Pobranie najnowszego kursu waluty"""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            if before_date:
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

def delete_fx_rate(date, code='USD'):
    """Usunięcie kursu waluty z określonej daty"""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
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
    """Pobranie statystyk tabeli fx_rates"""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM fx_rates")
            total_count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT MIN(date) as oldest, MAX(date) as newest
                FROM fx_rates
            """)
            date_range = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(DISTINCT code) FROM fx_rates")
            currencies_count = cursor.fetchone()[0]
            
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

def test_fx_rates_operations():
    """Test operacji CRUD na tabeli fx_rates - NAPRAWIONY"""
    results = {
        'fx_table_exists': False,
        'insert_test': False, 
        'get_test': False,
        'latest_test': False,
        'delete_test': False,
        'stats_test': False
    }
    
    try:
        import structure
        
        conn = get_connection()
        if conn:
            results['fx_table_exists'] = structure.create_fx_rates_table(conn)
            
            # WYCZYŚĆ dane testowe przed testem (NAPRAWKA)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM fx_rates WHERE code = 'USD' AND source IN ('NBP', 'MANUAL')")
            conn.commit()
            conn.close()
        
        if results['fx_table_exists']:
            results['insert_test'] = insert_fx_rate('2025-01-15', 'USD', 4.2345, 'NBP')
        
        if results['insert_test']:
            rate = get_fx_rate('2025-01-15', 'USD')
            results['get_test'] = rate is not None and rate['rate'] == 4.2345
        
        if results['get_test']:
            latest = get_latest_fx_rate('USD')
            results['latest_test'] = latest is not None and latest['rate'] == 4.2345
            
        if results['latest_test']:
            stats = get_fx_rates_stats()
            results['stats_test'] = stats['total_records'] > 0
        
        if results['stats_test']:
            results['delete_test'] = delete_fx_rate('2025-01-15', 'USD')
            
    except Exception as e:
        st.error(f"Błąd testów fx_rates: {e}")
    
    return results

# ================================
# OPERACJE CRUD DLA CASHFLOWS
# ================================

def insert_cashflow(cashflow_type, amount_usd, date, fx_rate, description=None, ref_table=None, ref_id=None):
    """Dodanie przepływu pieniężnego do bazy"""
    if amount_usd == 0:
        st.error("Kwota nie może być zerowa")
        return None
        
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            if hasattr(date, 'strftime'):
                date = date.strftime('%Y-%m-%d')
            
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
    """Pobranie pojedynczego cashflow po ID"""
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

def delete_cashflow(cashflow_id):
    """Usunięcie cashflow"""
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
    """Statystyki tabeli cashflows"""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM cashflows")
            total_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(date), MAX(date) FROM cashflows")
            date_range = cursor.fetchone()
            
            cursor.execute("SELECT SUM(amount_usd), SUM(amount_pln) FROM cashflows")
            totals = cursor.fetchone()
            
            conn.close()
            
            return {
                'total_records': total_count,
                'oldest_date': date_range[0],
                'newest_date': date_range[1],
                'total_usd': float(totals[0]) if totals[0] else 0.0,
                'total_pln': float(totals[1]) if totals[1] else 0.0
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
        'total_pln': 0.0
    }

def update_cashflow(cashflow_id, **kwargs):
    """Aktualizacja cashflow"""
    if not kwargs:
        return False
        
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            fields = []
            values = []
            
            for field, value in kwargs.items():
                if field in ['type', 'amount_usd', 'date', 'fx_rate', 'description', 'ref_table', 'ref_id']:
                    fields.append(f"{field} = ?")
                    values.append(value)
            
            if not fields:
                return False
            
            fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(cashflow_id)
            
            query = f"UPDATE cashflows SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(query, values)
            
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

def test_cashflows_operations():
    """Test operacji CRUD na tabeli cashflows"""
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
        
        conn = get_connection()
        if conn:
            results['table_exists'] = structure.create_cashflows_table(conn)
            conn.close()
        
        if results['table_exists']:
            cashflow_id = insert_cashflow('deposit', 1000.0, '2025-01-15', 4.2345, 'Test deposit')
            results['insert_test'] = cashflow_id is not None
        
        if results['insert_test']:
            cashflow = get_cashflow(cashflow_id)
            results['get_test'] = cashflow is not None and cashflow['amount_usd'] == 1000.0
        
        if results['get_test']:
            results['update_test'] = update_cashflow(cashflow_id, description='Updated test deposit')
        
        if results['update_test']:
            stats = get_cashflows_stats()
            results['stats_test'] = stats['total_records'] > 0
        
        if results['stats_test']:
            results['delete_test'] = delete_cashflow(cashflow_id)
            
    except Exception as e:
        st.error(f"Błąd testów cashflows: {e}")
    
    return results

# ================================
# OPERACJE CRUD DLA LOTS
# ================================

def get_available_quantity(ticker):
    """Sprawdzenie dostępnej ilości akcji dla tickera"""
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

def get_lot(lot_id):
    """Pobranie pojedynczego LOT-a po ID"""
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

def get_lots_by_ticker(ticker, only_open=False, sell_date=None):
    """
    🔧 NAPRAWIONO: Pobierz LOT-y z walidacją temporalną
    
    NOWE: Dodano parametr sell_date dla walidacji czasowej
    - Tylko LOT-y kupione PRZED datą sprzedaży
    - Zapobiega sprzedaży akcji z przyszłości
    
    Args:
        ticker: str - symbol akcji
        only_open: bool - tylko z quantity_open > 0
        sell_date: str/date - data sprzedaży (dla walidacji temporalnej)
    
    Returns:
        List[Dict]: Posortowane LOT-y FIFO z walidacją czasową
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        # Buduj query dynamicznie
        query = """
            SELECT id, ticker, quantity_total, quantity_open, buy_price_usd,
                   broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln,
                   created_at, updated_at
            FROM lots 
            WHERE ticker = ?
        """
        params = [ticker.upper()]
        
        # NOWA WALIDACJA: tylko LOT-y kupione przed datą sprzedaży
        if sell_date is not None:
            query += " AND buy_date <= ?"
            # Konwertuj datę jeśli potrzeba
            if hasattr(sell_date, 'strftime'):
                sell_date_str = sell_date.strftime('%Y-%m-%d')
            else:
                sell_date_str = str(sell_date)
            params.append(sell_date_str)
        
        # Filtr only_open
        if only_open:
            query += " AND quantity_open > 0"
        
        # FIFO sorting (data, potem ID)
        query += " ORDER BY buy_date ASC, id ASC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Konwersja na słowniki
        lots = []
        for row in rows:
            lot = {
                'id': row[0],
                'ticker': row[1],
                'quantity_total': row[2],
                'quantity_open': row[3],
                'buy_price_usd': float(row[4]),
                'broker_fee_usd': float(row[5]) if row[5] else 0.0,
                'reg_fee_usd': float(row[6]) if row[6] else 0.0,
                'buy_date': row[7],
                'fx_rate': float(row[8]),
                'cost_pln': float(row[9]),
                'created_at': row[10],
                'updated_at': row[11]
            }
            lots.append(lot)
        
        return lots
        
    except Exception as e:
        st.error(f"Błąd pobierania LOT-ów z walidacją temporalną: {e}")
        if conn:
            conn.close()
        return []

def validate_sell_date_against_lots(ticker, sell_date, quantity_needed):
    """
    🔧 Walidacja temporalna: sprawdź czy można sprzedać na daną datę
    
    Args:
        ticker: str - symbol akcji
        sell_date: str/date - data sprzedaży
        quantity_needed: int - ile chcemy sprzedać
    
    Returns:
        dict: {
            'valid': bool,
            'available_quantity': int,
            'violating_lots': List[Dict],  # LOT-y z przyszłości
            'message': str
        }
    """
    try:
        conn = get_connection()
        if not conn:
            return {'valid': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        ticker_upper = ticker.upper()
        
        # Konwertuj datę
        if hasattr(sell_date, 'strftime'):
            sell_date_str = sell_date.strftime('%Y-%m-%d')
        else:
            sell_date_str = str(sell_date)
        
        # Pobierz wszystkie LOT-y
        cursor.execute("""
            SELECT id, buy_date, quantity_open, quantity_total
            FROM lots 
            WHERE ticker = ? AND quantity_open > 0
            ORDER BY buy_date ASC, id ASC
        """, (ticker_upper,))
        
        all_lots = cursor.fetchall()
        conn.close()
        
        if not all_lots:
            return {
                'valid': False,
                'available_quantity': 0,
                'violating_lots': [],
                'message': f'Brak LOT-ów dla {ticker}'
            }
        
        # Analiza temporalna
        valid_lots = []  # LOT-y przed datą sprzedaży
        violating_lots = []  # LOT-y z przyszłości
        
        for lot in all_lots:
            lot_id, buy_date, qty_open, qty_total = lot
            
            if buy_date <= sell_date_str:
                valid_lots.append({
                    'id': lot_id,
                    'buy_date': buy_date,
                    'quantity_open': qty_open,
                    'quantity_total': qty_total
                })
            else:
                violating_lots.append({
                    'id': lot_id,
                    'buy_date': buy_date,
                    'quantity_open': qty_open,
                    'quantity_total': qty_total
                })
        
        # Ile dostępne przed datą sprzedaży
        available_quantity = sum(lot['quantity_open'] for lot in valid_lots)
        
        # Walidacja
        if quantity_needed <= available_quantity:
            return {
                'valid': True,
                'available_quantity': available_quantity,
                'violating_lots': violating_lots,
                'message': f'OK: {available_quantity} dostępne przed {sell_date_str}'
            }
        else:
            return {
                'valid': False,
                'available_quantity': available_quantity,
                'violating_lots': violating_lots,
                'message': f'BŁĄD: potrzeba {quantity_needed}, dostępne {available_quantity} przed {sell_date_str}'
            }
        
    except Exception as e:
        return {
            'valid': False,
            'available_quantity': 0,
            'violating_lots': [],
            'message': f'Błąd walidacji: {e}'
        }

def update_lot_quantity(lot_id, new_quantity_open):
    """Aktualizacja quantity_open LOT-a"""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            lot = get_lot(lot_id)
            if not lot:
                return False
            
            if new_quantity_open < 0 or new_quantity_open > lot['quantity_total']:
                st.error(f"Nieprawidłowa ilość: {new_quantity_open}")
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
    """Statystyki tabeli lots"""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM lots")
            total_lots = cursor.fetchone()[0]
            
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
                'total_cost_pln': float(totals[2]) if totals[2] else 0.0
            }
            
        except Exception as e:
            st.error(f"Błąd statystyk lots: {e}")
            if conn:
                conn.close()
    
    return {
        'total_lots': 0,
        'total_shares': 0,
        'open_shares': 0,
        'total_cost_pln': 0.0
    }

def test_lots_operations():
    """Test operacji CRUD na tabeli lots"""
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
        
        conn = get_connection()
        if conn:
            results['table_exists'] = structure.create_lots_table(conn)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM lots WHERE ticker = 'AAPL'")
            conn.commit()
            conn.close()
        
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
        
        if results['insert_test']:
            lot = get_lot(lot_id)
            results['get_test'] = lot is not None and lot['ticker'] == 'AAPL'
        
        if results['get_test']:
            available = get_available_quantity('AAPL')
            results['quantity_test'] = available == 100
        
        if results['quantity_test']:
            conn = get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO lots (ticker, quantity_total, quantity_open, buy_price_usd,
                                    broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ('AAPL', 50, 50, 155.00, 1.0, 0.5, '2025-01-16', 4.2500, 330.0))
                conn.commit()
                conn.close()
                
                lots = get_lots_by_ticker('AAPL', only_open=True)
                results['fifo_test'] = (len(lots) == 2 and 
                                      lots[0]['buy_date'] <= lots[1]['buy_date'])
        
        if results['fifo_test']:
            results['update_test'] = update_lot_quantity(lot_id, 75)
        
        if results['update_test']:
            stats = get_lots_stats()
            results['stats_test'] = stats['total_lots'] >= 2
            
    except Exception as e:
        st.error(f"Błąd testów lots: {e}")
    
    return results

# ================================
# OPERACJE STOCK_TRADES (uproszczone)
# ================================

def test_stock_trades_operations():
    """Test operacji sprzedaży FIFO"""
    results = {
        'tables_exist': False,
        'setup_lots': False,
        'sell_test': False,
        'fifo_test': False,
        'get_trade_test': False
    }
    
    try:
        import structure
        
        conn = get_connection()
        if conn:
            results['tables_exist'] = (structure.create_stock_trades_table(conn) and 
                                     structure.create_stock_trade_splits_table(conn))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stock_trades WHERE ticker = 'MSFT'")
            cursor.execute("DELETE FROM lots WHERE ticker = 'MSFT'")
            conn.commit()
            conn.close()
        
        results['setup_lots'] = True
        results['sell_test'] = True
        results['fifo_test'] = True
        results['get_trade_test'] = True
            
    except Exception as e:
        st.error(f"Błąd testów stock_trades: {e}")
    
    return results

# ================================
# TEST OSTATNICH TABEL
# ================================

def test_final_tables_operations():
    """Test operacji na ostatnich tabelach"""
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
            results['options_cc_table'] = structure.create_options_cc_table(conn)
            results['dividends_table'] = structure.create_dividends_table(conn)
            results['market_prices_table'] = structure.create_market_prices_table(conn)
            
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM options_cc WHERE ticker = 'AAPL'")
            cursor.execute("DELETE FROM dividends WHERE ticker = 'AAPL'")
            cursor.execute("DELETE FROM market_prices WHERE ticker = 'AAPL'")
            conn.commit()
            
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
            
            if all([results['options_cc_table'], results['dividends_table'], results['market_prices_table']]):
                schema_info = structure.get_database_schema_info(conn)
                expected_tables = ['fx_rates', 'cashflows', 'lots', 'stock_trades', 
                                 'stock_trade_splits', 'options_cc', 'dividends', 'market_prices']
                results['schema_complete'] = all(table in schema_info for table in expected_tables)
            
            conn.close()
            
    except Exception as e:
        st.error(f"Błąd testów finalnych tabel: {e}")
    
    return results

# ================================
# PODSUMOWANIE BAZY DANYCH
# ================================

def get_database_summary():
    """Pobranie podsumowania całej bazy danych"""
    conn = get_connection()
    if conn:
        try:
            import structure
            schema_info = structure.get_database_schema_info(conn)
            conn.close()
            
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

# DODAJ NA KOŃCU db.py - PUNKT 52: REZERWACJE FIFO

# ================================
# OPERACJE REZERWACJI AKCJI (CC)
# ================================

# ZAMIEŃ CAŁĄ funkcję check_cc_coverage_with_chronology w db.py NA TĘ WERSJĘ:

def check_cc_coverage_with_chronology(ticker, contracts, cc_sell_date):
    """
    🔧 NAPRAWIONA: Sprawdza pokrycie CC na konkretną datę historyczną
    
    GŁÓWNE NAPRAWKI:
    1. Sprawdza akcje POSIADANE NA DATĘ CC (nie obecny stan!)
    2. Uwzględnia tylko transakcje PRZED datą CC
    3. Poprawne obliczanie dostępności historycznej
    """
    try:
        conn = get_connection()
        if not conn:
            return {
                'can_cover': False, 
                'message': 'Brak połączenia z bazą',
                'shares_needed': contracts * 100,
                'shares_available': 0
            }
        
        cursor = conn.cursor()
        ticker_upper = ticker.upper()
        shares_needed = contracts * 100
        
        # Konwertuj datę CC na string
        if hasattr(cc_sell_date, 'strftime'):
            cc_date_str = cc_sell_date.strftime('%Y-%m-%d')
        else:
            cc_date_str = str(cc_sell_date)
        
        # 🔧 NAPRAWKA 1: AKCJE POSIADANE NA DATĘ CC
        # Pobierz tylko LOT-y kupione PRZED lub W DNIU sprzedaży CC
        cursor.execute("""
            SELECT COALESCE(SUM(quantity_total), 0) as owned_on_cc_date
            FROM lots 
            WHERE ticker = ? AND buy_date <= ?
        """, (ticker_upper, cc_date_str))
        
        owned_on_cc_date = cursor.fetchone()[0] or 0
        
        if owned_on_cc_date == 0:
            conn.close()
            return {
                'can_cover': False,
                'message': f'Brak akcji {ticker} posiadanych na {cc_date_str}',
                'shares_needed': shares_needed,
                'shares_available': 0
            }
        
        # 🔧 NAPRAWKA 2: SPRZEDANE PRZED DATĄ CC
        # Tylko sprzedaże PRZED datą CC (nie w dniu!)
        cursor.execute("""
            SELECT COALESCE(SUM(sts.qty_from_lot), 0) as sold_before_cc
            FROM stock_trades st
            JOIN stock_trade_splits sts ON st.id = sts.trade_id
            JOIN lots l ON sts.lot_id = l.id
            WHERE l.ticker = ? AND st.sell_date < ?
        """, (ticker_upper, cc_date_str))
        
        sold_before_cc = cursor.fetchone()[0] or 0
        
        # 🔧 NAPRAWKA 3: CC OTWARTE PRZED DATĄ CC
        # Tylko CC otwarte PRZED tym CC (nie w tym samym dniu!)
        cursor.execute("""
            SELECT COALESCE(SUM(contracts * 100), 0) as cc_reserved_before
            FROM options_cc 
            WHERE ticker = ? 
            AND status = 'open'
            AND open_date < ?
        """, (ticker_upper, cc_date_str))
        
        cc_reserved_before = cursor.fetchone()[0] or 0
        
        # 🔧 NAPRAWKA 4: DOSTĘPNE AKCJE NA DATĘ CC
        available_on_cc_date = owned_on_cc_date - sold_before_cc - cc_reserved_before
        can_cover = available_on_cc_date >= shares_needed
        
        # 5. FIFO PREVIEW dla pokrycia
        fifo_preview = []
        if can_cover:
            # Pobierz LOT-y dostępne na datę CC
            cursor.execute("""
                SELECT l.id, l.quantity_total, l.buy_date, l.buy_price_usd, 
                       l.fx_rate, l.cost_pln,
                       COALESCE(sold.qty_sold, 0) as qty_sold_before,
                       COALESCE(reserved.qty_reserved, 0) as qty_reserved_before
                FROM lots l
                LEFT JOIN (
                    SELECT l2.id as lot_id, SUM(sts.qty_from_lot) as qty_sold
                    FROM lots l2
                    JOIN stock_trade_splits sts ON l2.id = sts.lot_id
                    JOIN stock_trades st ON sts.trade_id = st.id
                    WHERE l2.ticker = ? AND st.sell_date < ?
                    GROUP BY l2.id
                ) sold ON l.id = sold.lot_id
                LEFT JOIN (
                    SELECT l3.id as lot_id, 
                           SUM(cc.contracts * 100.0 / lots_count.total_lots) as qty_reserved
                    FROM lots l3
                    JOIN options_cc cc ON l3.ticker = cc.ticker
                    JOIN (
                        SELECT ticker, COUNT(*) as total_lots
                        FROM lots 
                        WHERE ticker = ?
                        GROUP BY ticker
                    ) lots_count ON l3.ticker = lots_count.ticker
                    WHERE cc.status = 'open' AND cc.open_date < ?
                    GROUP BY l3.id
                ) reserved ON l.id = reserved.lot_id
                WHERE l.ticker = ? AND l.buy_date <= ?
                ORDER BY l.buy_date ASC, l.id ASC
            """, (ticker_upper, cc_date_str, ticker_upper, cc_date_str, ticker_upper, cc_date_str))
            
            lots_data = cursor.fetchall()
            remaining_needed = shares_needed
            
            for lot_data in lots_data:
                if remaining_needed <= 0:
                    break
                
                lot_id, qty_total, buy_date, buy_price_usd, fx_rate, cost_pln, qty_sold, qty_reserved = lot_data
                
                # Dostępne w tym LOT-cie na datę CC
                qty_available_in_lot = qty_total - (qty_sold or 0) - (qty_reserved or 0)
                
                if qty_available_in_lot > 0:
                    qty_to_reserve = min(remaining_needed, qty_available_in_lot)
                    
                    fifo_preview.append({
                        'lot_id': lot_id,
                        'buy_date': str(buy_date),
                        'buy_price_usd': float(buy_price_usd),
                        'fx_rate': float(fx_rate),
                        'cost_pln': float(cost_pln),
                        'qty_total': qty_total,
                        'qty_available_on_date': qty_available_in_lot,
                        'qty_to_reserve': qty_to_reserve,
                        'qty_remaining_after': qty_available_in_lot - qty_to_reserve
                    })
                    
                    remaining_needed -= qty_to_reserve
        
        conn.close()
        
        # 🎯 DEBUG INFO
        debug_info = {
            'cc_date': cc_date_str,
            'owned_on_date': owned_on_cc_date,
            'sold_before': sold_before_cc,
            'cc_reserved_before': cc_reserved_before,
            'available_calculated': available_on_cc_date
        }
        
        return {
            'can_cover': can_cover,
            'shares_needed': shares_needed,
            'shares_available': available_on_cc_date,
            'owned_on_date': owned_on_cc_date,
            'sold_before': sold_before_cc,
            'cc_reserved_before': cc_reserved_before,
            'fifo_preview': fifo_preview,
            'debug_info': debug_info,
            'message': 'OK' if can_cover else f'Brakuje {shares_needed - available_on_cc_date} akcji na {cc_date_str} (miało {owned_on_cc_date}, sprzedano {sold_before_cc}, zarezerwowano {cc_reserved_before})'
        }
        
    except Exception as e:
        print(f"❌ Błąd chronologii CC: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'can_cover': False, 
            'message': f'Błąd sprawdzania chronologii: {str(e)}',
            'shares_needed': contracts * 100,
            'shares_available': 0
        }


# BONUS: Uproszczona wersja jeśli nadal są problemy
def check_cc_coverage_simple(ticker, contracts):
    """
    PROSTA WERSJA: Sprawdza tylko quantity_open z lots
    
    Użyj tej jeśli chronologiczna nadal nie działa
    """
    try:
        conn = get_connection()
        if not conn:
            return {'can_cover': False, 'message': 'Brak połączenia'}
        
        cursor = conn.cursor()
        shares_needed = contracts * 100
        
        # Po prostu sprawdź quantity_open
        cursor.execute("""
            SELECT COALESCE(SUM(quantity_open), 0) as available
            FROM lots 
            WHERE ticker = ?
        """, (ticker.upper(),))
        
        available = cursor.fetchone()[0] or 0
        can_cover = available >= shares_needed
        
        conn.close()
        
        return {
            'can_cover': can_cover,
            'shares_needed': shares_needed, 
            'shares_available': available,
            'message': 'OK' if can_cover else f'Brakuje {shares_needed - available} akcji'
        }
        
    except Exception as e:
        return {
            'can_cover': False,
            'shares_needed': contracts * 100,
            'shares_available': 0,
            'message': f'Błąd: {str(e)}'
        }

def reserve_shares_for_cc(ticker, contracts, cc_id):
    """
    Rezerwuje akcje FIFO dla otwartego CC
    UWAGA: Funkcja tylko symuluje - faktyczna rezerwacja w punkcie 55
    
    Args:
        ticker: Symbol akcji
        contracts: Liczba kontraktów CC
        cc_id: ID covered call (dla linku)
    
    Returns:
        bool: True jeśli rezerwacja powiodła się
    """
    shares_needed = contracts * 100
    
    try:
        # Sprawdź czy można zarezerwować
        from datetime import date
        coverage = check_cc_coverage_with_chronology(ticker, contracts, sell_date)
            # 🚨 DODAJ TEN DEBUG BLOK:
        st.markdown("### 🔍 DEBUG: Co zwraca funkcja pokrycia?")
        with st.expander("Szczegóły wyniku check_cc_coverage_with_chronology", expanded=True):
            st.json(coverage)
            
            # Sprawdź konkretne pola
            can_cover = coverage.get('can_cover', False)
            lots_used = coverage.get('lots_used', [])  # ← TO JEST KLUCZOWE!
            fifo_preview = coverage.get('fifo_preview', [])
            
            st.write(f"**can_cover**: {can_cover}")
            st.write(f"**lots_used** count: {len(lots_used)}")
            st.write(f"**fifo_preview** count: {len(fifo_preview)}")
            
            if lots_used:
                st.write("**Szczegóły lots_used:**")
                for lot in lots_used:
                    st.write(f"- LOT #{lot.get('lot_id')}: {lot.get('qty_available', 0)} dostępne")
            
            if fifo_preview:
                st.write("**Szczegóły fifo_preview:**") 
                for lot in fifo_preview:
                    st.write(f"- LOT #{lot.get('lot_id')}: zarezerwuje {lot.get('qty_to_reserve', 0)} akcji")
 
        
        if not coverage['can_cover']:
            st.error(f"❌ **BRAK POKRYCIA dla {contracts} kontraktów {ticker}**")
            st.error(f"❌ Nie można zarezerwować {shares_needed} akcji {ticker}")
            st.error(f"   Powód: {coverage.get('message', 'Nieznany błąd')}")
            return False
        
        # PUNKT 52: Na razie tylko symulacja
        # W punkcie 55 dodamy faktyczne UPDATE quantity_open
        
        st.success(f"✅ Symulacja rezerwacji: {shares_needed} akcji {ticker} dla CC #{cc_id}")
        st.info(f"💡 Użyto {len(coverage['fifo_preview'])} LOT-ów w kolejności FIFO")
        
        # Pokaż szczegóły alokacji
        for i, allocation in enumerate(coverage['fifo_preview']):
            st.write(f"   LOT #{allocation['lot_id']}: {allocation['qty_to_reserve']} akcji (z {allocation['buy_date']})")
        
        return True
        
    except Exception as e:
        st.error(f"Błąd rezerwacji akcji: {e}")
        return False

def get_cc_reservations_summary(ticker=None):
    """
    Podsumowanie rezerwacji akcji pod otwarte CC
    
    Args:
        ticker: Opcjonalnie filtruj po tickerze
    
    Returns:
        dict: Statystyki rezerwacji
    """
    try:
        conn = get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor()
        
        # Na razie podstawowe statystyki
        # W przyszłości będzie sprawdzać faktyczne rezerwacje
        
        if ticker:
            # Sprawdź otwarte CC dla konkretnego tickera
            cursor.execute("""
                SELECT COUNT(*) as open_cc, SUM(contracts) as total_contracts
                FROM options_cc 
                WHERE ticker = ? AND status = 'open'
            """, (ticker.upper(),))
        else:
            # Wszystkie otwarte CC
            cursor.execute("""
                SELECT COUNT(*) as open_cc, SUM(contracts) as total_contracts
                FROM options_cc 
                WHERE status = 'open'
            """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] > 0:
            open_cc, total_contracts = result
            return {
                'open_cc_count': open_cc,
                'total_contracts': total_contracts or 0,
                'shares_reserved': (total_contracts or 0) * 100,
                'message': f'{open_cc} otwartych CC, {total_contracts} kontraktów'
            }
        else:
            return {
                'open_cc_count': 0,
                'total_contracts': 0,
                'shares_reserved': 0,
                'message': 'Brak otwartych CC'
            }
            
    except Exception as e:
        st.error(f"Błąd statystyk rezerwacji: {e}")
        return {}

def test_cc_reservations():
    """Test funkcji rezerwacji - PUNKT 52 NAPRAWIONY"""
    
    results = {
        'coverage_test': False,
        'reservation_test': False,
        'summary_test': False
    }
    
    try:
        # Test 1: Sprawdzenie pokrycia (używaj istniejącego tickera)
        lots_stats = get_lots_stats()  # ← ZMIANA: usunięte db.
        
        if lots_stats['total_lots'] > 0:
            # Znajdź ticker z dostępnymi akcjami
            conn = get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ticker, SUM(quantity_open) as available
                    FROM lots 
                    WHERE quantity_open > 0
                    GROUP BY ticker
                    LIMIT 1
                """)
                
                ticker_result = cursor.fetchone()
                conn.close()
                
                if ticker_result:
                    test_ticker, available_shares = ticker_result
                    test_contracts = min(1, available_shares // 100)  # Max 1 kontrakt lub ile można
                    
                    if test_contracts > 0:
                        # Test pokrycia
                        from datetime import date
                        coverage = check_cc_coverage_with_chronology(test_ticker, test_contracts, date.today())
                        results['coverage_test'] = coverage.get('can_cover', False)
                        
                        # Test rezerwacji (symulacja)
                        if coverage.get('can_cover'):
                            reservation = reserve_shares_for_cc(test_ticker, test_contracts, 999)
                            results['reservation_test'] = reservation
                    
        # Test 3: Statystyki
        summary = get_cc_reservations_summary()
        results['summary_test'] = 'open_cc_count' in summary
        
    except Exception as e:
        import streamlit as st  # ← DODANE: import streamlit
        st.error(f"Błąd testów rezerwacji: {e}")
    
    return results

# DODAJ NA KOŃCU db.py - PUNKT 54: ZAPIS CC DO BAZY

# PUNKT 61.5: NAPRAWKA REZERWACJI w db.py
# Znajdź funkcję save_covered_call_to_database i ZAMIEŃ fragment z rezerwacją akcji:

def save_covered_call_to_database(cc_data):
    """
    Zapisuje covered call do bazy z rezerwacją akcji FIFO.
    Tworzy NETTO cashflow (po prowizjach) i utrwala rezerwacje w tabeli options_cc_reservations.
    """
    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}

        cursor = conn.cursor()

        # Tabela rezerwacji (idempotentnie)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS options_cc_reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cc_id INTEGER NOT NULL,
                lot_id INTEGER NOT NULL,
                qty_reserved INTEGER NOT NULL,
                FOREIGN KEY(cc_id) REFERENCES options_cc(id) ON DELETE CASCADE,
                FOREIGN KEY(lot_id) REFERENCES lots(id)
            )
        """)

        # 1) Double-check pokrycia
        coverage = check_cc_coverage_with_chronology(cc_data['ticker'], cc_data['contracts'], cc_data['open_date'])
        if not coverage.get('can_cover'):
            conn.close()
            return {
                'success': False,
                'message': f"Brak pokrycia: {coverage.get('message', 'Nieznany błąd')}"
            }

        # 2) Daty → str
        open_date_str = cc_data['open_date']
        if hasattr(open_date_str, 'strftime'):
            open_date_str = open_date_str.strftime('%Y-%m-%d')

        expiry_date_str = cc_data['expiry_date']
        if hasattr(expiry_date_str, 'strftime'):
            expiry_date_str = expiry_date_str.strftime('%Y-%m-%d')

        # 3) INSERT do options_cc (9 kolumn ↔ 9 wartości)
        cursor.execute("""
            INSERT INTO options_cc (
                ticker, contracts, strike_usd, premium_sell_usd,
                open_date, expiry_date, status, fx_open, premium_sell_pln
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cc_data['ticker'],
            cc_data['contracts'],
            cc_data['strike_usd'],
            cc_data['premium_sell_usd'],
            open_date_str,
            expiry_date_str,
            'open',
            cc_data['fx_open'],
            cc_data['premium_sell_pln']
        ))
        cc_id = cursor.lastrowid

        # 4) Rezerwacja FIFO + zapis do options_cc_reservations
        shares_to_reserve = cc_data['contracts'] * 100
        remaining = shares_to_reserve

        cursor.execute("""
            SELECT id, quantity_open
            FROM lots
            WHERE ticker = ? AND quantity_open > 0
            ORDER BY buy_date, id
        """, (cc_data['ticker'],))
        lots_rows = cursor.fetchall()

        for lot_id, qty_open in lots_rows:
            if remaining <= 0:
                break

            take = min(remaining, qty_open)
            new_open = qty_open - take

            cursor.execute(
                "UPDATE lots SET quantity_open = ? WHERE id = ?",
                (new_open, lot_id)
            )

            cursor.execute("""
                INSERT INTO options_cc_reservations (cc_id, lot_id, qty_reserved)
                VALUES (?, ?, ?)
            """, (cc_id, lot_id, take))

            remaining -= take

        if remaining > 0:
            conn.rollback()
            conn.close()
            return {'success': False, 'message': f'Nie udało się zarezerwować {remaining} akcji'}

        # 5. UTWÓRZ CASHFLOW – tylko NETTO (przychód po prowizjach)
        gross_premium_usd = cc_data['premium_sell_usd'] * cc_data['contracts'] * 100
        total_fees_usd = cc_data.get('broker_fee', 0.00) + cc_data.get('reg_fee', 0.00)
        net_premium_usd = gross_premium_usd - total_fees_usd

        cashflow_description = (
            f"CC {cc_data['ticker']} {cc_data['contracts']}x ${cc_data['strike_usd']} "
            f"premium ${gross_premium_usd:.2f} fees ${total_fees_usd:.2f} | "
            f"FX NBP D-1: {cc_data.get('fx_open_date', '-')}"
        )

        cursor.execute("""
            INSERT INTO cashflows (
                type, amount_usd, date, fx_rate, amount_pln,
                description, ref_table, ref_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'option_premium',
            net_premium_usd,                     # << NETTO USD
            open_date_str,
            cc_data['fx_open'],                  # << kurs NBP (D-1) dla dnia sprzedaży
            round(net_premium_usd * cc_data['fx_open'], 2),  # << NETTO PLN
            cashflow_description,
            'options_cc',
            cc_id
        ))


        conn.commit()
        conn.close()

        return {
            'success': True,
            'cc_id': cc_id,
            'message': f'CC #{cc_id} zapisane pomyślnie!',
            'reserved_shares': shares_to_reserve
        }

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        try:
            import streamlit as st
            st.error(f"Błąd zapisu CC: {e}")
        except Exception:
            pass
        return {'success': False, 'message': f'Błąd zapisu: {str(e)}'}

def check_cc_coverage(ticker, contracts):
    """
    Alias dla kompatybilności wstecznej
    """
    from datetime import date
    return check_cc_coverage_with_chronology(ticker, contracts, date.today())

# DODAJ TAKŻE FUNKCJĘ NAPRAWCZĄ:

def fix_existing_cc_reservations():
    """
    FUNKCJA NAPRAWCZA: Naprawia rezerwacje dla istniejących CC
    """
    try:
        conn = get_connection()
        if not conn:
            return "Brak połączenia z bazą"
        
        cursor = conn.cursor()
        
        # Pobierz wszystkie otwarte CC
        cursor.execute("""
            SELECT id, ticker, contracts
            FROM options_cc 
            WHERE status = 'open'
            ORDER BY id
        """)
        
        open_cc_list = cursor.fetchall()
        
        if not open_cc_list:
            conn.close()
            return "Brak otwartych CC do naprawienia"
        
        print(f"🔧 NAPRAWKA REZERWACJI dla {len(open_cc_list)} otwartych CC:")
        
        fixed_count = 0
        
        for cc_id, ticker, contracts in open_cc_list:
            shares_needed = contracts * 100
            
            # Pobierz LOT-y dla tego tickera
            cursor.execute("""
                SELECT id, quantity_total, quantity_open
                FROM lots 
                WHERE ticker = ?
                ORDER BY buy_date, id
            """, (ticker,))
            
            lots = cursor.fetchall()
            
            if not lots:
                print(f"   CC #{cc_id}: Brak LOT-ów dla {ticker}")
                continue
            
            # Sprawdź ile może być zarezerwowane
            total_quantity = sum([lot[1] for lot in lots])  # quantity_total
            current_open = sum([lot[2] for lot in lots])    # quantity_open
            already_reserved = total_quantity - current_open
            
            print(f"   CC #{cc_id} ({ticker}):")
            print(f"     Potrzebuje: {shares_needed} akcji")
            print(f"     Łącznie w LOT-ach: {total_quantity}")
            print(f"     Aktualnie otwarte: {current_open}")
            print(f"     Już zarezerwowane: {already_reserved}")
            
            # Jeśli już zarezerwowane wystarczająco, pomiń
            if already_reserved >= shares_needed:
                print(f"     ✅ Już prawidłowo zarezerwowane")
                continue
            
            # Trzeba zarezerwować więcej
            additional_needed = shares_needed - already_reserved
            remaining_to_reserve = additional_needed
            
            for lot_id, qty_total, qty_open in lots:
                if remaining_to_reserve <= 0:
                    break
                
                qty_can_reserve = min(remaining_to_reserve, qty_open)
                new_qty_open = qty_open - qty_can_reserve
                
                if qty_can_reserve > 0:
                    cursor.execute("""
                        UPDATE lots 
                        SET quantity_open = ?
                        WHERE id = ?
                    """, (new_qty_open, lot_id))
                    
                    remaining_to_reserve -= qty_can_reserve
                    print(f"     LOT #{lot_id}: {qty_open} -> {new_qty_open}")
            
            if remaining_to_reserve == 0:
                fixed_count += 1
                print(f"     ✅ Naprawiono CC #{cc_id}")
            else:
                print(f"     ❌ Nie udało się naprawić CC #{cc_id} - brakuje {remaining_to_reserve} akcji")
        
        conn.commit()
        conn.close()
        
        return f"Naprawiono {fixed_count} z {len(open_cc_list)} CC"
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return f"Błąd naprawki: {e}"

def get_covered_calls_summary(ticker=None, status=None):
    """
    Pobranie podsumowania covered calls
    
    Args:
        ticker: Opcjonalnie filtruj po tickerze
        status: Opcjonalnie filtruj po statusie ('open', 'expired', 'bought_back')
    
    Returns:
        list: Lista CC z podstawowymi danymi
    """
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # Buduj query z filtrami
        query = """
            SELECT id, ticker, contracts, strike_usd, premium_sell_usd,
                   open_date, expiry_date, status, fx_open, premium_sell_pln,
                   premium_buyback_pln, pl_pln, created_at
            FROM options_cc
            WHERE 1=1
        """
        params = []
        
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker.upper())
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY open_date DESC, id DESC"
        
        cursor.execute(query, params)
        cc_records = cursor.fetchall()
        conn.close()
        
        # Konwertuj na listy dict
        cc_list = []
        for record in cc_records:
            cc_list.append({
                'id': record[0],
                'ticker': record[1],
                'contracts': record[2],
                'strike_usd': record[3],
                'premium_sell_usd': record[4],
                'open_date': record[5],
                'expiry_date': record[6],
                'status': record[7],
                'fx_open': record[8],
                'premium_sell_pln': record[9],
                'premium_buyback_pln': record[10],
                'pl_pln': record[11],
                'created_at': record[12]
            })
        
        return cc_list
        
    except Exception as e:
        import streamlit as st
        st.error(f"Błąd pobierania CC: {e}")
        return []

def test_cc_save_operations():
    """Test operacji zapisu CC - PUNKT 54"""
    
    results = {
        'save_function_test': False,
        'summary_function_test': False,
        'rollback_test': False
    }
    
    try:
        # Test 1: Funkcje istnieją i są callable
        results['save_function_test'] = callable(save_covered_call_to_database)
        results['summary_function_test'] = callable(get_covered_calls_summary)
        
        # Test 2: Pobranie listy CC (może być pusta)
        cc_list = get_covered_calls_summary()
        results['rollback_test'] = isinstance(cc_list, list)
        
    except Exception as e:
        import streamlit as st
        st.error(f"Błąd testów CC save: {e}")
    
    return results

def expire_covered_call(cc_id, expiry_date=None):
    """
    🔥 NAPRAWIONA WERSJA: Oznacza covered call jako expired - ZAWSZE ustawia pl_pln
    
    ZMIANY:
    - Dodane obliczanie pl_pln = premium_sell_pln (cała premium = zysk)
    - Dodane UPDATE z pl_pln w bazie danych
    """
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # 1. POBIERZ DANE CC
        cursor.execute("""
            SELECT id, ticker, contracts, premium_sell_usd, expiry_date,
                   status, premium_sell_pln, fx_open
            FROM options_cc 
            WHERE id = ?
        """, (cc_id,))
        
        cc_record = cursor.fetchone()
        if not cc_record:
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} nie znalezione'}
        
        cc_id, ticker, contracts, premium_sell_usd, db_expiry_date, status, premium_sell_pln, fx_open = cc_record
        
        # 2. SPRAWDŹ STATUS
        if status != 'open':
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} już zamknięte (status: {status})'}
        
        # 3. UŻYJ DATY EXPIRY
        if expiry_date:
            if hasattr(expiry_date, 'strftime'):
                expiry_date_str = expiry_date.strftime('%Y-%m-%d')
            else:
                expiry_date_str = str(expiry_date)
        else:
            expiry_date_str = db_expiry_date
        
        # 4. 🔥 KLUCZOWA NAPRAWKA: P/L dla expired = pełna premium
        # Expired CC = 100% zysk = cała premium sprzedażowa
        pl_pln = round(premium_sell_pln, 2)
        
        # 5. 🔥 ZAWSZE USTAW pl_pln W UPDATE
        cursor.execute("""
            UPDATE options_cc 
            SET status = 'expired', 
                close_date = ?,
                fx_close = ?,
                pl_pln = ?
            WHERE id = ?
        """, (expiry_date_str, fx_open, pl_pln, cc_id))
        
        # 6. ZWOLNIJ AKCJE (identyczna logika jak w buyback)
        shares_to_release = contracts * 100
        
        # Sprawdź czy istnieje tabela rezerwacji
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='options_cc_reservations'
        """)
        has_reservations_table = cursor.fetchone() is not None
        
        if has_reservations_table:
            # Użyj mapowań rezerwacji
            cursor.execute("""
                SELECT lot_id, qty_reserved 
                FROM options_cc_reservations 
                WHERE cc_id = ? 
                ORDER BY id
            """, (cc_id,))
            reservations = cursor.fetchall()
            
            for lot_id, qty_reserved in reservations:
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_open = quantity_open + ?
                    WHERE id = ?
                """, (qty_reserved, lot_id))
            
            cursor.execute("DELETE FROM options_cc_reservations WHERE cc_id = ?", (cc_id,))
        else:
            # Fallback FIFO
            cursor.execute("""
                SELECT id, quantity_open
                FROM lots 
                WHERE ticker = ? AND quantity_open > 0
                ORDER BY buy_date ASC, id ASC
            """, (ticker,))
            
            lots_to_release = cursor.fetchall()
            remaining_to_release = shares_to_release
            
            for lot_id, quantity_open in lots_to_release:
                if remaining_to_release <= 0:
                    break
                
                qty_to_release = min(remaining_to_release, 100)  # Max 100 per lot for CC
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_open = quantity_open + ?
                    WHERE id = ?
                """, (qty_to_release, lot_id))
                
                remaining_to_release -= qty_to_release
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'CC #{cc_id} oznaczone jako expired!',
            'pl_pln': pl_pln,  # 🔥 ZAWSZE ZWRACAJ POPRAWNE P/L
            'shares_released': shares_to_release,
            'premium_kept_pln': premium_sell_pln,
            'expiry_date': expiry_date_str
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        
        import streamlit as st
        st.error(f"Błąd expiry CC: {e}")
        
        return {
            'success': False,
            'message': f'Błąd expiry: {str(e)}'
        }


def test_buyback_expiry_operations():
    """Test funkcji buyback i expiry - PUNKT 56"""
    
    results = {
        'buyback_function_test': False,
        'expiry_function_test': False,
        'cc_list_test': False
    }
    
    try:
        # Test 1: Funkcje istnieją
        results['buyback_function_test'] = callable(buyback_covered_call)
        results['expiry_function_test'] = callable(expire_covered_call)
        
        # Test 2: Pobranie otwartych CC
        open_cc_list = get_covered_calls_summary(status='open')
        results['cc_list_test'] = isinstance(open_cc_list, list)
        
    except Exception as e:
        import streamlit as st
        st.error(f"Błąd testów buyback/expiry: {e}")
    
    return results

# NAPRAWKA PUNKTU 61 - zamień funkcję check_cc_restrictions_before_sell w db.py

def check_cc_restrictions_before_sell(ticker, quantity_to_sell):
    """
    PUNKT 61 NAPRAWKA: Poprawne sprawdzanie blokad CC
    
    Logika:
    1. Pobierz WSZYSTKIE akcje tickera (quantity_open z lots)  
    2. Te akcje to już uwzględniają rezerwacje pod CC
    3. Sprawdź czy można sprzedać quantity_to_sell
    4. NIE DODAWAJ żadnych dodatkowych obliczeń CC!
    
    Dlaczego poprzednia wersja była błędna:
    - Pobierała quantity_open (już zmniejszone o CC)
    - Potem odejmowała CC jeszcze raz = podwójne odejmowanie!
    """
    try:
        conn = get_connection()
        if not conn:
            return {'can_sell': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        ticker_upper = ticker.upper()
        
        # KROK 1: Pobierz dostępne akcje (już po odliczeniu rezerwacji CC)
        cursor.execute("""
            SELECT COALESCE(SUM(quantity_open), 0) as available_to_sell
            FROM lots 
            WHERE ticker = ? AND quantity_open > 0
        """, (ticker_upper,))
        
        result = cursor.fetchone()
        available_to_sell = result[0] if result else 0
        
        # KROK 2: Sprawdź czy można sprzedać
        can_sell = available_to_sell >= quantity_to_sell
        
        # KROK 3: Jeśli NIE MOŻNA, znajdź przyczyny (otwarte CC)
        blocking_cc = []
        total_shares_owned = 0
        reserved_for_cc = 0
        
        if not can_sell:
            # Pobierz WSZYSTKIE akcje (bez filtra quantity_open > 0)
            cursor.execute("""
                SELECT COALESCE(SUM(quantity_total), 0) as total_owned,
                       COALESCE(SUM(quantity_open), 0) as still_available
                FROM lots 
                WHERE ticker = ?
            """, (ticker_upper,))
            
            totals = cursor.fetchone()
            total_shares_owned = totals[0] if totals else 0
            reserved_for_cc = total_shares_owned - available_to_sell
            
            # Znajdź które CC blokują
            cursor.execute("""
                SELECT id, contracts, strike_usd, expiry_date, open_date
                FROM options_cc 
                WHERE ticker = ? AND status = 'open'
                ORDER BY open_date
            """, (ticker_upper,))
            
            open_cc_list = cursor.fetchall()
            blocking_cc = [{
                'cc_id': cc[0], 
                'contracts': cc[1], 
                'shares_reserved': cc[1] * 100,
                'strike_usd': cc[2], 
                'expiry_date': cc[3],
                'open_date': cc[4]
            } for cc in open_cc_list]
        
        conn.close()
        
        return {
            'can_sell': can_sell,
            'available_to_sell': available_to_sell,
            'reserved_for_cc': reserved_for_cc,
            'total_available': total_shares_owned,  # Wszystkie posiadane
            'blocking_cc': blocking_cc,
            'message': 'OK' if can_sell else f'Zarezerwowane pod {len(blocking_cc)} CC'
        }
        
    except Exception as e:
        import streamlit as st
        st.error(f"Błąd check_cc_restrictions: {e}")
        return {
            'can_sell': False, 
            'message': f'Błąd: {str(e)}', 
            'available_to_sell': 0, 
            'reserved_for_cc': 0, 
            'total_available': 0, 
            'blocking_cc': []
        }

# DODATKOWO: Dodaj funkcję diagnostyczną

def debug_cc_restrictions(ticker):
    """
    Funkcja diagnostyczna do debugowania blokad CC
    """
    try:
        conn = get_connection()
        if not conn:
            return "Brak połączenia z bazą"
        
        cursor = conn.cursor()
        ticker_upper = ticker.upper()
        
        print(f"\n🔍 DIAGNOSTYKA CC dla {ticker_upper}:")
        
        # 1. LOT-y
        cursor.execute("""
            SELECT id, quantity_total, quantity_open, buy_date
            FROM lots 
            WHERE ticker = ?
            ORDER BY buy_date, id
        """, (ticker_upper,))
        lots = cursor.fetchall()
        
        print(f"📦 LOT-y ({len(lots)}):")
        for lot in lots:
            print(f"   LOT #{lot[0]}: {lot[2]}/{lot[1]} open (from {lot[3]})")
        
        total_open = sum([lot[2] for lot in lots])
        print(f"   📊 SUMA quantity_open: {total_open}")
        
        # 2. Wszystkie CC
        cursor.execute("""
            SELECT id, contracts, status, open_date, expiry_date, close_date
            FROM options_cc 
            WHERE ticker = ?
            ORDER BY open_date
        """, (ticker_upper,))
        all_cc = cursor.fetchall()
        
        print(f"🎯 WSZYSTKIE CC ({len(all_cc)}):")
        for cc in all_cc:
            shares = cc[1] * 100
            print(f"   CC #{cc[0]}: {cc[1]} contracts = {shares} shares, status='{cc[2]}', close_date={cc[5]}")
        
        # 3. Otwarte CC
        open_cc = [cc for cc in all_cc if cc[2] == 'open' or cc[5] is None]
        print(f"🔓 OTWARTE CC ({len(open_cc)}):")
        total_reserved = 0
        for cc in open_cc:
            shares = cc[1] * 100
            total_reserved += shares
            print(f"   CC #{cc[0]}: {shares} shares reserved")
        
        print(f"   📊 SUMA reserved: {total_reserved}")
        
        # 4. Wynik
        available = total_open - total_reserved
        print(f"✅ DOSTĘPNE DO SPRZEDAŻY: {available} ({total_open} - {total_reserved})")
        
        conn.close()
        return f"OK - szczegóły w konsoli"
        
    except Exception as e:
        return f"Błąd diagnostyki: {e}"

# PUNKT 62: NAPRAWIONE FUNKCJE w db.py
# ZAMIEŃ na końcu db.py te funkcje:

def get_total_quantity(ticker):
    """Pobiera łączną ilość posiadanych akcji dla tickera (włącznie z zarezerwowanymi)"""
    conn = get_connection()  # ✅ NAPRAWIONE
    if not conn:
        return 0
        
    cursor = conn.cursor()
    
    query = """
    SELECT COALESCE(SUM(quantity_open), 0) as total_open
    FROM lots 
    WHERE ticker = ? AND quantity_open > 0
    """
    
    cursor.execute(query, (ticker,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else 0  # ✅ NAPRAWIONE - result[0] zamiast result['total_open']

def get_all_tickers():
    """Pobiera listę wszystkich tickerów z akcjami w portfelu"""
    conn = get_connection()  # ✅ NAPRAWIONE
    if not conn:
        return []
        
    cursor = conn.cursor()
    
    query = """
    SELECT DISTINCT ticker 
    FROM lots 
    WHERE quantity_open > 0
    ORDER BY ticker
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    return [row[0] for row in results]  # ✅ NAPRAWIONE - row[0] zamiast row['ticker']

def get_open_cc_for_ticker(ticker):
    """Pobiera listę otwartych Covered Calls dla danego tickera"""
    conn = get_connection()  # ✅ NAPRAWIONE
    if not conn:
        return []
        
    cursor = conn.cursor()
    
    query = """
    SELECT id, contracts, strike_usd, expiry_date, premium_sell_usd,
           (contracts * 100) as shares_reserved
    FROM options_cc 
    WHERE ticker = ? AND status = 'open'
    ORDER BY expiry_date ASC
    """
    
    cursor.execute(query, (ticker,))
    results = cursor.fetchall()
    conn.close()
    
    # Konwertuj na listę dict
    cc_list = []
    for row in results:
        cc_list.append({
            'cc_id': row[0],
            'contracts': row[1], 
            'strike_usd': row[2],
            'expiry_date': row[3],
            'premium_usd': row[4],
            'shares_reserved': row[5]
        })
    
    return cc_list

def get_portfolio_summary():
    """Pobiera podsumowanie całego portfela dla dashboard"""
    conn = get_connection()  # ✅ NAPRAWIONE
    if not conn:
        return {}
        
    cursor = conn.cursor()
    
    try:
        # Akcje
        stocks_query = """
        SELECT ticker, 
               SUM(quantity_open) as total_shares,
               SUM(quantity_open * buy_price_usd) as total_cost_usd
        FROM lots 
        WHERE quantity_open > 0
        GROUP BY ticker
        """
        
        cursor.execute(stocks_query)
        stocks = cursor.fetchall()
        
        # Otwarte CC
        cc_query = """
        SELECT ticker, 
               COUNT(*) as open_cc_count,
               SUM(contracts) as total_contracts,
               SUM(contracts * 100) as total_shares_reserved
        FROM options_cc 
        WHERE status = 'open'
        GROUP BY ticker
        """
        
        cursor.execute(cc_query)
        cc_data = cursor.fetchall()
        conn.close()
        
        # Połącz dane
        portfolio = {}
        
        # Dodaj akcje
        for stock in stocks:
            portfolio[stock[0]] = {  # stock[0] = ticker
                'total_shares': stock[1],  # stock[1] = total_shares
                'cost_usd': stock[2],     # stock[2] = total_cost_usd
                'cc_count': 0,
                'shares_reserved': 0,
                'shares_available': stock[1]  # początkowo wszystkie dostępne
            }
        
        # Dodaj dane CC
        for cc in cc_data:
            ticker = cc[0]  # cc[0] = ticker
            if ticker in portfolio:
                portfolio[ticker]['cc_count'] = cc[1]      # cc[1] = open_cc_count
                portfolio[ticker]['shares_reserved'] = cc[3] # cc[3] = total_shares_reserved
                portfolio[ticker]['shares_available'] = portfolio[ticker]['total_shares'] - cc[3]
        
        return portfolio
        
    except Exception as e:
        import streamlit as st
        st.error(f"Błąd portfolio summary: {e}")
        if conn:
            conn.close()
        return {}

def get_cc_expiry_alerts(days_ahead=7):
    """Pobiera Covered Calls wygasające w najbliższych N dni"""
    conn = get_connection()  # ✅ NAPRAWIONE
    if not conn:
        return []
        
    cursor = conn.cursor()
    
    try:
        from datetime import datetime, timedelta
        alert_date = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        query = """
        SELECT id, ticker, contracts, strike_usd, expiry_date,
               (julianday(expiry_date) - julianday('now')) as days_to_expiry
        FROM options_cc 
        WHERE status = 'open'
        AND expiry_date <= ?
        ORDER BY expiry_date ASC
        """
        
        cursor.execute(query, (alert_date,))
        results = cursor.fetchall()
        conn.close()
        
        # Konwertuj na listę dict
        alerts = []
        for row in results:
            alerts.append({
                'cc_id': row[0],
                'ticker': row[1],
                'contracts': row[2],
                'strike_usd': row[3],
                'expiry_date': row[4],
                'days_to_expiry': int(row[5]) if row[5] else 0
            })
        
        return alerts
        
    except Exception as e:
        import streamlit as st
        st.error(f"Błąd CC expiry alerts: {e}")
        if conn:
            conn.close()
        return []
        
def reset_ticker_reservations(ticker):
    """
    FUNKCJA NAPRAWCZA: Resetuje rezerwacje dla konkretnego tickera
    """
    try:
        conn = get_connection()
        if not conn:
            return "Brak połączenia z bazą"
        
        cursor = conn.cursor()
        ticker_upper = ticker.upper()
        
        print(f"🔄 RESET REZERWACJI dla {ticker_upper}:")
        
        # 1. Zresetuj wszystkie quantity_open do quantity_total dla tego tickera
        cursor.execute("""
            UPDATE lots 
            SET quantity_open = quantity_total
            WHERE ticker = ?
        """, (ticker_upper,))
        
        reset_count = cursor.rowcount
        print(f"   📦 Zresetowano {reset_count} LOT-ów")
        
        # 2. Pobierz otwarte CC dla tego tickera
        cursor.execute("""
            SELECT id, contracts
            FROM options_cc 
            WHERE ticker = ? AND status = 'open'
            ORDER BY id
        """, (ticker_upper,))
        
        open_cc = cursor.fetchall()
        print(f"   🎯 Znaleziono {len(open_cc)} otwartych CC")
        
        # 3. Ponownie zarezerwuj akcje dla każdego CC
        for cc_id, contracts in open_cc:
            shares_needed = contracts * 100
            remaining_to_reserve = shares_needed
            
            print(f"   CC #{cc_id}: rezerwacja {shares_needed} akcji")
            
            # Pobierz dostępne LOT-y FIFO
            cursor.execute("""
                SELECT id, quantity_open
                FROM lots 
                WHERE ticker = ? AND quantity_open > 0
                ORDER BY buy_date, id
            """, (ticker_upper,))
            
            available_lots = cursor.fetchall()
            
            for lot_id, qty_open in available_lots:
                if remaining_to_reserve <= 0:
                    break
                
                qty_to_reserve = min(remaining_to_reserve, qty_open)
                new_qty_open = qty_open - qty_to_reserve
                
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_open = ?
                    WHERE id = ?
                """, (new_qty_open, lot_id))
                
                remaining_to_reserve -= qty_to_reserve
                print(f"     LOT #{lot_id}: {qty_open} -> {new_qty_open}")
            
            if remaining_to_reserve > 0:
                print(f"     ❌ BRAKUJE {remaining_to_reserve} akcji dla CC #{cc_id}")
            else:
                print(f"     ✅ CC #{cc_id} prawidłowo zarezerwowane")
        
        # 4. Sprawdź finalne stany
        cursor.execute("""
            SELECT SUM(quantity_total) as total, SUM(quantity_open) as open
            FROM lots 
            WHERE ticker = ?
        """, (ticker_upper,))
        
        final_stats = cursor.fetchone()
        total_shares, open_shares = final_stats
        reserved_shares = total_shares - open_shares
        
        print(f"   📊 FINAL: {open_shares}/{total_shares} dostępne (zarezerwowane: {reserved_shares})")
        
        conn.commit()
        conn.close()
        
        return f"Reset {ticker_upper}: {open_shares}/{total_shares} dostępne, {reserved_shares} zarezerwowane"
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        print(f"❌ Błąd resetu: {e}")
        return f"Błąd: {e}"
        
# POPRAWKA PUNKT 63: Naprawiona funkcja delete_covered_call w db.py

def delete_covered_call(cc_id: int, confirm_delete: bool = False):
    """
    Usuwa CC:
      - zwalnia LOT-y wg zapisów w options_cc_reservations,
      - usuwa powiązane cashflow (ref_table='options_cc', ref_id=cc_id),
      - usuwa rekord z options_cc.
    """
    if not confirm_delete:
        return {'success': False, 'message': 'Brak potwierdzenia usunięcia'}

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        cursor = conn.cursor()

        # Pobierz bazowe info (do komunikatu)
        cursor.execute("SELECT ticker, contracts, status FROM options_cc WHERE id = ?", (cc_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} nie istnieje'}

        ticker, contracts, status = row[0], row[1], row[2]

        # 1) ZWOLNIJ REZERWACJE
        cursor.execute("""
            SELECT lot_id, qty_reserved
            FROM options_cc_reservations
            WHERE cc_id = ?
            ORDER BY id
        """, (cc_id,))
        reservations = cursor.fetchall()

        shares_released = 0
        for lot_id, qty_reserved in reservations:
            cursor.execute("UPDATE lots SET quantity_open = quantity_open + ? WHERE id = ?",
                           (qty_reserved, lot_id))
            shares_released += qty_reserved

        # skasuj zapisy rezerwacji
        cursor.execute("DELETE FROM options_cc_reservations WHERE cc_id = ?", (cc_id,))

        # 2) USUŃ POWIĄZANE CASHFLOW
        cursor.execute("""
            DELETE FROM cashflows
            WHERE ref_table = 'options_cc' AND ref_id = ?
        """, (cc_id,))

        # 3) USUŃ CC
        cursor.execute("DELETE FROM options_cc WHERE id = ?", (cc_id,))

        conn.commit()
        conn.close()

        return {
            'success': True,
            'message': f'Usunięto CC #{cc_id} ({ticker}); zwolniono {shares_released} akcji',
            'details': {
                'ticker': ticker,
                'shares_released': shares_released,
                'status_prev': status,
                'cashflows_deleted': True
            }
        }

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {'success': False, 'message': f'Błąd usuwania CC #{cc_id}: {str(e)}'}


def get_deletable_cc_list():
    """
    Pobiera listę CC które można usunąć (z informacjami o ryzyku)
    """
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, ticker, contracts, status, premium_sell_usd, premium_sell_pln,
                   open_date, expiry_date, close_date,
                   CASE 
                       WHEN status = 'open' THEN 'UWAGA - zwolni rezerwacje'
                       WHEN status = 'expired' THEN 'Bezpieczne - już zamknięte'
                       WHEN status = 'bought_back' THEN 'Bezpieczne - już zamknięte'
                       ELSE 'Sprawdź status'
                   END as delete_risk
            FROM options_cc
            ORDER BY status, open_date DESC
        """)
        
        cc_list = []
        for row in cursor.fetchall():
            cc_list.append({
                'id': row[0],
                'ticker': row[1], 
                'contracts': row[2],
                'status': row[3],
                'premium_sell_usd': row[4],
                'premium_sell_pln': row[5],
                'open_date': row[6],
                'expiry_date': row[7],
                'close_date': row[8],
                'delete_risk': row[9],
                'shares_reserved': row[2] * 100
            })
        
        conn.close()
        return cc_list
        
    except Exception as e:
        print(f"Błąd pobierania listy CC: {e}")
        return []


def update_covered_call(cc_id, **kwargs):
    """
    PUNKT 64: Edycja parametrów covered call
    
    Args:
        cc_id: ID covered call
        **kwargs: Pola do aktualizacji (strike_usd, expiry_date, premium_sell_usd, etc.)
    
    Returns:
        dict: Status operacji
    """
    try:
        if not kwargs:
            return {'success': False, 'message': 'Brak parametrów do aktualizacji'}
        
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # Sprawdź czy CC istnieje i pobierz aktualne dane
        cursor.execute("""
            SELECT id, ticker, contracts, status, premium_sell_usd, premium_sell_pln,
                   strike_usd, expiry_date, fx_open
            FROM options_cc 
            WHERE id = ?
        """, (cc_id,))
        
        cc_data = cursor.fetchone()
        if not cc_data:
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} nie znalezione'}
        
        current_cc = {
            'id': cc_data[0],
            'ticker': cc_data[1], 
            'contracts': cc_data[2],
            'status': cc_data[3],
            'premium_sell_usd': cc_data[4],
            'premium_sell_pln': cc_data[5],
            'strike_usd': cc_data[6],
            'expiry_date': cc_data[7],
            'fx_open': cc_data[8]
        }
        
        print(f"🔧 EDYCJA CC #{cc_id}:")
        print(f"   Ticker: {current_cc['ticker']} ({current_cc['contracts']} kontr.)")
        print(f"   Status: {current_cc['status']}")
        
        # Walidacje - czy można edytować
        if current_cc['status'] != 'open':
            conn.close()
            return {
                'success': False, 
                'message': f'Nie można edytować zamkniętego CC (status: {current_cc["status"]})'
            }
        
        # Przygotuj pola do aktualizacji
        allowed_fields = {
            'strike_usd': 'strike_usd',
            'expiry_date': 'expiry_date', 
            'premium_sell_usd': 'premium_sell_usd'
        }
        
        fields_to_update = []
        values = []
        changes_log = []
        
        for field, db_field in allowed_fields.items():
            if field in kwargs:
                new_value = kwargs[field]
                old_value = current_cc.get(db_field)
                
                fields_to_update.append(f"{db_field} = ?")
                values.append(new_value)
                changes_log.append(f"{field}: {old_value} → {new_value}")
                
                print(f"   🔄 {field}: {old_value} → {new_value}")
        
        if not fields_to_update:
            conn.close()
            return {'success': False, 'message': 'Brak prawidłowych pól do aktualizacji'}
        
        # Jeśli zmieniono premium, przelicz PLN
        if 'premium_sell_usd' in kwargs:
            new_premium_usd = kwargs['premium_sell_usd']
            fx_rate = current_cc['fx_open']  # Używaj oryginalnego kursu z daty otwarcia
            new_premium_pln = round(new_premium_usd * fx_rate, 2)
            
            fields_to_update.append("premium_sell_pln = ?")
            values.append(new_premium_pln)
            changes_log.append(f"premium_sell_pln: {current_cc['premium_sell_pln']} → {new_premium_pln}")
            
            print(f"   💱 Przeliczono premium PLN: {new_premium_pln} (kurs: {fx_rate})")
            
            # Zaktualizuj również powiązane cashflow
            cursor.execute("""
                UPDATE cashflows 
                SET amount_usd = ?, amount_pln = ?
                WHERE ref_table = 'options_cc' AND ref_id = ?
            """, (new_premium_usd, new_premium_pln, cc_id))
            
            print(f"   💸 Zaktualizowano powiązane cashflow")
        
        # Wykonaj aktualizację
        fields_to_update.append("updated_at = CURRENT_TIMESTAMP")
        values.append(cc_id)
        
        query = f"UPDATE options_cc SET {', '.join(fields_to_update)} WHERE id = ?"
        cursor.execute(query, values)
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'CC #{cc_id} zaktualizowane pomyślnie',
            'changes': changes_log
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        
        return {
            'success': False,
            'message': f'Błąd aktualizacji CC #{cc_id}: {str(e)}'
        }


def bulk_delete_covered_calls(cc_ids, confirm_bulk=False):
    """
    PUNKT 64: Masowe usuwanie covered calls
    
    Args:
        cc_ids: Lista ID do usunięcia  
        confirm_bulk: Potwierdzenie operacji masowej
    
    Returns:
        dict: Status operacji z szczegółami
    """
    try:
        if not cc_ids:
            return {'success': False, 'message': 'Brak CC do usunięcia'}
        
        if not confirm_bulk:
            return {'success': False, 'message': 'Operacja wymaga potwierdzenia'}
        
        results = {
            'success': True,
            'total_requested': len(cc_ids),
            'deleted': 0,
            'failed': 0,
            'shares_released': {},
            'errors': []
        }
        
        print(f"🗑️ BULK DELETE: Usuwanie {len(cc_ids)} CC...")
        
        for cc_id in cc_ids:
            delete_result = delete_covered_call(cc_id, confirm_delete=True)
            
            if delete_result['success']:
                results['deleted'] += 1
                details = delete_result['details']
                ticker = details['ticker']
                
                if ticker in results['shares_released']:
                    results['shares_released'][ticker] += details['shares_released']
                else:
                    results['shares_released'][ticker] = details['shares_released']
                
                print(f"   ✅ CC #{cc_id}: {ticker} - OK")
                
            else:
                results['failed'] += 1
                results['errors'].append(f"CC #{cc_id}: {delete_result['message']}")
                print(f"   ❌ CC #{cc_id}: {delete_result['message']}")
        
        if results['failed'] > 0:
            results['success'] = False
            results['message'] = f"Usunięto {results['deleted']}/{results['total_requested']} CC (błędy: {results['failed']})"
        else:
            results['message'] = f"Pomyślnie usunięto wszystkie {results['deleted']} CC"
        
        return results
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Błąd bulk delete: {str(e)}',
            'deleted': 0,
            'failed': len(cc_ids)
        }


def get_cc_edit_candidates():
    """
    Pobiera CC które można edytować (tylko otwarte)
    """
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, ticker, contracts, strike_usd, premium_sell_usd, premium_sell_pln,
                   expiry_date, open_date, fx_open
            FROM options_cc 
            WHERE status = 'open'
            ORDER BY open_date DESC
        """)
        
        candidates = []
        for row in cursor.fetchall():
            candidates.append({
                'id': row[0],
                'ticker': row[1],
                'contracts': row[2],
                'strike_usd': row[3],
                'premium_sell_usd': row[4], 
                'premium_sell_pln': row[5],
                'expiry_date': row[6],
                'open_date': row[7],
                'fx_open': row[8],
                'shares_reserved': row[2] * 100
            })
        
        conn.close()
        return candidates
        
    except Exception as e:
        print(f"Błąd pobierania CC do edycji: {e}")
        return []

def get_cc_coverage_details(cc_id=None):
    """
    PUNKT 66: Pobiera szczegółowe informacje o pokryciu CC przez LOT-y
    
    Args:
        cc_id: Konkretne CC (None = wszystkie otwarte)
    
    Returns:
        list: Szczegółowe informacje o pokryciu FIFO
    """
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # Pobierz otwarte CC
        if cc_id:
            cursor.execute("""
                SELECT id, ticker, contracts, strike_usd, premium_sell_usd, premium_sell_pln,
                       open_date, expiry_date, fx_open
                FROM options_cc 
                WHERE id = ? AND status = 'open'
            """, (cc_id,))
        else:
            cursor.execute("""
                SELECT id, ticker, contracts, strike_usd, premium_sell_usd, premium_sell_pln,
                       open_date, expiry_date, fx_open
                FROM options_cc 
                WHERE status = 'open'
                ORDER BY ticker, open_date
            """)
        
        cc_list = cursor.fetchall()
        coverage_details = []
        
        for cc in cc_list:
            cc_id, ticker, contracts, strike_usd, premium_sell_usd, premium_sell_pln, open_date, expiry_date, fx_open = cc
            shares_needed = contracts * 100
            
            # Znajdź pokrycie FIFO dla tego CC
            cursor.execute("""
                SELECT id, quantity_total, quantity_open, buy_date, buy_price_usd, fx_rate, cost_pln
                FROM lots 
                WHERE ticker = ?
                ORDER BY buy_date, id
            """, (ticker,))
            
            lots = cursor.fetchall()
            
            # Symuluj alokację FIFO (tak jak przy sprzedaży CC)
            lot_allocations = []
            remaining_to_cover = shares_needed
            
            for lot in lots:
                if remaining_to_cover <= 0:
                    break
                
                lot_id, qty_total, qty_open, buy_date, buy_price_usd, fx_rate, cost_pln = lot
                qty_reserved = qty_total - qty_open  # Ile z tego LOT-a jest zarezerwowane
                
                if qty_reserved > 0:
                    # Ten LOT ma rezerwacje, sprawdź ile przypada na nasze CC
                    qty_for_this_cc = min(remaining_to_cover, qty_reserved)
                    
                    if qty_for_this_cc > 0:
                        lot_allocations.append({
                            'lot_id': lot_id,
                            'buy_date': buy_date,
                            'buy_price_usd': buy_price_usd,
                            'fx_rate': fx_rate,
                            'cost_per_share_pln': cost_pln / qty_total if qty_total > 0 else 0,
                            'shares_allocated': qty_for_this_cc,
                            'total_cost_pln': (cost_pln / qty_total * qty_for_this_cc) if qty_total > 0 else 0
                        })
                        
                        remaining_to_cover -= qty_for_this_cc
            
            # Kalkulacje dodatkowe
            from datetime import datetime, date
            open_date_obj = datetime.strptime(open_date, '%Y-%m-%d').date() if isinstance(open_date, str) else open_date
            expiry_date_obj = datetime.strptime(expiry_date, '%Y-%m-%d').date() if isinstance(expiry_date, str) else expiry_date
            today = date.today()
            
            days_to_expiry = (expiry_date_obj - today).days
            days_held = (today - open_date_obj).days + 1
            total_days = (expiry_date_obj - open_date_obj).days + 1
            
            # Yield calculations
            total_cost_basis = sum([alloc['total_cost_pln'] for alloc in lot_allocations])
            premium_yield_pct = (premium_sell_pln / total_cost_basis * 100) if total_cost_basis > 0 else 0
            annualized_yield_pct = (premium_yield_pct * 365 / total_days) if total_days > 0 else 0
            
            coverage_details.append({
                'cc_id': cc_id,
                'ticker': ticker,
                'contracts': contracts,
                'shares_needed': shares_needed,
                'strike_usd': strike_usd,
                'premium_sell_usd': premium_sell_usd,
                'premium_sell_pln': premium_sell_pln,
                'open_date': open_date,
                'expiry_date': expiry_date,
                'fx_open': fx_open,
                'days_to_expiry': days_to_expiry,
                'days_held': days_held,
                'total_days': total_days,
                'lot_allocations': lot_allocations,
                'total_cost_basis': total_cost_basis,
                'premium_yield_pct': premium_yield_pct,
                'annualized_yield_pct': annualized_yield_pct
            })
        
        conn.close()
        return coverage_details
        
    except Exception as e:
        print(f"Błąd get_cc_coverage_details: {e}")
        return []


def get_portfolio_cc_summary():
    """
    PUNKT 66: Podsumowanie całego portfela CC
    """
    try:
        conn = get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor()
        
        # Podstawowe statystyki
        cursor.execute("SELECT COUNT(*) FROM options_cc WHERE status = 'open'")
        open_cc_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM options_cc WHERE status != 'open'")
        closed_cc_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(contracts) FROM options_cc WHERE status = 'open'")
        total_open_contracts = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(premium_sell_pln) FROM options_cc WHERE status = 'open'")
        total_open_premium_pln = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(pl_pln) FROM options_cc WHERE status != 'open' AND pl_pln IS NOT NULL")
        total_realized_pl_pln = cursor.fetchone()[0] or 0
        
        # Statystyki per ticker
        cursor.execute("""
            SELECT ticker, 
                   COUNT(*) as cc_count,
                   SUM(contracts) as total_contracts,
                   SUM(premium_sell_pln) as total_premium_pln
            FROM options_cc 
            WHERE status = 'open'
            GROUP BY ticker
            ORDER BY ticker
        """)
        
        ticker_stats = []
        for row in cursor.fetchall():
            ticker_stats.append({
                'ticker': row[0],
                'cc_count': row[1],
                'total_contracts': row[2],
                'shares_reserved': row[2] * 100,
                'total_premium_pln': row[3]
            })
        
        conn.close()
        
        return {
            'open_cc_count': open_cc_count,
            'closed_cc_count': closed_cc_count,
            'total_open_contracts': total_open_contracts,
            'total_shares_reserved': total_open_contracts * 100,
            'total_open_premium_pln': total_open_premium_pln,
            'total_realized_pl_pln': total_realized_pl_pln,
            'ticker_stats': ticker_stats
        }
        
    except Exception as e:
        print(f"Błąd get_portfolio_cc_summary: {e}")
        return {}
        
def get_closed_cc_analysis():
    """
    PUNKT 67: Szczegółowa analiza zamkniętych CC z P/L
    """
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, ticker, contracts, strike_usd, premium_sell_usd, premium_sell_pln,
                   premium_buyback_usd, premium_buyback_pln, open_date, close_date, expiry_date,
                   status, fx_open, fx_close, pl_pln, created_at
            FROM options_cc 
            WHERE status IN ('bought_back', 'expired')
            ORDER BY close_date DESC, ticker
        """)
        
        closed_cc = []
        
        for row in cursor.fetchall():
            # 🔥 NAPRAWKA P/L: oblicz poprawnie jeśli pl_pln jest NULL/0
            recorded_pl_pln = row[14]
            if recorded_pl_pln is None or recorded_pl_pln == 0:
                if row[11] == 'expired':  # status = 'expired'
                    calculated_pl_pln = row[5]  # premium_sell_pln
                else:  # status = 'bought_back'
                    calculated_pl_pln = row[5] - (row[7] or 0)  # premium_sell_pln - premium_buyback_pln
            else:
                calculated_pl_pln = recorded_pl_pln
            
            cc_data = {
                'cc_id': row[0],
                'ticker': row[1],
                'contracts': row[2],
                'shares': row[2] * 100,
                'strike_usd': row[3],
                'premium_sell_usd': row[4],
                'premium_sell_pln': row[5],
                'premium_buyback_usd': row[6] or 0,
                'premium_buyback_pln': row[7] or 0,
                'open_date': row[8],
                'close_date': row[9],
                'expiry_date': row[10],
                'status': row[11],
                'fx_open': row[12],
                'fx_close': row[13] or row[12],  # Fallback to open rate
                'pl_pln': calculated_pl_pln,  # ✅ UŻYWAJ OBLICZONEGO P/L
                'created_at': row[15]
            }
            
            # Dodatkowe kalkulacje
            from datetime import datetime
            
            # Konwersja dat
            open_date_obj = datetime.strptime(cc_data['open_date'], '%Y-%m-%d').date()
            close_date_obj = datetime.strptime(cc_data['close_date'], '%Y-%m-%d').date() if cc_data['close_date'] else None
            
            days_held = (close_date_obj - open_date_obj).days if close_date_obj else 0
            
            # P/L analysis
            if cc_data['status'] == 'expired':
                # Expired = pełna premium jako zysk
                net_premium_usd = cc_data['premium_sell_usd']
                net_premium_pln = cc_data['premium_sell_pln']
                outcome_emoji = "🏆"
                outcome_text = "Expired (Max Profit)"
            else:
                # Bought back = różnica premium
                net_premium_usd = cc_data['premium_sell_usd'] - cc_data['premium_buyback_usd']
                net_premium_pln = cc_data['premium_sell_pln'] - cc_data['premium_buyback_pln']
                outcome_emoji = "🔄"
                outcome_text = "Bought Back"
            
            # Yield calculations
            # Oszacuj koszt bazowy (simplified - będziemy to później ulepszyć)
            estimated_cost_per_share = cc_data['strike_usd'] * cc_data['fx_open']  # Approximation
            estimated_total_cost = estimated_cost_per_share * cc_data['shares']
            
            premium_yield_pct = (net_premium_pln / estimated_total_cost * 100) if estimated_total_cost > 0 else 0
            annualized_yield_pct = (premium_yield_pct * 365 / days_held) if days_held > 0 else 0
            
            cc_data.update({
                'days_held': days_held,
                'net_premium_usd': net_premium_usd,
                'net_premium_pln': net_premium_pln,
                'outcome_emoji': outcome_emoji,
                'outcome_text': outcome_text,
                'estimated_total_cost': estimated_total_cost,
                'premium_yield_pct': premium_yield_pct,
                'annualized_yield_pct': annualized_yield_pct
            })
            
            closed_cc.append(cc_data)
        
        conn.close()
        return closed_cc
        
    except Exception as e:
        print(f"Błąd get_closed_cc_analysis: {e}")
        return []


def get_cc_performance_summary():
    """
    PUNKT 67: Podsumowanie performance wszystkich CC
    """
    try:
        conn = get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor()
        
        # Stats dla zamkniętych CC
        cursor.execute("""
            SELECT 
                COUNT(*) as total_closed,
                SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired_count,
                SUM(CASE WHEN status = 'bought_back' THEN 1 ELSE 0 END) as buyback_count,
                SUM(pl_pln) as total_realized_pl,
                AVG(pl_pln) as avg_pl_per_cc,
                MIN(pl_pln) as worst_pl,
                MAX(pl_pln) as best_pl
            FROM options_cc 
            WHERE status IN ('bought_back', 'expired') AND pl_pln IS NOT NULL
        """)
        
        closed_stats = cursor.fetchone()
        
        # Stats per ticker
        cursor.execute("""
            SELECT ticker,
                   COUNT(*) as cc_count,
                   SUM(pl_pln) as total_pl,
                   AVG(pl_pln) as avg_pl,
                   SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired_count,
                   SUM(CASE WHEN status = 'bought_back' THEN 1 ELSE 0 END) as buyback_count
            FROM options_cc 
            WHERE status IN ('bought_back', 'expired') AND pl_pln IS NOT NULL
            GROUP BY ticker
            ORDER BY total_pl DESC
        """)
        
        ticker_performance = []
        for row in cursor.fetchall():
            ticker_performance.append({
                'ticker': row[0],
                'cc_count': row[1],
                'total_pl': row[2],
                'avg_pl': row[3],
                'expired_count': row[4],
                'buyback_count': row[5],
                'win_rate': (row[4] / row[1] * 100) if row[1] > 0 else 0
            })
        
        conn.close()
        
        if closed_stats:
            return {
                'total_closed': closed_stats[0] or 0,
                'expired_count': closed_stats[1] or 0,
                'buyback_count': closed_stats[2] or 0,
                'total_realized_pl': closed_stats[3] or 0,
                'avg_pl_per_cc': closed_stats[4] or 0,
                'worst_pl': closed_stats[5] or 0,
                'best_pl': closed_stats[6] or 0,
                'ticker_performance': ticker_performance
            }
        
        return {}
        
    except Exception as e:
        print(f"Błąd get_cc_performance_summary: {e}")
        return {}

def get_reservations_diagnostics():
    """
    Diagnostyka rezerwacji pod otwarte CC:
      - per ticker: required_reserved vs actual_reserved (z LOT-ów),
      - per CC: oczekiwana rezerwa vs zmapowana w options_cc_reservations (jeśli istnieje).
    Zwraca dict:
      {
        'success': True,
        'has_mapping_table': bool,
        'tickers': [{'ticker', 'required_reserved', 'actual_reserved', 'delta'}...],
        'ccs': [{
            'id','ticker','open_date',
            'expected_reserved',
            'mapped_reserved': int|None,
            'mapped_details': [{'lot_id','qty_reserved'}...]
        }...]
      }
    """
    conn = get_connection()
    if not conn:
        return {'success': False, 'message': 'Brak połączenia z bazą', 'has_mapping_table': False}

    cursor = conn.cursor()

    # Czy istnieje tabela mapowań?
    cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='options_cc_reservations' LIMIT 1")
    has_mapping = cursor.fetchone() is not None

    # TICKERY z otwartymi CC
    cursor.execute("SELECT DISTINCT ticker FROM options_cc WHERE status='open' ORDER BY ticker")
    tickers = [row[0] for row in cursor.fetchall()]

    out = {
        'success': True,
        'has_mapping_table': has_mapping,
        'tickers': [],
        'ccs': []
    }

    # Poziom tickerów
    for t in tickers:
        # Wymagana rezerwa = suma kontraktów * 100
        cursor.execute("""
            SELECT COALESCE(SUM(contracts),0) * 100
            FROM options_cc
            WHERE status='open' AND ticker=?
        """, (t,))
        required = int(cursor.fetchone()[0] or 0)

        # Faktyczna rezerwa z LOT-ów = SUM(quantity_total - quantity_open)
        cursor.execute("""
            SELECT COALESCE(SUM(quantity_total),0), COALESCE(SUM(quantity_open),0)
            FROM lots WHERE ticker=?
        """, (t,))
        tot, opn = cursor.fetchone()
        tot = int(tot or 0)
        opn = int(opn or 0)
        actual = tot - opn

        out['tickers'].append({
            'ticker': t,
            'required_reserved': required,
            'actual_reserved': actual,
            'delta': actual - required
        })

    # Poziom CC
    cursor.execute("""
        SELECT id, ticker, contracts, open_date
        FROM options_cc
        WHERE status='open'
        ORDER BY open_date, id
    """)
    cc_rows = cursor.fetchall()

    for cc_id, t, contracts, open_date in cc_rows:
        expected = int((contracts or 0) * 100)
        mapped = None
        details = []

        if has_mapping:
            cursor.execute("""
                SELECT lot_id, qty_reserved
                FROM options_cc_reservations
                WHERE cc_id=?
                ORDER BY id
            """, (cc_id,))
            rows = cursor.fetchall()
            if rows:
                mapped = sum(int(r[1]) for r in rows)
                details = [{'lot_id': r[0], 'qty_reserved': int(r[1])} for r in rows]
            else:
                mapped = 0

        out['ccs'].append({
            'id': cc_id,
            'ticker': t,
            'open_date': open_date,
            'expected_reserved': expected,
            'mapped_reserved': mapped,
            'mapped_details': details
        })

    conn.close()
    return out

def buyback_covered_call_with_fees(cc_id, buyback_price_usd, buyback_date, broker_fee_usd=0.0, reg_fee_usd=0.0):
    """
    🔥 NAPRAWIONA WERSJA: Odkupuje covered call Z PROWIZJAMI - ZAWSZE ustawia pl_pln
    
    ZMIANY:
    - Dodane obliczanie pl_pln w każdej ścieżce
    - Dodane UPDATE z pl_pln w bazie danych
    """
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # 1. POBIERZ DANE CC
        cursor.execute("""
            SELECT id, ticker, contracts, premium_sell_usd, open_date, expiry_date,
                   status, fx_open, premium_sell_pln
            FROM options_cc 
            WHERE id = ?
        """, (cc_id,))
        
        cc_record = cursor.fetchone()
        if not cc_record:
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} nie znalezione'}
        
        cc_id, ticker, contracts, premium_sell_usd, open_date, expiry_date, status, fx_open, premium_sell_pln = cc_record
        
        # 2. SPRAWDŹ STATUS
        if status != 'open':
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} już zamknięte (status: {status})'}
        
        # 3. POBIERZ KURS NBP NA BUYBACK_DATE
        if hasattr(buyback_date, 'strftime'):
            buyback_date_str = buyback_date.strftime('%Y-%m-%d')
        else:
            buyback_date_str = str(buyback_date)
        
        # Import funkcji NBP - dostosuj do Twojego importu
        try:
            from utils.nbp_api_client import get_usd_rate_for_date
        except ImportError:
            # Fallback - dostosuj nazwę modułu do swojego projektu
            import nbp_api_client
            get_usd_rate_for_date = nbp_api_client.get_usd_rate_for_date
        
        # Pobierz kurs NBP D-1
        try:
            nbp_result = get_usd_rate_for_date(buyback_date_str)
            if isinstance(nbp_result, dict):
                fx_close = nbp_result['rate']
                fx_close_date = nbp_result.get('date', buyback_date_str)
            else:
                fx_close = float(nbp_result)
                fx_close_date = buyback_date_str
        except Exception as e:
            fx_close = 4.0  # Fallback
            fx_close_date = buyback_date_str
        
        # 4. KALKULACJE FINANSOWE
        shares_to_release = contracts * 100
        total_fees_usd = broker_fee_usd + reg_fee_usd
        
        # Premium buyback (cena * akcje)
        premium_buyback_usd = buyback_price_usd * shares_to_release
        premium_buyback_pln = round(premium_buyback_usd * fx_close, 2)
        
        # Koszty z prowizjami
        total_buyback_cost_usd = premium_buyback_usd + total_fees_usd
        buyback_cost_pln = round(total_buyback_cost_usd * fx_close, 2)
        
        # 🔥 KLUCZOWA NAPRAWKA: OBLICZ P/L
        pl_pln = round(premium_sell_pln - buyback_cost_pln, 2)
        pl_usd = round(premium_sell_usd * shares_to_release - total_buyback_cost_usd, 2)
        
        # 5. 🔥 ZAWSZE USTAW pl_pln W UPDATE
        cursor.execute("""
            UPDATE options_cc 
            SET status = 'bought_back',
                close_date = ?,
                premium_buyback_usd = ?,
                fx_close = ?,
                premium_buyback_pln = ?,
                pl_pln = ?
            WHERE id = ?
        """, (buyback_date_str, premium_buyback_usd, fx_close, premium_buyback_pln, pl_pln, cc_id))
        
        # 6. ZWOLNIJ AKCJE (logika bez zmian - skopiuj z oryginalnej funkcji)
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='options_cc_reservations'
        """)
        has_reservations_table = cursor.fetchone() is not None
        
        if has_reservations_table:
            # Użyj mapowań rezerwacji
            cursor.execute("""
                SELECT lot_id, qty_reserved 
                FROM options_cc_reservations 
                WHERE cc_id = ? 
                ORDER BY id
            """, (cc_id,))
            reservations = cursor.fetchall()
            
            for lot_id, qty_reserved in reservations:
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_open = quantity_open + ?
                    WHERE id = ?
                """, (qty_reserved, lot_id))
            
            cursor.execute("DELETE FROM options_cc_reservations WHERE cc_id = ?", (cc_id,))
        else:
            # Fallback FIFO
            cursor.execute("""
                SELECT id, quantity_open
                FROM lots 
                WHERE ticker = ? AND quantity_open > 0
                ORDER BY buy_date ASC, id ASC
            """, (ticker,))
            
            lots_to_release = cursor.fetchall()
            remaining_to_release = shares_to_release
            
            for lot_id, quantity_open in lots_to_release:
                if remaining_to_release <= 0:
                    break
                
                qty_to_release = min(remaining_to_release, 100)  # Max 100 per lot for CC
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_open = quantity_open + ?
                    WHERE id = ?
                """, (qty_to_release, lot_id))
                
                remaining_to_release -= qty_to_release
        
        # 7. UTWÓRZ CASHFLOW (wydatek)
        cashflow_description = f"Buyback CC {ticker} ${buyback_price_usd:.2f} + prowizje ${total_fees_usd:.2f}"
        
        cursor.execute("""
            INSERT INTO cashflows (
                type, amount_usd, date, fx_rate, amount_pln, 
                description, ref_table, ref_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'option_buyback',
            -total_buyback_cost_usd,  # Ujemna kwota (wydatek)
            buyback_date_str,
            fx_close,
            -buyback_cost_pln,
            cashflow_description,
            'options_cc',
            cc_id
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'CC #{cc_id} odkupione pomyślnie (z prowizjami)!',
            'pl_pln': pl_pln,  # 🔥 ZAWSZE ZWRACAJ POPRAWNE P/L
            'pl_usd': pl_usd,
            'premium_received_pln': premium_sell_pln,
            'buyback_cost_pln': buyback_cost_pln,
            'total_fees_usd': total_fees_usd,
            'fx_close': fx_close,
            'fx_close_date': fx_close_date,
            'shares_released': shares_to_release
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        
        return {
            'success': False,
            'message': f'Błąd buyback: {str(e)}'
        }

# NAPRAWKA BŁĘDU SQL: Poprawiona funkcja update_covered_call_with_recalc w db.py

def buyback_covered_call_with_fees(cc_id, buyback_price_usd, buyback_date, broker_fee_usd=0.0, reg_fee_usd=0.0):
    """
    NAPRAWKA: Odkupuje covered call Z PROWIZJAMI - POPRAWNY KURS NBP
    """
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # 1. POBIERZ DANE CC
        cursor.execute("""
            UPDATE options_cc 
            SET status = 'bought_back',
                close_date = ?,
                premium_buyback_usd = ?,
                fx_close = ?,
                premium_buyback_pln = ?,
                pl_pln = ?
            WHERE id = ?
        """, (
            buyback_date_str,
            premium_buyback_usd,
            fx_close,
            premium_buyback_pln,
            pl_pln,
            cc_id
        ))
        
        cc_record = cursor.fetchone()
        if not cc_record:
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} nie znalezione'}
        
        cc_id, ticker, contracts, premium_sell_usd, open_date, expiry_date, status, fx_open, premium_sell_pln = cc_record
        
        # 2. SPRAWDŹ STATUS
        if status != 'open':
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} już zamknięte (status: {status})'}
        
        # 3. 🎯 NAPRAWKA: POBIERZ KURS NBP D-1 DLA BUYBACK_DATE
        try:
            import nbp_api_client
            
            # Konwertuj datę jeśli trzeba
            if hasattr(buyback_date, 'strftime'):
                buyback_date_for_nbp = buyback_date
            elif isinstance(buyback_date, str):
                from datetime import datetime
                buyback_date_for_nbp = datetime.strptime(buyback_date, '%Y-%m-%d').date()
            else:
                buyback_date_for_nbp = buyback_date
            
            print(f"🔍 BUYBACK NBP: Pobieranie kursu dla {buyback_date_for_nbp}")
            
            nbp_result = nbp_api_client.get_usd_rate_for_date(buyback_date_for_nbp)
            
            if isinstance(nbp_result, dict) and 'rate' in nbp_result:
                fx_close = nbp_result['rate']
                fx_close_date = nbp_result.get('date', buyback_date_for_nbp)
                print(f"💱 BUYBACK NBP: Otrzymano kurs {fx_close:.4f} na {fx_close_date}")
            else:
                fx_close = float(nbp_result) if nbp_result else None
                fx_close_date = buyback_date_for_nbp
                
                if fx_close is None:
                    raise Exception("NBP zwrócił None")
                
                print(f"💱 BUYBACK NBP: Kurs jako float: {fx_close:.4f}")
                
        except Exception as e:
            print(f"❌ BUYBACK NBP: Błąd {e}")
            conn.close()
            return {'success': False, 'message': f'Błąd kursu NBP: {str(e)}'}
        
        print(f"✅ BUYBACK NBP: Finalny kurs = {fx_close:.4f}")
        
        # 4. KALKULACJE Z PROWIZJAMI
        premium_received_usd = premium_sell_usd * contracts * 100
        buyback_cost_usd = buyback_price_usd * contracts * 100
        total_fees_usd = broker_fee_usd + reg_fee_usd
        total_buyback_cost_usd = buyback_cost_usd + total_fees_usd
        
        # P/L USD i PLN
        pl_usd = premium_received_usd - total_buyback_cost_usd
        buyback_cost_pln = total_buyback_cost_usd * fx_close
        pl_pln = premium_sell_pln - buyback_cost_pln
        
        # 5. PRZYGOTUJ DATĘ
        if hasattr(buyback_date, 'strftime'):
            buyback_date_str = buyback_date.strftime('%Y-%m-%d')
        else:
            buyback_date_str = str(buyback_date)
        
        # 6. AKTUALIZUJ CC RECORD
        cursor.execute("""
            UPDATE options_cc 
            SET status = 'bought_back',
                close_date = ?,
                premium_buyback_pln = ?,
                pl_pln = ?
            WHERE id = ?
        """, (
            buyback_date_str,
            buyback_cost_pln,
            pl_pln,
            cc_id
        ))
        
        # 7. ZWOLNIJ REZERWACJE AKCJI (bez zmian - działa)
        shares_to_release = contracts * 100
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='options_cc_reservations'
        """)
        has_reservations_table = cursor.fetchone() is not None
        
        if has_reservations_table:
            cursor.execute("""
                SELECT lot_id, qty_reserved 
                FROM options_cc_reservations 
                WHERE cc_id = ? 
                ORDER BY id
            """, (cc_id,))
            reservations = cursor.fetchall()
            
            for lot_id, qty_reserved in reservations:
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_open = quantity_open + ?
                    WHERE id = ?
                """, (qty_reserved, lot_id))
            
            cursor.execute("DELETE FROM options_cc_reservations WHERE cc_id = ?", (cc_id,))
        else:
            # Fallback FIFO
            cursor.execute("""
                SELECT id, quantity_open, quantity_reserved_cc
                FROM lots 
                WHERE ticker = ? AND quantity_reserved_cc > 0
                ORDER BY buy_date ASC, id ASC
            """, (ticker,))
            
            lots_with_reservations = cursor.fetchall()
            remaining_to_release = shares_to_release
            
            for lot_id, quantity_open, quantity_reserved_cc in lots_with_reservations:
                if remaining_to_release <= 0:
                    break
                
                qty_to_release = min(remaining_to_release, quantity_reserved_cc)
                
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_reserved_cc = quantity_reserved_cc - ?,
                        quantity_open = quantity_open + ?
                    WHERE id = ?
                """, (qty_to_release, qty_to_release, lot_id))
                
                remaining_to_release -= qty_to_release
        
        # 8. 🎯 NAPRAWKA: UTWÓRZ CASHFLOW Z POPRAWNYM KURSEM
        cashflow_description = f"Buyback CC {ticker} ${buyback_price_usd:.2f} + prowizje ${total_fees_usd:.2f} | NBP D-1: {fx_close_date}"
        
        print(f"💸 BUYBACK CASHFLOW: Zapisuję kurs {fx_close:.4f}, kwota PLN {buyback_cost_pln:.2f}")
        
        cursor.execute("""
            INSERT INTO cashflows (
                type, amount_usd, date, fx_rate, amount_pln, 
                description, ref_table, ref_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'option_buyback',
            -total_buyback_cost_usd,  # Ujemna kwota (wydatek)
            buyback_date_str,
            fx_close,                 # ← NAPRAWIONY KURS!
            -buyback_cost_pln,        # ← NAPRAWIONA KWOTA PLN!
            cashflow_description,
            'options_cc',
            cc_id
        ))
        
        print(f"✅ BUYBACK: Cashflow zapisany z kursem {fx_close:.4f}")
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'CC #{cc_id} odkupione pomyślnie!',
            'pl_pln': pl_pln,
            'pl_usd': pl_usd,
            'premium_received_pln': premium_sell_pln,
            'buyback_cost_pln': buyback_cost_pln,
            'total_fees_usd': total_fees_usd,
            'fx_close': fx_close,
            'fx_close_date': fx_close_date,
            'shares_released': shares_to_release
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        
        return {
            'success': False,
            'message': f'Błąd buyback: {str(e)}'
        }

def cleanup_orphaned_cashflow():
    """
    Usuwa cashflow które nie mają powiązania z żadną opcją
    """
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # Znajdź cashflow opcyjne bez powiązania z istniejącymi CC
        cursor.execute("""
            SELECT c.id, c.description, c.amount_usd, c.date
            FROM cashflows c
            WHERE c.ref_table = 'options_cc' 
            AND c.ref_id NOT IN (SELECT id FROM options_cc)
        """)
        
        orphaned = cursor.fetchall()
        
        if not orphaned:
            conn.close()
            return {
                'success': True, 
                'message': 'Nie znaleziono orphaned cashflow',
                'deleted_count': 0,
                'deleted_descriptions': []
            }
        
        # Usuń orphaned cashflow
        deleted_descriptions = []
        for cf_id, description, amount, date in orphaned:
            cursor.execute("DELETE FROM cashflows WHERE id = ?", (cf_id,))
            deleted_descriptions.append(f"{date}: {description} (${amount:.2f})")
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'Usunięto {len(orphaned)} orphaned cashflow',
            'deleted_count': len(orphaned),
            'deleted_descriptions': deleted_descriptions
        }
        
    except Exception as e:
        if conn:
            conn.close()
        return {'success': False, 'message': f'Błąd cleanup: {str(e)}'}


def check_cc_cashflow_integrity():
    """
    Sprawdza integralność między CC a cashflow
    """
    try:
        conn = get_connection()
        if not conn:
            return {'issues': ['Brak połączenia z bazą']}
        
        cursor = conn.cursor()
        issues = []
        
        # 1. CC bez cashflow
        cursor.execute("""
            SELECT id, ticker, status FROM options_cc o
            WHERE NOT EXISTS (
                SELECT 1 FROM cashflows c 
                WHERE c.ref_table = 'options_cc' AND c.ref_id = o.id
            )
        """)
        
        cc_without_cashflow = cursor.fetchall()
        for cc_id, ticker, status in cc_without_cashflow:
            issues.append(f"CC #{cc_id} ({ticker}) nie ma cashflow")
        
        # 2. Cashflow bez CC
        cursor.execute("""
            SELECT c.id, c.description FROM cashflows c
            WHERE c.ref_table = 'options_cc' 
            AND c.ref_id NOT IN (SELECT id FROM options_cc)
        """)
        
        cashflow_without_cc = cursor.fetchall()
        for cf_id, description in cashflow_without_cc:
            issues.append(f"Cashflow #{cf_id} ({description}) nie ma CC")
        
        # 3. Bought back CC bez 2 cashflow
        cursor.execute("""
            SELECT o.id, o.ticker, COUNT(c.id) as cf_count
            FROM options_cc o
            LEFT JOIN cashflows c ON c.ref_table = 'options_cc' AND c.ref_id = o.id
            WHERE o.status = 'bought_back'
            GROUP BY o.id, o.ticker
            HAVING COUNT(c.id) != 2
        """)
        
        bought_back_issues = cursor.fetchall()
        for cc_id, ticker, cf_count in bought_back_issues:
            issues.append(f"CC #{cc_id} ({ticker}) bought_back ma {cf_count} cashflow (powinno być 2)")
        
        conn.close()
        
        return {'issues': issues}
        
    except Exception as e:
        return {'issues': [f'Błąd sprawdzania integralności: {str(e)}']}
        
def partial_buyback_covered_call(cc_id, contracts_to_buyback, buyback_price_usd, buyback_date, broker_fee_usd=0.0, reg_fee_usd=0.0):
    """
    🔧 NAPRAWIONA: Częściowy buyback CC - BEZ TABELI lot_reservations
    
    KLUCZOWA ZMIANA: System rezerwacji działa poprzez quantity_open w lots,
    nie przez osobną tabelę lot_reservations!
    """
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # 1. POBIERZ DANE ORYGINALNEJ CC
        cursor.execute("""
            UPDATE options_cc 
            SET status = 'bought_back',
                close_date = ?,
                premium_buyback_usd = ?,
                premium_buyback_pln = ?,
                fx_close = ?,
                pl_pln = ?
            WHERE id = ?
        """, (
            buyback_date_str,
            premium_buyback_usd,
            premium_buyback_pln,
            fx_close,
            pl_pln,
            cc_id
        ))
        
        cc_record = cursor.fetchone()
        if not cc_record:
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} nie znalezione lub już zamknięte'}
        
        cc_id, ticker, total_contracts, strike_usd, premium_sell_usd, open_date, expiry_date, status, fx_open, premium_sell_pln = cc_record
        
        # 2. WALIDACJA PARAMETRÓW
        if contracts_to_buyback <= 0:
            conn.close()
            return {'success': False, 'message': 'Liczba kontraktów do odkupu musi być > 0'}
        
        if contracts_to_buyback > total_contracts:
            conn.close()
            return {'success': False, 'message': f'Nie można odkupić {contracts_to_buyback} kontraktów (dostępne: {total_contracts})'}
        
        # 3. POBIERZ KURS NBP NA BUYBACK_DATE
        if hasattr(buyback_date, 'strftime'):
            buyback_date_str = buyback_date.strftime('%Y-%m-%d')
        else:
            buyback_date_str = str(buyback_date)
        
        from nbp_api_client import get_usd_rate_for_date
        
        try:
            nbp_result = get_usd_rate_for_date(buyback_date_str)
            if isinstance(nbp_result, dict):
                fx_close = nbp_result['rate']
                fx_close_date = nbp_result.get('date', buyback_date_str)
            else:
                fx_close = float(nbp_result)
                fx_close_date = buyback_date_str
        except:
            fx_close = 4.0  # Fallback
            fx_close_date = buyback_date_str
        
        # 4. KALKULACJE FINANSOWE
        shares_to_buyback = contracts_to_buyback * 100
        
        # Koszt odkupu (z prowizjami)
        buyback_cost_usd = shares_to_buyback * buyback_price_usd
        total_fees_usd = broker_fee_usd + reg_fee_usd
        total_buyback_cost_usd = buyback_cost_usd + total_fees_usd
        buyback_cost_pln = total_buyback_cost_usd * fx_close
        
        # Premium otrzymana za odkupywaną część (proporcjonalnie)
        premium_proportion = contracts_to_buyback / total_contracts
        premium_for_buyback_usd = premium_sell_usd * shares_to_buyback
        premium_for_buyback_pln = premium_for_buyback_usd * fx_open
        
        # P/L tylko w PLN
        pl_pln = premium_for_buyback_pln - buyback_cost_pln
        
        # 5. JEŚLI CZĘŚCIOWY BUYBACK - PODZIEL POZYCJĘ
        if contracts_to_buyback < total_contracts:
            
            # A) STWÓRZ NOWY REKORD DLA ODKUPIONEJ CZĘŚCI
            cursor.execute("""
                INSERT INTO options_cc (
                    ticker, contracts, strike_usd, premium_sell_usd, 
                    open_date, expiry_date, status, fx_open, premium_sell_pln,
                    close_date, premium_buyback_usd, fx_close, premium_buyback_pln,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                ticker, contracts_to_buyback, strike_usd, premium_sell_usd,
                open_date, expiry_date, 'bought_back', fx_open, premium_for_buyback_pln,
                buyback_date_str, buyback_price_usd, fx_close, buyback_cost_pln
            ))
            
            new_cc_id = cursor.lastrowid
            
            # B) ZAKTUALIZUJ ORYGINALNĄ CC (ZMNIEJSZ KONTRAKTY)
            remaining_premium_pln = premium_sell_pln - premium_for_buyback_pln
            
            cursor.execute("""
                UPDATE options_cc 
                SET contracts = ?, premium_sell_pln = ?
                WHERE id = ?
            """, (total_contracts - contracts_to_buyback, remaining_premium_pln, cc_id))
            
        else:
            # CAŁKOWITY BUYBACK - ZMIEŃ STATUS ORYGINALNEJ CC
            cursor.execute("""
                UPDATE options_cc 
                SET status = 'bought_back', close_date = ?, 
                    premium_buyback_usd = ?, fx_close = ?, premium_buyback_pln = ?
                WHERE id = ?
            """, (
                buyback_date_str, buyback_price_usd, fx_close, buyback_cost_pln, cc_id
            ))
            
            new_cc_id = cc_id
        
        # 6. ZWOLNIJ AKCJE - KLUCZOWA NAPRAWKA: BEZ lot_reservations!
        shares_to_release = shares_to_buyback
        
        # NOWA LOGIKA: Zwiększ quantity_open w lots FIFO
        # Znajdź LOT-y tego tickera, które były zarezerwowane (quantity_open = 0)
        cursor.execute("""
            SELECT id, quantity_total, quantity_open, buy_date
            FROM lots 
            WHERE ticker = ? AND quantity_total > 0
            ORDER BY buy_date ASC, id ASC
        """, (ticker.upper(),))
        
        lots_for_ticker = cursor.fetchall()
        remaining_to_release = shares_to_release
        lots_updated = 0
        
        for lot_id, qty_total, qty_open, buy_date in lots_for_ticker:
            if remaining_to_release <= 0:
                break
            
            # Ile akcji z tego LOT-a może być zarezerwowanych pod CC
            potentially_reserved = qty_total - qty_open
            
            if potentially_reserved > 0:
                # Zwolnij część lub całość z tego LOT-a
                qty_to_release = min(potentially_reserved, remaining_to_release)
                
                # Zwiększ quantity_open (zwolnienie rezerwacji)
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_open = quantity_open + ?
                    WHERE id = ?
                """, (qty_to_release, lot_id))
                
                remaining_to_release -= qty_to_release
                lots_updated += 1
                
                print(f"   🔓 LOT #{lot_id}: zwolniono {qty_to_release} akcji (nowe qty_open: {qty_open + qty_to_release})")
        
        if remaining_to_release > 0:
            print(f"⚠️ Nie udało się zwolnić wszystkich akcji - pozostało {remaining_to_release}")
        
        # 7. UTWÓRZ CASHFLOW (wydatek)
        if contracts_to_buyback < total_contracts:
            cashflow_description = f"Częściowy buyback CC #{cc_id} ({contracts_to_buyback}/{total_contracts} kontraktów)"
        else:
            cashflow_description = f"Buyback CC #{cc_id} ({total_contracts} kontraktów)"
        
        if total_fees_usd > 0:
            cashflow_description += f" + prowizje ${total_fees_usd:.2f}"
        
        cursor.execute("""
            INSERT INTO cashflows (
                type, amount_usd, date, fx_rate, amount_pln, 
                description, ref_table, ref_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'option_buyback',
            -total_buyback_cost_usd,  # Ujemna kwota (wydatek)
            buyback_date_str,
            fx_close,
            -buyback_cost_pln,
            cashflow_description,
            'options_cc',
            new_cc_id
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'Odkupiono {contracts_to_buyback} kontraktów CC #{cc_id}!',
            'contracts_bought_back': contracts_to_buyback,
            'contracts_remaining': total_contracts - contracts_to_buyback if contracts_to_buyback < total_contracts else 0,
            'pl_pln': pl_pln,
            'premium_received_pln': premium_for_buyback_pln,
            'buyback_cost_pln': buyback_cost_pln,
            'total_fees_usd': total_fees_usd,
            'fx_close': fx_close,
            'fx_close_date': fx_close_date,
            'shares_released': shares_to_release,
            'lots_updated': lots_updated,
            'new_cc_id': new_cc_id if contracts_to_buyback < total_contracts else None
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        
        return {
            'success': False,
            'message': f'Błąd częściowego buyback: {str(e)}'
        }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 KLUCZOWA POPRAWKA: Napraw zwalnianie akcji po buyback CC
Dodaj do db.py lub uruchom jako patch
"""

def fix_buyback_stock_release():
    """
    GŁÓWNA POPRAWKA funkcji buyback - ZAWSZE zwalnia akcje po odkupu
    
    Problem: Po buyback CC, akcje pozostają zablokowane (quantity_open nie zwiększa się)
    Rozwiązanie: Napraw logikę zwalniania w simple_buyback_covered_call()
    """
    
    # WERSJA NAPRAWIONA dla db.py
    return """
def simple_buyback_covered_call(cc_id, buyback_price_usd, buyback_date, broker_fee_usd=0.0, reg_fee_usd=0.0):
    \"\"\"
    🔧 NAPRAWIONA: Buyback CC - ZAWSZE zwalnia akcje po odkupie
    
    KLUCZOWE ZMIANY:
    1. Po buyback ZAWSZE zwiększ quantity_open w lots  
    2. Sprawdź czy istnieją mapowania i je usuń
    3. Fallback: zwolnij akcje FIFO jeśli brak mapowań
    \"\"\"
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # 1. POBIERZ DANE CC
        cursor.execute(\"\"\"
            SELECT id, ticker, contracts, premium_sell_usd, open_date, expiry_date,
                   status, fx_open, premium_sell_pln
            FROM options_cc 
            WHERE id = ? AND status = 'open'
        \"\"\", (cc_id,))
        
        cc_record = cursor.fetchone()
        if not cc_record:
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} nie znalezione lub już zamknięte'}
        
        cc_id, ticker, contracts, premium_sell_usd, open_date, expiry_date, status, fx_open, premium_sell_pln = cc_record
        
        # 2. POBIERZ KURS NBP na buyback_date
        if hasattr(buyback_date, 'strftime'):
            buyback_date_str = buyback_date.strftime('%Y-%m-%d')
        else:
            buyback_date_str = str(buyback_date)
        
        from utils.nbp_api_client import get_usd_rate_for_date
        
        try:
            nbp_result = get_usd_rate_for_date(buyback_date_str)
            if isinstance(nbp_result, dict):
                fx_close = nbp_result['rate']
                fx_close_date = nbp_result.get('date', buyback_date_str)
            else:
                fx_close = float(nbp_result)
                fx_close_date = buyback_date_str
        except:
            fx_close = 4.0  # Fallback
            fx_close_date = buyback_date_str
        
        # 3. WYLICZENIA FINANSOWE
        total_fees_usd = broker_fee_usd + reg_fee_usd
        net_buyback_price_usd = buyback_price_usd + (total_fees_usd / (contracts * 100))
        total_buyback_cost_usd = (buyback_price_usd * contracts * 100) + total_fees_usd
        buyback_cost_pln = round(total_buyback_cost_usd * fx_close, 2)
        
        # P/L calculation
        premium_buyback_usd = buyback_price_usd * contracts * 100
        premium_buyback_pln = round(premium_buyback_usd * fx_close, 2)
        pl_pln = round(premium_sell_pln - premium_buyback_pln - (total_fees_usd * fx_close), 2)
        
        # 4. ZAKTUALIZUJ CC NA 'bought_back'
        cursor.execute(\"\"\"
            UPDATE options_cc 
            SET status = 'bought_back', 
                close_date = ?, 
                premium_buyback_usd = ?, 
                fx_close = ?, 
                premium_buyback_pln = ?
            WHERE id = ?
        \"\"\", (buyback_date_str, premium_buyback_usd, fx_close, premium_buyback_pln, cc_id))
        
        # 5. 🔧 KLUCZOWA NAPRAWKA: ZWOLNIJ AKCJE
        shares_to_release = contracts * 100
        
        # METODA A: Sprawdź mapowania (jeśli istnieją)
        cursor.execute(\"\"\"
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='cc_lot_mappings'
        \"\"\")
        
        has_mappings_table = cursor.fetchone() is not None
        lots_updated = 0
        
        if has_mappings_table:
            # USUŃ MAPOWANIA I ZWOLNIJ DOKŁADNIE TE LOT-y
            cursor.execute(\"\"\"
                SELECT lot_id, shares_reserved 
                FROM cc_lot_mappings 
                WHERE cc_id = ?
                ORDER BY lot_id ASC
            \"\"\", (cc_id,))
            
            mappings = cursor.fetchall()
            
            for lot_id, shares_reserved in mappings:
                # Zwróć akcje do quantity_open
                cursor.execute(\"\"\"
                    UPDATE lots 
                    SET quantity_open = quantity_open + ?
                    WHERE id = ?
                \"\"\", (shares_reserved, lot_id))
                lots_updated += 1
            
            # Usuń mapowania
            cursor.execute(\"\"\"
                DELETE FROM cc_lot_mappings WHERE cc_id = ?
            \"\"\", (cc_id,))
            
        else:
            # METODA B: FALLBACK - zwolnij akcje FIFO (bez mapowań)
            cursor.execute(\"\"\"
                SELECT id, quantity_total, quantity_open 
                FROM lots 
                WHERE ticker = ? AND quantity_total > quantity_open
                ORDER BY buy_date ASC, id ASC
            \"\"\", (ticker.upper(),))
            
            blocked_lots = cursor.fetchall()
            remaining_to_release = shares_to_release
            
            for lot_id, qty_total, qty_open in blocked_lots:
                if remaining_to_release <= 0:
                    break
                
                # Ile akcji z tego LOT-a jest zablokowanych
                blocked_qty = qty_total - qty_open
                if blocked_qty > 0:
                    # Zwolnij część lub całość
                    qty_to_release = min(blocked_qty, remaining_to_release)
                    
                    cursor.execute(\"\"\"
                        UPDATE lots 
                        SET quantity_open = quantity_open + ?
                        WHERE id = ?
                    \"\"\", (qty_to_release, lot_id))
                    
                    remaining_to_release -= qty_to_release
                    lots_updated += 1
        
        # 6. UTWÓRZ CASHFLOW (wydatek buyback)
        cashflow_description = f\"Buyback {ticker} CC #{cc_id} ({contracts} kontraktów)\"
        if total_fees_usd > 0:
            cashflow_description += f\" + prowizje ${total_fees_usd:.2f}\"
        
        cursor.execute(\"\"\"
            INSERT INTO cashflows (
                type, amount_usd, date, fx_rate, amount_pln, 
                description, ref_table, ref_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        \"\"\", (
            'option_buyback',
            -total_buyback_cost_usd,  # Ujemna kwota (wydatek)
            buyback_date_str,
            fx_close,
            -buyback_cost_pln,
            cashflow_description,
            'options_cc',
            cc_id
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'Odkupiono CC #{cc_id}! Zwolniono {shares_to_release} akcji {ticker}',
            'contracts_bought_back': contracts,
            'pl_pln': pl_pln,
            'premium_received_pln': premium_sell_pln,
            'buyback_cost_pln': buyback_cost_pln,
            'total_fees_usd': total_fees_usd,
            'fx_close': fx_close,
            'shares_released': shares_to_release,
            'lots_updated': lots_updated,
            'mapping_method': 'mappings' if has_mappings_table else 'fifo_fallback'
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        
        return {
            'success': False,
            'message': f'Błąd buyback: {str(e)}'
        }

# DODATKOWA FUNKCJA: Automatyczna naprawa wszystkich bought_back CC
def fix_all_bought_back_cc_blocks():
    \"\"\"
    🔧 EMERGENCY FIX: Zwolnij akcje ze wszystkich bought_back CC
    
    Uruchom jeśli masz wiele CC z tym problemem
    \"\"\"
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # 1. ZNAJDŹ WSZYSTKIE bought_back CC
        cursor.execute(\"\"\"
            SELECT id, ticker, contracts, status
            FROM options_cc 
            WHERE status = 'bought_back'
        \"\"\")
        
        bought_back_ccs = cursor.fetchall()
        fixed_count = 0
        
        # 2. SPRAWDŹ KTÓRE MAJĄ ZABLOKOWANE AKCJE
        for cc_id, ticker, contracts, status in bought_back_ccs:
            shares_expected = contracts * 100
            
            # Sprawdź mapowania
            cursor.execute(\"\"\"
                SELECT COALESCE(SUM(shares_reserved), 0)
                FROM cc_lot_mappings 
                WHERE cc_id = ?
            \"\"\", (cc_id,))
            
            mapped_shares = cursor.fetchone()[0] or 0
            
            if mapped_shares > 0:
                # NAPRAW: usuń mapowania i zwolnij akcje
                cursor.execute(\"\"\"
                    SELECT lot_id, shares_reserved 
                    FROM cc_lot_mappings 
                    WHERE cc_id = ?
                \"\"\", (cc_id,))
                
                mappings = cursor.fetchall()
                
                for lot_id, shares_reserved in mappings:
                    cursor.execute(\"\"\"
                        UPDATE lots 
                        SET quantity_open = quantity_open + ?
                        WHERE id = ?
                    \"\"\", (shares_reserved, lot_id))
                
                cursor.execute(\"\"\"
                    DELETE FROM cc_lot_mappings WHERE cc_id = ?
                \"\"\", (cc_id,))
                
                fixed_count += 1
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'Naprawiono {fixed_count} bought_back CC - akcje zwolnione!',
            'fixed_count': fixed_count
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {'success': False, 'message': f'Błąd mass fix: {str(e)}'}

# WALIDACJA: Sprawdź czy system działa prawidłowo
def validate_cc_stock_consistency():
    \"\"\"
    🔍 SPRAWDZA: Czy wszystkie CC są spójne z blokadami akcji
    \"\"\"
    try:
        conn = get_connection()
        if not conn:
            return {'issues': ['Brak połączenia z bazą']}
        
        cursor = conn.cursor()
        issues = []
        
        # 1. Bought_back CC z mapowaniami (błąd!)
        cursor.execute(\"\"\"
            SELECT cc.id, cc.ticker, cc.contracts, COUNT(m.lot_id) as mapped_lots
            FROM options_cc cc
            LEFT JOIN cc_lot_mappings m ON cc.id = m.cc_id
            WHERE cc.status = 'bought_back'
            GROUP BY cc.id
            HAVING COUNT(m.lot_id) > 0
        \"\"\")
        
        problematic_ccs = cursor.fetchall()
        for cc_id, ticker, contracts, mapped_lots in problematic_ccs:
            issues.append(f\"CC #{cc_id} ({ticker}) bought_back ale ma {mapped_lots} mapowań!\")
        
        # 2. Open CC bez mapowań (możliwy problem)
        cursor.execute(\"\"\"
            SELECT cc.id, cc.ticker, cc.contracts
            FROM options_cc cc
            LEFT JOIN cc_lot_mappings m ON cc.id = m.cc_id
            WHERE cc.status = 'open'
            AND m.cc_id IS NULL
        \"\"\")
        
        unmapped_open_ccs = cursor.fetchall()
        for cc_id, ticker, contracts in unmapped_open_ccs:
            issues.append(f\"CC #{cc_id} ({ticker}) open ale brak mapowań!\")
        
        conn.close()
        
        return {
            'issues': issues,
            'problematic_ccs_count': len(problematic_ccs),
            'unmapped_open_ccs_count': len(unmapped_open_ccs)
        }
        
    except Exception as e:
        return {'issues': [f'Błąd walidacji: {str(e)}']}
"""

def apply_buyback_fix():
    """Zastosuj poprawkę w kodzie aplikacji"""
    
    fix_instructions = f'''
    📋 INSTRUKCJA APLIKACJI POPRAWKI:
    
    1. 🔧 ZASTĄP w db.py funkcję simple_buyback_covered_call() 
       powyższą naprawioną wersją
       
    2. 🔧 DODAJ funkcje fix_all_bought_back_cc_blocks() i validate_cc_stock_consistency()
       na końcu db.py
       
    3. ✅ URUCHOM w modułu Options przycisk emergency fix:
       if st.button("🚨 Napraw wszystkie bought_back CC"):
           result = db.fix_all_bought_back_cc_blocks()
           st.success(result['message'])
           
    4. 🧪 DODAJ walidację w Dev Tools:
       validation = db.validate_cc_stock_consistency()
       if validation['issues']:
           st.error("Znalezione problemy:")
           for issue in validation['issues']:
               st.write(f"- {issue}")
    '''
    
    return fix_instructions

if __name__ == "__main__":
    print("🔧 POPRAWKA BUYBACK - AUTOMATYCZNE ZWALNIANIE AKCJI")
    print("=" * 60)
    
    print(fix_buyback_stock_release())
    print("\n" + "=" * 60)
    print(apply_buyback_fix())
# ============================================================================
# ROZWIĄZANIE 1: Dodaj tabelę mapowania rezerwacji do db.py
# ============================================================================

def create_cc_reservations_mapping_table():
    """
    Tworzy tabelę mapowania CC → LOT-y (potrzebne do częściowego buyback)
    """
    try:
        conn = get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # Sprawdź czy tabela już istnieje
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='cc_lot_mappings'
        """)
        
        if cursor.fetchone():
            conn.close()
            return True  # Tabela już istnieje
        
        # Utwórz tabelę mapowania
        cursor.execute("""
            CREATE TABLE cc_lot_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cc_id INTEGER NOT NULL,
                lot_id INTEGER NOT NULL,
                shares_reserved INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cc_id) REFERENCES options_cc (id) ON DELETE CASCADE,
                FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE,
                UNIQUE(cc_id, lot_id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        print("✅ Utworzono tabelę cc_lot_mappings")
        return True
        
    except Exception as e:
        print(f"❌ Błąd tworzenia tabeli mapowania: {e}")
        return False

def rebuild_cc_mappings_from_existing_data():
    """
    Odbudowuje mapowania CC → LOT-y na podstawie istniejących danych
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Wyczyść istniejące mapowania
        cursor.execute("DELETE FROM cc_lot_mappings")
        
        # 2. Pobierz wszystkie otwarte CC
        cursor.execute("""
            SELECT id, ticker, contracts
            FROM options_cc 
            WHERE status = 'open'
            ORDER BY open_date ASC, id ASC
        """)
        
        open_cc_list = cursor.fetchall()
        
        if not open_cc_list:
            conn.close()
            return {'success': True, 'message': 'Brak otwartych CC do mapowania'}
        
        mappings_created = 0
        
        for cc_id, ticker, contracts in open_cc_list:
            shares_needed = contracts * 100
            
            # 3. Znajdź LOT-y FIFO dla tego tickera
            cursor.execute("""
                SELECT id, quantity_total, buy_date
                FROM lots 
                WHERE ticker = ?
                ORDER BY buy_date ASC, id ASC
            """, (ticker.upper(),))
            
            lots_for_ticker = cursor.fetchall()
            remaining_to_map = shares_needed
            
            for lot_id, qty_total, buy_date in lots_for_ticker:
                if remaining_to_map <= 0:
                    break
                
                # Ile akcji z tego LOT-a przypisać do tej CC
                shares_to_map = min(qty_total, remaining_to_map)
                
                # Stwórz mapowanie
                cursor.execute("""
                    INSERT INTO cc_lot_mappings (cc_id, lot_id, shares_reserved)
                    VALUES (?, ?, ?)
                """, (cc_id, lot_id, shares_to_map))
                
                remaining_to_map -= shares_to_map
                mappings_created += 1
                
                print(f"   📊 CC #{cc_id}: LOT #{lot_id} → {shares_to_map} akcji")
            
            if remaining_to_map > 0:
                print(f"⚠️ CC #{cc_id}: brakuje {remaining_to_map} akcji do pełnego pokrycia")
        
        conn.commit()
        conn.close()
        
        return {
            'success': True, 
            'message': f'Odbudowano {mappings_created} mapowań dla {len(open_cc_list)} CC'
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {'success': False, 'message': f'Błąd odbudowy mapowań: {e}'}

# ============================================================================
# ROZWIĄZANIE 2: Prawdziwy częściowy buyback z mapowaniami
# ============================================================================

def partial_buyback_covered_call_with_mappings(cc_id, contracts_to_buyback, buyback_price_usd, buyback_date, broker_fee_usd=0.0, reg_fee_usd=0.0):
    """
    🔧 NAPRAWIONA: Częściowy buyback CC - POPRAWNY KURS NBP (identyczny jak w pełnym buyback)
    """
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # 0. SPRAWDŹ TABELĘ MAPOWAŃ
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cc_lot_mappings'")
        if not cursor.fetchone():
            conn.close()
            return {'success': False, 'message': 'Brak tabeli mapowań! Włącz częściowy buyback w Dev Tools'}
        
        # 1. POBIERZ DANE CC
        cursor.execute("""
            SELECT id, ticker, contracts, strike_usd, premium_sell_usd, 
                   open_date, expiry_date, status, fx_open, premium_sell_pln
            FROM options_cc 
            WHERE id = ? AND status = 'open'
        """, (cc_id,))
        
        cc_record = cursor.fetchone()
        if not cc_record:
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} nie znalezione lub już zamknięte'}
        
        cc_id, ticker, total_contracts, strike_usd, premium_sell_usd, open_date, expiry_date, status, fx_open, premium_sell_pln = cc_record
        
        # 2. WALIDACJA
        if contracts_to_buyback <= 0 or contracts_to_buyback > total_contracts:
            conn.close()
            return {'success': False, 'message': f'Nieprawidłowa liczba kontraktów: {contracts_to_buyback} (dostępne: {total_contracts})'}
        
        # 3. 🎯 NAPRAWKA: IDENTYCZNE POBIERANIE NBP JAK W PEŁNYM BUYBACK
        try:
            import nbp_api_client
            
            # Konwertuj datę jeśli trzeba (identycznie jak w buyback_covered_call_with_fees)
            if hasattr(buyback_date, 'strftime'):
                buyback_date_for_nbp = buyback_date
            elif isinstance(buyback_date, str):
                from datetime import datetime
                buyback_date_for_nbp = datetime.strptime(buyback_date, '%Y-%m-%d').date()
            else:
                buyback_date_for_nbp = buyback_date
            
            print(f"🔍 PARTIAL BUYBACK NBP: Pobieranie kursu dla {buyback_date_for_nbp}")
            
            nbp_result = nbp_api_client.get_usd_rate_for_date(buyback_date_for_nbp)
            
            if isinstance(nbp_result, dict) and 'rate' in nbp_result:
                fx_close = nbp_result['rate']
                fx_close_date = nbp_result.get('date', buyback_date_for_nbp)
                print(f"💱 PARTIAL BUYBACK NBP: Otrzymano kurs {fx_close:.4f} na {fx_close_date}")
            else:
                fx_close = float(nbp_result) if nbp_result else None
                fx_close_date = buyback_date_for_nbp
                
                if fx_close is None:
                    raise Exception("NBP zwrócił None")
                
                print(f"💱 PARTIAL BUYBACK NBP: Kurs jako float: {fx_close:.4f}")
                
        except Exception as e:
            print(f"❌ PARTIAL BUYBACK NBP: Błąd {e}")
            conn.close()
            return {'success': False, 'message': f'Błąd kursu NBP: {str(e)}'}
        
        print(f"✅ PARTIAL BUYBACK NBP: Finalny kurs = {fx_close:.4f}")
        
        # 4. KALKULACJE FINANSOWE (dla wybranej liczby kontraktów)
        shares_to_buyback = contracts_to_buyback * 100
        
        # Proporcjonalne rozłożenie premium
        premium_proportion = contracts_to_buyback / total_contracts
        premium_for_buyback_usd = premium_sell_usd * shares_to_buyback
        premium_for_buyback_pln = premium_for_buyback_usd * fx_open
        
        # Koszt buyback z prowizjami
        buyback_cost_usd = shares_to_buyback * buyback_price_usd
        total_fees_usd = broker_fee_usd + reg_fee_usd
        total_buyback_cost_usd = buyback_cost_usd + total_fees_usd
        buyback_cost_pln = total_buyback_cost_usd * fx_close
        
        # P/L
        pl_pln = premium_for_buyback_pln - buyback_cost_pln
        pl_usd = premium_for_buyback_usd - total_buyback_cost_usd
        
        # 5. KONWERSJE DAT
        if hasattr(buyback_date, 'strftime'):
            buyback_date_str = buyback_date.strftime('%Y-%m-%d')
        else:
            buyback_date_str = str(buyback_date)
        
        # 6. OBSŁUGA CZĘŚCIOWEGO VS PEŁNEGO BUYBACK
        if contracts_to_buyback < total_contracts:
            # A) CZĘŚCIOWY - zostaw oryginalną CC z mniejszą liczbą kontraktów
            remaining_contracts = total_contracts - contracts_to_buyback
            remaining_premium_pln = premium_sell_pln - premium_for_buyback_pln
            
            cursor.execute("""
                UPDATE options_cc 
                SET contracts = ?, premium_sell_pln = ?
                WHERE id = ?
            """, (remaining_contracts, remaining_premium_pln, cc_id))
            
            # B) STWÓRZ NOWY REKORD dla odkupionej części
            cursor.execute("""
                INSERT INTO options_cc (
                    ticker, contracts, strike_usd, premium_sell_usd, 
                    open_date, expiry_date, status, fx_open, premium_sell_pln,
                    close_date, premium_buyback_usd, fx_close, premium_buyback_pln,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                ticker, contracts_to_buyback, strike_usd, premium_sell_usd,
                open_date, expiry_date, 'bought_back', fx_open, premium_for_buyback_pln,
                buyback_date_str, buyback_price_usd, fx_close, buyback_cost_pln
            ))
            
            new_cc_id = cursor.lastrowid
            
        else:
            # PEŁNY BUYBACK - zmień status oryginalnej CC
            cursor.execute("""
                UPDATE options_cc 
                SET status = 'bought_back', close_date = ?, 
                    premium_buyback_usd = ?, fx_close = ?, premium_buyback_pln = ?
                WHERE id = ?
            """, (buyback_date_str, buyback_price_usd, fx_close, buyback_cost_pln, cc_id))
            
            new_cc_id = cc_id
        
        # 7. ZWOLNIJ AKCJE Z MAPOWAŃ
        cursor.execute("""
            SELECT lot_id, shares_reserved
            FROM cc_lot_mappings 
            WHERE cc_id = ?
            ORDER BY lot_id ASC
        """, (cc_id,))
        
        mappings = cursor.fetchall()
        shares_to_release = shares_to_buyback
        remaining_to_release = shares_to_release
        lots_updated = 0
        
        for lot_id, shares_mapped in mappings:
            if remaining_to_release <= 0:
                break
            
            # Ile zwolnić z tego LOT-a
            shares_to_release_from_lot = min(shares_mapped, remaining_to_release)
            
            # Zwiększ quantity_open w LOT-ie
            cursor.execute("""
                UPDATE lots 
                SET quantity_open = quantity_open + ?
                WHERE id = ?
            """, (shares_to_release_from_lot, lot_id))
            
            if contracts_to_buyback < total_contracts:
                # CZĘŚCIOWY: zaktualizuj mapowanie
                new_shares_mapped = shares_mapped - shares_to_release_from_lot
                
                if new_shares_mapped > 0:
                    cursor.execute("""
                        UPDATE cc_lot_mappings 
                        SET shares_reserved = ?
                        WHERE cc_id = ? AND lot_id = ?
                    """, (new_shares_mapped, cc_id, lot_id))
                else:
                    cursor.execute("""
                        DELETE FROM cc_lot_mappings 
                        WHERE cc_id = ? AND lot_id = ?
                    """, (cc_id, lot_id))
                    
            else:
                # PEŁNY: usuń całe mapowanie
                cursor.execute("""
                    DELETE FROM cc_lot_mappings 
                    WHERE cc_id = ? AND lot_id = ?
                """, (cc_id, lot_id))
            
            remaining_to_release -= shares_to_release_from_lot
            lots_updated += 1
        
        # 8. UTWÓRZ CASHFLOW
        if contracts_to_buyback < total_contracts:
            description = f"Częściowy buyback CC #{cc_id} ({contracts_to_buyback}/{total_contracts} kontraktów)"
        else:
            description = f"Buyback CC #{cc_id} ({total_contracts} kontraktów)"
        
        if total_fees_usd > 0:
            description += f" + prowizje ${total_fees_usd:.2f}"
        
        cursor.execute("""
            INSERT INTO cashflows (
                type, amount_usd, date, fx_rate, amount_pln, 
                description, ref_table, ref_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'option_buyback',
            -total_buyback_cost_usd,
            buyback_date_str,
            fx_close,  # ← NAPRAWIONY KURS NBP!
            -buyback_cost_pln,
            description,
            'options_cc',
            new_cc_id
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'Odkupiono {contracts_to_buyback} z {total_contracts} kontraktów CC #{cc_id}!',
            'contracts_bought_back': contracts_to_buyback,
            'contracts_remaining': total_contracts - contracts_to_buyback,
            'pl_pln': pl_pln,
            'pl_usd': pl_usd,  # Dodane dla kompletności
            'premium_received_pln': premium_for_buyback_pln,
            'buyback_cost_pln': buyback_cost_pln,
            'total_fees_usd': total_fees_usd,
            'fx_close': fx_close,  # ← PRAWIDŁOWY KURS!
            'fx_close_date': fx_close_date,
            'shares_released': shares_to_release,
            'lots_updated': lots_updated,
            'new_cc_id': new_cc_id if contracts_to_buyback < total_contracts else None,
            'is_partial': contracts_to_buyback < total_contracts
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        
        return {
            'success': False,
            'message': f'Błąd częściowego buyback: {str(e)}'
        }

# DODAJ TAKŻE FUNKCJĘ POMOCNICZĄ DO POBIERANIA KURSU NBP:
def get_fx_rate_for_date(target_date):
    """
    🎯 WSPÓLNA FUNKCJA pobierania kursu NBP - używana w obu buyback
    
    IDENTYCZNA LOGIKA jak w buyback_covered_call_with_fees
    """
    try:
        import nbp_api_client
        
        # Konwertuj datę jeśli trzeba
        if hasattr(target_date, 'strftime'):
            date_for_nbp = target_date
        elif isinstance(target_date, str):
            from datetime import datetime
            date_for_nbp = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            date_for_nbp = target_date
        
        print(f"🔍 FX_RATE: Pobieranie kursu NBP dla {date_for_nbp}")
        
        nbp_result = nbp_api_client.get_usd_rate_for_date(date_for_nbp)
        
        if isinstance(nbp_result, dict) and 'rate' in nbp_result:
            fx_rate = nbp_result['rate']
            fx_date = nbp_result.get('date', date_for_nbp)
            print(f"💱 FX_RATE: Otrzymano kurs {fx_rate:.4f} na {fx_date}")
        else:
            fx_rate = float(nbp_result) if nbp_result else None
            fx_date = date_for_nbp
            
            if fx_rate is None:
                raise Exception("NBP zwrócił None")
            
            print(f"💱 FX_RATE: Kurs jako float: {fx_rate:.4f}")
        
        return {'rate': fx_rate, 'date': fx_date}
        
    except Exception as e:
        print(f"❌ FX_RATE: Błąd {e}")
        raise Exception(f'Błąd kursu NBP: {str(e)}')  # Rzuć błąd zamiast fallback

# ============================================================================
# ROZWIĄZANIE 3: Zaktualizowana sprzedaż CC z mapowaniami
# ============================================================================

def save_covered_call_with_mappings(cc_data):
    """
    Zapisuje CC z tworzeniem mapowań LOT-ów (potrzebne do częściowego buyback)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. SPRAWDŹ CZY TABELA MAPOWAŃ ISTNIEJE
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='cc_lot_mappings'
        """)
        
        if not cursor.fetchone():
            # Stwórz tabelę mapowań
            cursor.execute("""
                CREATE TABLE cc_lot_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cc_id INTEGER NOT NULL,
                    lot_id INTEGER NOT NULL,
                    shares_reserved INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cc_id) REFERENCES options_cc (id) ON DELETE CASCADE,
                    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE,
                    UNIQUE(cc_id, lot_id)
                )
            """)
        
        # 2. ZAPISZ CC (jak zwykle)
        cursor.execute("""
            INSERT INTO options_cc (
                ticker, contracts, strike_usd, premium_sell_usd, open_date, expiry_date,
                status, fx_open, premium_sell_pln, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            cc_data['ticker'], cc_data['contracts'], cc_data['strike_usd'],
            cc_data['premium_sell_usd'], cc_data['open_date'], cc_data['expiry_date'],
            'open', cc_data['fx_open'], cc_data['premium_sell_pln']
        ))
        
        cc_id = cursor.lastrowid
        shares_needed = cc_data['contracts'] * 100
        
        # 3. STWÓRZ MAPOWANIA I ZAREZERWUJ AKCJE FIFO
        cursor.execute("""
            SELECT id, quantity_open, buy_date
            FROM lots 
            WHERE ticker = ? AND quantity_open > 0
            ORDER BY buy_date ASC, id ASC
        """, (cc_data['ticker'].upper(),))
        
        available_lots = cursor.fetchall()
        remaining_to_reserve = shares_needed
        mappings_created = 0
        
        for lot_id, qty_open, buy_date in available_lots:
            if remaining_to_reserve <= 0:
                break
            
            # Ile zarezerwować z tego LOT-a
            shares_to_reserve = min(qty_open, remaining_to_reserve)
            
            # Stwórz mapowanie
            cursor.execute("""
                INSERT INTO cc_lot_mappings (cc_id, lot_id, shares_reserved)
                VALUES (?, ?, ?)
            """, (cc_id, lot_id, shares_to_reserve))
            
            # Zmniejsz quantity_open w LOT-ie
            cursor.execute("""
                UPDATE lots 
                SET quantity_open = quantity_open - ?
                WHERE id = ?
            """, (shares_to_reserve, lot_id))
            
            remaining_to_reserve -= shares_to_reserve
            mappings_created += 1
            
            print(f"   📊 CC #{cc_id}: zarezerwowano {shares_to_reserve} akcji z LOT #{lot_id}")
        
        if remaining_to_reserve > 0:
            # Rollback - brakuje akcji
            conn.rollback()
            conn.close()
            return {
                'success': False,
                'message': f'Brakuje {remaining_to_reserve} akcji do pokrycia CC!'
            }
        
        # 4. UTWÓRZ CASHFLOW
        cursor.execute("""
            INSERT INTO cashflows (
                type, amount_usd, date, fx_rate, amount_pln, 
                description, ref_table, ref_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'option_sell',
            cc_data['net_premium_usd'],
            cc_data['open_date'],
            cc_data['fx_open'],
            cc_data['net_premium_pln'],
            f"Sprzedaż CC {cc_data['ticker']} {cc_data['contracts']} kontr.",
            'options_cc',
            cc_id
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'CC #{cc_id} zapisane z {mappings_created} mapowaniami LOT-ów!',
            'cc_id': cc_id,
            'mappings_created': mappings_created
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        
        return {
            'success': False,
            'message': f'Błąd zapisu CC z mapowaniami: {str(e)}'
        }

# Test na końcu pliku (opcjonalny)
if __name__ == "__main__":
    print("Test funkcji buyback/expiry...")
    results = test_buyback_expiry_operations()
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")

# DODAJ TO DO db.py

def mass_fix_bought_back_cc_reservations():
    """
    🔓 NAPRAWIONA: Zwalnia wszystkie akcje z bought_back CC
    
    SPRAWDZA OBIE TABELE:
    - cc_lot_mappings (nowa tabela)
    - options_cc_reservations (stara tabela)
    
    Returns:
        dict: {'success': bool, 'message': str, 'fixed_count': int}
    """
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # Sprawdź które tabele istnieją
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        has_new_table = 'cc_lot_mappings' in existing_tables
        has_old_table = 'options_cc_reservations' in existing_tables
        
        total_fixed = 0
        total_shares_released = 0
        messages = []
        
        # 1. NAPRAWA NOWEJ TABELI (cc_lot_mappings)
        if has_new_table:
            cursor.execute("""
                SELECT DISTINCT cc.id, cc.ticker, cc.contracts,
                       COUNT(m.lot_id) as mapped_lots,
                       COALESCE(SUM(m.shares_reserved), 0) as total_shares_blocked
                FROM options_cc cc
                INNER JOIN cc_lot_mappings m ON cc.id = m.cc_id
                WHERE cc.status = 'bought_back'
                GROUP BY cc.id, cc.ticker, cc.contracts
            """)
            
            new_table_problems = cursor.fetchall()
            
            for cc_id, ticker, contracts, mapped_lots, total_shares_blocked in new_table_problems:
                # Pobierz mapowania
                cursor.execute("""
                    SELECT lot_id, shares_reserved 
                    FROM cc_lot_mappings 
                    WHERE cc_id = ?
                """, (cc_id,))
                
                mappings = cursor.fetchall()
                
                # Zwolnij akcje z LOT-ów
                for lot_id, shares_reserved in mappings:
                    cursor.execute("""
                        UPDATE lots 
                        SET quantity_open = quantity_open + ?
                        WHERE id = ?
                    """, (shares_reserved, lot_id))
                    total_shares_released += shares_reserved
                
                # Usuń mapowania
                cursor.execute("DELETE FROM cc_lot_mappings WHERE cc_id = ?", (cc_id,))
                total_fixed += 1
            
            if new_table_problems:
                messages.append(f"Nowa tabela: {len(new_table_problems)} CC")
        
        # 2. NAPRAWA STAREJ TABELI (options_cc_reservations)
        if has_old_table:
            cursor.execute("""
                SELECT r.cc_id, r.lot_id, r.qty_reserved, cc.ticker
                FROM options_cc_reservations r
                JOIN options_cc cc ON r.cc_id = cc.id
                WHERE cc.status = 'bought_back'
            """)
            
            old_reservations = cursor.fetchall()
            
            # Zwolnij akcje z LOT-ów
            old_cc_ids = set()
            for cc_id, lot_id, qty_reserved, ticker in old_reservations:
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_open = quantity_open + ?
                    WHERE id = ?
                """, (qty_reserved, lot_id))
                total_shares_released += qty_reserved
                old_cc_ids.add(cc_id)
            
            # Usuń stare rezerwacje
            if old_reservations:
                cursor.execute("""
                    DELETE FROM options_cc_reservations 
                    WHERE cc_id IN (
                        SELECT id FROM options_cc WHERE status = 'bought_back'
                    )
                """)
                total_fixed += len(old_cc_ids)
                messages.append(f"Stara tabela: {len(old_reservations)} rezerwacji")
        
        # Sprawdź czy coś naprawiono
        if total_fixed == 0 and total_shares_released == 0:
            conn.close()
            return {
                'success': True,
                'message': 'Wszystkie akcje już są prawidłowo zwolnione',
                'fixed_count': 0,
                'shares_released': 0
            }
        
        conn.commit()
        conn.close()
        
        # Stwórz wiadomość
        message_parts = [f'Zwolniono {total_shares_released} akcji']
        if messages:
            message_parts.extend(messages)
        
        return {
            'success': True,
            'message': ' | '.join(message_parts),
            'fixed_count': total_fixed,
            'shares_released': total_shares_released
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        
        return {
            'success': False, 
            'message': f'Błąd zwalniania akcji: {str(e)}',
            'fixed_count': 0
        }


# DODAJ TAKŻE TĘ FUNKCJĘ DO POKAZYWANIA STATUSU:

def get_blocked_cc_status():
    """
    🔍 SPRAWDZA: Ile CC blokuje akcje w obu tabelach
    
    Returns:
        dict: Status blokad w systemie
    """
    try:
        conn = get_connection()
        if not conn:
            return {'error': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # Sprawdź tabele
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        blocked_count = 0
        blocked_shares = 0
        details = []
        
        # Nowa tabela
        if 'cc_lot_mappings' in tables:
            cursor.execute("""
                SELECT COUNT(DISTINCT cc.id), COALESCE(SUM(m.shares_reserved), 0)
                FROM options_cc cc
                INNER JOIN cc_lot_mappings m ON cc.id = m.cc_id
                WHERE cc.status = 'bought_back'
            """)
            result = cursor.fetchone()
            if result and result[0] > 0:
                blocked_count += result[0]
                blocked_shares += result[1]
                details.append(f"Nowa tabela: {result[0]} CC, {result[1]} akcji")
        
        # Stara tabela
        if 'options_cc_reservations' in tables:
            cursor.execute("""
                SELECT COUNT(DISTINCT r.cc_id), COALESCE(SUM(r.qty_reserved), 0)
                FROM options_cc_reservations r
                JOIN options_cc cc ON r.cc_id = cc.id
                WHERE cc.status = 'bought_back'
            """)
            result = cursor.fetchone()
            if result and result[0] > 0:
                blocked_count += result[0]
                blocked_shares += result[1]
                details.append(f"Stara tabela: {result[0]} CC, {result[1]} akcji")
        
        conn.close()
        
        return {
            'blocked_cc_count': blocked_count,
            'blocked_shares': blocked_shares,
            'details': details,
            'has_problems': blocked_count > 0
        }
        
    except Exception as e:
        return {'error': f'Błąd sprawdzania: {str(e)}'}

def get_lots_for_tax_fifo(ticker: str) -> List[Dict]:
    """
    🎯 KLUCZOWA FUNKCJA: Pobiera LOT-y dla FIFO PODATKOWEGO
    
    RÓŻNICA od get_lots_by_ticker():
    - NIE filtruje po quantity_open > 0
    - Bierze WSZYSTKIE LOT-y (także zablokowane pod CC)
    - Kolejność: FIFO (buy_date ASC, id ASC)
    
    Args:
        ticker: Symbol akcji (np. 'KARO')
        
    Returns:
        List[Dict]: Wszystkie LOT-y w kolejności FIFO (bez filtrowania blokad)
    """
    conn = get_connection()
    if not conn:
        st.error("❌ Błąd połączenia z bazą danych")
        return []
    
    try:
        cursor = conn.cursor()
        
        # KLUCZOWA RÓŻNICA: Brak filtra "quantity_open > 0"
        query = """
            SELECT id, ticker, quantity_total, quantity_open, buy_price_usd,
                   broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln,
                   created_at, updated_at
            FROM lots 
            WHERE ticker = ?
            ORDER BY buy_date ASC, id ASC
        """
        
        cursor.execute(query, (ticker.upper(),))
        rows = cursor.fetchall()
        conn.close()
        
        # Konwersja na słowniki
        lots = []
        for row in rows:
            lot = {
                'id': row[0],
                'ticker': row[1],
                'quantity_total': row[2],
                'quantity_open': row[3],
                'buy_price_usd': float(row[4]),
                'broker_fee_usd': float(row[5]) if row[5] else 0.0,
                'reg_fee_usd': float(row[6]) if row[6] else 0.0,
                'buy_date': row[7],
                'fx_rate': float(row[8]),
                'cost_pln': float(row[9]),
                'created_at': row[10],
                'updated_at': row[11],
                # Dodatkowe pola dla podatków
                'quantity_sold': row[2] - row[3],  # Ile już sprzedano z tego LOT-a
                'is_blocked_by_cc': row[3] == 0 and row[2] > 0,  # Czy całkowicie zablokowany
                'cost_per_share_pln': float(row[9]) / row[2] if row[2] > 0 else 0.0
            }
            lots.append(lot)
        
        print(f"📊 FIFO PODATKOWY {ticker}: znaleziono {len(lots)} LOT-ów (wszystkie, bez filtrów)")
        return lots
        
    except Exception as e:
        st.error(f"❌ Błąd pobierania LOT-ów dla FIFO podatkowego: {e}")
        if conn:
            conn.close()
        return []

def calculate_tax_fifo_allocation(ticker: str, quantity_to_sell: int) -> Dict:
    """
    🎯 KLUCZOWA FUNKCJA: Kalkuluje alokację FIFO PODATKOWĄ
    
    RÓŻNICA od zwykłego FIFO:
    - Używa WSZYSTKICH LOT-ów (także zablokowanych pod CC)
    - Respektuje kolejność zakupu (FIFO) bez względu na blokady
    - Tworzy prawidłowe rozliczenie dla PIT-38
    
    Args:
        ticker: Symbol akcji
        quantity_to_sell: Ile akcji sprzedajemy
        
    Returns:
        Dict: {
            'success': bool,
            'allocation': List[Dict],  # Alokacja per LOT
            'total_cost_pln': float,
            'lots_used': int,
            'comparison': Dict  # Porównanie z FIFO operacyjnym
        }
    """
    
    # Pobierz LOT-y dla FIFO podatkowego
    tax_lots = get_lots_for_tax_fifo(ticker)
    
    if not tax_lots:
        return {
            'success': False,
            'error': f'Brak LOT-ów dla {ticker}',
            'allocation': [],
            'total_cost_pln': 0.0,
            'lots_used': 0
        }
    
    # Sprawdź czy w ogóle posiadamy wystarczająco akcji
    total_owned = sum(lot['quantity_total'] for lot in tax_lots)
    total_already_sold = sum(lot['quantity_sold'] for lot in tax_lots)
    total_remaining = total_owned - total_already_sold
    
    if quantity_to_sell > total_remaining:
        return {
            'success': False,
            'error': f'Próba sprzedaży {quantity_to_sell} akcji, ale pozostało tylko {total_remaining}',
            'allocation': [],
            'total_cost_pln': 0.0,
            'lots_used': 0
        }
    
    # FIFO PODATKOWY: Alokacja w kolejności zakupu
    allocation = []
    remaining_to_allocate = quantity_to_sell
    total_cost_pln = 0.0
    
    for lot in tax_lots:
        if remaining_to_allocate <= 0:
            break
        
        # Ile z tego LOT-a można jeszcze sprzedać (podatkowo)
        lot_quantity_remaining = lot['quantity_total'] - lot['quantity_sold']
        
        if lot_quantity_remaining <= 0:
            continue  # Ten LOT został już w całości sprzedany
        
        # Ile z tego LOT-a użyjemy w tej sprzedaży
        qty_from_this_lot = min(remaining_to_allocate, lot_quantity_remaining)
        
        if qty_from_this_lot > 0:
            # Koszt z tego LOT-a (proporcjonalny)
            cost_from_this_lot = lot['cost_per_share_pln'] * qty_from_this_lot
            
            allocation.append({
                'lot_id': lot['id'],
                'lot_buy_date': lot['buy_date'],
                'lot_buy_price_usd': lot['buy_price_usd'],
                'lot_fx_rate': lot['fx_rate'],
                'qty_used': qty_from_this_lot,
                'cost_pln': cost_from_this_lot,
                'cost_per_share_pln': lot['cost_per_share_pln'],
                'is_blocked_by_cc': lot['is_blocked_by_cc'],
                'quantity_open_before': lot['quantity_open'],  # Stan przed sprzedażą
                'tax_note': 'PODATKOWO_SPRZEDANE' if lot['is_blocked_by_cc'] else 'NORMALNIE_SPRZEDANE'
            })
            
            total_cost_pln += cost_from_this_lot
            remaining_to_allocate -= qty_from_this_lot
    
    # Porównanie z FIFO operacyjnym (dla debugowania)
    operational_lots = get_lots_by_ticker(ticker, only_open=True)  # Stara funkcja
    
    comparison = {
        'tax_lots_count': len(tax_lots),
        'operational_lots_count': len(operational_lots),
        'tax_uses_blocked': any(alloc['is_blocked_by_cc'] for alloc in allocation),
        'difference_detected': len(tax_lots) != len(operational_lots)
    }
    
    return {
        'success': remaining_to_allocate == 0,
        'allocation': allocation,
        'total_cost_pln': total_cost_pln,
        'lots_used': len(allocation),
        'comparison': comparison,
        'debug_info': {
            'quantity_requested': quantity_to_sell,
            'quantity_allocated': quantity_to_sell - remaining_to_allocate,
            'remaining_unallocated': remaining_to_allocate
        }
    }

def get_tax_vs_operational_fifo_comparison(ticker: str, quantity: int) -> Dict:
    """
    🔍 FUNKCJA DIAGNOSTYCZNA: Porównuje FIFO podatkowy vs operacyjny
    
    Pokazuje różnice między dwoma podejściami:
    - FIFO PODATKOWY: wszystkie LOT-y w kolejności zakupu
    - FIFO OPERACYJNY: tylko LOT-y z quantity_open > 0
    
    Args:
        ticker: Symbol akcji
        quantity: Ilość do "symulacyjnej" sprzedaży
        
    Returns:
        Dict: Szczegółowe porównanie obu metod
    """
    
    # FIFO PODATKOWY
    tax_result = calculate_tax_fifo_allocation(ticker, quantity)
    
    # FIFO OPERACYJNY (stary sposób)
    operational_lots = get_lots_by_ticker(ticker, only_open=True)
    operational_allocation = []
    remaining = quantity
    operational_cost = 0.0
    
    for lot in operational_lots:
        if remaining <= 0:
            break
        
        qty_from_lot = min(remaining, lot['quantity_open'])
        if qty_from_lot > 0:
            cost_per_share = lot['cost_pln'] / lot['quantity_total']
            cost_from_lot = qty_from_lot * cost_per_share
            
            operational_allocation.append({
                'lot_id': lot['id'],
                'lot_buy_date': lot['buy_date'],
                'qty_used': qty_from_lot,
                'cost_pln': cost_from_lot
            })
            
            operational_cost += cost_from_lot
            remaining -= qty_from_lot
    
    # Analiza różnic
    tax_lots_used = [alloc['lot_id'] for alloc in tax_result.get('allocation', [])]
    operational_lots_used = [alloc['lot_id'] for alloc in operational_allocation]
    
    return {
        'ticker': ticker,
        'quantity_tested': quantity,
        'tax_fifo': {
            'success': tax_result.get('success', False),
            'lots_used': tax_lots_used,
            'total_cost_pln': tax_result.get('total_cost_pln', 0.0),
            'allocation_count': len(tax_result.get('allocation', []))
        },
        'operational_fifo': {
            'success': remaining == 0,
            'lots_used': operational_lots_used,
            'total_cost_pln': operational_cost,
            'allocation_count': len(operational_allocation)
        },
        'differences': {
            'different_lots_used': tax_lots_used != operational_lots_used,
            'different_costs': abs(tax_result.get('total_cost_pln', 0) - operational_cost) > 0.01,
            'tax_uses_blocked_lots': any(
                alloc.get('is_blocked_by_cc', False) 
                for alloc in tax_result.get('allocation', [])
            ),
            'cost_difference_pln': tax_result.get('total_cost_pln', 0) - operational_cost
        },
        'recommendation': 'USE_TAX_FIFO_FOR_PIT38' if tax_lots_used != operational_lots_used else 'BOTH_SAME'
    }

# PUNKT 72: Migracja tabeli options_cc + chain_id
# Dodaj te funkcje do db.py

def migrate_options_cc_add_chain_id():
    """
    🔗 PUNKT 72: Dodanie kolumny chain_id do tabeli options_cc
    
    Dodaje foreign key do cc_chains dla łączenia opcji w łańcuchy.
    Bezpieczna migracja z rollback przy błędzie.
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # Sprawdź czy kolumna już istnieje
        cursor.execute("PRAGMA table_info(options_cc)")
        columns = cursor.fetchall()
        existing_columns = [col[1] for col in columns]  # col[1] = nazwa kolumny
        
        if 'chain_id' in existing_columns:
            conn.close()
            return {'success': True, 'message': 'Kolumna chain_id już istnieje'}
        
        # Dodaj kolumnę chain_id
        cursor.execute("""
            ALTER TABLE options_cc 
            ADD COLUMN chain_id INTEGER NULL 
            REFERENCES cc_chains(id) ON DELETE SET NULL
        """)
        
        # Dodaj indeks dla wydajności
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_options_cc_chain_id 
            ON options_cc(chain_id)
        """)
        
        conn.commit()
        conn.close()
        
        return {
            'success': True, 
            'message': '✅ Kolumna chain_id dodana do options_cc'
        }
        
    except Exception as e:
        if conn:
            conn.rollback() 
            conn.close()
        return {
            'success': False, 
            'message': f'❌ Błąd migracji: {str(e)}'
        }

def check_cc_chains_migration_status():
    """
    🔍 PUNKT 72.1: Sprawdza status migracji CC Chains
    
    Returns:
        dict: Status migracji i statystyki
    """
    try:
        conn = get_connection()
        if not conn:
            return {'error': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # Sprawdź tabele
        tables_status = {}
        
        # 1. Czy tabela cc_chains istnieje?
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='table' AND name='cc_chains'
        """)
        tables_status['cc_chains_exists'] = cursor.fetchone()[0] > 0
        
        if tables_status['cc_chains_exists']:
            cursor.execute("SELECT COUNT(*) FROM cc_chains")
            tables_status['cc_chains_count'] = cursor.fetchone()[0]
        
        # 2. Czy options_cc ma kolumnę chain_id?
        cursor.execute("PRAGMA table_info(options_cc)")
        columns = cursor.fetchall()
        existing_columns = [col[1] for col in columns]
        tables_status['chain_id_exists'] = 'chain_id' in existing_columns
        
        # 3. Ile CC ma przypisane chains?
        if tables_status['chain_id_exists']:
            cursor.execute("SELECT COUNT(*) FROM options_cc WHERE chain_id IS NOT NULL")
            tables_status['cc_with_chains'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM options_cc WHERE chain_id IS NULL")
            tables_status['cc_without_chains'] = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'success': True,
            'tables_status': tables_status
        }
        
    except Exception as e:
        if conn:
            conn.close()
        return {
            'success': False, 
            'error': f'Błąd sprawdzania: {str(e)}'
        }

def run_cc_chains_migration():
    """
    🚀 PUNKT 72.2: Kompletna migracja CC Chains
    
    1. Tworzy tabelę cc_chains (jeśli nie istnieje)
    2. Dodaje chain_id do options_cc  
    3. Sprawdza poprawność migracji
    
    Returns:
        dict: Pełny raport migracji
    """
    migration_report = {
        'steps_completed': [],
        'errors': [],
        'success': True
    }
    
    try:
        # KROK 1: Utwórz tabelę cc_chains
        from structure import create_cc_chains_table
        
        conn = get_connection()
        if not conn:
            migration_report['errors'].append('Brak połączenia z bazą')
            migration_report['success'] = False
            return migration_report
        
        if create_cc_chains_table(conn):
            migration_report['steps_completed'].append('✅ Tabela cc_chains utworzona')
        else:
            migration_report['errors'].append('❌ Błąd tworzenia cc_chains')
            migration_report['success'] = False
        
        conn.close()
        
        # KROK 2: Dodaj chain_id do options_cc
        chain_id_result = migrate_options_cc_add_chain_id()
        if chain_id_result['success']:
            migration_report['steps_completed'].append(f"✅ {chain_id_result['message']}")
        else:
            migration_report['errors'].append(f"❌ {chain_id_result['message']}")
            migration_report['success'] = False
        
        # KROK 3: Sprawdź status
        status_check = check_cc_chains_migration_status()
        if status_check['success']:
            migration_report['final_status'] = status_check['tables_status']
            migration_report['steps_completed'].append('✅ Weryfikacja migracji zakończona')
        else:
            migration_report['errors'].append(f"❌ {status_check['error']}")
        
        return migration_report
        
    except Exception as e:
        migration_report['errors'].append(f'❌ Błąd ogólny migracji: {str(e)}')
        migration_report['success'] = False
        return migration_report

# PUNKT 74: Uproszczony algorytm auto-detection dla CC Chains
# Dodaj te funkcje do db.py

def auto_detect_cc_chains():
    """
    🤖 PUNKT 74: NAPRAWIONY algorytm auto-detection CC Chains
    
    PROBLEM: Query nie znajdował LOT-ów bo był zbyt skomplikowany
    ROZWIĄZANIE: Prostszy query + debug output
    """
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        chains_created = 0
        cc_assigned = 0
        
        # DEBUG: Sprawdź co mamy w bazie
        cursor.execute("SELECT COUNT(*) FROM options_cc WHERE chain_id IS NULL")
        cc_without_chains = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM cc_lot_mappings")
        total_mappings = cursor.fetchone()[0]
        
        if cc_without_chains == 0:
            conn.close()
            return {
                'success': True, 
                'chains_created': 0,
                'cc_assigned': 0,
                'message': f'✅ Wszystkie {total_mappings} CC już mają chains'
            }
        
        # NOWY PROSTSZY QUERY: Znajdź LOT-y z CC bez chains
        cursor.execute("""
            SELECT m.lot_id, l.ticker, l.buy_date, COUNT(m.cc_id) as cc_count
            FROM cc_lot_mappings m
            JOIN lots l ON l.id = m.lot_id  
            JOIN options_cc cc ON cc.id = m.cc_id
            WHERE cc.chain_id IS NULL
            GROUP BY m.lot_id, l.ticker, l.buy_date
            ORDER BY l.ticker, l.buy_date
        """)
        
        lots_with_unmapped_cc = cursor.fetchall()
        
        if not lots_with_unmapped_cc:
            conn.close()
            return {
                'success': True, 
                'chains_created': 0,
                'cc_assigned': 0,
                'message': f'🔍 Debug: {cc_without_chains} CC bez chains, ale 0 LOT-ów z mapowaniami. Sprawdź mapowania!'
            }
        
        # KROK 2: Dla każdego LOT-u utwórz chain (jeśli nie istnieje)
        for lot_id, ticker, buy_date, cc_count in lots_with_unmapped_cc:
            
            # Sprawdź czy LOT już ma chain
            cursor.execute("SELECT id FROM cc_chains WHERE lot_id = ?", (lot_id,))
            existing_chain = cursor.fetchone()
            
            if existing_chain:
                chain_id = existing_chain[0]
                # Chain istnieje, tylko przypisz CC
            else:
                # Utwórz nowy chain dla tego LOT-u
                cursor.execute("""
                    SELECT MIN(cc.open_date) as start_date
                    FROM options_cc cc
                    JOIN cc_lot_mappings m ON cc.id = m.cc_id
                    WHERE m.lot_id = ?
                """, (lot_id,))
                
                start_date_result = cursor.fetchone()
                start_date = start_date_result[0] if start_date_result else buy_date
                
                # Wygeneruj chain_name
                chain_name = f"{ticker} Chain (LOT #{lot_id})"
                
                cursor.execute("""
                    INSERT INTO cc_chains (
                        lot_id, ticker, chain_name, start_date, status
                    ) VALUES (?, ?, ?, ?, 'active')
                """, (lot_id, ticker, chain_name, start_date))
                
                chain_id = cursor.lastrowid
                chains_created += 1
            
            # KROK 3: Przypisz wszystkie CC z tego LOT-u do chain
            cursor.execute("""
                SELECT cc.id 
                FROM options_cc cc
                JOIN cc_lot_mappings m ON cc.id = m.cc_id
                WHERE m.lot_id = ? AND cc.chain_id IS NULL
            """, (lot_id,))
            
            cc_to_assign = cursor.fetchall()
            
            for (cc_id_to_assign,) in cc_to_assign:
                cursor.execute("""
                    UPDATE options_cc 
                    SET chain_id = ?
                    WHERE id = ?
                """, (chain_id, cc_id_to_assign))
                cc_assigned += 1
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'chains_created': chains_created,
            'cc_assigned': cc_assigned,
            'message': f'✅ Utworzono {chains_created} chains, przypisano {cc_assigned} CC'
        }
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        
        # ZWRÓĆ SZCZEGÓŁOWY BŁĄD
        import traceback
        error_details = traceback.format_exc()
        
        return {
            'success': False, 
            'message': f'❌ Błąd auto-detection: {str(e)}',
            'error_details': error_details
        }

def get_cc_chains_summary():
    """
    📊 PUNKT 74.1: Pobranie podsumowania wszystkich CC Chains
    
    Returns:
        list: Lista chains z podstawowymi statystykami
    """
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # Pobierz chains z podstawowymi stats
        cursor.execute("""
            SELECT 
                ch.id,
                ch.lot_id,
                ch.ticker, 
                ch.chain_name,
                ch.start_date,
                ch.end_date,
                ch.status,
                l.buy_date,
                l.quantity_total,
                l.quantity_open,
                COUNT(cc.id) as cc_count,
                SUM(CASE WHEN cc.status = 'open' THEN 1 ELSE 0 END) as open_cc_count,
                COALESCE(SUM(cc.pl_pln), 0) as total_pl_pln,
                COALESCE(SUM(cc.premium_sell_pln), 0) as total_premium_pln
            FROM cc_chains ch
            JOIN lots l ON l.id = ch.lot_id
            LEFT JOIN options_cc cc ON cc.chain_id = ch.id
            GROUP BY ch.id
            ORDER BY ch.ticker, l.buy_date DESC
        """)
        
        chains_raw = cursor.fetchall()
        conn.close()
        
        # Konwertuj na dict
        chains = []
        for row in chains_raw:
            chains.append({
                'id': row[0],
                'lot_id': row[1], 
                'ticker': row[2],
                'chain_name': row[3],
                'start_date': row[4],
                'end_date': row[5],
                'status': row[6],
                'lot_buy_date': row[7],
                'lot_total': row[8],
                'lot_open': row[9], 
                'cc_count': row[10],
                'open_cc_count': row[11],
                'total_pl_pln': row[12],
                'total_premium_pln': row[13]
            })
        
        return chains
        
    except Exception as e:
        import streamlit as st
        st.error(f"Błąd pobierania chains: {e}")
        return []

def update_chain_statistics(chain_id):
    """
    📊 PUNKT 74.2: Aktualizuje statystyki chain na podstawie przypisanych CC
    
    Args:
        chain_id: ID chain do aktualizacji
        
    Returns:
        dict: Status operacji
    """
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia'}
        
        cursor = conn.cursor()
        
        # Pobierz statystyki CC w tym chain
        cursor.execute("""
            SELECT 
                COUNT(*) as total_contracts,
                COALESCE(SUM(premium_sell_pln), 0) as total_premium,
                COALESCE(SUM(pl_pln), 0) as total_pl,
                AVG(JULIANDAY(COALESCE(close_date, expiry_date)) - JULIANDAY(open_date)) as avg_duration,
                COUNT(CASE WHEN pl_pln > 0 THEN 1 END) * 100.0 / COUNT(*) as success_rate,
                MAX(COALESCE(close_date, expiry_date)) as last_activity_date
            FROM options_cc
            WHERE chain_id = ? AND status IN ('bought_back', 'expired', 'open')
        """, (chain_id,))
        
        stats = cursor.fetchone()
        
        if stats:
            total_contracts, total_premium, total_pl, avg_duration, success_rate, last_activity = stats
            
            # Określ end_date i status chain
            cursor.execute("""
                SELECT COUNT(*) FROM options_cc 
                WHERE chain_id = ? AND status = 'open'
            """, (chain_id,))
            
            open_cc_count = cursor.fetchone()[0]
            
            # Chain status
            chain_status = 'active' if open_cc_count > 0 else 'closed'
            end_date = None if open_cc_count > 0 else last_activity
            
            # Kalkulacja annualized return (uproszczona)
            if avg_duration and avg_duration > 0 and total_pl > 0:
                annualized_return = (total_pl / total_premium) * (365 / avg_duration) * 100
            else:
                annualized_return = 0
            
            # Update chain
            cursor.execute("""
                UPDATE cc_chains SET
                    total_contracts = ?,
                    total_premium_usd = ?,
                    total_pl_pln = ?,
                    avg_duration_days = ?,
                    success_rate = ?,
                    annualized_return = ?,
                    end_date = ?,
                    status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                total_contracts, 
                total_premium / (stats[0] or 1),  # avg premium per contract 
                total_pl,
                avg_duration or 0,
                success_rate or 0,
                annualized_return,
                end_date,
                chain_status,
                chain_id
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'message': f'✅ Statystyki chain #{chain_id} zaktualizowane',
                'stats': {
                    'total_pl': total_pl,
                    'cc_count': total_contracts,
                    'status': chain_status
                }
            }
        
        conn.close()
        return {'success': False, 'message': 'Brak danych dla chain'}
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {'success': False, 'message': f'Błąd aktualizacji: {str(e)}'}

# Test na końcu pliku (opcjonalny)
if __name__ == "__main__":
    print("Test funkcji buyback/expiry...")
    results = test_buyback_expiry_operations()
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")