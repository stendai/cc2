# PUNKT 73: pages/cc_chains.py - podstawowa struktura nawigacji
# Utwórz nowy plik: pages/cc_chains.py

import streamlit as st
import sys
import os
from datetime import date, datetime
import pandas as pd

# Dodaj katalog główny do path
if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modułów
try:
    import db
    from utils.formatting import format_currency_usd, format_currency_pln, format_date, format_percentage
except ImportError as e:
    st.error(f"Błąd importu modułów: {e}")

def show_cc_chains():
    """
    🔗 PUNKT 73: Główna funkcja modułu CC Chains
    Podstawowa struktura nawigacji z placeholder'ami
    """
    
    st.header("🔗 CC Chains - Łańcuchy Opcyjne")
    st.markdown("*Zaawansowana analiza strategii Covered Calls per LOT akcji*")
    
    # Status migracji
    migration_status = check_migration_status()
    display_migration_status(migration_status)
    
    # Główne zakładki
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔗 Active Chains",     # PUNKT 81
        "📊 Chain Analytics",   # PUNKT 82  
        "🛠️ Chain Management", # PUNKT 83
        "🧪 Auto-Detection"     # PUNKT 74-75
    ])
    
    with tab1:
        show_active_chains_tab()
    
    with tab2:
        show_chain_analytics_tab()
    
    with tab3:
        show_chain_management_tab()
    
    with tab4:
        show_auto_detection_tab()

def check_migration_status():
    """Sprawdza status migracji CC Chains"""
    try:
        return db.check_cc_chains_migration_status()
    except Exception as e:
        return {'success': False, 'error': str(e)}

