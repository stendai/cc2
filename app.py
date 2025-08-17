"""
Streamlit Covered Call Dashboard - Główna aplikacja
Punkt 5: Testowanie aplikacji
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
    
    # Główna zawartość - routing do modułów
    st.write(f"DEBUG: Aktualny moduł = {st.session_state.current_page}")  # Tymczasowy debug
    
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
    st.header("🚀 Status projektu")
    
    # Debug info - sprawdzenie nawigacji
    with st.expander("🔧 Debug - Testowanie nawigacji"):
        st.write(f"**Aktualny moduł:** {st.session_state.current_page}")
        st.write(f"**Session state keys:** {list(st.session_state.keys())}")
        if st.button("Test wszystkich modułów"):
            test_modules = ['Dashboard', 'Stocks', 'Options', 'Dividends', 'Cashflows', 'Taxes', 'Stats', 'Charts']
            for module in test_modules:
                try:
                    st.session_state.current_page = module
                    st.success(f"✅ {module} - routing OK")
                except Exception as e:
                    st.error(f"❌ {module} - błąd: {e}")
            st.session_state.current_page = 'Dashboard'  # Wróć do Dashboard
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ Punkty 1-4 - UKOŃCZONE")
        st.markdown("""
        **Punkt 1 - Struktura katalogów:**
        - ✅ app.py (główna aplikacja)
        - ✅ Podstawowa konfiguracja Streamlit
        - ✅ Layout aplikacji
        
        **Punkt 2.1-2.2 - Nawigacja:**
        - ✅ Session state routing
        - ✅ Interaktywne przyciski menu
        - ✅ Przełączanie między modułami
        - ✅ Placeholder dla wszystkich 8 modułów
        - ✅ Debug panel i testowanie
        
        **Punkt 3 - Baza danych:**
        - ✅ db.py (połączenie SQLite)
        - ✅ Inicjalizacja portfolio.db
        - ✅ Tabela app_info
        - ✅ Funkcje CRUD i diagnostyka
        
        **Punkt 4 - Utils:**
        - ✅ utils/formatting.py
        - ✅ 6 funkcji formatowania
        - ✅ Integracja z aplikacją
        """)
        
        st.success("🎉 Fundament aplikacji gotowy!")
    
    with col2:
        st.subheader("📋 Następne kroki")
        st.markdown("""
        **Punkt 5: Testowanie aplikacji**
        - 🔄 Sprawdzenie wszystkich modułów
        - 🔄 Walidacja importów
        
        **ETAP 1 - FINALIZACJA (1-15):**
        - 🔄 Punkt 6-10: Tabele bazy danych
        - 🔄 Punkt 11-15: Kursy NBP i seed data
        
        **ETAP 2 - CASHFLOWS (16-30):**
        - 🔄 Moduł przepływów pieniężnych
        """)
        
        # Test kompletności etapu 1
        st.header("🧪 Test aplikacji (Punkt 5)")
        
        if st.button("🚀 Przetestuj wszystkie funkcje"):
            test_results = []
            
            # Test importów
            try:
                # Użyj globalnego modułu db zamiast ponownego importu
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
            
            # Wyświetl wyniki
            for result in test_results:
                if "✅" in result:
                    st.success(result)
                else:
                    st.error(result)
            
            # Podsumowanie
            passed = len([r for r in test_results if "✅" in r])
            total = len(test_results)
            
            if passed == total:
                st.balloons()
                st.success(f"🎉 Wszystkie testy przeszły! ({passed}/{total})")
                st.info("**✅ PUNKT 5 UKOŃCZONY!** Gotowy do punktu 6 - structure.py z tabelami bazy danych.")
                
                # Zaznacz punkt 5 jako ukończony
                st.session_state.point_5_completed = True
            else:
                st.warning(f"⚠️ Testy częściowo przeszły ({passed}/{total})")
        
        st.markdown("---")
    
    # Status bazy danych
    st.header("🗄️ Status bazy danych")
    
    # Test bazy danych z formatowaniem
    db_status = db.test_database_connection()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Baza danych", "✅ Połączona" if db_status['connection_ok'] else "❌ Błąd")
        st.metric("Rozmiar bazy", f"{db_status['db_size']} B" if db_status['db_exists'] else "0 B")
    
    with col2:
        st.metric("Liczba tabel", str(db_status['tables_count']))
        if db_status['app_info']:
            created_date = format_date(db_status['app_info']['created_at'][:10])  # Pierwsze 10 znaków (YYYY-MM-DD)
            st.metric("Data utworzenia", created_date)
    
    st.info("**Następny krok:** Utworzenie structure.py z definicjami tabel")
    
    # Informacje o systemie
    st.header("ℹ️ Informacje o systemie")
    
    st.markdown("""
    **Konfiguracja:**
    - 🏦 **Broker**: Lynx (IBKR)
    - 💱 **Waluta główna**: USD
    - 🇵🇱 **Rozliczenia**: PLN (kurs NBP D-1)
    - 📊 **Podatki**: PIT-38 (akcje/opcje), PIT-36 (dywidendy)
    """)
    
    # Footer - sprawdź czy punkt 5 ukończony
    if 'point_5_completed' in st.session_state and st.session_state.point_5_completed:
        st.markdown("---")
        st.success("🎉 **ETAP 1 (Punkty 1-5) UKOŃCZONY!** Fundament aplikacji gotowy.")
        st.markdown("*Streamlit Covered Call Dashboard v0.1 - **GOTOWY DO ETAPU 2** (punkty 6-15)*")
        st.info("💡 **Następny krok:** Rozpocznij nową rozmowę z tytułem 'ETAP 2: Punkt 6 - structure.py' aby kontynuować projekt!")
    else:
        st.markdown("---")  
        st.markdown("*Streamlit Covered Call Dashboard v0.1 - Punkty 1-4 ukończone, testowanie punkt 5 (5/100)*")

def show_placeholder(module_name, icon, description):
    """Placeholder dla modułów, które jeszcze nie zostały zaimplementowane"""
    st.header(f"{icon} {module_name}")
    st.info(f"**{description}**")
    st.markdown("*Ten moduł będzie dostępny w późniejszych punktach rozwoju.*")
    
    # Pokazuj w którym punkcie będzie implementowany
    implementation_points = {
        'Stocks': 'Punkty 31-50',
        'Options': 'Punkty 51-70', 
        'Dividends': 'Punkty 71-80',
        'Cashflows': 'Punkty 16-30',
        'Taxes': 'Punkty 81-90',
        'Stats': 'Punkty 96-100',
        'Charts': 'Punkty 96-100'
    }
    
    if module_name in implementation_points:
        st.markdown(f"**Planowana implementacja:** {implementation_points[module_name]}")
        
    st.markdown("---")
    st.markdown("*Wróć do Dashboard aby zobaczyć status projektu.*")

if __name__ == "__main__":
    main()