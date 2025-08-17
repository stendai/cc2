"""
Streamlit Covered Call Dashboard - Główna aplikacja
ETAP 1 UKOŃCZONY: Punkty 1-10 (Fundament + Struktura bazy danych)

STATUS PROJEKTU:
✅ PUNKTY 1-5: Fundament aplikacji (struktura, nawigacja, baza, utils, testy)
✅ PUNKTY 6-10: Struktura bazy danych (8 tabel + operacje CRUD + logika FIFO)

NASTĘPNE ETAPY:
🔄 PUNKTY 11-15: Kursy NBP + seed data
🔄 PUNKTY 16-30: Moduł cashflows (UI + funkcjonalności)
🔄 PUNKTY 31-50: Moduł stocks (zakupy LOT-ów + sprzedaże FIFO)
🔄 PUNKTY 51-70: Moduł options (covered calls + rezerwacje)
🔄 PUNKTY 71-80: Moduł dividends (dywidendy z PIT-36)
🔄 PUNKTY 81-90: Moduł taxes (rozliczenia PIT-38/PIT-36)
🔄 PUNKTY 91-100: Dashboard + wykresy + finalizacja

UKOŃCZONE KOMPONENTY:
- Struktura aplikacji Streamlit z 8 modułami
- Pełna baza danych SQLite (9 tabel)
- Operacje CRUD dla wszystkich tabel
- Logika FIFO dla sprzedaży akcji
- Podstawowe utils (formatowanie)
- Kompletne testy wszystkich struktur

BAZA DANYCH (9 tabel):
1. app_info - metadane aplikacji
2. fx_rates - kursy NBP (punkt 6)
3. cashflows - przepływy pieniężne (punkt 7)
4. lots - LOT-y akcji z logiką FIFO (punkt 8)
5. stock_trades - sprzedaże akcji (punkt 9)
6. stock_trade_splits - rozbicia FIFO (punkt 9)
7. options_cc - covered calls (punkt 10)
8. dividends - dywidendy (punkt 10)
9. market_prices - cache cen rynkowych (punkt 10)

GOTOWE DO KONTYNUACJI: Punkt 11 - pobieranie kursów NBP
"""

import streamlit as st
import os
import sys

# Dodaj katalog główny do path żeby móc importować moduły
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import modułu bazy danych i utils
try:
    import db
    from utils.formatting import format_currency_usd, format_date
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
            'Charts': '📊 Charts'
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
        st.markdown("Punkty 1-10 (10/100)")
        st.markdown("*Struktura bazy danych gotowa*")
    
    # Główna zawartość - routing do modułów
    if st.session_state.current_page == 'Dashboard':
        show_dashboard()
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

