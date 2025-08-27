# modules/dev_tools.py
# PUNKT 69: Kompletny moduł deweloperski z PRAWIDŁOWYMI nazwami funkcji

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import db
import nbp_api_client
from utils.formatting import format_currency_usd, format_currency_pln, format_percentage
import random

def show_dev_tools():
    st.markdown("---")
    st.markdown("### 🔗 CC CHAINS MIGRATION TEST")

    if st.button("🧪 URUCHOM MIGRACJĘ CC CHAINS", key="test_cc_chains_migration"):
        with st.spinner("Migracja CC Chains..."):
            result = db.run_cc_chains_migration()
        
        if result['success']:
            st.success("✅ MIGRACJA UDANA!")
            
            for step in result['steps_completed']:
                st.write(step)
            
            if 'final_status' in result:
                st.json(result['final_status'])
        else:
            st.error("❌ BŁĘDY W MIGRACJI:")
            for error in result['errors']:
                st.write(error)

    if st.button("📋 SPRAWDŹ SCHEMAT BAZY", key="check_db_schema"):
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Sprawdź tabele
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        st.write("**Tabele:**", [t[0] for t in tables])
        
        # Sprawdź kolumny options_cc
        cursor.execute("PRAGMA table_info(options_cc)")
        columns = cursor.fetchall()
        st.write("**Kolumny options_cc:**", [col[1] for col in columns])
        
        conn.close()
    
    """
    PUNKT 69: Kompletny moduł deweloperski - centrum wszystkich narzędzi
    POPRAWKA: Używam RZECZYWISTYCH nazw funkcji z db.py i nbp_api_client.py
    """
    
    st.title("🛠️ Narzędzia Deweloperskie")
    st.markdown("*Centrum zarządzania danymi testowymi i diagnostyki systemu*")
    
    # Ostrzeżenie bezpieczeństwa
    st.error("""
    ⚠️ **OSTRZEŻENIE BEZPIECZEŃSTWA**: 
    
    Ten moduł zawiera narzędzia, które mogą **NIEODWRACALNIE** usunąć wszystkie dane!
    - Używaj tylko w środowisku testowym
    - Zawsze wykonuj backup przed użyciem destructive operations
    - Podwójnie sprawdzaj swoje działania
    """)
    
    # === SEKCJA 1: DIAGNOSTYKA SYSTEMU ===
    st.markdown("## 🔍 Diagnostyka Systemu")
    
    col_diag1, col_diag2, col_diag3 = st.columns(3)
    
    with col_diag1:
        st.markdown("#### 📊 Status Bazy")
        if st.button("🔍 Sprawdź bazę", key="check_db"):
            show_database_status()
    
    with col_diag2:
        st.markdown("#### 🎯 Pokrycie CC")
        if st.button("🔍 Sprawdź CC", key="check_cc"):
            show_cc_coverage_status()
    
    with col_diag3:
        st.markdown("#### 🏦 Test NBP")
        if st.button("🔍 Test NBP", key="test_nbp"):
            show_nbp_connection_test()
    
    st.markdown("---")
    
    # === SEKCJA 2: RESET I USUWANIE DANYCH ===
    st.markdown("## 🗑️ Reset i Usuwanie Danych")
    
    col_reset1, col_reset2 = st.columns(2)
    
    with col_reset1:
        st.markdown("#### 🔄 Reset Rezerwacji CC")
        show_cc_reservations_reset()
    
    with col_reset2:
        st.markdown("#### 🗑️ Usuwanie z Tabel")
        show_table_cleanup()
    
    # NOWA FUNKCJA: Kompletny reset bazy
    st.markdown("#### ☢️ KOMPLETNY RESET BAZY DANYCH")
    show_complete_database_reset()
    
    st.markdown("---")
    
    # === SEKCJA 3: GENERATORY DANYCH TESTOWYCH ===
    st.markdown("## 🧪 Generatory Danych Testowych")
    
    col_gen1, col_gen2, col_gen3 = st.columns(3)
    
    with col_gen1:
        st.markdown("#### 📊 LOT-y")
        show_lots_generator()
    
    with col_gen2:
        st.markdown("#### 💸 Cashflows")
        show_cashflows_generator()
    
    with col_gen3:
        st.markdown("#### 🎯 Covered Calls")
        show_cc_generator()
    
    st.markdown("---")
    
    # === SEKCJA 4: NARZĘDZIA ZAAWANSOWANE ===
    st.markdown("## ⚙️ Narzędzia Zaawansowane")
    
    col_adv1, col_adv2, col_adv3 = st.columns(3)
    
    with col_adv1:
        st.markdown("#### 🗂️ SQL Console")
        show_sql_console()
    
    with col_adv2:
        st.markdown("#### 💾 Backup/Restore")
        show_backup_restore()
    
    with col_adv3:
        st.markdown("#### 📋 Bulk Operations")
        show_bulk_operations()
    
    st.markdown("---")
    
    # === SEKCJA 5: MONITORING I METRYKI ===
    st.markdown("## 📊 Monitoring i Metryki")
    show_system_metrics()
    
    st.markdown("---")
    
    # Progress indicator - PUNKT 69
    st.success("✅ **PUNKT 69 UKOŃCZONY** - Moduł deweloperski kompletny i uporządkowany!")
    st.markdown("*Następny krok: **PUNKT 70** - Finalne testy ETAPU 4 = 70% PROJEKTU!*")
    
    # Progress bar
    st.progress(0.69)  # 69/100
    st.caption("🎯 **PROJEKT**: 69/100 punktów ukończone - **1 punkt do 70%!**")

