"""
Streamlit Covered Call Dashboard - Główna aplikacja
ETAP 3 W TRAKCIE: Punkty 31-38 UKOŃCZONE (Stocks: LOT-y + FIFO)

STATUS PROJEKTU:
✅ PUNKTY 1-15: ETAP 1 - Fundament aplikacji (NBP API, baza, utils, testy)
✅ PUNKTY 16-30: ETAP 2 - Moduł Cashflows (kompletny przepływy pieniężne)
🚀 PUNKTY 31-38: ETAP 3 - Moduł Stocks (LOT-y + sprzedaże FIFO) - W TRAKCIE!

NASTĘPNE ETAPY:
⏳ PUNKTY 39-50: ETAP 3 - Dokończenie Stocks (tabele, UI, eksport)
🔄 PUNKTY 51-70: ETAP 4 - Moduł Options (covered calls)
🔄 PUNKTY 71-80: ETAP 5 - Moduł Dividends 
🔄 PUNKTY 81-90: ETAP 6 - Moduł Taxes
🔄 PUNKTY 91-100: ETAP 7 - Dashboard + finalizacja

UKOŃCZONE KOMPONENTY ETAPU 1+2+3A:
- Struktura aplikacji Streamlit z 8 modułami
- Pełna baza danych SQLite (9 tabel) z operacjami CRUD
- NBP API Client z cache, seed data, obsługą świąt
- KOMPLETNY moduł Cashflows z pełną funkcjonalnością
- CZĘŚCIOWY moduł Stocks (31-38):
  * Formularze zakupu LOT-ów z automatycznym kursem NBP D-1
  * Manual override kursów NBP przy zakupie
  * Automatyczne cashflows przy zakupie akcji
  * Logika FIFO dla sprzedaży akcji
  * Formularze sprzedaży z dokładnymi kalkulacjami P/L PLN
  * Zapis sprzedaży z rozbiciem po LOT-ach (FIFO)
  * Persistent komunikaty sukcesu
  * Diagnostyka sprzedaży z detalami FIFO

BAZA DANYCH (9 tabel):
1. app_info - metadane aplikacji
2. fx_rates - kursy NBP (cache + API) ✅
3. cashflows - przepływy pieniężne ✅ KOMPLETNE
4. lots - LOT-y akcji z logiką FIFO ✅ DZIAŁAJĄ
5. stock_trades - sprzedaże akcji ✅ DZIAŁAJĄ
6. stock_trade_splits - rozbicia FIFO ✅ DZIAŁAJĄ
7. options_cc - covered calls (gotowe do ETAPU 4)
8. dividends - dywidendy (gotowe do ETAPU 5)
9. market_prices - cache cen rynkowych (gotowe do ETAPU 7)

GOTOWE DO DOKOŃCZENIA ETAPU 3: Punkty 39-50 (tabele, UI, eksport)
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
        st.markdown("**ETAP 3 W TRAKCIE** 🚀")
        st.markdown("Punkty 1-38 (38/100)")
        st.markdown("*Stocks: LOT-y + FIFO*")
    
    # Główna zawartość - routing do modułów
    if st.session_state.current_page == 'Dashboard':
        show_dashboard()
    elif st.session_state.current_page == 'NBP_Test':
        show_nbp_test()
    elif st.session_state.current_page == 'Stocks':
        try:
            from modules.stocks import show_stocks
            show_stocks()
        except ImportError:
            # Fallback jeśli plik stocks.py jest w głównym katalogu
            try:
                import stocks
                stocks.show_stocks()
            except ImportError:
                st.error("❌ Nie można zaimportować modułu stocks")
                st.info("💡 Upewnij się, że plik stocks.py istnieje w katalogu modules/ lub głównym")
    elif st.session_state.current_page == 'Options':
        show_placeholder('Options', '🎯', 'Covered calls')
    elif st.session_state.current_page == 'Dividends':
        show_placeholder('Dividends', '💰', 'Dywidendy')
    elif st.session_state.current_page == 'Cashflows':
        try:
            from modules.cashflows import show_cashflows
            show_cashflows()
        except ImportError:
            st.error("❌ Nie można zaimportować modułu cashflows")
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
    st.header("🎉 ETAP 3 W TRAKCIE - STOCKS DZIAŁAJĄ!")
    
    # Auto-seed kursów NBP przy każdym wejściu na dashboard (PUNKT 15B)
    try:
        if nbp_api_client.auto_seed_on_startup():
            st.info("💡 Automatycznie uzupełniono brakujące kursy NBP")
    except Exception as e:
        st.warning(f"⚠️ Auto-seed nie powiódł się: {e}")
    
    # Podsumowanie ETAPU 1+2+3A
    with st.expander("✅ ETAP 1+2+3A UKOŃCZONE - Punkty 1-38", expanded=True):
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
            **📊 ETAP 3A: STOCKS (31-38)**
            - ✅ Formularze zakupu LOT-ów
            - ✅ Automatyczne cashflows
            - ✅ Logika FIFO działająca
            - ✅ Formularze sprzedaży
            - ✅ Kalkulacje P/L PLN
            """)
    
    # ETAP 3B - Następne kroki
    with st.expander("🚀 ETAP 3B: DOKOŃCZENIE STOCKS - Punkty 39-50 (NASTĘPNY!)"):
        st.markdown("""
        **🎯 CEL ETAPU 3B:** Dokończenie modułu Stocks z tabelami i eksportami
        
        **📊 FUNKCJONALNOŚCI DO ZROBIENIA:**
        - 📋 **Punkt 46**: Tabela LOT-ów (quantity_open, koszt PLN, kursy, daty)
        - 📈 **Punkt 47**: Tabela sprzedaży z rozbiciami po LOT-ach 
        - 🔍 **Punkt 48**: Filtry i sortowanie w tabelach
        - 📤 **Punkt 49**: Eksport stocks do CSV
        - 🧪 **Punkt 50**: Finalne testowanie modułu stocks
        
        **🏗️ OCZEKIWANY REZULTAT:**
        - Pełny podgląd portfela akcji w tabelach
        - Historia sprzedaży z detalami FIFO
        - Profesjonalne UI gotowe do użytkowania
        - Eksporty dla celów podatkowych
        - Solidna podstawa pod moduł Options (ETAP 4)
        """)
    
    # Pozostałe etapy
    with st.expander("🗺️ POZOSTAŁE ETAPY - Punkty 51-100"):
        st.markdown("""
        **🎯 ETAP 4: MODUŁ OPTIONS (51-70)**
        - Covered calls z rezerwacjami akcji FIFO
        - Buyback i expiry z P/L
        - Rolowanie opcji (buyback + nowa sprzedaż)
        - Blokady sprzedaży akcji pod otwartymi CC
        
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
    
    # Test modułów
    st.header("🧪 Test działających modułów")
    
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
        if st.button("📊 Test Stocks"):
            try:
                lots_stats = db.get_lots_stats()
                st.success(f"✅ Stocks: {lots_stats['total_lots']} LOT-ów")
                st.write(f"Akcje w portfelu: {lots_stats['open_shares']}")
                
                # Test sprzedaży
                conn = db.get_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM stock_trades")
                    trades_count = cursor.fetchone()[0]
                    conn.close()
                    st.write(f"Sprzedaże: {trades_count}")
            except Exception as e:
                st.error(f"❌ Błąd: {e}")
    
    with col3:
        if st.button("🏦 Test NBP API"):
            test_results = nbp_api_client.test_nbp_api()
            passed = sum(test_results.values())
            total = len(test_results)
            
            if passed == total:
                st.success(f"✅ NBP API: {passed}/{total}")
            else:
                st.warning(f"⚠️ NBP API: {passed}/{total}")
    
    # Quick access
    st.header("🔗 Szybki dostęp")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💸 Przejdź do Cashflows", use_container_width=True):
            st.session_state.current_page = 'Cashflows'
            st.rerun()
    
    with col2:
        if st.button("📊 Przejdź do Stocks", use_container_width=True):
            st.session_state.current_page = 'Stocks'
            st.rerun()
    
    with col3:
        if st.button("🏦 Test NBP", use_container_width=True):
            st.session_state.current_page = 'NBP_Test'
            st.rerun()
    
    # Testy infrastruktury
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
            lots_stats = db.get_lots_stats()
            
            st.write("**Baza danych:**")
            st.write(f"- Tabel: {db_summary['total_tables']}")
            st.write(f"- Rekordów: {db_summary['total_records']}")
            
            st.write("**NBP Cache:**")
            st.write(f"- Kursów USD: {fx_stats['total_records']}")
            
            st.write("**Cashflows:**")
            st.write(f"- Operacji: {cashflow_stats['total_records']}")
            st.write(f"- Saldo USD: ${cashflow_stats['total_usd']:.2f}")
            
            st.write("**Stocks:**")
            st.write(f"- LOT-y: {lots_stats['total_lots']}")
            st.write(f"- Akcje: {lots_stats['open_shares']}")
    
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
        - 📊 **Stocks**: LOT-y + FIFO ✅
        """)
    
    # Footer z statusem
    st.markdown("---")
    st.success("🎉 **PUNKTY 31-38 UKOŃCZONE!** Stocks LOT-y + sprzedaże FIFO działają!")
    st.info("🚀 **Następny etap:** Punkty 39-50 - tabele, UI, eksport CSV")
    st.markdown("*Streamlit Covered Call Dashboard v3.0 - **ETAP 3 W TRAKCIE** (38/100 punktów)*")

def show_placeholder(module_name, icon, description):
    """Placeholder dla modułów, które będą implementowane w kolejnych etapach"""
    st.header(f"{icon} {module_name}")
    st.info(f"**{description}**")
    st.markdown("*Ten moduł będzie dostępny w kolejnych etapach rozwoju.*")
    
    # Pokazuj w którym etapie będzie implementowany
    implementation_points = {
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
    st.success("✅ **ETAP 3A UKOŃCZONY** - Stocks LOT-y + FIFO działają")
    st.info("🚀 **NASTĘPNY KROK** - Punkty 39-50: tabele, UI, eksport")

if __name__ == "__main__":
    main()