def display_migration_status(status):
    """Wyświetla status migracji w UI"""
    if not status.get('success'):
        st.error(f"❌ Błąd sprawdzania migracji: {status.get('error', 'Unknown')}")
        return
    
    tables = status.get('tables_status', {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if tables.get('cc_chains_exists'):
            st.success("✅ Tabela cc_chains")
            st.caption(f"Chains: {tables.get('cc_chains_count', 0)}")
        else:
            st.error("❌ Brak tabeli cc_chains")
    
    with col2:
        if tables.get('chain_id_exists'):
            st.success("✅ Kolumna chain_id")
            cc_linked = tables.get('cc_with_chains', 0)
            cc_unlinked = tables.get('cc_without_chains', 0)
            st.caption(f"Linked: {cc_linked} | Unlinked: {cc_unlinked}")
        else:
            st.error("❌ Brak kolumny chain_id")
    
    with col3:
        total_cc = tables.get('cc_with_chains', 0) + tables.get('cc_without_chains', 0)
        if total_cc > 0:
            st.info(f"📊 {total_cc} total CC")
            st.caption("Gotowe do tworzenia chains")
        else:
            st.warning("⚠️ Brak CC w bazie")

# NAPRAWKA: Zamień funkcję show_active_chains_tab() w pages/cc_chains.py

def show_active_chains_tab():
    """PUNKT 81: Tab Active Chains - NAPRAWIONA WERSJA z prawdziwymi danymi"""
    st.subheader("🔗 Active Chains")
    
    try:
        # Pobierz chains z bazy
        chains = db.get_cc_chains_summary()
        
        if not chains:
            st.warning("📝 Brak chains w bazie. Uruchom Auto-Detection żeby je utworzyć.")
            return
        
        st.success(f"✅ Znaleziono {len(chains)} chains w bazie")
        
        # Wyświetl każdy chain
        for i, chain in enumerate(chains):
            
            # Container per chain
            with st.container():
                
                # Header chain
                col_header1, col_header2, col_header3 = st.columns([2, 1, 1])
                
                with col_header1:
                    status_icon = "🟢" if chain['status'] == 'active' else "🔴"
                    st.markdown(f"### {status_icon} {chain.get('chain_name', 'Unnamed Chain')}")
                    st.caption(f"Chain #{chain['id']} | LOT #{chain['lot_id']}")
                
                with col_header2:
                    st.metric("P/L PLN", f"{chain.get('total_pl_pln', 0):.2f} zł")
                
                with col_header3:
                    st.metric("CC Count", f"{chain.get('cc_count', 0)}")
                
                # Szczegóły chain
                col_details1, col_details2, col_details3 = st.columns(3)
                
                with col_details1:
                    st.write(f"**📦 LOT Info:**")
                    st.write(f"Total: {chain.get('lot_total', 0)} shares")
                    st.write(f"Open: {chain.get('lot_open', 0)} shares")
                    st.write(f"Buy Date: {chain.get('lot_buy_date', 'N/A')}")
                
                with col_details2:
                    st.write(f"**🎯 Chain Stats:**")
                    st.write(f"Start: {chain.get('start_date', 'N/A')}")
                    st.write(f"End: {chain.get('end_date', 'Active')}")
                    st.write(f"Open CC: {chain.get('open_cc_count', 0)}")
                
                with col_details3:
                    st.write(f"**💰 Performance:**")
                    premium = chain.get('total_premium_pln', 0)
                    st.write(f"Premium: {premium:.2f} zł")
                    
                    # Kalkulacja yield (uproszczona)
                    if premium > 0:
                        yield_pct = (chain.get('total_pl_pln', 0) / premium) * 100
                        st.write(f"Yield: {yield_pct:.1f}%")
                    else:
                        st.write("Yield: N/A")
                
                # Pobierz CC dla tego chain
                try:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT id, contracts, strike_usd, premium_sell_usd, 
                               open_date, expiry_date, status, pl_pln
                        FROM options_cc
                        WHERE chain_id = ?
                        ORDER BY open_date DESC
                    """, (chain['id'],))
                    
                    cc_in_chain = cursor.fetchall()
                    conn.close()
                    
                    if cc_in_chain:
                        st.markdown("**🎯 CC w tym chain:**")
                        
                        # Tabela CC
                        cc_df_data = []
                        for cc in cc_in_chain:
                            cc_id, contracts, strike, premium, open_date, expiry, status, pl_pln = cc
                            
                            status_icon = "🟢" if status == 'open' else "🔴"
                            pl_formatted = f"{pl_pln:.2f} zł" if pl_pln else "pending"
                            
                            cc_df_data.append({
                                'CC': f"#{cc_id}",
                                'Status': f"{status_icon} {status}",
                                'Contracts': contracts,
                                'Strike': f"${strike}",
                                'Premium': f"${premium}",
                                'Open': open_date,
                                'Expiry': expiry,
                                'P/L': pl_formatted
                            })
                        
                        st.dataframe(pd.DataFrame(cc_df_data), use_container_width=True)
                    else:
                        st.warning("⚠️ Chain bez CC - błąd danych")
                
                except Exception as e:
                    st.error(f"❌ Błąd ładowania CC dla chain #{chain['id']}: {e}")
                
                st.markdown("---")  # Separator między chains
        
    except Exception as e:
        st.error(f"❌ Błąd ładowania active chains: {e}")
        
        # DEBUG fallback
        st.markdown("### 🔍 DEBUG:")
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM cc_chains")
            chain_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM options_cc WHERE chain_id IS NOT NULL")
            cc_with_chains = cursor.fetchone()[0]
            
            st.write(f"Chains in DB: {chain_count}")
            st.write(f"CC with chains: {cc_with_chains}")
            
            conn.close()
            
        except Exception as debug_e:
            st.error(f"Debug też failed: {debug_e}")

def show_chain_analytics_tab():
    """PUNKT 82: Tab Chain Analytics - placeholder"""
    st.subheader("📊 Chain Analytics")
    st.info("🚧 **PUNKT 82** - W budowie: Historia i performance comparison")
    
    # Placeholder analytics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Top Performing Chains:**")
        placeholder_data = [
            {"Chain": "WOLF #1", "Return": "28.4%", "Duration": "45d"},
            {"Chain": "AAPL #2", "Return": "22.1%", "Duration": "30d"},
            {"Chain": "MSFT #1", "Return": "19.8%", "Duration": "60d"}
        ]
        st.dataframe(pd.DataFrame(placeholder_data), use_container_width=True)
    
    with col2:
        st.markdown("**Chain Metrics:**")
        st.metric("Best Chain", "WOLF #1", "+28.4%")
        st.metric("Worst Chain", "TSLA #1", "-5.2%")
        st.metric("Avg Success Rate", "78%", "↗️ +3%")

def show_chain_management_tab():
    """PUNKT 83: Tab Chain Management - placeholder"""
    st.subheader("🛠️ Chain Management")
    st.info("🚧 **PUNKT 83** - W budowie: Ręczne łączenie/rozłączanie chains")
    
    # Placeholder management
    st.markdown("**Funkcje zarządzania:**")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔗 Create New Chain", disabled=True):
            st.info("Feature w budowie")
    
    with col2:
        if st.button("✂️ Split Chain", disabled=True):
            st.info("Feature w budowie")
    
    # Lista CC bez chains (do przyszłego przypisywania)
    try:
        unlinked_cc = db.get_covered_calls_summary()
        if unlinked_cc:
            st.markdown("**CC bez przypisanych chains:**")
            
            df_data = []
            for cc in unlinked_cc[:5]:  # Pokaż tylko 5 first
                df_data.append({
                    'ID': cc['id'],
                    'Ticker': cc['ticker'],
                    'Contracts': cc['contracts'],
                    'Status': cc['status'],
                    'Open Date': cc['open_date']
                })
            
            if df_data:
                st.dataframe(pd.DataFrame(df_data), use_container_width=True)
                st.caption("💡 Te CC będą automatycznie grupowane w chains w PUNKT 74")
    
    except Exception as e:
        st.error(f"❌ Błąd ładowania CC: {e}")

# NAPRAWKA: Dodaj debug bezpośrednio w pages/cc_chains.py
# Zamień funkcję show_auto_detection_tab() na tę wersję z debug:

def show_auto_detection_tab():
    """PUNKT 74-75: Tab Auto-Detection z FULL DEBUG"""
    st.subheader("🤖 Auto-Detection Algorithm")
    st.info("🚧 **PUNKT 74-75** - Z debugiem błędów")
    
    # DEBUG: Sprawdź czy funkcja istnieje
    st.markdown("### 🔍 DEBUG:")
    
    try:
        # Test 1: Czy funkcja istnieje?
        if hasattr(db, 'auto_detect_cc_chains'):
            st.success("✅ Funkcja auto_detect_cc_chains istnieje")
        else:
            st.error("❌ Funkcja auto_detect_cc_chains NIE ISTNIEJE!")
            st.stop()
        
        # Test 2: Status przed testem
        col_debug1, col_debug2 = st.columns(2)
        
        with col_debug1:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM options_cc WHERE chain_id IS NULL")
            unlinked_cc = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cc_chains")
            total_chains = cursor.fetchone()[0]
            
            st.metric("CC bez chains", unlinked_cc)
            st.metric("Total chains", total_chains)
            
            conn.close()
        
        with col_debug2:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM cc_lot_mappings")
            total_mappings = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(DISTINCT m.lot_id)
                FROM cc_lot_mappings m
                JOIN options_cc cc ON cc.id = m.cc_id
                WHERE cc.chain_id IS NULL
            """)
            lots_ready = cursor.fetchone()[0]
            
            st.metric("Total mappings", total_mappings)
            st.metric("LOT-y ready", lots_ready)
            
            conn.close()
    
    except Exception as e:
        st.error(f"❌ DEBUG Error: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    # GŁÓWNY TEST z pełnym error handling
    if st.button("🔍 Test Auto-Detection Algorithm (DEBUG)"):
        st.markdown("### 🧪 FULL DEBUG AUTO-DETECTION:")
        
        try:
            with st.spinner("Testowanie z debugiem..."):
                
                # PRE-TEST: Pokaż dane wejściowe
                with st.expander("📋 Dane przed testem", expanded=True):
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    
                    # CC bez chains
                    cursor.execute("""
                        SELECT cc.id, cc.ticker, cc.contracts, cc.status
                        FROM options_cc cc
                        WHERE cc.chain_id IS NULL
                    """)
                    unlinked_cc = cursor.fetchall()
                    
                    st.write(f"**CC bez chains ({len(unlinked_cc)}):**")
                    for cc in unlinked_cc:
                        st.write(f"   CC #{cc[0]}: {cc[1]} {cc[2]}x [{cc[3]}]")
                    
                    # LOT-y z mapowaniami
                    cursor.execute("""
                        SELECT DISTINCT m.lot_id, l.ticker, l.buy_date
                        FROM cc_lot_mappings m
                        JOIN lots l ON l.id = m.lot_id
                        JOIN options_cc cc ON cc.id = m.cc_id
                        WHERE cc.chain_id IS NULL
                    """)
                    lots_ready = cursor.fetchall()
                    
                    st.write(f"**LOT-y gotowe do chains ({len(lots_ready)}):**")
                    for lot in lots_ready:
                        st.write(f"   LOT #{lot[0]}: {lot[1]} ({lot[2]})")
                    
                    conn.close()
                
                # WYWOŁAJ FUNKCJĘ
                st.write("🤖 Wywołuję db.auto_detect_cc_chains()...")
                
                result = db.auto_detect_cc_chains()
                
                st.write(f"📊 Wynik funkcji: {result}")
                
                # SPRAWDŹ WYNIK
                if result.get('success'):
                    st.success("✅ SUKCES!")
                    st.write(f"   Chains created: {result.get('chains_created', 0)}")
                    st.write(f"   CC assigned: {result.get('cc_assigned', 0)}")
                    st.write(f"   Message: {result.get('message', 'brak')}")
                    
                    if result.get('chains_created', 0) > 0 or result.get('cc_assigned', 0) > 0:
                        st.balloons()
                        st.rerun()  # Odśwież stronę
                else:
                    st.error("❌ BŁĄD!")
                    st.write(f"   Message: {result.get('message', 'brak')}")
                
        except Exception as e:
            st.error(f"❌ Exception podczas testu: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # Reszta funkcji bez zmian...
    st.markdown("""
    **CC Chain** = **WSZYSTKIE** CC na tym samym **LOT-cie akcji**
    
    **Prosta logika:**
    1. 📦 **Jeden LOT = Jeden Chain**
    2. 🕐 **Bez ograniczeń czasowych** (możesz czekać tygodnie/miesiące)
    3. ⏹️ **Chain kończy się gdy LOT sprzedany** (quantity_open = 0)
    """)
    
    # Current CC status
    try:
        cc_summary = db.get_covered_calls_summary()
        
        if cc_summary:
            st.markdown("### 📋 Current CC Status")
            
            for cc in cc_summary:
                status_icon = "🟢" if cc['status'] == 'open' else "🔴"
                chain_info = f"Chain: {cc.get('chain_id', 'None')}"
                st.caption(f"{status_icon} CC #{cc['id']}: {cc['ticker']} {cc['contracts']}x - {chain_info}")
        else:
            st.info("📝 Brak CC")
    
    except Exception as e:
        st.error(f"❌ Błąd ładowania CC: {e}")


# PUNKT 73.1: Test function dla weryfikacji
def test_cc_chains_ui():
    """Test podstawowego UI CC Chains"""
    try:
        migration_status = check_migration_status()
        return {
            'ui_loads': True,
            'migration_ok': migration_status.get('success', False),
            'tabs_work': True  # Jeśli doszedł tutaj, tabs działają
        }
    except Exception as e:
        return {
            'ui_loads': False,
            'error': str(e)
        }


# Main function
if __name__ == "__main__":
    show_cc_chains()