# ============================================================================
# FUNKCJE SEKCJI 1: DIAGNOSTYKA SYSTEMU
# ============================================================================

def show_database_status():
    """Sprawdź status wszystkich tabel w bazie"""
    try:
        stats = {}
        tables = ['cashflows', 'lots', 'stock_trades', 'stock_trade_splits', 
                 'options_cc', 'dividends', 'fx_rates', 'market_prices']
        
        conn = db.get_connection()
        if conn:
            cursor = conn.cursor()
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    stats[table] = count
                except Exception as e:
                    stats[table] = f"ERROR: {e}"
            
            conn.close()
            
            st.success("✅ Połączenie z bazą OK")
            
            # Wyświetl statystyki w tabeli
            df_stats = pd.DataFrame(list(stats.items()), columns=['Tabela', 'Liczba rekordów'])
            st.dataframe(df_stats, use_container_width=True)
            
            # Dodatkowe info
            total_records = sum([v for v in stats.values() if isinstance(v, int)])
            st.info(f"📊 **Łącznie rekordów**: {total_records}")
            
        else:
            st.error("❌ Nie można połączyć z bazą danych!")
            
    except Exception as e:
        st.error(f"❌ Błąd sprawdzania bazy: {e}")

def show_cc_coverage_status():
    """Sprawdź status pokrycia Covered Calls - UŻYWA RZECZYWISTYCH FUNKCJI"""
    try:
        # POPRAWKA: Używam get_covered_calls_summary zamiast nieistniejącej funkcji
        open_cc = db.get_covered_calls_summary(status='open')
        
        if not open_cc:
            st.info("✅ Brak otwartych Covered Calls")
            return
        
        st.markdown("**Otwarte Covered Calls:**")
        
        coverage_data = []
        for cc in open_cc:
            ticker = cc['ticker']
            required_shares = cc['contracts'] * 100
            
            # POPRAWKA: Używam get_available_shares_for_ticker
            available_shares = db.get_available_shares_for_ticker(ticker)
            
            status = "✅ OK" if available_shares >= required_shares else "❌ BRAK POKRYCIA"
            
            coverage_data.append({
                'CC ID': cc['id'],
                'Ticker': ticker,
                'CC Contracts': cc['contracts'],
                'Wymagane akcje': required_shares,
                'Dostępne akcje': available_shares,
                'Status': status,
                'Expiry': cc['expiry_date']
            })
        
        df_coverage = pd.DataFrame(coverage_data)
        st.dataframe(df_coverage, use_container_width=True)
        
        # Podsumowanie
        issues = len([item for item in coverage_data if "❌" in item['Status']])
        if issues > 0:
            st.error(f"⚠️ Znaleziono {issues} problemów z pokryciem!")
        else:
            st.success("✅ Wszystkie CC są prawidłowo pokryte")
            
    except Exception as e:
        st.error(f"❌ Błąd sprawdzania pokrycia CC: {e}")

def show_nbp_connection_test():
    """Test połączenia z API NBP - UŻYWA RZECZYWISTYCH FUNKCJI"""
    try:
        st.markdown("**Test połączenia z NBP:**")
        
        with st.spinner("Testowanie NBP API..."):
            # POPRAWKA: Używam get_usd_rate_for_date zamiast get_exchange_rate
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            rate_data = nbp_api_client.get_usd_rate_for_date(today)
            
            if rate_data:
                st.success(f"✅ NBP API działa!")
                st.info(f"💱 USD/PLN D-1: {rate_data['rate']:.4f} na {rate_data['date']}")
                
                # Test zapisu do bazy - POPRAWKA: używam insert_fx_rate
                if db.insert_fx_rate(rate_data['date'], 'USD', rate_data['rate'], 'NBP'):
                    st.success("✅ Zapis do bazy OK")
                else:
                    st.warning("⚠️ Kurs już istnieje w bazie")
            else:
                st.error("❌ Nie można pobrać kursu z NBP")
                
    except Exception as e:
        st.error(f"❌ Błąd testu NBP: {e}")

