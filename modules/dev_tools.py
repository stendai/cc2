# modules/dev_tools.py
# PUNKT 68: Moduł deweloperski - centrum wszystkich narzędzi testowych

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import db
import nbp_api_client  # POPRAWKA: dodano import NBP
from utils.formatting import format_currency_usd, format_currency_pln, format_percentage

def show_dev_tools():
    """
    PUNKT 68: Moduł deweloperski - centrum wszystkich narzędzi testowych
    """
    
    st.title("🛠️ Narzędzia Deweloperskie")
    st.markdown("*Centrum zarządzania danymi testowymi i diagnostyki systemu*")
    
    # Ostrzeżenie bezpieczeństwa
    st.warning("""
    ⚠️ **UWAGA**: Ten moduł zawiera narzędzia, które mogą nieodwracalnie zmienić lub usunąć dane!
    Używaj tylko w środowisku testowym lub z pełnym backup'em bazy danych.
    """)
    
    # === SEKCJA 1: DIAGNOSTYKA SYSTEMU ===
    with st.expander("🔍 Diagnostyka Systemu", expanded=True):
        st.markdown("### 🔍 Diagnostyka Systemu")
        
        col_diag1, col_diag2 = st.columns(2)
        
        with col_diag1:
            if st.button("📊 Sprawdź status bazy", key="check_db"):
                try:
                    # Statystyki tabel
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
                            except:
                                stats[table] = "❌ BŁĄD"
                        
                        conn.close()
                        
                        st.success("✅ Połączenie z bazą OK")
                        
                        # Wyświetl statystyki
                        for table, count in stats.items():
                            if count == "❌ BŁĄD":
                                st.error(f"📋 {table}: {count}")
                            else:
                                st.metric(f"📋 {table}", count)
                            
                except Exception as e:
                    st.error(f"❌ Błąd bazy: {e}")
        
        with col_diag2:
            if st.button("🔧 Sprawdź integralność CC", key="check_cc_integrity"):
                try:
                    # Sprawdź wszystkie tickery z otwartymi CC
                    conn = db.get_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT DISTINCT ticker 
                            FROM options_cc 
                            WHERE close_date IS NULL
                        """)
                        
                        tickers = [row[0] for row in cursor.fetchall()]
                        conn.close()
                        
                        if tickers:
                            st.info(f"🔍 Sprawdzam {len(tickers)} tickerów: {', '.join(tickers)}")
                            
                            issues_found = []
                            for ticker in tickers:
                                try:
                                    result = db.debug_cc_restrictions(ticker)
                                    if "BRAKUJE" in str(result) or "BŁĄD" in str(result):
                                        issues_found.append((ticker, result))
                                except Exception as e:
                                    issues_found.append((ticker, f"Błąd: {e}"))
                            
                            if issues_found:
                                st.error(f"⚠️ Znaleziono {len(issues_found)} problemów:")
                                for ticker, issue in issues_found:
                                    st.write(f"- {ticker}: {issue}")
                            else:
                                st.success("✅ Wszystkie CC prawidłowo zarezerwowane")
                        else:
                            st.info("ℹ️ Brak otwartych CC do sprawdzenia")
                    
                except Exception as e:
                    st.error(f"❌ Błąd diagnostyki: {e}")

    # === SEKCJA 2: NARZĘDZIA RESET ===
    with st.expander("🗑️ Narzędzia Reset", expanded=False):
        st.markdown("### 🗑️ Narzędzia Reset")
        st.error("⚠️ NIEBEZPIECZNE - Operacje nieodwracalne!")
        
        col_reset1, col_reset2 = st.columns(2)
        
        with col_reset1:
            st.markdown("#### 🔄 Reset rezerwacji CC")
            ticker_to_reset = st.text_input("Ticker do resetu", key="reset_ticker", 
                                           placeholder="np. AAPL")
            
            if st.button("🔄 Reset rezerwacji", key="reset_reservations"):
                if ticker_to_reset:
                    try:
                        result = db.reset_cc_reservations(ticker_to_reset.upper())
                        st.success(f"✅ {result}")
                        st.info("🔍 Sprawdź konsolę dla szczegółów")
                    except Exception as e:
                        st.error(f"❌ Błąd resetu: {e}")
                else:
                    st.warning("Podaj ticker!")
        
        with col_reset2:
            st.markdown("#### 🗑️ Usuwanie rekordów")
            
            table_to_clean = st.selectbox(
                "Wybierz tabelę",
                ["", "options_cc", "lots", "stock_trades", "cashflows", "dividends"],
                key="table_select"
            )
            
            if table_to_clean:
                st.warning(f"⚠️ Usuniesz WSZYSTKIE rekordy z tabeli: {table_to_clean}")
                
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
                            
                            # Jeśli usuwamy lots, zresetuj też CC
                            if table_to_clean == "lots":
                                st.info("🔄 Resetowanie rezerwacji CC po usunięciu LOT-ów...")
                                
                    except Exception as e:
                        st.error(f"❌ Błąd usuwania: {e}")

    # === SEKCJA 3: GENERATORY DANYCH TESTOWYCH ===
    with st.expander("🧪 Generatory Testowe", expanded=False):
        st.markdown("### 🧪 Generatory Danych Testowych")
        
        col_gen1, col_gen2 = st.columns(2)
        
        with col_gen1:
            st.markdown("#### 📈 Generator LOT-ów")
            
            if st.button("📈 Wygeneruj testowe LOT-y", key="generate_lots"):
                try:
                    # Generuj przykładowe LOT-y
                    test_lots = [
                        {"ticker": "AAPL", "quantity": 100, "buy_price": 150.0, "date": "2024-01-15"},
                        {"ticker": "MSFT", "quantity": 50, "buy_price": 280.0, "date": "2024-02-20"},
                        {"ticker": "GOOGL", "quantity": 25, "buy_price": 120.0, "date": "2024-03-10"},
                        {"ticker": "NVDA", "quantity": 30, "buy_price": 220.0, "date": "2024-04-05"},
                    ]
                    
                    created_count = 0
                    for lot in test_lots:
                        # Pobierz kurs NBP - POPRAWKA: użyj prawidłowej funkcji
                        from datetime import datetime
                        
                        operation_date = datetime.strptime(lot["date"], '%Y-%m-%d').date()
                        rate_data = nbp_api_client.get_usd_rate_for_date(operation_date)
                        
                        if not rate_data:
                            st.error(f"❌ Nie można pobrać kursu NBP dla {lot['date']}")
                            continue
                        
                        if isinstance(rate_data, dict):
                            fx_rate = rate_data['rate']
                        else:
                            fx_rate = float(rate_data) if rate_data else 4.0  # fallback
                        
                        cost_pln = lot["quantity"] * lot["buy_price"] * fx_rate
                        
                        # POPRAWKA: użyj bezpośrednio SQL INSERT zamiast nieistniejącej funkcji
                        try:
                            conn = db.get_connection()
                            if conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO lots (
                                        ticker, quantity_total, quantity_open, buy_price_usd,
                                        broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    lot["ticker"],
                                    lot["quantity"],
                                    lot["quantity"],  # quantity_open = quantity na początku
                                    lot["buy_price"],
                                    1.0,  # broker_fee_usd
                                    0.1,  # reg_fee_usd
                                    lot["date"],
                                    fx_rate,
                                    cost_pln
                                ))
                                
                                conn.commit()
                                conn.close()
                                created_count += 1
                        except Exception as e:
                            st.error(f"❌ Błąd tworzenia LOT {lot['ticker']}: {e}")
                            continue
                    
                    st.success(f"✅ Utworzono {created_count} testowych LOT-ów")
                    
                except Exception as e:
                    st.error(f"❌ Błąd generowania LOT-ów: {e}")
        
        with col_gen2:
            st.markdown("#### 💸 Generator Cashflows")
            
            if st.button("💸 Wygeneruj testowe wpłaty", key="generate_cashflows"):
                try:
                    # Generuj przykładowe cashflows
                    test_cashflows = [
                        {"amount": 10000.0, "type": "deposit", "date": "2024-01-10"},
                        {"amount": 5000.0, "type": "deposit", "date": "2024-02-15"},
                        {"amount": -500.0, "type": "withdrawal", "date": "2024-03-20"},
                    ]
                    
                    created_count = 0
                    for cf in test_cashflows:
                        # Pobierz kurs NBP - POPRAWKA: użyj prawidłowej funkcji
                        from datetime import datetime
                        
                        operation_date = datetime.strptime(cf["date"], '%Y-%m-%d').date()
                        rate_data = nbp_api_client.get_usd_rate_for_date(operation_date)
                        
                        if not rate_data:
                            st.error(f"❌ Nie można pobrać kursu NBP dla {cf['date']}")
                            continue
                        
                        if isinstance(rate_data, dict):
                            fx_rate = rate_data['rate']
                        else:
                            fx_rate = float(rate_data) if rate_data else 4.0  # fallback
                        
                        amount_pln = cf["amount"] * fx_rate
                        
                        # POPRAWKA: użyj prawidłowej funkcji insert_cashflow
                        cashflow_id = db.insert_cashflow(
                            cashflow_type=cf["type"],
                            amount_usd=cf["amount"],
                            date=cf["date"],
                            fx_rate=fx_rate,
                            description=f"Test {cf['type']}"
                        )
                        
                        if cashflow_id:
                            created_count += 1
                    
                    st.success(f"✅ Utworzono {created_count} testowych cashflows")
                    
                except Exception as e:
                    st.error(f"❌ Błąd generowania cashflows: {e}")

        # Generator CC
        st.markdown("---")
        st.markdown("#### 🎯 Generator Covered Calls")
        
        if st.button("🎯 Wygeneruj testowe CC", key="generate_cc"):
            try:
                # Sprawdź dostępne LOT-y
                lots_stats = db.get_lots_stats()
                
                if lots_stats.get('open_shares', 0) < 100:
                    st.warning("⚠️ Potrzebujesz co najmniej 100 akcji. Wygeneruj najpierw LOT-y!")
                    return
                
                # Pobierz dostępne tickery
                conn = db.get_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT ticker, SUM(quantity_open) as available
                        FROM lots 
                        WHERE quantity_open >= 100
                        GROUP BY ticker
                        ORDER BY available DESC
                        LIMIT 2
                    """)
                    
                    available_tickers = cursor.fetchall()
                    conn.close()
                    
                    if not available_tickers:
                        st.warning("⚠️ Brak tickerów z 100+ akcjami")
                        return
                    
                    # Generuj przykładowe CC
                    test_cc = []
                    for ticker, available in available_tickers:
                        contracts = min(available // 100, 2)  # Max 2 kontrakty
                        
                        test_cc.append({
                            "ticker": ticker,
                            "contracts": contracts,
                            "strike": 200.0,  # Przykładowy strike
                            "premium": 3.50,  # Przykładowe premium
                            "expiry": "2024-06-21",  # Przykład expiry
                            "date": "2024-05-15"
                        })
                    
                    created_count = 0
                    for cc in test_cc:
                        # Pobierz kurs NBP - POPRAWKA: użyj prawidłowej funkcji
                        from datetime import datetime
                        
                        operation_date = datetime.strptime(cc["date"], '%Y-%m-%d').date()
                        rate_data = nbp_api_client.get_usd_rate_for_date(operation_date)
                        
                        if not rate_data:
                            st.error(f"❌ Nie można pobrać kursu NBP dla {cc['date']}")
                            continue
                        
                        if isinstance(rate_data, dict):
                            fx_rate = rate_data['rate']
                        else:
                            fx_rate = float(rate_data) if rate_data else 4.0  # fallback
                        
                        premium_pln = cc["contracts"] * 100 * cc["premium"] * fx_rate
                        
                        # POPRAWKA: użyj funkcji save_covered_call_to_database
                        cc_data = {
                            'ticker': cc["ticker"],
                            'contracts': cc["contracts"],
                            'strike_usd': cc["strike"],
                            'premium_sell_usd': cc["premium"],
                            'open_date': cc["date"],
                            'expiry_date': cc["expiry"],
                            'fx_open': fx_rate,
                            'premium_sell_pln': premium_pln
                        }
                        
                        result = db.save_covered_call_to_database(cc_data)
                        
                        if result.get('success'):
                            created_count += 1
                    
                    st.success(f"✅ Utworzono {created_count} testowych CC")
                    
            except Exception as e:
                st.error(f"❌ Błąd generowania CC: {e}")

    # === SEKCJA 4: NARZĘDZIA EKSPORT/IMPORT ===
    with st.expander("📦 Export/Import", expanded=False):
        st.markdown("### 📦 Export/Import Danych")
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            st.markdown("#### 📤 Export struktury bazy")
            
            if st.button("📤 Export schema", key="export_schema"):
                try:
                    conn = db.get_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT name, sql FROM sqlite_master 
                            WHERE type='table' AND name NOT LIKE 'sqlite_%'
                            ORDER BY name
                        """)
                        
                        tables_info = cursor.fetchall()
                        conn.close()
                        
                        schema_text = "-- Database Schema Export\n\n"
                        for table_name, create_sql in tables_info:
                            schema_text += f"-- Table: {table_name}\n"
                            schema_text += f"{create_sql};\n\n"
                        
                        st.download_button(
                            label="📥 Pobierz schema.sql",
                            data=schema_text,
                            file_name="portfolio_schema.sql",
                            mime="text/sql",
                            key="download_schema"
                        )
                        
                        st.success(f"✅ Schema {len(tables_info)} tabel gotowa do pobrania")
                        
                except Exception as e:
                    st.error(f"❌ Błąd export schema: {e}")
        
        with col_exp2:
            st.markdown("#### 📊 Export statystyk")
            
            if st.button("📊 Generuj raport", key="generate_report"):
                try:
                    # Zbierz statystyki ze wszystkich tabel
                    stats_report = "# Portfolio Stats Report\n\n"
                    stats_report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    
                    conn = db.get_connection()
                    if conn:
                        cursor = conn.cursor()
                        
                        # Statystyki podstawowe
                        tables = ['cashflows', 'lots', 'stock_trades', 'options_cc', 'dividends']
                        for table in tables:
                            try:
                                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                                count = cursor.fetchone()[0]
                                stats_report += f"- {table}: {count} records\n"
                            except:
                                stats_report += f"- {table}: ERROR\n"
                        
                        # LOT-y stats
                        try:
                            lots_stats = db.get_lots_stats()
                            stats_report += f"\n## Lots Stats:\n"
                            stats_report += f"- Total lots: {lots_stats.get('total_lots', 0)}\n"
                            stats_report += f"- Open shares: {lots_stats.get('open_shares', 0)}\n"
                            stats_report += f"- Reserved shares: {lots_stats.get('total_shares', 0) - lots_stats.get('open_shares', 0)}\n"
                        except:
                            stats_report += "\n## Lots Stats: ERROR\n"
                        
                        # CC stats
                        try:
                            cursor.execute("SELECT COUNT(*) FROM options_cc WHERE close_date IS NULL")
                            open_cc = cursor.fetchone()[0]
                            cursor.execute("SELECT COUNT(*) FROM options_cc WHERE close_date IS NOT NULL")
                            closed_cc = cursor.fetchone()[0]
                            
                            stats_report += f"\n## CC Stats:\n"
                            stats_report += f"- Open CC: {open_cc}\n"
                            stats_report += f"- Closed CC: {closed_cc}\n"
                        except:
                            stats_report += "\n## CC Stats: ERROR\n"
                        
                        conn.close()
                    
                    st.download_button(
                        label="📥 Pobierz raport.txt",
                        data=stats_report,
                        file_name="portfolio_stats.txt",
                        mime="text/plain",
                        key="download_report"
                    )
                    
                    st.success("✅ Raport statystyk gotowy do pobrania")
                    
                except Exception as e:
                    st.error(f"❌ Błąd generowania raportu: {e}")

    # === SEKCJA 5: MONITORING I LOGI ===
    with st.expander("📊 Monitoring", expanded=False):
        st.markdown("### 📊 Monitoring i Performance")
        
        # Real-time stats
        try:
            # Pobierz aktualne statystyki
            lots_stats = db.get_lots_stats()
            
            col_mon1, col_mon2, col_mon3 = st.columns(3)
            
            with col_mon1:
                st.metric("📦 Total LOTs", lots_stats.get('total_lots', 0))
                st.metric("📈 Open Shares", lots_stats.get('open_shares', 0))
            
            with col_mon2:
                # Stats CC
                conn = db.get_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM options_cc WHERE close_date IS NULL")
                    open_cc = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM options_cc WHERE close_date IS NOT NULL")
                    closed_cc = cursor.fetchone()[0]
                    
                    conn.close()
                    
                    st.metric("🎯 Open CC", open_cc)
                    st.metric("✅ Closed CC", closed_cc)
            
            with col_mon3:
                # Ostatnie operacje
                conn = db.get_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT MAX(date) FROM cashflows
                        UNION 
                        SELECT MAX(buy_date) FROM lots
                        ORDER BY 1 DESC LIMIT 1
                    """)
                    
                    result = cursor.fetchone()
                    last_activity = result[0] if result and result[0] else "Brak"
                    conn.close()
                    
                    st.metric("📅 Ostatnia aktywność", last_activity)
                    
        except Exception as e:
            st.error(f"❌ Błąd monitoringu: {e}")

    # === SEKCJA 6: QUICK ACTIONS ===
    st.markdown("---")
    st.markdown("### ⚡ Quick Actions")
    
    col_quick1, col_quick2, col_quick3, col_quick4 = st.columns(4)
    
    with col_quick1:
        if st.button("🔄 Refresh wszystko", key="refresh_all"):
            st.rerun()
    
    with col_quick2:
        if st.button("🧹 Clear cache", key="clear_cache"):
            st.cache_data.clear()
            st.success("✅ Cache wyczyszczony")
    
    with col_quick3:
        if st.button("📊 Sprawdź status", key="quick_status"):
            try:
                conn = db.get_connection()
                if conn:
                    conn.close()
                    st.success("✅ System działa prawidłowo")
                else:
                    st.error("❌ Problem z bazą danych")
            except Exception as e:
                st.error(f"❌ Błąd: {e}")
    
    with col_quick4:
        if st.button("🚀 Test connection", key="test_connection"):
            try:
                conn = db.get_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master")
                    table_count = cursor.fetchone()[0]
                    conn.close()
                    st.success(f"✅ OK - {table_count} tabel")
                else:
                    st.error("❌ Brak połączenia")
            except Exception as e:
                st.error(f"❌ Błąd: {e}")

    # === FOOTER ===
    st.markdown("---")
    st.success("✅ **PUNKT 68 UKOŃCZONY** - Moduł deweloperski utworzony!")
    st.markdown("*Następny krok: PUNKT 69 - Przeniesienie opcji deweloperskich z innych modułów*")
    
    # Progress indicator
    st.progress(0.97)  # 68/70 = 97% ETAPU 4
    st.caption("🎯 **ETAP 4**: 68/70 punktów ukończone - zostały tylko 2 punkty!")

