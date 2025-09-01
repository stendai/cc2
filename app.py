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
    
    # 🎨 ŁADOWANIE NIESTANDARDOWEGO CSS
    load_css('static/style.css')
    
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
        
        # Menu items z kluczami - PUNKT 68: DODANO Dev_Tools
        menu_items = {
            'Dashboard': '🏠 Dashboard',
            'Stocks': '📊 Stocks',
            'Options': '🎯 Options', 
            'CC_Chains': '🔗 CC Chains', 
            'Dividends': '💰 Dividends',
            'Cashflows': '💸 Cashflows',
            'Taxes': '📋 Taxes', 
            'Stats': '📈 Stats',
            'Charts': '📊 Charts',
            'NBP_Test': '🏦 NBP Test',
            'Dev_Tools': '🛠️ Dev Tools'
        }
        
        st.markdown("### Moduły:")
        for key, label in menu_items.items():
            if st.button(label, use_container_width=True):
                st.session_state.current_page = key
        
        # Status projektu w sidebar - PUNKT 68: AKTUALIZACJA
        st.markdown("---")
        st.markdown("### 📊 Status projektu")
        st.markdown("**PUNKT 68 UKOŃCZONY** ✅")  # ZMIENIONO z 61 na 68
        st.markdown("Punkty 1-68 (68/100)")  # ZMIENIONO z 61 na 68
        st.markdown("*Dev Tools: Moduł deweloperski gotowy!*")  # ZMIENIONO opis

        # Progress bar - PUNKT 68: AKTUALIZACJA
        progress = 68 / 100  # ZMIENIONO z 61 na 68
        st.progress(progress)
        st.caption("68% projektu ukończone")  # ZMIENIONO z 61% na 68%
    
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
        try:
            from modules.options import show_options
            show_options()
        except ImportError:
            st.error("❌ Nie można zaimportować modułu options")

    elif st.session_state.current_page == 'CC_Chains':
        try:
            from modules.cc_chains import show_cc_chains
            show_cc_chains()
        except ImportError:
            st.error("❌ Nie można zaimportować modułu cc_chains")        
            
    elif st.session_state.current_page == 'Dividends':
        show_placeholder('Dividends', '💰', 'Dywidendy - ETAP 5')
    elif st.session_state.current_page == 'Cashflows':
        try:
            from modules.cashflows import show_cashflows
            show_cashflows()
        except ImportError:
            st.error("❌ Nie można zaimportować modułu cashflows")
    elif st.session_state.current_page == 'Taxes':
        show_placeholder('Taxes', '📋', 'Rozliczenia podatkowe - ETAP 6')
    elif st.session_state.current_page == 'Stats':
        show_placeholder('Stats', '📈', 'Statystyki i analizy - ETAP 7')
    elif st.session_state.current_page == 'Charts':
        show_placeholder('Charts', '📊', 'Wykresy i wizualizacje - ETAP 7')
    # PUNKT 68: DODANO ROUTING DO DEV TOOLS
    elif st.session_state.current_page == 'Dev_Tools':
        try:
            from modules.dev_tools import show_dev_tools
            show_dev_tools()
        except ImportError:
            st.error("❌ Nie można zaimportować modułu dev_tools")
            st.info("💡 Upewnij się, że plik modules/dev_tools.py istnieje")

def show_nbp_test():
    """Strona testowania NBP API - pełna funkcjonalność"""
    st.header("🏦 NBP API Client - Kompletny")
    st.markdown("*Pełny system kursów NBP z cache, seed data i obsługą świąt*")
    
    # Użyj UI z modułu nbp_api_client
    nbp_api_client.show_nbp_test_ui()