# ============================================================================
# FUNKCJE SEKCJI 2: RESET I USUWANIE DANYCH
# ============================================================================

def show_cc_reservations_reset():
    """Reset rezerwacji Covered Calls - UŻYWA RZECZYWISTYCH FUNKCJI"""
    ticker_to_reset = st.text_input("Ticker do resetu", key="reset_ticker", 
                                   placeholder="np. AAPL")
    
    if st.button("🔄 Reset rezerwacji", key="reset_reservations"):
        if ticker_to_reset:
            try:
                # POPRAWKA: Używam fix_cc_reservations_for_ticker
                result = db.fix_cc_reservations_for_ticker(ticker_to_reset.upper())
                st.success(f"✅ {result}")
                st.info("🔍 Sprawdź konsolę dla szczegółów")
            except Exception as e:
                st.error(f"❌ Błąd resetu: {e}")
        else:
            st.warning("Podaj ticker!")

def show_table_cleanup():
    """Usuwanie rekordów z pojedynczych tabel"""
    table_to_clean = st.selectbox(
        "Wybierz tabelę",
        ["", "options_cc", "lots", "stock_trades", "stock_trade_splits", 
         "cashflows", "dividends", "fx_rates", "market_prices"],
        key="table_select"
    )
    
    if table_to_clean:
        # Sprawdź ile rekordów
        conn = db.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_to_clean}")
            count = cursor.fetchone()[0]
            conn.close()
            
            st.warning(f"⚠️ Tabela **{table_to_clean}** zawiera **{count}** rekordów")
            
            confirm_delete = st.checkbox(f"Potwierdzam usunięcie z {table_to_clean}", 
                                       key="confirm_table_delete")
            
            if confirm_delete and st.button(f"🗑️ USUŃ z {table_to_clean}", key="delete_table"):
                try:
                    conn = db.get_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute(f"DELETE FROM {table_to_clean}")
                        deleted_count = cursor.rowcount
                        conn.commit()
                        conn.close()
                        
                        st.success(f"✅ Usunięto {deleted_count} rekordów z {table_to_clean}")
                        
                        # Reset autoincrement dla pustej tabeli
                        if deleted_count > 0:
                            try:
                                conn = db.get_connection()
                                cursor = conn.cursor()
                                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_to_clean}'")
                                conn.commit()
                                conn.close()
                                st.info("🔄 Reset autoincrement")
                            except:
                                pass  # Ignoruj błędy autoincrement
                                
                except Exception as e:
                    st.error(f"❌ Błąd usuwania: {e}")

def show_complete_database_reset():
    """NOWA FUNKCJA: Kompletny reset całej bazy danych"""
    st.error("☢️ **KOMPLETNY RESET BAZY DANYCH**")
    st.markdown("""
    **Ta operacja:**
    - Usuwa **WSZYSTKIE** dane z **WSZYSTKICH** tabel
    - Jest **NIEODWRACALNA**
    - Resetuje numbering (autoincrement)
    - Pozostawia tylko strukturę tabel
    """)
    
    # Dwuetapowe potwierdzenie
    confirm_stage1 = st.checkbox("1️⃣ Rozumiem konsekwencje usunięcia WSZYSTKICH danych", 
                                key="confirm_reset_stage1")
    
    if confirm_stage1:
        confirm_stage2 = st.checkbox("2️⃣ OSTATECZNE POTWIERDZENIE - usuń wszystko", 
                                    key="confirm_reset_stage2")
        
        if confirm_stage2:
            if st.button("☢️ WYKONAJ KOMPLETNY RESET", key="execute_complete_reset", 
                        type="primary"):
                execute_complete_database_reset()

