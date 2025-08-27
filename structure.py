"""
Definicje struktur tabel SQLite dla Covered Call Dashboard
Punkt 6: Tabela fx_rates + funkcje tworzenia tabel
"""

import sqlite3
from datetime import datetime
import streamlit as st

def create_fx_rates_table(conn):
    """
    Utworzenie tabeli fx_rates - kursy walut NBP
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        bool: True jeśli sukces
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fx_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                code TEXT NOT NULL DEFAULT 'USD',
                rate DECIMAL(10,6) NOT NULL,
                source TEXT DEFAULT 'NBP',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, code)
            )
        """)
        
        # Indeks dla szybkiego wyszukiwania po dacie
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fx_rates_date 
            ON fx_rates(date DESC)
        """)
        
        # Indeks dla wyszukiwania po kodzie waluty i dacie
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fx_rates_code_date 
            ON fx_rates(code, date DESC)
        """)
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Błąd tworzenia tabeli fx_rates: {e}")
        return False

def create_all_tables(conn):
    """
    Utworzenie wszystkich tabel w bazie danych
    Punkty 6-8: fx_rates + cashflows + lots
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        dict: Status tworzenia poszczególnych tabel
    """
    results = {}
    
    # Tabela fx_rates (punkt 6)
    results['fx_rates'] = create_fx_rates_table(conn)
    
    # Tabela cashflows (punkt 7) 
    results['cashflows'] = create_cashflows_table(conn)
    
    # Tabela lots (punkt 8)
    results['lots'] = create_lots_table(conn)
    
    # TODO: Kolejne tabele w punktach 9-10:
    # results['stock_trades'] = create_stock_trades_table(conn)  # punkt 9
    # results['options_cc'] = create_options_cc_table(conn)      # punkt 10
    # results['dividends'] = create_dividends_table(conn)        # punkt 10
    # results['market_prices'] = create_market_prices_table(conn) # punkt 10
    # results['cc_chains'] = create_cc_chains_table(conn)	
    
    return results

def get_table_info(conn, table_name):
    """
    Pobiera informacje o strukturze tabeli
    
    Args:
        conn: sqlite3.Connection
        table_name: str - nazwa tabeli
    
    Returns:
        list: Lista kolumn tabeli
    """
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Błąd pobierania informacji o tabeli {table_name}: {e}")
        return []

def table_exists(conn, table_name):
    """
    Sprawdza czy tabela istnieje w bazie
    
    Args:
        conn: sqlite3.Connection  
        table_name: str - nazwa tabeli
    
    Returns:
        bool: True jeśli tabela istnieje
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        return cursor.fetchone()[0] > 0
    except Exception as e:
        st.error(f"Błąd sprawdzania istnienia tabeli {table_name}: {e}")
        return False

def get_all_tables(conn):
    """
    Pobiera listę wszystkich tabel w bazie
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        list: Lista nazw tabel
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"Błąd pobierania listy tabel: {e}")
        return []

# Test funkcji dla debugowania
if __name__ == "__main__":
    print("Test struktur tabel:")
    
    # Test connection
    try:
        conn = sqlite3.connect(":memory:")  # Test w pamięci
        
        # Test tworzenia tabeli fx_rates
        success = create_fx_rates_table(conn)
        print(f"Tworzenie fx_rates: {'✅' if success else '❌'}")
        
        # Test sprawdzania istnienia tabeli
        exists = table_exists(conn, 'fx_rates')
        print(f"Tabela fx_rates istnieje: {'✅' if exists else '❌'}")
        
        # Test informacji o tabeli
        info = get_table_info(conn, 'fx_rates')
        print(f"Kolumny fx_rates: {len(info)} kolumn")
        for col in info:
            print(f"  - {col[1]} ({col[2]})")
            
        # Test listy tabel
        tables = get_all_tables(conn)
        print(f"Wszystkie tabele: {tables}")
        
        conn.close()
        print("✅ Test struktur zakończony pomyślnie!")
        
    except Exception as e:
        print(f"❌ Błąd testu struktur: {e}")

