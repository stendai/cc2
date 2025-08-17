"""
Streamlit Covered Call Dashboard - Główna aplikacja
ETAP 1 UKOŃCZONY: Punkty 1-15 (NBP API + Cache + Seed data)

STATUS PROJEKTU:
✅ PUNKTY 1-5: Fundament aplikacji (struktura, nawigacja, baza, utils, testy)
✅ PUNKTY 6-10: Struktura bazy danych (9 tabel + operacje CRUD + logika FIFO)
✅ PUNKTY 11-15: NBP API Client kompletny (cache + seed + święta + auto-seed)

NASTĘPNE ETAPY:
🔄 PUNKTY 16-30: Moduł Cashflows (ETAP 2)
🔄 PUNKTY 31-50: Moduł Stocks (ETAP 3)
🔄 PUNKTY 51-70: Moduł Options (ETAP 4)
🔄 PUNKTY 71-80: Moduł Dividends (ETAP 5)
🔄 PUNKTY 81-90: Moduł Taxes (ETAP 6)
🔄 PUNKTY 91-100: Dashboard + finalizacja (ETAP 7)

UKOŃCZONE KOMPONENTY ETAPU 1:
- Struktura aplikacji Streamlit z 8 modułami
- Pełna baza danych SQLite (9 tabel)
- Operacje CRUD dla wszystkich tabel
- Logika FIFO dla sprzedaży akcji
- Podstawowe utils (formatowanie)
- NBP API Client z pełną funkcjonalnością:
  * Pobieranie kursów USD z API NBP
  * Cache'owanie w bazie danych
  * Obsługa weekendów i świąt narodowych
  * Bulk loading kursów
  * Seed data (automatyczne uzupełnianie)
  * Manual override kursów
  * Auto-seed przy starcie aplikacji
- Kompletne testy wszystkich struktur

BAZA DANYCH (9 tabel):
1. app_info - metadane aplikacji
2. fx_rates - kursy NBP (cache + API)
3. cashflows - przepływy pieniężne
4. lots - LOT-y akcji z logiką FIFO
5. stock_trades - sprzedaże akcji
6. stock_trade_splits - rozbicia FIFO
7. options_cc - covered calls
8. dividends - dywidendy
9. market_prices - cache cen rynkowych

GOTOWE DO ETAPU 2: Moduł Cashflows (punkty 16-30)
"""

import streamlit as st
import os
import sys

# Dodaj katalog główny do path żeby móc importować moduły
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import modułów bazy danych i utils
try:
    import db
    from utils.formatting import format_currency_usd, format_date
    # Import NBP API Client (punkty 11-15)
    import nbp_api_client
except ImportError as e:
    st.error(f"Nie można zaimportować modułów: {e}")
    st.stop()