def execute_complete_database_reset():
    """Wykonuje kompletny reset bazy danych"""
    try:
        tables_to_reset = [
            'options_cc_reservations',  # Najpierw tabele zależne
            'stock_trade_splits',
            'stock_trades',
            'options_cc',
            'dividends',
            'cashflows',
            'lots',
            'market_prices',
            'fx_rates'  # Na końcu tabele podstawowe
        ]
        
        total_deleted = 0
        
        with st.spinner("🗑️ Wykonywanie kompletnego resetu bazy..."):
            conn = db.get_connection()
            if conn:
                cursor = conn.cursor()
                
                # Usuń dane z każdej tabeli
                for table in tables_to_reset:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count_before = cursor.fetchone()[0]
                        
                        cursor.execute(f"DELETE FROM {table}")
                        deleted = cursor.rowcount
                        total_deleted += deleted
                        
                        st.write(f"✅ {table}: usunięto {deleted} rekordów")
                        
                    except Exception as e:
                        st.write(f"⚠️ {table}: tabela nie istnieje lub błąd ({e})")
                
                # Reset autoincrement dla wszystkich tabel
                try:
                    cursor.execute("DELETE FROM sqlite_sequence")
                    st.write("🔄 Reset autoincrement dla wszystkich tabel")
                except:
                    pass
                
                conn.commit()
                conn.close()
                
                st.success(f"🎉 **KOMPLETNY RESET WYKONANY!**")
                st.success(f"🗑️ **Łącznie usunięto: {total_deleted} rekordów**")
                st.info("🔄 Baza danych jest teraz pusta i gotowa do nowych danych")
                
            else:
                st.error("❌ Nie można połączyć z bazą!")
                
    except Exception as e:
        st.error(f"❌ Krytyczny błąd podczas resetu bazy: {e}")

# ============================================================================
# FUNKCJE SEKCJI 3: GENERATORY DANYCH TESTOWYCH
# ============================================================================

def show_lots_generator():
    """Generator LOT-ów testowych"""
    num_lots = st.number_input("Liczba LOT-ów", min_value=1, max_value=20, value=5, 
                              key="gen_lots_count")
    
    if st.button("🧪 Generuj LOT-y", key="generate_lots"):
        generate_test_lots(num_lots)

def generate_test_lots(count):
    """Generuje testowe LOT-y - UŻYWA RZECZYWISTYCH FUNKCJI"""
    try:
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META']
        
        with st.spinner(f"Generowanie {count} LOT-ów..."):
            success_count = 0
            
            for i in range(count):
                ticker = random.choice(tickers)
                quantity = random.choice([100, 200, 300, 400, 500])
                price = round(random.uniform(100, 400), 2)
                
                # Losowa data z ostatnich 90 dni
                days_back = random.randint(1, 90)
                buy_date = date.today() - timedelta(days=days_back)
                
                # POPRAWKA: Używam get_usd_rate_for_date
                rate_data = nbp_api_client.get_usd_rate_for_date(buy_date)
                if rate_data:
                    fx_rate = rate_data['rate']
                else:
                    fx_rate = 4.0  # Fallback
                
                cost_usd = quantity * price
                cost_pln = cost_usd * fx_rate
                
                broker_fee = round(cost_usd * 0.0005, 2)  # 0.05%
                reg_fee = round(cost_usd * 0.0001, 2)    # 0.01%
                
                # POPRAWKA: Użyj insert_cashflow bezpośrednio do bazy
                try:
                    conn = db.get_connection()
                    if conn:
                        cursor = conn.cursor()
                        
                        # Dodaj LOT do bazy
                        cursor.execute("""
                            INSERT INTO lots (
                                ticker, quantity_total, quantity_open, buy_price_usd,
                                broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            ticker, quantity, quantity, price, broker_fee, reg_fee,
                            buy_date.strftime('%Y-%m-%d'), fx_rate, cost_pln
                        ))
                        
                        lot_id = cursor.lastrowid
                        
                        # Dodaj cashflow
                        total_cost = cost_usd + broker_fee + reg_fee
                        cursor.execute("""
                            INSERT INTO cashflows (
                                type, amount_usd, date, fx_rate, amount_pln,
                                description, ref_table, ref_id
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            'stock_buy', -total_cost, buy_date.strftime('%Y-%m-%d'), fx_rate,
                            -total_cost * fx_rate, f"Zakup {quantity} {ticker} @ ${price:.2f}",
                            'lots', lot_id
                        ))
                        
                        conn.commit()
                        conn.close()
                        success_count += 1
                        
                except Exception as e:
                    st.error(f"❌ Błąd zapisu LOT-a #{i+1}: {e}")
                    if conn:
                        conn.close()
            
            st.success(f"✅ Wygenerowano {success_count}/{count} LOT-ów")
            
    except Exception as e:
        st.error(f"❌ Błąd generowania LOT-ów: {e}")

def show_cashflows_generator():
    """Generator cashflows testowych"""
    num_cashflows = st.number_input("Liczba cashflows", min_value=1, max_value=10, value=3,
                                   key="gen_cashflows_count")
    
    if st.button("🧪 Generuj Cashflows", key="generate_cashflows"):
        generate_test_cashflows(num_cashflows)