def create_cashflows_table(conn):
    """
    Utworzenie tabeli cashflows - przepływy pieniężne
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        bool: True jeśli sukces
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cashflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                amount_usd DECIMAL(15,2) NOT NULL,
                date DATE NOT NULL,
                fx_rate DECIMAL(10,6) NOT NULL,
                amount_pln DECIMAL(15,2) NOT NULL,
                description TEXT,
                ref_table TEXT,
                ref_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indeksy dla wydajności
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cashflows_date 
            ON cashflows(date DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cashflows_type 
            ON cashflows(type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cashflows_ref 
            ON cashflows(ref_table, ref_id)
        """)
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Błąd tworzenia tabeli cashflows: {e}")
        return False

def create_lots_table(conn):
    """
    Utworzenie tabeli lots - LOT-y akcji (zakupy)
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        bool: True jeśli sukces
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                quantity_total INTEGER NOT NULL,
                quantity_open INTEGER NOT NULL,
                buy_price_usd DECIMAL(10,4) NOT NULL,
                broker_fee_usd DECIMAL(10,2) DEFAULT 0.00,
                reg_fee_usd DECIMAL(10,2) DEFAULT 0.00,
                buy_date DATE NOT NULL,
                fx_rate DECIMAL(10,6) NOT NULL,
                cost_pln DECIMAL(15,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_quantities CHECK (quantity_open <= quantity_total),
                CONSTRAINT chk_quantities_positive CHECK (quantity_total > 0 AND quantity_open >= 0)
            )
        """)
        
        # Indeksy dla wydajności i logiki FIFO
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lots_ticker_date 
            ON lots(ticker, buy_date, id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lots_ticker_open 
            ON lots(ticker, quantity_open) WHERE quantity_open > 0
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lots_date 
            ON lots(buy_date DESC)
        """)
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Błąd tworzenia tabeli lots: {e}")
        return False
# DODAJ te funkcje do structure.py

def create_stock_trades_table(conn):
    """
    Utworzenie tabeli stock_trades - sprzedaże akcji (główna operacja)
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        bool: True jeśli sukces
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                sell_price_usd DECIMAL(10,4) NOT NULL,
                sell_date DATE NOT NULL,
                fx_rate DECIMAL(10,6) NOT NULL,
                broker_fee_usd DECIMAL(10,2) DEFAULT 0.00,
                reg_fee_usd DECIMAL(10,2) DEFAULT 0.00,
                proceeds_pln DECIMAL(15,2) NOT NULL,
                cost_pln DECIMAL(15,2) NOT NULL,
                pl_pln DECIMAL(15,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_quantity_positive CHECK (quantity > 0)
            )
        """)
        
        # Indeksy
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_trades_ticker_date 
            ON stock_trades(ticker, sell_date DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_trades_date 
            ON stock_trades(sell_date DESC)
        """)
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Błąd tworzenia tabeli stock_trades: {e}")
        return False

