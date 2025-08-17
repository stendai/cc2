"""
Streamlit Covered Call Dashboard - Główna aplikacja
ETAP 2 UKOŃCZONY: Punkty 1-30 (NBP API + Cashflows kompletny)

STATUS PROJEKTU:
✅ PUNKTY 1-15: ETAP 1 - Fundament aplikacji (NBP API, baza, utils, testy)
✅ PUNKTY 16-30: ETAP 2 - Moduł Cashflows (kompletny przepływy pieniężne)

NASTĘPNE ETAPY:
🚀 PUNKTY 31-50: Moduł Stocks (ETAP 3) - NASTĘPNY!
🔄 PUNKTY 51-70: Moduł Options (ETAP 4)
🔄 PUNKTY 71-80: Moduł Dividends (ETAP 5)
🔄 PUNKTY 81-90: Moduł Taxes (ETAP 6)
🔄 PUNKTY 91-100: Dashboard + finalizacja (ETAP 7)

UKOŃCZONE KOMPONENTY ETAPU 1+2:
- Struktura aplikacji Streamlit z 8 modułami
- Pełna baza danych SQLite (9 tabel) z operacjami CRUD
- NBP API Client z cache, seed data, obsługą świąt
- KOMPLETNY moduł Cashflows z pełną funkcjonalnością:
  * Formularze wpłat/wypłat z automatycznym kursem NBP D-1
  * Manual override kursów NBP
  * Walidacje biznesowe (wpłaty dodatnie, wypłaty ujemne)
  * Tabele z filtrami (typ, źródło, kwota)
  * Edycja/usuwanie operacji ręcznych
  * Eksport CSV z timestampem
  * Statystyki (saldo, wpływy, wydatki)
  * 3 taby: Ręczne | Automatyczne | Wszystkie
  * Integracja z automatycznymi cashflows

BAZA DANYCH (9 tabel):
1. app_info - metadane aplikacji
2. fx_rates - kursy NBP (cache + API) ✅
3. cashflows - przepływy pieniężne ✅ KOMPLETNE
4. lots - LOT-y akcji z logiką FIFO
5. stock_trades - sprzedaże akcji
6. stock_trade_splits - rozbicia FIFO
7. options_cc - covered calls
8. dividends - dywidendy
9. market_prices - cache cen rynkowych

GOTOWE DO ETAPU 3: Moduł Stocks (punkty 31-50)
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
        st.markdown("**ETAP 2 UKOŃCZONY** ✅")
        st.markdown("Punkty 1-30 (30/100)")
        st.markdown("*NBP API + Cashflows*")
    
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
        from modules.cashflows import show_cashflows
        show_cashflows()
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
    st.header("🎉 ETAP 2 UKOŃCZONY - CASHFLOWS KOMPLETNY!")
    
    # Auto-seed kursów NBP przy każdym wejściu na dashboard (PUNKT 15B)
    try:
        if nbp_api_client.auto_seed_on_startup():
            st.info("💡 Automatycznie uzupełniono brakujące kursy NBP")
    except Exception as e:
        st.warning(f"⚠️ Auto-seed nie powiódł się: {e}")
    
    # Podsumowanie ETAPU 1+2
    with st.expander("✅ ETAP 1+2 UKOŃCZONE - Punkty 1-30", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **📁 ETAP 1: FUNDAMENT (1-15)**
            - ✅ Struktura katalogów i plików
            - ✅ Aplikacja Streamlit z nawigacją
            - ✅ Baza SQLite (9 tabel + CRUD)
            - ✅ Utils (formatowanie)
            - ✅ NBP API Client kompletny
            """)
            
        with col2:
            st.markdown("""
            **💸 ETAP 2: CASHFLOWS (16-30)**
            - ✅ Formularze wpłat/wypłat
            - ✅ Kursy NBP D-1 + manual override
            - ✅ Walidacje biznesowe
            - ✅ Tabele z filtrami
            - ✅ Edycja/usuwanie + eksport CSV
            """)
            
        with col3:
            st.markdown("""
            **📊 FUNKCJONALNOŚCI CASHFLOWS**
            - ✅ 3 taby (Ręczne/Auto/Wszystkie)
            - ✅ Statystyki (saldo, wpływy, wydatki)
            - ✅ Linki ref do operacji źródłowych
            - ✅ Integracja z automatycznymi cashflows
            - ✅ Profesjonalny UI gotowy do produkcji
            """)
    
    # ETAP 3 - Następne kroki
    with st.expander("🚀 ETAP 3: MODUŁ STOCKS - Punkty 31-50 (NASTĘPNY!)"):
        st.markdown("""
        **🎯 CEL ETAPU 3:** Pełny moduł zarządzania akcjami z logiką FIFO
        
        **📊 FUNKCJONALNOŚCI DO ZROBIENIA:**
        - 📝 Formularze zakupu LOT-ów akcji z kursem NBP D-1
        - 💰 Automatyczne tworzenie cashflows przy zakupie/sprzedaży
        - 🔄 Sprzedaże FIFO z rozbiciem po LOT-ach
        - 📊 Tabele LOT-ów (quantity_open, koszt PLN, P/L)
        - 📈 Tabele sprzedaży z alokacją FIFO
        - 🔒 Blokady sprzedaży pod otwarte covered calls
        - 📤 Eksporty stocks do CSV
        
        **🏗️ STRUKTURA:**
        - modules/stocks.py - główny UI modułu
        - Rozszerzenie operacji CRUD w db.py
        - Integracja z cashflows (automatyczne operacje)
        
        **🎯 OCZEKIWANY REZULTAT:**
        - Kompletne zarządzanie portfelem akcji
        - Logika FIFO działająca automatycznie
        - Podstawa pod covered calls (ETAP 4)
        - Wszystkie operacje zintegrowane z cashflows
        """)
    
    # Pozostałe etapy
    with st.expander("🗺️ POZOSTAŁE ETAPY - Punkty 51-100"):
        st.markdown("""
        **🎯 ETAP 4: MODUŁ OPTIONS (51-70)**
        - Covered calls z rezerwacjami akcji FIFO
        - Buyback i expiry z P/L
        - Rolowanie opcji (buyback + nowa sprzedaż)
        
        **💰 ETAP 5: MODUŁ DIVIDENDS (71-80)**
        - Dywidendy z rozliczeniami PIT-36
        - WHT 15% + dopłata 4%
        
        **📋 ETAP 6: MODUŁ TAXES (81-90)**
        - Rozliczenia PIT-38/PIT-36
        - Agregacja z wszystkich modułów
        - Eksporty do rozliczeń
        
        **📈 ETAP 7: DASHBOARD + FINALIZACJA (91-100)**
        - KPI i alerty na dashboardzie
        - Wykresy i statystyki
        - Integracja z yfinance (MTM)
        """)
    
    # Test cashflows
    st.header("🧪 Test modułu Cashflows")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💸 Test Cashflows"):
            try:
                stats = db.get_cashflows_stats()
                st.success(f"✅ Cashflows: {stats['total_records']} operacji")
                st.write(f"Saldo: ${stats['total_usd']:.2f}")
                if stats['total_records'] > 0:
                    st.write(f"Zakres: {stats['oldest_date']} → {stats['newest_date']}")
            except Exception as e:
                st.error(f"❌ Błąd: {e}")
    
    with col2:
        if st.button("🏦 Test NBP API"):
            test_results = nbp_api_client.test_nbp_api()
            passed = sum(test_results.values())
            total = len(test_results)
            
            if passed == total:
                st.success(f"✅ NBP API: {passed}/{total}")
            else:
                st.warning(f"⚠️ NBP API: {passed}/{total}")
    
    with col3:
        if st.button("🔗 Przejdź do Cashflows"):
            st.session_state.current_page = 'Cashflows'
            st.rerun()
    
    # Testy bazy danych
    st.header("🧪 Testy infrastruktury")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Test wszystkich modułów
        if st.button("🗄️ Test bazy danych"):
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
            cashflow_stats = db.get_cashflows_stats()
            
            st.write("**Baza danych:**")
            st.write(f"- Tabel: {db_summary['total_tables']}")
            st.write(f"- Rekordów: {db_summary['total_records']}")
            
            st.write("**NBP Cache:**")
            st.write(f"- Kursów USD: {fx_stats['total_records']}")
            
            st.write("**Cashflows:**")
            st.write(f"- Operacji: {cashflow_stats['total_records']}")
            st.write(f"- Saldo USD: ${cashflow_stats['total_usd']:.2f}")
    
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
        - 💸 **Cashflows**: Kompletny moduł ✅
        - 📊 **Dane**: Ręczne wprowadzanie
        """)
    
    # Footer z statusem
    st.markdown("---")
    st.success("🎉 **ETAP 2 UKOŃCZONY!** Cashflows kompletny - wszystkie funkcjonalności działają")
    st.info("🚀 **Następny etap:** ETAP 3 - Moduł Stocks (punkty 31-50)")
    st.markdown("*Streamlit Covered Call Dashboard v2.0 - **GOTOWY DO ETAPU 3** (30/100 punktów)*")

def show_placeholder(module_name, icon, description):
    """Placeholder dla modułów, które będą implementowane w kolejnych etapach"""
    st.header(f"{icon} {module_name}")
    st.info(f"**{description}**")
    st.markdown("*Ten moduł będzie dostępny w kolejnych etapach rozwoju.*")
    
    # Pokazuj w którym etapie będzie implementowany
    implementation_points = {
        'Stocks': 'ETAP 3: Punkty 31-50 (NASTĘPNY!)',
        'Options': 'ETAP 4: Punkty 51-70', 
        'Dividends': 'ETAP 5: Punkty 71-80',
        'Taxes': 'ETAP 6: Punkty 81-90',
        'Stats': 'ETAP 7: Punkty 91-100',
        'Charts': 'ETAP 7: Punkty 91-100'
    }
    
    if module_name in implementation_points:
        st.markdown(f"**Planowana implementacja:** {implementation_points[module_name]}")
    
    # Status obecnego etapu
    st.markdown("---")
    st.success("✅ **ETAP 2 UKOŃCZONY** - NBP API + Cashflows kompletne")
    
    if module_name == 'Stocks':
        st.info("🚀 **TEN MODUŁ JEST NASTĘPNY** - rozpocznij nową rozmowę dla ETAPU 3!")
    else:
        st.info("💡 Wróć do Dashboard aby zobaczyć pełny status projektu")

if __name__ == "__main__":
    main()