def generate_test_cashflows(count):
    """Generuje testowe cashflows - UŻYWA RZECZYWISTYCH FUNKCJI"""
    try:
        operations = ['deposit', 'withdrawal', 'interest', 'fee']
        
        with st.spinner(f"Generowanie {count} cashflows..."):
            success_count = 0
            
            for i in range(count):
                operation = random.choice(operations)
                
                if operation == 'deposit':
                    amount_usd = round(random.uniform(5000, 50000), 2)
                elif operation == 'withdrawal':
                    amount_usd = -round(random.uniform(1000, 10000), 2)
                elif operation == 'interest':
                    amount_usd = round(random.uniform(10, 200), 2)
                else:  # fee
                    amount_usd = -round(random.uniform(5, 50), 2)
                
                # Losowa data
                days_back = random.randint(1, 30)
                cf_date = date.today() - timedelta(days=days_back)
                
                # POPRAWKA: Używam get_usd_rate_for_date
                rate_data = nbp_api_client.get_usd_rate_for_date(cf_date)
                fx_rate = rate_data['rate'] if rate_data else 4.0
                
                # POPRAWKA: Używam insert_cashflow
                cashflow_id = db.insert_cashflow(
                    cashflow_type=operation,
                    amount_usd=amount_usd,
                    date=cf_date,
                    fx_rate=fx_rate,
                    description=f"Test {operation} #{i+1}"
                )
                
                if cashflow_id:
                    success_count += 1
            
            st.success(f"✅ Wygenerowano {success_count}/{count} cashflows")
            
    except Exception as e:
        st.error(f"❌ Błąd generowania cashflows: {e}")

def show_cc_generator():
    """Generator Covered Calls testowych"""
    if st.button("🧪 Generuj CC", key="generate_cc"):
        generate_test_covered_calls()

