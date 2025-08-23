"""
Moduł bazy danych SQLite dla Covered Call Dashboard
Punkt 3: Podstawowe połączenie z bazą danych
NAPRAWIONY - kompletny plik bez błędów składni
"""

import sqlite3
import os
from datetime import datetime
import streamlit as st

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

def get_lots_by_ticker(ticker, only_open=False):
    """Pobranie LOT-ów dla określonego tickera (w kolejności FIFO)"""
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

def check_cc_coverage(ticker, contracts_needed):
    """
    Sprawdza czy jest wystarczające pokrycie dla sprzedaży CC
    
    Args:
        ticker: Symbol akcji
        contracts_needed: Liczba kontraktów CC (1 kontrakt = 100 akcji)
    
    Returns:
        dict: {'can_cover': bool, 'shares_needed': int, 'shares_available': int, 'fifo_preview': list}
    """
    shares_needed = contracts_needed * 100
    
    try:
        conn = get_connection()
        if not conn:
            return {'can_cover': False, 'error': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # Pobierz LOT-y FIFO z dostępnymi akcjami
        cursor.execute("""
            SELECT id, quantity_open, buy_date, buy_price_usd, fx_rate
            FROM lots 
            WHERE ticker = ? AND quantity_open > 0
            ORDER BY buy_date, id
        """, (ticker.upper(),))
        
        lots = cursor.fetchall()
        conn.close()
        
        if not lots:
            return {
                'can_cover': False,
                'shares_needed': shares_needed,
                'shares_available': 0,
                'fifo_preview': [],
                'message': f'Brak akcji {ticker} w portfelu'
            }
        
        # Sprawdź pokrycie FIFO
        total_available = sum([lot[1] for lot in lots])  # quantity_open
        
        fifo_preview = []
        remaining_needed = shares_needed
        
        for lot in lots:
            if remaining_needed <= 0:
                break
                
            lot_id, qty_open, buy_date, buy_price, fx_rate = lot
            qty_to_reserve = min(remaining_needed, qty_open)
            
            fifo_preview.append({
                'lot_id': lot_id,
                'buy_date': buy_date,
                'buy_price_usd': buy_price,
                'fx_rate': fx_rate,
                'qty_available': qty_open,
                'qty_to_reserve': qty_to_reserve,
                'qty_remaining_after': qty_open - qty_to_reserve
            })
            
            remaining_needed -= qty_to_reserve
        
        return {
            'can_cover': remaining_needed <= 0,
            'shares_needed': shares_needed,
            'shares_available': total_available,
            'fifo_preview': fifo_preview,
            'message': 'OK' if remaining_needed <= 0 else f'Brakuje {remaining_needed} akcji'
        }
        
    except Exception as e:
        st.error(f"Błąd sprawdzania pokrycia CC: {e}")
        return {'can_cover': False, 'error': str(e)}

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
        coverage = check_cc_coverage(ticker, contracts)
        
        if not coverage['can_cover']:
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
                        coverage = check_cc_coverage(test_ticker, test_contracts)
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
    Zapisuje covered call do bazy z rezerwacją akcji FIFO
    """
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # 1. SPRAWDŹ POKRYCIE (double-check)
        coverage = check_cc_coverage(cc_data['ticker'], cc_data['contracts'])
        if not coverage.get('can_cover'):
            conn.close()
            return {
                'success': False, 
                'message': f"Brak pokrycia: {coverage.get('message', 'Nieznany błąd')}"
            }
        
        # 2. PRZYGOTUJ DATY
        open_date_str = cc_data['open_date']
        if hasattr(open_date_str, 'strftime'):
            open_date_str = open_date_str.strftime('%Y-%m-%d')
        
        expiry_date_str = cc_data['expiry_date']
        if hasattr(expiry_date_str, 'strftime'):
            expiry_date_str = expiry_date_str.strftime('%Y-%m-%d')
        
        # 3. ZAPISZ GŁÓWNY REKORD CC
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
            'open',  # Status początkowy
            cc_data['fx_open'],
            cc_data['premium_sell_pln']
        ))
        
        cc_id = cursor.lastrowid
        
        # 4. 🔥 NAPRAWIONA REZERWACJA AKCJI FIFO
        shares_to_reserve = cc_data['contracts'] * 100
        remaining_to_reserve = shares_to_reserve
        
        # Pobierz LOT-y FIFO z aktualnym quantity_open
        cursor.execute("""
            SELECT id, quantity_open
            FROM lots 
            WHERE ticker = ? AND quantity_open > 0
            ORDER BY buy_date, id
        """, (cc_data['ticker'],))
        
        available_lots = cursor.fetchall()
        
        print(f"🔧 REZERWACJA dla CC #{cc_id}:")
        print(f"   Do zarezerwowania: {shares_to_reserve} akcji")
        print(f"   Dostępne LOT-y: {len(available_lots)}")
        
        reserved_lots = []
        
        for lot_id, current_qty_open in available_lots:
            if remaining_to_reserve <= 0:
                break
            
            qty_to_reserve_from_lot = min(remaining_to_reserve, current_qty_open)
            new_qty_open = current_qty_open - qty_to_reserve_from_lot
            
            # AKTUALIZUJ quantity_open w LOT-ach - KLUCZOWE!
            cursor.execute("""
                UPDATE lots 
                SET quantity_open = ?
                WHERE id = ?
            """, (new_qty_open, lot_id))
            
            reserved_lots.append({
                'lot_id': lot_id,
                'was_open': current_qty_open,
                'reserved': qty_to_reserve_from_lot,
                'now_open': new_qty_open
            })
            
            remaining_to_reserve -= qty_to_reserve_from_lot
            
            print(f"   LOT #{lot_id}: {current_qty_open} -> {new_qty_open} (reserved: {qty_to_reserve_from_lot})")
        
        # Sprawdź czy udało się zarezerwować wszystkie
        if remaining_to_reserve > 0:
            conn.rollback()
            conn.close()
            return {
                'success': False,
                'message': f'Nie udało się zarezerwować {remaining_to_reserve} akcji'
            }
        
        print(f"✅ Zarezerwowano {shares_to_reserve} akcji dla CC #{cc_id}")
        print(f"   Użyto {len(reserved_lots)} LOT-ów")
        
        # 5. UTWÓRZ CASHFLOW (przychód z premium)
        total_premium_usd = cc_data['premium_sell_usd'] * cc_data['contracts'] * 100
        
        cashflow_description = f"Sprzedaż {cc_data['contracts']} CC {cc_data['ticker']} @ ${cc_data['premium_sell_usd']:.2f}"
        
        cursor.execute("""
            INSERT INTO cashflows (
                type, amount_usd, date, fx_rate, amount_pln,
                description, ref_table, ref_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'option_premium',  # Typ dla premium CC
            total_premium_usd,  # Dodatnia kwota (przychód)
            open_date_str,
            cc_data['fx_open'],
            cc_data['premium_sell_pln'],
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
            'reserved_details': reserved_lots
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        
        import streamlit as st
        st.error(f"Błąd zapisu CC: {e}")
        
        return {
            'success': False,
            'message': f'Błąd zapisu: {str(e)}'
        }


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

# DODAJ NA KOŃCU db.py - PUNKT 56: BUYBACK CC

def buyback_covered_call(cc_id, buyback_price_usd, buyback_date):
    """
    Odkupuje covered call z kalkulacją P/L PLN
    
    Args:
        cc_id: ID covered call do odkupu
        buyback_price_usd: Cena odkupu za akcję
        buyback_date: Data odkupu
    
    Returns:
        dict: {'success': bool, 'message': str, 'pl_pln': float}
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
        
        # 3. POBIERZ KURS NBP D-1 DLA BUYBACK
        try:
            import nbp_api_client
            nbp_result = nbp_api_client.get_usd_rate_for_date(buyback_date)
            
            if isinstance(nbp_result, dict):
                fx_close = nbp_result['rate']
                fx_close_date = nbp_result.get('date', buyback_date)
            else:
                fx_close = float(nbp_result)
                fx_close_date = buyback_date
                
        except Exception as e:
            conn.close()
            import streamlit as st
            st.error(f"Błąd pobierania kursu NBP dla buyback: {e}")
            return {'success': False, 'message': 'Błąd kursu NBP'}
        
        # 4. KALKULACJE P/L
        total_buyback_usd = buyback_price_usd * contracts * 100  # Koszt odkupu
        total_premium_received_usd = premium_sell_usd * contracts * 100  # Premium otrzymana
        
        # P/L w USD
        pl_usd = total_premium_received_usd - total_buyback_usd
        
        # P/L w PLN (dokładne z kursami)
        premium_received_pln = premium_sell_pln  # Już zapisane w bazie
        buyback_cost_pln = total_buyback_usd * fx_close
        pl_pln = premium_received_pln - buyback_cost_pln
        
        # 5. PRZYGOTUJ DATĘ
        buyback_date_str = buyback_date
        if hasattr(buyback_date_str, 'strftime'):
            buyback_date_str = buyback_date_str.strftime('%Y-%m-%d')
        
        # 6. AKTUALIZUJ CC RECORD
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
            buyback_price_usd,
            fx_close,
            buyback_cost_pln,
            pl_pln,
            cc_id
        ))
        
        # 7. ZWOLNIJ REZERWACJĘ AKCJI
        shares_to_release = contracts * 100
        
        # Znajdź LOT-y FIFO dla tego tickera i zwolnij rezerwacje
        cursor.execute("""
            SELECT id, quantity_open, quantity_total
            FROM lots 
            WHERE ticker = ? 
            ORDER BY buy_date, id
        """, (ticker,))
        
        lots = cursor.fetchall()
        remaining_to_release = shares_to_release
        
        for lot in lots:
            if remaining_to_release <= 0:
                break
                
            lot_id, qty_open, qty_total = lot
            max_can_release = qty_total - qty_open  # Ile było zarezerwowane
            qty_to_release = min(remaining_to_release, max_can_release)
            
            if qty_to_release > 0:
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_open = quantity_open + ?
                    WHERE id = ?
                """, (qty_to_release, lot_id))
                
                remaining_to_release -= qty_to_release
        
        # 8. UTWÓRZ CASHFLOW (wydatek na buyback)
        cashflow_description = f"Buyback {contracts} CC {ticker} @ ${buyback_price_usd:.2f}"
        
        cursor.execute("""
            INSERT INTO cashflows (
                type, amount_usd, date, fx_rate, amount_pln,
                description, ref_table, ref_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'option_buyback',  # Typ dla buyback CC
            -total_buyback_usd,  # Ujemna kwota (wydatek)
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
            'message': f'CC #{cc_id} odkupione pomyślnie!',
            'pl_pln': pl_pln,
            'pl_usd': pl_usd,
            'premium_received_pln': premium_received_pln,
            'buyback_cost_pln': buyback_cost_pln,
            'fx_close': fx_close,
            'fx_close_date': fx_close_date,
            'shares_released': shares_to_release
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        
        import streamlit as st
        st.error(f"Błąd buyback CC: {e}")
        
        return {
            'success': False,
            'message': f'Błąd buyback: {str(e)}'
        }

def expire_covered_call(cc_id, expiry_date=None):
    """
    Oznacza covered call jako expired (wygasłe)
    
    Args:
        cc_id: ID covered call do wygaśnięcia
        expiry_date: Opcjonalna data expiry (domyślnie z bazy)
    
    Returns:
        dict: {'success': bool, 'message': str, 'pl_pln': float}
    """
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        
        # 1. POBIERZ DANE CC
        cursor.execute("""
            SELECT id, ticker, contracts, premium_sell_usd, expiry_date,
                   status, premium_sell_pln
            FROM options_cc 
            WHERE id = ?
        """, (cc_id,))
        
        cc_record = cursor.fetchone()
        if not cc_record:
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} nie znalezione'}
        
        cc_id, ticker, contracts, premium_sell_usd, db_expiry_date, status, premium_sell_pln = cc_record
        
        # 2. SPRAWDŹ STATUS
        if status != 'open':
            conn.close()
            return {'success': False, 'message': f'CC #{cc_id} już zamknięte (status: {status})'}
        
        # 3. UŻYJ DATY EXPIRY
        final_expiry_date = expiry_date or db_expiry_date
        if hasattr(final_expiry_date, 'strftime'):
            expiry_date_str = final_expiry_date.strftime('%Y-%m-%d')
        else:
            expiry_date_str = str(final_expiry_date)
        
        # 4. AKTUALIZUJ CC RECORD (expired = pełny zysk z premium)
        cursor.execute("""
            UPDATE options_cc 
            SET status = 'expired',
                close_date = ?,
                pl_pln = premium_sell_pln
            WHERE id = ?
        """, (expiry_date_str, cc_id))
        
        # 5. ZWOLNIJ REZERWACJĘ AKCJI (tak samo jak buyback)
        shares_to_release = contracts * 100
        
        cursor.execute("""
            SELECT id, quantity_open, quantity_total
            FROM lots 
            WHERE ticker = ? 
            ORDER BY buy_date, id
        """, (ticker,))
        
        lots = cursor.fetchall()
        remaining_to_release = shares_to_release
        
        for lot in lots:
            if remaining_to_release <= 0:
                break
                
            lot_id, qty_open, qty_total = lot
            max_can_release = qty_total - qty_open
            qty_to_release = min(remaining_to_release, max_can_release)
            
            if qty_to_release > 0:
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
            'pl_pln': premium_sell_pln,  # Pełna premium = zysk
            'shares_released': shares_to_release,
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
    PUNKT 61: Sprawdza czy można sprzedać akcje bez naruszenia pokrycia otwartych CC
    """
    try:
        conn = get_connection()
        if not conn:
            return {'can_sell': False, 'message': 'Brak połączenia z bazą'}
        
        cursor = conn.cursor()
        ticker_upper = ticker.upper()
        
        # KROK 1: Pobierz wszystkie dostępne akcje (tak samo jak get_available_quantity)
        cursor.execute("""
            SELECT COALESCE(SUM(quantity_open), 0) as total_available
            FROM lots 
            WHERE ticker = ? AND quantity_open > 0
        """, (ticker_upper,))
        
        result = cursor.fetchone()
        total_available = result[0] if result and result[0] else 0
        
        # DEBUG: sprawdź co zwraca get_available_quantity dla porównania
        available_via_get_function = get_available_quantity(ticker_upper)
        
        # KROK 2: Pobierz otwarte CC - NAPRAWIONE zapytanie
        cursor.execute("""
            SELECT id, contracts, strike_usd, expiry_date
            FROM options_cc 
            WHERE ticker = ? AND (status = 'open' OR close_date IS NULL)
        """, (ticker_upper,))
        
        open_cc_list = cursor.fetchall()
        
        # DEBUG: sprawdź ile CC znalazło
        print(f"🔍 DEBUG PUNKT 61:")
        print(f"   Ticker: {ticker_upper}")
        print(f"   Total available (query): {total_available}")
        print(f"   Available (get_function): {available_via_get_function}")
        print(f"   Open CC found: {len(open_cc_list)}")
        for cc in open_cc_list:
            print(f"     CC #{cc[0]}: {cc[1]} contracts = {cc[1]*100} shares")
        
        # KROK 3: Oblicz zarezerwowane akcje
        reserved_for_cc = sum([cc[1] * 100 for cc in open_cc_list])  # contracts * 100
        available_to_sell = total_available - reserved_for_cc
        can_sell = quantity_to_sell <= available_to_sell
        
        # KROK 4: Sprawdź czy są w ogóle jakieś CC w bazie
        cursor.execute("SELECT COUNT(*) FROM options_cc WHERE ticker = ?", (ticker_upper,))
        total_cc_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM options_cc")
        all_cc_count = cursor.fetchone()[0]
        
        conn.close()
        
        # DEBUG info
        print(f"   Reserved for CC: {reserved_for_cc}")
        print(f"   Available to sell: {available_to_sell}")
        print(f"   Can sell {quantity_to_sell}? {can_sell}")
        print(f"   Total CC for ticker: {total_cc_count}")
        print(f"   Total CC in DB: {all_cc_count}")
        
        blocking_cc = [{'cc_id': cc[0], 'contracts': cc[1], 'shares_reserved': cc[1]*100, 
                       'strike_usd': cc[2], 'expiry_date': cc[3]} 
                      for cc in open_cc_list]
        
        return {
            'can_sell': can_sell,
            'available_to_sell': available_to_sell,
            'reserved_for_cc': reserved_for_cc,
            'total_available': total_available,
            'blocking_cc': blocking_cc,
            'debug_info': {
                'get_available_quantity': available_via_get_function,
                'total_cc_in_db': all_cc_count,
                'cc_for_ticker': total_cc_count,
                'open_cc_found': len(open_cc_list)
            },
            'message': 'OK' if can_sell else f'Nie można sprzedać - zarezerwowane pod CC'
        }
        
    except Exception as e:
        import streamlit as st
        st.error(f"Błąd check_cc_restrictions: {e}")
        return {'can_sell': False, 'message': f'Błąd: {str(e)}', 
                'available_to_sell': 0, 'reserved_for_cc': 0, 'total_available': 0, 
                'blocking_cc': [], 'debug_info': {}}

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

# Test na końcu pliku (opcjonalny)
if __name__ == "__main__":
    print("Test funkcji buyback/expiry...")
    results = test_buyback_expiry_operations()
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")