def show_dashboard():
    """Główna strona dashboard - PUNKT 68: FINALNE CLEANUP UI"""
    st.header("🏠 Dashboard - Portfolio Overview")
    
    # Auto-seed kursów NBP przy każdym wejściu na dashboard
    try:
        if nbp_api_client.auto_seed_on_startup():
            st.info("💡 Automatycznie uzupełniono brakujące kursy NBP")
    except Exception as e:
        st.warning(f"⚠️ Auto-seed nie powiódł się: {e}")
    
    # Status portfela
    st.markdown("### 📊 Status portfela")
    
    # Progress bar - PUNKT 68: AKTUALIZACJA
    progress = 68 / 100  # ZMIENIONO z 61 na 68
    st.progress(progress)
    st.caption("68% funkcjonalności dostępne")  # ZMIENIONO opis
    
    # Statystyki systemu - wersja uproszczona
    st.markdown("### 📈 Statystyki")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        try:
            cashflow_stats = db.get_cashflow_stats()
            st.metric("💰 Saldo USD", f"${cashflow_stats['total_usd']:.2f}")
        except:
            st.metric("💰 Saldo USD", "$0.00")
    
    with col2:
        try:
            lots_stats = db.get_lots_stats()
            st.metric("📦 Akcje", f"{lots_stats['open_shares']}")
        except:
            st.metric("📦 Akcje", "0")
    
    with col3:
        try:
            # Test czy moduł Options działa
            test_cc = db.check_cc_restrictions_before_sell("TEST", 1)
            cc_status = "✅ Działają" if 'can_sell' in test_cc else "❌ Błąd"
            st.metric("🎯 Options CC", cc_status)
        except:
            st.metric("🎯 Options CC", "❌ Błąd")
    
    # Informacje o systemie
    st.markdown("### ℹ️ Informacje")
    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown("""
        **Broker:** Lynx (IBKR)  
        **Waluta:** USD  
        **Rozliczenia:** PLN (NBP D-1)  
        **Podatki:** PIT-38, PIT-36
        """)
    
    with col_info2:
        st.markdown("""
        **Zakończone moduły:**  
        ✅ Cashflows  
        ✅ Stocks (FIFO)  
        ✅ Options (CC)  
        ✅ Dev Tools  
        ⏳ Dividends, Taxes, Charts
        """)
    
    # Status ETAPU 4 - PUNKT 68: AKTUALIZACJA
    st.markdown("---")
    st.info("🎯 **ETAP 4 w finalizacji** - zostały tylko punkty 69-70 do ukończenia 70% projektu!")
    st.success("✅ **PUNKT 68 UKOŃCZONY** - Moduł Dev Tools dodany do systemu!")

def show_placeholder(module_name, icon, description):
    """Placeholder dla modułów, które będą implementowane w kolejnych etapach"""
    st.header(f"{icon} {module_name}")
    st.info(f"**{description}**")
    st.markdown("*Ten moduł będzie dostępny w kolejnych etapach rozwoju.*")
    
    # Pokazuj w którym etapie będzie implementowany
    implementation_points = {
        'Options': 'ETAP 4: Punkty 51-70 (NASTĘPNY!)', 
        'Dividends': 'ETAP 5: Punkty 71-80',
        'Taxes': 'ETAP 6: Punkty 81-90',
        'Stats': 'ETAP 7: Punkty 91-100',
        'Charts': 'ETAP 7: Punkty 91-100'
    }
    
    if module_name in implementation_points:
        st.markdown(f"**Planowana implementacja:** {implementation_points[module_name]}")
    
    # Status obecnego etapu
    st.markdown("---")
    st.success("✅ **ETAP 3 UKOŃCZONY** - Stocks kompletny z wszystkimi funkcjami!")
    
    if module_name == 'Options':
        st.info("🚀 **GOTOWE DO ROZPOCZĘCIA** - Wszystkie wymagane fundamenty są ukończone")
        
        # Sprawdzenie gotowości do ETAPU 4
        st.markdown("### 🎯 Gotowość do ETAPU 4 - Options")
        
        try:
            lots_stats = db.get_lots_stats()
            
            readiness_checks = {
                "📦 LOT-y w portfelu": lots_stats['total_lots'] > 0,
                "📊 Akcje dostępne": lots_stats['open_shares'] > 0,
                "🏦 System kursów NBP": True,  # Wiemy że działa
                "💸 Cashflows": True,  # Wiemy że działa
                "🔧 Tabela options_cc": True   # Stworzona w structure.py
            }
            
            st.markdown("**✅ Sprawdzenie wymagań:**")
            all_ready = True
            for check, status in readiness_checks.items():
                icon = "✅" if status else "❌"
                st.write(f"{icon} {check}")
                if not status:
                    all_ready = False
            
            if all_ready:
                st.success("🚀 **SYSTEM GOTOWY DO ETAPU 4!** Można rozpocząć implementację Options.")
            else:
                st.warning("⚠️ Niektóre wymagania nie są spełnione.")
                
        except Exception as e:
            st.warning(f"⚠️ Nie można sprawdzić gotowości: {e}")
    else:
        st.info("⏳ **OCZEKUJE** - Będzie dostępny po ukończeniu wcześniejszych etapów")

def load_css(file_name):
    """Ładuje niestandardowy CSS z pliku"""
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"⚠️ Plik CSS {file_name} nie został znaleziony")

if __name__ == "__main__":
    main()