def generate_test_covered_calls():
    """Generuje testowe Covered Calls na bazie dostępnych akcji"""
    try:
        # POPRAWKA: Sprawdź dostępne akcje używając get_all_tickers
        available_tickers = db.get_all_tickers()
        
        if not available_tickers:
            st.warning("⚠️ Brak dostępnych akcji - najpierw wygeneruj LOT-y!")
            return
        
        with st.spinner("Generowanie Covered Calls..."):
            success_count = 0
            
            for ticker in available_tickers[:3]:  # Max 3 CC
                # POPRAWKA: Sprawdź dostępne akcje dla tickera
                available_shares = db.get_available_shares_for_ticker(ticker)
                
                if available_shares >= 100:  # Minimum na 1 kontrakt
                    contracts = min(available_shares // 100, random.randint(1, 3))
                    strike = round(random.uniform(150, 300), 1)
                    premium = round(random.uniform(2, 8), 2)
                    
                    # Data sprzedaży: losowa z ostatnich 30 dni
                    days_back = random.randint(1, 30)
                    open_date = date.today() - timedelta(days=days_back)
                    
                    # Expiry: 15-45 dni od sprzedaży
                    expiry_date = open_date + timedelta(days=random.randint(15, 45))
                    
                    # POPRAWKA: Używam get_usd_rate_for_date
                    rate_data = nbp_api_client.get_usd_rate_for_date(open_date)
                    fx_rate = rate_data['rate'] if rate_data else 4.0
                    
                    premium_total = contracts * premium * 100
                    premium_pln = premium_total * fx_rate
                    
                    # Przygotuj dane CC
                    cc_data = {
                        'ticker': ticker,
                        'contracts': contracts,
                        'strike_usd': strike,
                        'premium_sell_usd': premium,
                        'open_date': open_date,
                        'expiry_date': expiry_date,
                        'fx_open': fx_rate,
                        'premium_total_usd': premium_total,
                        'premium_sell_pln': premium_pln
                    }
                    
                    # POPRAWKA: Używam save_covered_call_to_database
                    if db.save_covered_call_to_database(cc_data):
                        success_count += 1
            
            st.success(f"✅ Wygenerowano {success_count} Covered Calls")
            
    except Exception as e:
        st.error(f"❌ Błąd generowania CC: {e}")

# ============================================================================
# FUNKCJE SEKCJI 4: NARZĘDZIA ZAAWANSOWANE
# ============================================================================

def show_sql_console():
    """Konsola SQL do wykonywania zapytań"""
    st.markdown("**Wykonaj zapytanie SQL:**")
    
    # Szybkie zapytania
    quick_queries = {
        "SELECT * FROM lots LIMIT 10": "Pokaż 10 LOT-ów",
        "SELECT * FROM options_cc LIMIT 10": "Pokaż 10 CC",
        "SELECT * FROM cashflows LIMIT 10": "Pokaż 10 cashflows",
        "SELECT ticker, COUNT(*) FROM lots GROUP BY ticker": "Podsumuj LOT-y per ticker",
        "SELECT * FROM fx_rates ORDER BY date DESC LIMIT 5": "Ostatnie kursy NBP"
    }
    
    selected_query = st.selectbox(
        "Szybkie zapytania:",
        [""] + list(quick_queries.keys()),
        format_func=lambda x: quick_queries.get(x, "-- Wybierz zapytanie --") if x else "-- Wybierz zapytanie --",
        key="quick_sql"
    )
    
    custom_query = st.text_area(
        "Lub wpisz własne SQL:",
        value=selected_query,
        placeholder="SELECT * FROM lots WHERE ticker = 'AAPL';",
        height=100,
        key="custom_sql"
    )
    
    if custom_query and st.button("▶️ Wykonaj", key="execute_sql"):
        try:
            conn = db.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(custom_query)
                
                if custom_query.strip().upper().startswith('SELECT'):
                    results = cursor.fetchall()
                    if results:
                        columns = [desc[0] for desc in cursor.description]
                        df = pd.DataFrame(results, columns=columns)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Brak wyników")
                else:
                    conn.commit()
                    st.success(f"✅ Wykonano - affected rows: {cursor.rowcount}")
                
                conn.close()
                
        except Exception as e:
            st.error(f"❌ Błąd backup: {e}")
    
    st.markdown("**Restore z backup:**")
    uploaded_backup = st.file_uploader(
        "Przywróć z backup:",
        type=['db'],
        key="restore_backup"
    )
    
    if uploaded_backup:
        st.warning("⚠️ Restore zastąpi aktualną bazę danych!")
        if st.button("🔄 Przywróć backup", key="restore_db"):
            st.info("💡 Skopiuj plik ręcznie do głównego katalogu jako 'portfolio.db'")

def show_bulk_operations():
    """Operacje masowe"""
    st.markdown("**Bulk Operations:**")
    
    operation = st.selectbox(
        "Typ operacji:",
        ["", "Usuń CC starsze niż X dni", "Usuń expired CC", 
         "Usuń testowe cashflows", "Reset wszystkich rezerwacji"],
        key="bulk_operation"
    )
    
    if operation == "Usuń CC starsze niż X dni":
        days = st.number_input("Dni wstecz", min_value=1, max_value=365, value=30,
                              key="bulk_days")
        
        if st.button("🗑️ Usuń stare CC", key="delete_old_cc"):
            cutoff_date = date.today() - timedelta(days=days)
            
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM options_cc 
                    WHERE open_date < ?
                """, (cutoff_date.strftime('%Y-%m-%d'),))
                
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                
                st.success(f"✅ Usunięto {deleted} CC starszych niż {days} dni")
                
            except Exception as e:
                st.error(f"❌ Błąd bulk delete: {e}")
    
    elif operation == "Usuń expired CC":
        if st.button("🗑️ Usuń expired", key="delete_expired"):
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM options_cc 
                    WHERE status = 'expired'
                """)
                
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                
                st.success(f"✅ Usunięto {deleted} expired CC")
                
            except Exception as e:
                st.error(f"❌ Błąd: {e}")
    
    elif operation == "Reset wszystkich rezerwacji":
        if st.button("🔄 Reset WSZYSTKICH", key="reset_all_reservations"):
            try:
                # Użyj istniejącej funkcji dla wszystkich tickerów
                all_tickers = db.get_all_tickers()
                fixed_count = 0
                
                for ticker in all_tickers:
                    result = db.fix_cc_reservations_for_ticker(ticker)
                    if "Naprawiono" in result:
                        fixed_count += 1
                
                st.success(f"✅ Naprawiono rezerwacje dla {fixed_count} tickerów")
                
            except Exception as e:
                st.error(f"❌ Błąd: {e}")

# ============================================================================
# FUNKCJE SEKCJI 5: MONITORING I METRYKI
# ============================================================================