def main():
    """Główna funkcja aplikacji"""
    
    # Konfiguracja strony
    st.set_page_config(
        page_title="Covered Call Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Inicjalizacja bazy danych
    if 'db_initialized' not in st.session_state:
        with st.spinner("Inicjalizacja bazy danych..."):
            if db.init_database():
                st.session_state.db_initialized = True
                st.success("✅ Baza danych zainicjalizowana!")
            else:
                st.error("❌ Błąd inicjalizacji bazy danych!")
                st.stop()
    
    # Inicjalizacja session state dla nawigacji
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'Dashboard'
    
    # Tytuł główny
    st.title("📈 Covered Call Dashboard")
    st.markdown("*Zarządzanie portfelem opcji pokrytych z rozliczeniami podatkowymi PL*")
    
    # Sidebar - nawigacja z przyciskami
    with st.sidebar:
        st.header("🧭 Nawigacja")
        
        # Menu items z kluczami
        menu_items = {
            'Dashboard': '🏠 Dashboard',
            'Stocks': '📊 Stocks',
            'Options': '🎯 Options', 
            'Dividends': '💰 Dividends',
            'Cashflows': '💸 Cashflows',
            'Taxes': '📋 Taxes', 
            'Stats': '📈 Stats',
            'Charts': '📊 Charts',
            'NBP_Test': '🏦 NBP Test'
        }
        
        st.markdown("### Moduły:")
        for key, label in menu_items.items():
            if st.button(label, use_container_width=True):
                st.session_state.current_page = key
        
        # Pokazuj aktualną stronę
        st.markdown(f"**Aktywny moduł:** {st.session_state.current_page}")
        
        # Status projektu w sidebar
        st.markdown("---")
        st.markdown("### 📊 Status projektu")
        st.markdown("**ETAP 1 UKOŃCZONY** ✅")
        st.markdown("Punkty 1-15 (15/100)")
        st.markdown("*NBP API kompletny*")
    
    # Główna zawartość - routing do modułów
    if st.session_state.current_page == 'Dashboard':
        show_dashboard()
    elif st.session_state.current_page == 'NBP_Test':
        show_nbp_test()
    elif st.session_state.current_page == 'Stocks':
        show_placeholder('Stocks', '📊', 'Zarządzanie akcjami i LOT-ami')
    elif st.session_state.current_page == 'Options':
        show_placeholder('Options', '🎯', 'Covered calls')
    elif st.session_state.current_page == 'Dividends':
        show_placeholder('Dividends', '💰', 'Dywidendy')
    elif st.session_state.current_page == 'Cashflows':
        show_placeholder('Cashflows', '💸', 'Przepływy pieniężne')
    elif st.session_state.current_page == 'Taxes':
        show_placeholder('Taxes', '📋', 'Rozliczenia podatkowe')
    elif st.session_state.current_page == 'Stats':
        show_placeholder('Stats', '📈', 'Statystyki i analizy')
    elif st.session_state.current_page == 'Charts':
        show_placeholder('Charts', '📊', 'Wykresy i wizualizacje')

def show_nbp_test():
    """Strona testowania NBP API - pełna funkcjonalność"""
    st.header("🏦 NBP API Client - Kompletny")
    st.markdown("*Pełny system kursów NBP z cache, seed data i obsługą świąt*")
    
    # Użyj UI z modułu nbp_api_client
    nbp_api_client.show_nbp_test_ui()

def show_dashboard():
    """Główna strona dashboard"""
    st.header("🎉 ETAP 1 UKOŃCZONY - NBP API KOMPLETNY!")
    
    # Auto-seed kursów NBP przy każdym wejściu na dashboard (PUNKT 15B)
    try:
        if nbp_api_client.auto_seed_on_startup():
            st.info("💡 Automatycznie uzupełniono brakujące kursy NBP")
    except Exception as e:
        st.warning(f"⚠️ Auto-seed nie powiódł się: {e}")
    
    # Podsumowanie ETAPU 1
    with st.expander("✅ ETAP 1 UKOŃCZONY - Punkty 1-15", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **📁 PUNKTY 1-5: FUNDAMENT**
            - ✅ Struktura katalogów i plików
            - ✅ Aplikacja Streamlit z nawigacją
            - ✅ Połączenie z bazą SQLite
            - ✅ Utils (formatowanie)
            - ✅ Testy podstawowych funkcji
            """)
            
        with col2:
            st.markdown("""
            **🗄️ PUNKTY 6-10: BAZA DANYCH**
            - ✅ Tabele fx_rates (kursy NBP)
            - ✅ Tabele cashflows (przepływy)
            - ✅ Tabele lots (LOT-y akcji)
            - ✅ Tabele stock_trades (sprzedaże FIFO)
            - ✅ Tabele options_cc, dividends, market_prices
            """)
            
        with col3:
            st.markdown("""
            **🏦 PUNKTY 11-15: NBP API**
            - ✅ Podstawowy client (11)
            - ✅ Bulk loading + seed (12)
            - ✅ Obsługa świąt PL (13)
            - ✅ UI zarządzania cache (14)
            - ✅ Auto-seed startup (15)
            """)
    
    # ETAP 2 - Następne kroki
    with st.expander("🔄 ETAP 2: MODUŁ CASHFLOWS - Punkty 16-30"):
        st.markdown("""
        **🎯 CEL ETAPU 2:** Pełny moduł przepływów pieniężnych z UI
        
        **💸 FUNKCJONALNOŚCI DO ZROBIENIA:**
        - 📝 Formularze wpłat/wypłat z automatycznym kursem NBP D-1
        - 📊 Tabele cashflows z filtrami (typ, data, kwota)
        - ✏️ Edycja i usuwanie operacji
        - 📤 Eksporty do CSV
        - ⚡ Walidacje i kontrole błędów
        - 🔗 Integracja z innymi modułami (automatyczne cashflows)
        
        **🏗️ STRUKTURA:**
        - pages/cashflows.py - główny UI modułu
        - Rozszerzenie db.py o dodatkowe operacje
        - Integracja z NBP API dla kursów
        
        **🎯 OCZEKIWANY REZULTAT:**
        - Kompletny dziennik przepływów pieniężnych
        - Każda operacja z kursem NBP D-1 i przeliczeniem PLN
        - Gotowa podstawa dla pozostałych modułów
        """)
    
    # Pozostałe etapy
    with st.expander("🗺️ POZOSTAŁE ETAPY - Punkty 31-100"):
        st.markdown("""
        **📊 ETAP 3: MODUŁ STOCKS (31-50)**
        - Zakupy LOT-ów akcji z kursem NBP
        - Sprzedaże FIFO z UI i rozbiciami
        - Blokady pod covered calls
        
        **🎯 ETAP 4: MODUŁ OPTIONS (51-70)**
        - Covered calls z rezerwacjami akcji
        - Buyback i expiry
        - Rolowanie opcji
        
        **💰 ETAP 5: MODUŁ DIVIDENDS (71-80)**
        - Dywidendy z rozliczeniami PIT-36
        
        **📋 ETAP 6: MODUŁ TAXES (81-90)**
        - Rozliczenia PIT-38/PIT-36
        - Eksporty do rozliczeń
        
        **📈 ETAP 7: DASHBOARD + FINALIZACJA (91-100)**
        - KPI i alerty
        - Wykresy i statystyki
        - Integracja z yfinance
        """)
    
    # Test kompletnego systemu NBP
    st.header("🧪 Test kompletnego systemu NBP")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🏦 Test pełnego NBP API"):
            test_results = nbp_api_client.test_nbp_api()
            
            st.write("**Wyniki testów:**")
            for test_name, result in test_results.items():
                if result:
                    st.success(f"✅ {test_name}")
                else:
                    st.error(f"❌ {test_name}")
            
            passed = sum(test_results.values())
            total = len(test_results)
            
            if passed == total:
                st.success(f"🎉 NBP API działa perfekcyjnie! ({passed}/{total})")
            else:
                st.warning(f"⚠️ NBP API częściowo działa ({passed}/{total})")
    
    with col2:
        if st.button("🌱 Test seed data"):
            with st.spinner("Testowanie seed..."):
                end_date = nbp_api_client.date.today()
                start_date = end_date - nbp_api_client.timedelta(days=7)
                results = nbp_api_client.nbp_client.bulk_load_fx_rates(start_date, end_date)
                success_count = len([v for v in results.values() if v])
                st.success(f"✅ Seed test: {success_count} kursów")
    
    with col3:
        if st.button("🔗 Przejdź do NBP Test"):
            st.session_state.current_page = 'NBP_Test'
            st.rerun()
    
    # Testy wszystkich komponentów ETAPU 1
    st.header("🧪 Testy wszystkich komponentów")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Test podstawowych funkcji (Punkty 1-5)
        if st.button("🚀 Test fundament (Punkty 1-5)"):
            test_results = []
            
            try:
                from utils.formatting import format_currency_usd
                test_results.append("✅ Import modułów - OK")
            except Exception as e:
                test_results.append(f"❌ Import modułów - {e}")
            
            try:
                db_status = db.test_database_connection()
                if db_status['connection_ok']:
                    test_results.append("✅ Połączenie z bazą - OK")
                else:
                    test_results.append("❌ Połączenie z bazą - BŁĄD")
            except Exception as e:
                test_results.append(f"❌ Test bazy - {e}")
            
            try:
                test_usd = format_currency_usd(1234.56)
                if "$1,234.56" in test_usd:
                    test_results.append("✅ Formatowanie - OK")
                else:
                    test_results.append("❌ Formatowanie - BŁĄD")
            except Exception as e:
                test_results.append(f"❌ Formatowanie - {e}")
            
            for result in test_results:
                if "✅" in result:
                    st.success(result)
                else:
                    st.error(result)
        
        # Test bazy danych (Punkty 6-10)
        if st.button("🗄️ Test bazy danych (Punkty 6-10)"):
            try:
                import structure
                
                # Test wszystkich tabel
                tests = {
                    'fx_rates': db.test_fx_rates_operations(),
                    'cashflows': db.test_cashflows_operations(),
                    'lots': db.test_lots_operations(),
                    'stock_trades': db.test_stock_trades_operations(),
                    'final_tables': db.test_final_tables_operations()
                }
                
                all_passed = 0
                all_total = 0
                
                for table_name, results in tests.items():
                    passed = sum(results.values())
                    total = len(results)
                    all_passed += passed
                    all_total += total
                    
                    if passed == total:
                        st.success(f"✅ {table_name}: {passed}/{total}")
                    else:
                        st.warning(f"⚠️ {table_name}: {passed}/{total}")
                
                st.info(f"**Całość:** {all_passed}/{all_total} testów")
                
            except Exception as e:
                st.error(f"Błąd testowania bazy: {e}")
    
    with col2:
        # Statystyki systemu
        if st.button("📊 Statystyki systemu"):
            db_summary = db.get_database_summary()
            fx_stats = db.get_fx_rates_stats()
            
            st.write("**Baza danych:**")
            st.write(f"- Tabel: {db_summary['total_tables']}")
            st.write(f"- Rekordów: {db_summary['total_records']}")
            
            st.write("**NBP Cache:**")
            st.write(f"- Kursów USD: {fx_stats['total_records']}")
            st.write(f"- Zakres: {fx_stats['oldest_date']} → {fx_stats['newest_date']}")
            if fx_stats['latest_usd_rate']:
                st.write(f"- Ostatni kurs: {fx_stats['latest_usd_rate']:.4f}")
        
        # Sprawdzenie pokrycia kursów
        if st.button("🔍 Pokrycie kursów NBP"):
            # Sprawdź ostatnie 30 dni
            end_date = nbp_api_client.date.today()
            start_date = end_date - nbp_api_client.timedelta(days=30)
            
            # Policz dni robocze
            business_days = 0
            current_date = start_date
            while current_date <= end_date:
                if nbp_api_client.is_business_day(current_date):
                    business_days += 1
                current_date += nbp_api_client.timedelta(days=1)
            
            # Sprawdź ile w bazie
            conn = db.get_connection()
            existing_count = 0
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM fx_rates 
                    WHERE code = 'USD' AND date BETWEEN ? AND ?
                """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
                existing_count = cursor.fetchone()[0]
                conn.close()
            
            coverage = (existing_count / business_days * 100) if business_days > 0 else 0
            
            st.metric("Pokrycie 30 dni", f"{coverage:.1f}%")
            st.write(f"Dni robocze: {business_days}")
            st.write(f"W cache: {existing_count}")
            st.write(f"Brakuje: {business_days - existing_count}")
    
    # Informacje o systemie
    st.header("ℹ️ Informacje o systemie")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Konfiguracja:**
        - 🏦 **Broker**: Lynx (IBKR)
        - 💱 **Waluta główna**: USD
        - 🇵🇱 **Rozliczenia**: PLN (kurs NBP D-1)
        - 📊 **Podatki**: PIT-38 (akcje/opcje), PIT-36 (dywidendy)
        """)
    
    with col2:
        st.markdown("""
        **Technologie:**
        - 🐍 **Backend**: Python + SQLite
        - 🌐 **Frontend**: Streamlit
        - 🏦 **Kursy**: NBP API + cache ✅
        - 📈 **Ceny**: yfinance (w przyszłości)
        - 📊 **Dane**: Ręczne wprowadzanie
        """)
    
    # Footer z statusem
    st.markdown("---")
    st.success("🎉 **ETAP 1 UKOŃCZONY!** NBP API kompletny - wszystkie funkcjonalności działają")
    st.info("🚀 **Następny etap:** ETAP 2 - Moduł Cashflows (punkty 16-30)")
    st.markdown("*Streamlit Covered Call Dashboard v1.0 - **GOTOWY DO ETAPU 2** (15/100 punktów)*")

def show_placeholder(module_name, icon, description):
    """Placeholder dla modułów, które będą implementowane w kolejnych etapach"""
    st.header(f"{icon} {module_name}")
    st.info(f"**{description}**")
    st.markdown("*Ten moduł będzie dostępny w kolejnych etapach rozwoju.*")
    
    # Pokazuj w którym etapie będzie implementowany
    implementation_points = {
        'Stocks': 'ETAP 3: Punkty 31-50',
        'Options': 'ETAP 4: Punkty 51-70', 
        'Dividends': 'ETAP 5: Punkty 71-80',
        'Cashflows': 'ETAP 2: Punkty 16-30 (NASTĘPNY!)',
        'Taxes': 'ETAP 6: Punkty 81-90',
        'Stats': 'ETAP 7: Punkty 91-100',
        'Charts': 'ETAP 7: Punkty 91-100'
    }
    
    if module_name in implementation_points:
        st.markdown(f"**Planowana implementacja:** {implementation_points[module_name]}")
    
    # Status obecnego etapu
    st.markdown("---")
    st.success("✅ **ETAP 1 UKOŃCZONY** - NBP API kompletny")
    
    if module_name == 'Cashflows':
        st.info("🚀 **TEN MODUŁ JEST NASTĘPNY** - rozpocznij nową rozmowę dla ETAPU 2!")
    else:
        st.info("💡 Wróć do Dashboard aby zobaczyć pełny status projektu")

if __name__ == "__main__":
    main()