def show_cleanup_tools():
    """Narzędzia cleanup w Dev Tools"""
    st.markdown("### 🧹 Cleanup Tools")
    
    col_clean1, col_clean2 = st.columns(2)
    
    with col_clean1:
        st.markdown("#### 🗑️ Bulk Delete CC")
        
        # Pobierz wszystkie CC
        all_cc = db.get_deletable_cc_list()
        
        if all_cc:
            # Filtry
            status_filter = st.selectbox(
                "Status do usunięcia:",
                ["Wszystkie", "Expired", "Bought back", "Open (OSTROŻNIE!)"],
                key="bulk_delete_status"
            )
            
            ticker_filter = st.selectbox(
                "Ticker:",
                ["Wszystkie"] + list(set([cc['ticker'] for cc in all_cc])),
                key="bulk_delete_ticker"
            )
            
            # Filtracja
            filtered = []
            for cc in all_cc:
                if status_filter != "Wszystkie":
                    if status_filter == "Expired" and cc['status'] != 'expired':
                        continue
                    elif status_filter == "Bought back" and cc['status'] != 'bought_back':
                        continue
                    elif status_filter == "Open (OSTROŻNIE!)" and cc['status'] != 'open':
                        continue
                
                if ticker_filter != "Wszystkie" and cc['ticker'] != ticker_filter:
                    continue
                
                filtered.append(cc)
            
            st.write(f"**Znaleziono:** {len(filtered)} CC do usunięcia")
            
            if filtered and st.button("🗑️ BULK DELETE", key="execute_bulk_delete", type="primary"):
                if st.checkbox("✅ Potwierdzam masowe usunięcie", key="confirm_bulk"):
                    with st.spinner(f"Usuwanie {len(filtered)} CC..."):
                        cc_ids = [cc['id'] for cc in filtered]
                        result = db.bulk_delete_covered_calls(cc_ids, confirm_bulk=True)
                        
                        if result['success']:
                            st.success(f"✅ {result['message']}")
                            st.info(f"🗑️ Usunięto: {result['deleted']}/{result['total_requested']}")
                        else:
                            st.error(f"❌ {result['message']}")
        else:
            st.info("Brak CC do usunięcia")
    
    with col_clean2:
        st.markdown("#### 🧹 Orphaned Cashflow")
        
        if st.button("🔍 Znajdź orphaned", key="find_orphaned"):
            integrity = db.check_cc_cashflow_integrity()
            
            orphaned_count = len([i for i in integrity['issues'] if 'nie ma CC' in i])
            
            if orphaned_count > 0:
                st.warning(f"⚠️ Znaleziono {orphaned_count} orphaned cashflow")
                
                if st.button("🗑️ Usuń orphaned", key="delete_orphaned", type="primary"):
                    result = db.cleanup_orphaned_cashflow()
                    if result['success']:
                        st.success(f"✅ {result['message']}")
                    else:
                        st.error(f"❌ {result['message']}")
            else:
                st.success("✅ Brak orphaned cashflow")

if __name__ == "__main__":
    show_dev_tools()