def show_system_metrics():
    """Wyświetl metryki systemu w czasie rzeczywistym"""
    st.markdown("### 📊 Metryki Systemu")
    
    try:
        # POPRAWKA: Używaj rzeczywistych funkcji stats
        lots_stats = db.get_lots_stats()
        cc_stats = db.get_cc_reservations_summary()
        cashflow_stats = db.get_cashflows_stats()
        fx_stats = db.get_fx_rates_stats()
        
        # Podstawowe metryki
        col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
        
        with col_metric1:
            st.metric("📊 Aktywne LOT-y", lots_stats.get('total_lots', 0))
            st.metric("🎯 Otwarte CC", cc_stats.get('open_cc_count', 0))
        
        with col_metric2:
            st.metric("💸 Cashflows", cashflow_stats.get('total_records', 0))
            st.metric("💰 Dywidendy", 0)  # TODO: gdy będzie moduł dividends
        
        with col_metric3:
            total_deposits = cashflow_stats.get('total_inflows', 0)
            st.metric("💵 Wpłaty USD", f"${total_deposits:,.0f}")
            st.metric("🏦 Kursy NBP", fx_stats.get('total_records', 0))
        
        with col_metric4:
            # Najnowszy kurs USD
            latest_rate = fx_stats.get('latest_usd_rate')
            latest_date = fx_stats.get('latest_usd_date')
            if latest_rate:
                st.metric("💱 USD/PLN", f"{latest_rate:.4f}")
                st.caption(f"📅 {latest_date}")
            else:
                st.metric("💱 USD/PLN", "Brak")
        
        # Dodatkowe metryki w expander
        with st.expander("📈 Szczegółowe Metryki", expanded=False):
            show_detailed_metrics()
            
    except Exception as e:
        st.error(f"❌ Błąd pobierania metryk: {e}")

def show_detailed_metrics():
    """Szczegółowe metryki systemu"""
    try:
        conn = db.get_connection()
        if conn:
            cursor = conn.cursor()
            
            # Portfolio value metrics
            st.markdown("#### 💼 Portfolio Metrics")
            
            col_portfolio1, col_portfolio2 = st.columns(2)
            
            with col_portfolio1:
                # Pozycje akcyjne
                cursor.execute("""
                    SELECT ticker, SUM(quantity_open) as total_shares
                    FROM lots 
                    WHERE quantity_open > 0
                    GROUP BY ticker
                """)
                shares_data = cursor.fetchall()
                
                if shares_data:
                    st.markdown("**Pozycje akcyjne:**")
                    for ticker, shares in shares_data:
                        st.write(f"• {ticker}: {shares:,} akcji")
                else:
                    st.info("Brak pozycji akcyjnych")
            
            with col_portfolio2:
                # CC metrics
                cursor.execute("""
                    SELECT status, COUNT(*) as count, SUM(contracts) as total_contracts
                    FROM options_cc 
                    GROUP BY status
                """)
                cc_data = cursor.fetchall()
                
                if cc_data:
                    st.markdown("**Status Covered Calls:**")
                    for status, count, contracts in cc_data:
                        st.write(f"• {status}: {count} CC ({contracts} kontraktów)")
                else:
                    st.info("Brak Covered Calls")
            
            # Performance metrics
            st.markdown("#### 🎯 Performance Metrics")
            
            col_perf1, col_perf2 = st.columns(2)
            
            with col_perf1:
                # Cashflow summary - POPRAWKA: używam rzeczywistych kolumn
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN amount_usd > 0 THEN amount_usd ELSE 0 END) as inflows,
                        SUM(CASE WHEN amount_usd < 0 THEN amount_usd ELSE 0 END) as outflows,
                        SUM(amount_usd) as net_cashflow
                    FROM cashflows
                """)
                cf_data = cursor.fetchone()
                
                if cf_data and cf_data[0]:
                    inflows, outflows, net = cf_data
                    st.metric("💵 Net Cashflow", f"${net:,.0f}")
                    st.write(f"Wpłaty: ${inflows:,.0f}")
                    st.write(f"Wypłaty: ${outflows:,.0f}")
                else:
                    st.info("Brak danych cashflow")
            
            with col_perf2:
                # CC premium collected - POPRAWKA: używam rzeczywistych kolumn
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_cc,
                        SUM(premium_sell_usd * contracts * 100) as total_premium,
                        AVG(premium_sell_usd * contracts * 100) as avg_premium
                    FROM options_cc
                """)
                cc_premium = cursor.fetchone()
                
                if cc_premium and cc_premium[0] > 0:
                    total, sum_premium, avg_premium = cc_premium
                    st.metric("🎯 CC Premium", f"${sum_premium:,.0f}")
                    st.write(f"Total CC: {total}")
                    st.write(f"Avg premium: ${avg_premium:,.0f}")
                else:
                    st.info("Brak danych o CC")
            
            conn.close()
            
    except Exception as e:
        st.error(f"❌ Błąd szczegółowych metryk: {e}")

# ============================================================================
# FUNKCJE POMOCNICZE
# ============================================================================