def show_dashboard():
    """Główna strona dashboard"""
    st.header("🚀 Status projektu - ETAP 1 UKOŃCZONY!")
    
    # Podsumowanie ukończonych punktów
    with st.expander("✅ UKOŃCZONE - Punkty 1-10", expanded=True):
        col1, col2 = st.columns(2)
        
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
    
    # Następne kroki
    with st.expander("🔄 NASTĘPNE KROKI - Punkty 11-100"):
        st.markdown("""
        **🏦 PUNKTY 11-15: Kursy NBP + seed data**
        - 🔄 Punkt 11: Pobieranie kursów NBP z API
        - 🔄 Punkt 12: Cache'owanie kursów
        - 🔄 Punkt 13: Obsługa weekendów/świąt
        - 🔄 Punkt 14: Manual override kursów
        - 🔄 Punkt 15: Seed data testowych
        
        **💸 PUNKTY 16-30: Moduł Cashflows**
        - 🔄 UI dla wpłat/wypłat
        - 🔄 Tabele z filtrami
        - 🔄 Eksporty CSV
        
        **📊 PUNKTY 31-50: Moduł Stocks**
        - 🔄 Formularze zakupu LOT-ów
        - 🔄 Sprzedaże FIFO z UI
        - 🔄 Blokady pod covered calls
        
        **🎯 PUNKTY 51-70: Moduł Options**
        - 🔄 Covered calls z rezerwacjami
        - 🔄 Buyback i expiry
        - 🔄 Rolowanie opcji
        
        **💰 PUNKTY 71-80: Moduł Dividends**
        - 🔄 Dywidendy z rozliczeniami PIT-36
        
        **📋 PUNKTY 81-90: Moduł Taxes**
        - 🔄 Rozliczenia PIT-38/PIT-36
        - 🔄 Eksporty do rozliczeń
        
        **📈 PUNKTY 91-100: Dashboard + Finalizacja**
        - 🔄 KPI i alerty
        - 🔄 Wykresy i statystyki
        - 🔄 Integracja z yfinance
        """)
    
    # Testy ukończonych komponentów
    st.header("🧪 Testy ukończonych komponentów")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Test podstawowych funkcji (Punkt 5)
        if st.button("🚀 Test podstawowych funkcji (Punkty 1-5)"):
            test_results = []
            
            # Test importów
            try:
                from utils.formatting import format_currency_usd
                test_results.append("✅ Import modułów - OK")
            except Exception as e:
                test_results.append(f"❌ Import modułów - {e}")
            
            # Test bazy danych
            try:
                db_status = db.test_database_connection()
                if db_status['connection_ok']:
                    test_results.append("✅ Połączenie z bazą - OK")
                else:
                    test_results.append("❌ Połączenie z bazą - BŁĄD")
            except Exception as e:
                test_results.append(f"❌ Test bazy - {e}")
            
            # Test formatowania
            try:
                test_usd = format_currency_usd(1234.56)
                if "$1,234.56" in test_usd:
                    test_results.append("✅ Formatowanie - OK")
                else:
                    test_results.append("❌ Formatowanie - BŁĄD")
            except Exception as e:
                test_results.append(f"❌ Formatowanie - {e}")
            
            # Test nawigacji
            try:
                if 'current_page' in st.session_state:
                    test_results.append("✅ Session state - OK")
                else:
                    test_results.append("❌ Session state - BŁĄD")
            except Exception as e:
                test_results.append(f"❌ Session state - {e}")
            
            # Wyświetl wyniki testów
            for result in test_results:
                if "✅" in result:
                    st.success(result)
                else:
                    st.error(result)
            
            # Podsumowanie
            passed = len([r for r in test_results if "✅" in r])
            total = len(test_results)
            
            if passed == total:
                st.success(f"🎉 Punkty 1-5 działają poprawnie! ({passed}/{total})")
            else:
                st.warning(f"⚠️ Punkty 1-5 częściowo działają ({passed}/{total})")
        
        # Test tabeli fx_rates (Punkt 6)
        if st.button("🧪 Test tabeli fx_rates (Punkt 6)"):
            try:
                import structure
                fx_test_results = db.test_fx_rates_operations()
                
                st.write("**Wyniki testów fx_rates:**")
                for test_name, result in fx_test_results.items():
                    if result:
                        st.success(f"✅ {test_name}")
                    else:
                        st.error(f"❌ {test_name}")
                
                passed = sum(fx_test_results.values())
                total = len(fx_test_results)
                
                if passed == total:
                    st.success(f"🎉 Punkt 6 działa poprawnie! ({passed}/{total})")
                else:
                    st.warning(f"⚠️ Punkt 6 częściowo działa ({passed}/{total})")
                    
            except Exception as e:
                st.error(f"Błąd testowania fx_rates: {e}")
        
        # Test tabeli cashflows (Punkt 7)
        if st.button("🧪 Test tabeli cashflows (Punkt 7)"):
            try:
                import structure
                cashflow_test_results = db.test_cashflows_operations()
                
                st.write("**Wyniki testów cashflows:**")
                for test_name, result in cashflow_test_results.items():
                    if result:
                        st.success(f"✅ {test_name}")
                    else:
                        st.error(f"❌ {test_name}")
                
                passed = sum(cashflow_test_results.values())
                total = len(cashflow_test_results)
                
                if passed == total:
                    st.success(f"🎉 Punkt 7 działa poprawnie! ({passed}/{total})")
                else:
                    st.warning(f"⚠️ Punkt 7 częściowo działa ({passed}/{total})")
                    
            except Exception as e:
                st.error(f"Błąd testowania cashflows: {e}")
    
    with col2:
        # Test tabeli lots (Punkt 8)
        if st.button("🧪 Test tabeli lots (Punkt 8)"):
            try:
                import structure
                lots_test_results = db.test_lots_operations()
                
                st.write("**Wyniki testów lots:**")
                for test_name, result in lots_test_results.items():
                    if result:
                        st.success(f"✅ {test_name}")
                    else:
                        st.error(f"❌ {test_name}")
                
                passed = sum(lots_test_results.values())
                total = len(lots_test_results)
                
                if passed == total:
                    st.success(f"🎉 Punkt 8 działa poprawnie! ({passed}/{total})")
                else:
                    st.warning(f"⚠️ Punkt 8 częściowo działa ({passed}/{total})")
                    
            except Exception as e:
                st.error(f"Błąd testowania lots: {e}")
        
        # Test tabel stock_trades (Punkt 9)
        if st.button("🧪 Test tabel stock_trades (Punkt 9)"):
            try:
                import structure
                trades_test_results = db.test_stock_trades_operations()
                
                st.write("**Wyniki testów stock_trades (FIFO):**")
                for test_name, result in trades_test_results.items():
                    if result:
                        st.success(f"✅ {test_name}")
                    else:
                        st.error(f"❌ {test_name}")
                
                passed = sum(trades_test_results.values())
                total = len(trades_test_results)
                
                if passed == total:
                    st.success(f"🎉 Punkt 9 działa poprawnie! ({passed}/{total})")
                else:
                    st.warning(f"⚠️ Punkt 9 częściowo działa ({passed}/{total})")
                    
            except Exception as e:
                st.error(f"Błąd testowania stock_trades: {e}")
        
        # Test ostatnich tabel (Punkt 10)
        if st.button("🧪 Test ostatnich tabel (Punkt 10)"):
            try:
                import structure
                final_test_results = db.test_final_tables_operations()
                
                st.write("**Wyniki testów ostatnich tabel:**")
                for test_name, result in final_test_results.items():
                    if result:
                        st.success(f"✅ {test_name}")
                    else:
                        st.error(f"❌ {test_name}")
                
                passed = sum(final_test_results.values())
                total = len(final_test_results)
                
                if passed == total:
                    st.success(f"🎉 Punkt 10 działa poprawnie! ({passed}/{total})")
                else:
                    st.warning(f"⚠️ Punkt 10 częściowo działa ({passed}/{total})")
                    
            except Exception as e:
                st.error(f"Błąd testowania ostatnich tabel: {e}")
    
    # Status bazy danych
    st.header("🗄️ Status bazy danych")
    
    # Podsumowanie całej bazy
    db_summary = db.get_database_summary()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Łączna liczba tabel", db_summary['total_tables'])
    with col2:
        st.metric("Łączna liczba rekordów", db_summary['total_records'])
    with col3:
        # Test bazy danych z formatowaniem
        db_status = db.test_database_connection()
        st.metric("Rozmiar bazy", f"{db_status['db_size']} B" if db_status['db_exists'] else "0 B")
    
    # Szczegóły tabel
    with st.expander("📊 Szczegóły wszystkich tabel"):
        st.write("**Tabele w bazie danych:**")
        for table_name, info in db_summary['tables'].items():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{table_name}**")
            with col2:
                st.write(f"{info['records']} rekordów")
            with col3:
                st.write(f"{info['columns']} kolumn")
    
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
        - 📊 **Dane**: Ręczne wprowadzanie
        - 🏦 **Kursy**: NBP API
        - 📈 **Ceny**: yfinance
        """)
    
    # Footer z statusem
    st.markdown("---")
    st.success("🎉 **ETAP 1 UKOŃCZONY!** Struktura bazy danych kompletna (Punkty 1-10)")
    st.info("💡 **Następny krok:** Rozpocznij nową rozmowę z tytułem 'ETAP 2: Punkt 11 - kursy NBP' aby kontynuować projekt")
    st.markdown("*Streamlit Covered Call Dashboard v0.1 - **GOTOWY DO ETAPU 2** (10/100 punktów)*")

def show_placeholder(module_name, icon, description):
    """Placeholder dla modułów, które jeszcze nie zostały zaimplementowane"""
    st.header(f"{icon} {module_name}")
    st.info(f"**{description}**")
    st.markdown("*Ten moduł będzie dostępny w późniejszych punktach rozwoju.*")
    
    # Pokazuj w którym punkcie będzie implementowany
    implementation_points = {
        'Stocks': 'Punkty 31-50 (ETAP 3)',
        'Options': 'Punkty 51-70 (ETAP 4)', 
        'Dividends': 'Punkty 71-80 (ETAP 5)',
        'Cashflows': 'Punkty 16-30 (ETAP 2)',
        'Taxes': 'Punkty 81-90 (ETAP 6)',
        'Stats': 'Punkty 91-100 (ETAP 7)',
        'Charts': 'Punkty 91-100 (ETAP 7)'
    }
    
    if module_name in implementation_points:
        st.markdown(f"**Planowana implementacja:** {implementation_points[module_name]}")
    
    # Status obecnego etapu
    st.markdown("---")
    st.success("✅ **ETAP 1 UKOŃCZONY** - Struktura bazy danych gotowa")
    st.info("💡 Wróć do Dashboard aby zobaczyć pełny status projektu lub rozpocznij nową rozmowę dla kolejnego etapu")

if __name__ == "__main__":
    main()