def create_stock_trade_splits_table(conn):
    """
    Utworzenie tabeli stock_trade_splits - rozbicie sprzedaży po LOT-ach
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        bool: True jeśli sukces
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_trade_splits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER NOT NULL,
                lot_id INTEGER NOT NULL,
                qty_from_lot INTEGER NOT NULL,
                cost_part_pln DECIMAL(15,2) NOT NULL,
                commission_part_usd DECIMAL(10,2) NOT NULL,
                commission_part_pln DECIMAL(15,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trade_id) REFERENCES stock_trades(id),
                FOREIGN KEY (lot_id) REFERENCES lots(id),
                CONSTRAINT chk_qty_positive CHECK (qty_from_lot > 0)
            )
        """)
        
        # Indeksy
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_splits_trade 
            ON stock_trade_splits(trade_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_splits_lot 
            ON stock_trade_splits(lot_id)
        """)
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Błąd tworzenia tabeli stock_trade_splits: {e}")
        return False

# ZAKTUALIZUJ funkcję create_all_tables() w structure.py:

def create_all_tables(conn):
    """
    Utworzenie wszystkich tabel w bazie danych
    Punkty 6-9: fx_rates + cashflows + lots + stock_trades
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        dict: Status tworzenia poszczególnych tabel
    """
    results = {}
    
    # Tabela fx_rates (punkt 6)
    results['fx_rates'] = create_fx_rates_table(conn)
    
    # Tabela cashflows (punkt 7) 
    results['cashflows'] = create_cashflows_table(conn)
    
    # Tabela lots (punkt 8)
    results['lots'] = create_lots_table(conn)
    
    # Tabele stock_trades (punkt 9)
    results['stock_trades'] = create_stock_trades_table(conn)
    results['stock_trade_splits'] = create_stock_trade_splits_table(conn)
    
    # TODO: Kolejne tabele w punkcie 10:
    # results['options_cc'] = create_options_cc_table(conn)      # punkt 10
    # results['dividends'] = create_dividends_table(conn)        # punkt 10
    # results['market_prices'] = create_market_prices_table(conn) # punkt 10
    
    return results

# DODAJ te funkcje do structure.py

def create_options_cc_table(conn):
    """
    Utworzenie tabeli options_cc - covered calls
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        bool: True jeśli sukces
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS options_cc (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                lot_linked_id INTEGER,
                contracts INTEGER NOT NULL,
                strike_usd DECIMAL(10,4) NOT NULL,
                premium_sell_usd DECIMAL(10,4) NOT NULL,
                premium_buyback_usd DECIMAL(10,4),
                open_date DATE NOT NULL,
                close_date DATE,
                expiry_date DATE NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                fx_open DECIMAL(10,6) NOT NULL,
                fx_close DECIMAL(10,6),
                premium_sell_pln DECIMAL(15,2) NOT NULL,
                premium_buyback_pln DECIMAL(15,2),
                pl_pln DECIMAL(15,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lot_linked_id) REFERENCES lots(id),
                CONSTRAINT chk_contracts_positive CHECK (contracts > 0),
                CONSTRAINT chk_status CHECK (status IN ('open', 'expired', 'bought_back'))
            )
        """)
        
        # Indeksy
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_options_cc_ticker_status 
            ON options_cc(ticker, status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_options_cc_expiry 
            ON options_cc(expiry_date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_options_cc_lot 
            ON options_cc(lot_linked_id)
        """)
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Błąd tworzenia tabeli options_cc: {e}")
        return False

def create_dividends_table(conn):
    """
    Utworzenie tabeli dividends - dywidendy
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        bool: True jeśli sukces
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dividends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                gross_usd DECIMAL(10,4) NOT NULL,
                date_paid DATE NOT NULL,
                fx_rate DECIMAL(10,6) NOT NULL,
                gross_pln DECIMAL(15,2) NOT NULL,
                wht_15_pln DECIMAL(15,2) NOT NULL,
                tax_4_pln DECIMAL(15,2) NOT NULL,
                net_pln DECIMAL(15,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_gross_positive CHECK (gross_usd > 0)
            )
        """)
        
        # Indeksy
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dividends_ticker_date 
            ON dividends(ticker, date_paid DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dividends_date 
            ON dividends(date_paid DESC)
        """)
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Błąd tworzenia tabeli dividends: {e}")
        return False

def create_market_prices_table(conn):
    """
    Utworzenie tabeli market_prices - cache cen rynkowych
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        bool: True jeśli sukces
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date DATE NOT NULL,
                price_usd DECIMAL(10,4) NOT NULL,
                source TEXT DEFAULT 'yfinance',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, date),
                CONSTRAINT chk_price_positive CHECK (price_usd > 0)
            )
        """)
        
        # Indeksy
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_prices_ticker_date 
            ON market_prices(ticker, date DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_prices_date 
            ON market_prices(date DESC)
        """)
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Błąd tworzenia tabeli market_prices: {e}")
        return False

# ZAKTUALIZUJ funkcję create_all_tables() w structure.py:

def create_all_tables(conn):
    """
    Utworzenie wszystkich tabel w bazie danych
    Punkty 6-10: WSZYSTKIE TABELE GOTOWE!
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        dict: Status tworzenia poszczególnych tabel
    """
    results = {}
    
    # Tabela fx_rates (punkt 6)
    results['fx_rates'] = create_fx_rates_table(conn)
    
    # Tabela cashflows (punkt 7) 
    results['cashflows'] = create_cashflows_table(conn)
    
    # Tabela lots (punkt 8)
    results['lots'] = create_lots_table(conn)
    
    # Tabele stock_trades (punkt 9)
    results['stock_trades'] = create_stock_trades_table(conn)
    results['stock_trade_splits'] = create_stock_trade_splits_table(conn)
    
    # Ostatnie tabele (punkt 10)
    results['options_cc'] = create_options_cc_table(conn)
    results['dividends'] = create_dividends_table(conn)
    results['market_prices'] = create_market_prices_table(conn)
    
    return results

def get_database_schema_info(conn):
    """
    Pobranie informacji o schemacie bazy danych
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        dict: Informacje o wszystkich tabelach
    """
    try:
        cursor = conn.cursor()
        
        # Lista wszystkich tabel
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_info = {}
        
        for table in tables:
            # Informacje o kolumnach
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            # Liczba rekordów
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            record_count = cursor.fetchone()[0]
            
            schema_info[table] = {
                'columns': len(columns),
                'records': record_count,
                'column_details': [{
                    'name': col[1],
                    'type': col[2],
                    'not_null': bool(col[3]),
                    'primary_key': bool(col[5])
                } for col in columns]
            }
        
        return schema_info
        
    except Exception as e:
        st.error(f"Błąd pobierania schematu: {e}")
        return {}

# PUNKT 71: Tabela cc_chains w structure.py
# Dodaj tę funkcję do pliku structure.py

def create_cc_chains_table(conn):
    """
    🔗 PUNKT 71: Utworzenie tabeli cc_chains - łańcuchy opcyjne
    
    CC Chain = grupa powiązanych covered calls na tym samym tickerze,
    gdzie każde kolejne CC jest wystawiane po zamknięciu poprzedniego.
    
    Args:
        conn: sqlite3.Connection
    
    Returns:
        bool: True jeśli sukces
    """
    try:
        cursor = conn.cursor()
        
        # Tabela cc_chains
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cc_chains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id INTEGER NOT NULL,       -- 🔗 POWIĄZANIE Z LOT-EM!
                ticker TEXT NOT NULL,          -- dublowanie dla ułatwienia queries
                chain_name TEXT,               -- np. "WOLF Chain #1 (LOT #5)"
                start_date DATE NOT NULL,      -- data pierwszego CC w chain
                end_date DATE,                 -- data zamknięcia ostatniego CC (NULL = aktywny)
                status TEXT NOT NULL DEFAULT 'active',  -- active, closed
                total_contracts INTEGER DEFAULT 0,      -- suma kontraktów w chain
                total_premium_usd DECIMAL(15,4) DEFAULT 0,  -- suma premii w USD
                total_pl_pln DECIMAL(15,2) DEFAULT 0,       -- łączny P/L w PLN
                avg_duration_days DECIMAL(8,2) DEFAULT 0,   -- średni czas trwania CC
                success_rate DECIMAL(5,2) DEFAULT 0,        -- % zyskownych CC
                annualized_return DECIMAL(8,4) DEFAULT 0,   -- zwrot roczny %
                notes TEXT,                    -- notatki użytkownika
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lot_id) REFERENCES lots(id) ON DELETE CASCADE
            )
        """)
        
        # Indeksy dla wydajności
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cc_chains_lot_id 
            ON cc_chains(lot_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cc_chains_ticker_status 
            ON cc_chains(ticker, status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cc_chains_status_date 
            ON cc_chains(status, start_date DESC)
        """)
        
        conn.commit()
        return True
        
    except Exception as e:
        import streamlit as st
        st.error(f"Błąd tworzenia tabeli cc_chains: {e}")
        return False