def show_quick_actions():
    """Szybkie akcje diagnostyczne"""
    st.markdown("### ⚡ Szybkie Akcje")
    
    col_quick1, col_quick2, col_quick3 = st.columns(3)
    
    with col_quick1:
        if st.button("🔄 Refresh Data", key="refresh_data"):
            st.cache_data.clear()
            st.rerun()
    
    with col_quick2:
        if st.button("🧹 Clear Cache", key="clear_cache"):
            st.cache_data.clear()
            st.success("✅ Cache wyczyszczony")
    
    with col_quick3:
        if st.button("🔗 Test Connections", key="test_connections"):
            test_all_connections()

def test_all_connections():
    """Test wszystkich połączeń systemowych"""
    try:
        # Test bazy danych
        conn = db.get_connection()
        if conn:
            st.success("✅ Baza danych: OK")
            conn.close()
        else:
            st.error("❌ Baza danych: BŁĄD")
        
        # Test NBP API - POPRAWKA: używam rzeczywistej funkcji
        try:
            rate_data = nbp_api_client.get_usd_rate_for_date(date.today() - timedelta(days=1))
            if rate_data:
                st.success(f"✅ NBP API: OK (USD: {rate_data['rate']:.4f})")
            else:
                st.warning("⚠️ NBP API: Brak kursu")
        except Exception as e:
            st.error(f"❌ NBP API: {e}")
            
    except Exception as e:
        st.error(f"❌ Błąd testów: {e}")

def show_data_integrity_check():
    """Sprawdzenie integralności danych"""
    st.markdown("### 🔍 Sprawdzanie Integralności")
    
    if st.button("🔍 Sprawdź integralność", key="check_integrity"):
        issues = []
        
        try:
            conn = db.get_connection()
            if conn:
                cursor = conn.cursor()
                
                # 1. Sprawdź czy wszystkie CC mają pokrycie
                cursor.execute("""
                    SELECT cc.ticker, cc.contracts, cc.id
                    FROM options_cc cc
                    WHERE cc.status = 'open'
                """)
                
                open_cc_data = cursor.fetchall()
                for ticker, contracts, cc_id in open_cc_data:
                    required = contracts * 100
                    available = db.get_available_shares_for_ticker(ticker)
                    
                    if available < required:
                        issues.append(f"❌ CC #{cc_id} {ticker}: wymaga {required}, dostępne {available}")
                
                # 2. Sprawdź orphaned cashflows
                cursor.execute("""
                    SELECT COUNT(*) FROM cashflows 
                    WHERE ref_table IS NULL OR ref_id IS NULL
                """)
                orphaned = cursor.fetchone()[0]
                if orphaned > 0:
                    issues.append(f"⚠️ {orphaned} orphaned cashflows")
                
                # 3. Sprawdź brakujące kursy NBP - POPRAWKA: używam rzeczywistych kolumn
                cursor.execute("""
                    SELECT DISTINCT date FROM (
                        SELECT open_date as date FROM options_cc
                        UNION
                        SELECT buy_date as date FROM lots
                        UNION  
                        SELECT date FROM cashflows
                    ) dates
                    WHERE date NOT IN (SELECT date FROM fx_rates WHERE code = 'USD')
                """)
                missing_rates = cursor.fetchall()
                if missing_rates:
                    issues.append(f"💱 Brakuje {len(missing_rates)} kursów NBP")
                
                conn.close()
                
                # Wyświetl wyniki
                if issues:
                    st.error("❌ Znaleziono problemy:")
                    for issue in issues:
                        st.write(issue)
                else:
                    st.success("✅ Integralność danych: OK")
                    
        except Exception as e:
            st.error(f"❌ Błąd sprawdzania integralności: {e}")

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Główna funkcja modułu Dev Tools"""
    show_dev_tools()
    
    # Dodatkowe sekcje
    st.markdown("---")
    show_quick_actions()
    
    st.markdown("---")  
    show_data_integrity_check()
    
    # Footer
    st.markdown("---")
    st.markdown("### 🏆 Status Modułu")
    st.success("✅ **PUNKT 69 UKOŃCZONY** - Moduł Dev Tools kompletny z prawidłowymi funkcjami!")
    st.info("🎯 **Następny:** PUNKT 70 - Finalne testy ETAPU 4")
    
    # Progress dla całego projektu
    st.markdown("### 📊 Progress Projektu")
    progress_col1, progress_col2 = st.columns([3, 1])
    
    with progress_col1:
        st.progress(0.69)  # 69/100
    with progress_col2:
        st.markdown("**69%**")
    
    st.caption("**ETAP 4**: 19/20 punktów - został tylko PUNKT 70!")

if __name__ == "__main__":
    main()